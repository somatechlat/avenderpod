import secrets
import hmac
import os
import requests
import re
from django.utils import timezone
from datetime import timedelta
from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from .models import (
    Tenant,
    Plan,
    CatalogItem,
    TenantConfig,
    InteractionRecord,
    Subscription,
    TenantPlanHistory,
    TenantUsage,
    VaultRecord,
    GlobalConfig,
)
from .schemas import (
    CatalogItemIn,
    CatalogItemOut,
    ChallengeIn,
    ConfigIn,
    InteractionRecordOut,
    PendingChallengeOut,
    PlanIn,
    PlanOut,
    PlanPatch,
    TenantIn,
    TenantOut,
    TenantStatusOut,
    TenantUsageIn,
    TenantUsageOut,
    VaultRecordOut,
)
from .security import (
    SessionOrServiceAuth,
    audit_event,
    check_sysadmin,
    check_tenant_access,
    get_service_credential,
    has_platform_perm,
    is_service_request,
)
from .vultr_service import deploy_tenant_pod, suspend_tenant_pod, reactivate_tenant_pod
from .vault_service import provision_tenant_secrets, build_tenant_bootstrap_env
from common.messages import get_message


router = Router(auth=SessionOrServiceAuth())

PHONE_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


# --- SYSTEM ENDPOINTS (SysAdmin Only) ---


@router.get("/plans", response=list[PlanOut])
def list_plans(request):
    if not has_platform_perm(request, "tenants.view_plan"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return Plan.objects.order_by("-is_active", "price_monthly", "name")


@router.post("/plans", response=PlanOut)
def create_plan(request, payload: PlanIn):
    if not has_platform_perm(request, "tenants.add_plan"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    plan = Plan.objects.create(**payload.dict())
    audit_event(request, "plan.created", target_type="Plan", target_id=str(plan.id))
    return plan


@router.patch("/plans/{plan_id}", response=PlanOut)
def update_plan(request, plan_id: str, payload: PlanPatch):
    if not has_platform_perm(request, "tenants.change_plan"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    plan = get_object_or_404(Plan, id=plan_id)
    changes = payload.dict(exclude_unset=True)
    for key, value in changes.items():
        setattr(plan, key, value)
    plan.save()
    audit_event(
        request,
        "plan.updated",
        target_type="Plan",
        target_id=str(plan.id),
        metadata={"fields": sorted(changes.keys())},
    )
    return plan


@router.get("/vault", response=list[VaultRecordOut])
def list_vault_records(request):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    records = (
        VaultRecord.objects.select_related("tenant").all().order_by("-created_at")[:100]
    )
    return [
        {
            "id": str(r.id),
            "tenant_name": r.tenant.name,
            "vault_path": r.vault_path,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/interactions", response=list[InteractionRecordOut])
def list_interactions(request):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    records = InteractionRecord.objects.select_related("tenant").order_by(
        "-created_at"
    )[:100]
    return [
        {
            "id": str(r.id),
            "tenant_name": r.tenant.name,
            "customer_wa_id": r.customer_wa_id,
            "archetype": r.archetype,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


# --- TENANT LIFECYCLE (SysAdmin Only) ---


@router.post("/tenants", response=TenantOut)
def create_tenant(request, payload: TenantIn):
    if not has_platform_perm(request, "tenants.add_tenant"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    plan = (
        Plan.objects.filter(slug__iexact=payload.plan_name).first()
        or Plan.objects.filter(name__iexact=payload.plan_name).first()
    )
    if not plan:
        raise HttpError(400, "Active plan is required before tenant deployment.")
    if not plan.is_active:
        raise HttpError(400, "Selected plan is inactive.")

    business_name = payload.business_name.strip()
    owner_email = payload.owner_email.strip().lower()
    owner_full_name = payload.owner_full_name.strip()
    owner_phone = payload.owner_phone_e164.strip()
    if not business_name or not owner_full_name:
        raise HttpError(400, "Business name and owner name are required.")
    if not PHONE_E164_RE.match(owner_phone):
        raise HttpError(400, "Owner phone must be in E.164 format, e.g. +593979445965.")

    with transaction.atomic():
        owner_user, created = User.objects.get_or_create(
            username=owner_email,
            defaults={
                "email": owner_email,
                "first_name": owner_full_name[:150],
            },
        )
        if created:
            owner_user.set_unusable_password()
            owner_user.save(update_fields=["password"])
        elif not owner_user.email:
            owner_user.email = owner_email
            owner_user.save(update_fields=["email"])

        tenant = Tenant.objects.create(
            name=business_name,
            email=owner_email,
            owner_full_name=owner_full_name,
            owner_phone_e164=owner_phone,
            plan=plan,
            status="pending",
            owner=owner_user,
        )
        Subscription.objects.create(tenant=tenant, plan=plan, status="active")
        TenantPlanHistory.objects.create(
            tenant=tenant,
            old_plan=None,
            new_plan=plan,
            changed_by=request.user,
            reason="initial tenant provisioning",
        )

    try:
        tenant_secrets = provision_tenant_secrets(tenant)
        # Compute unique port BEFORE bootstrap so it can be passed to cloud-init
        existing_ports = set(
            Tenant.objects.exclude(id=tenant.id)
            .exclude(assigned_port__isnull=True)
            .values_list("assigned_port", flat=True)
        )
        assigned_port = 45001
        while assigned_port in existing_ports:
            assigned_port += 1
        tenant.assigned_port = assigned_port
        tenant.save()
        bootstrap_env = build_tenant_bootstrap_env(
            tenant, tenant_secrets, assigned_port
        )
        deploy_tenant_pod(tenant, bootstrap_env=bootstrap_env)
    except (EnvironmentError, RuntimeError, ValueError) as e:
        tenant.status = "pending"
        tenant.save()
        # Return 502 so the caller knows provisioning failed
        raise HttpError(502, f"Tenant provisioning failed: {str(e)}")

    audit_event(
        request,
        "tenant.created",
        tenant=tenant,
        target_type="Tenant",
        target_id=str(tenant.id),
        metadata={"plan": plan.slug or plan.name},
    )
    return tenant


@router.get("/tenants", response=list[TenantOut])
def list_tenants(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    if request.user.is_superuser:
        return Tenant.objects.all()
    # If not superuser, return only their tenants
    return Tenant.objects.filter(owner=request.user)


@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(request, tenant_id: str):
    if not has_platform_perm(request, "tenants.suspend_tenant"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = suspend_tenant_pod(tenant)
        audit_event(
            request, "tenant.suspended", tenant=tenant, target_id=str(tenant.id)
        )
        return {
            "ok": True,
            "message": get_message("SUCCESS_POD_SUSPENDED", name=tenant.name),
            "detail": result,
        }
    except (EnvironmentError, RuntimeError, ValueError) as e:
        # Do NOT update status on failure — prevents split-brain state
        return {
            "ok": False,
            "message": get_message("ERR_VULTR_API_FAILED", detail=str(e)),
        }


@router.post("/tenants/{tenant_id}/reactivate")
def reactivate_tenant(request, tenant_id: str):
    if not has_platform_perm(request, "tenants.reactivate_tenant"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = reactivate_tenant_pod(tenant)
        audit_event(
            request, "tenant.reactivated", tenant=tenant, target_id=str(tenant.id)
        )
        return {
            "ok": True,
            "message": get_message("SUCCESS_POD_REACTIVATED", name=tenant.name),
            "detail": result,
        }
    except (EnvironmentError, RuntimeError, ValueError) as e:
        return {
            "ok": False,
            "message": get_message("ERR_VULTR_API_FAILED", detail=str(e)),
        }


# --- TENANT DATA (SysAdmin or Tenant Owner) ---


@router.get("/tenants/{tenant_id}/catalog", response=list[CatalogItemOut])
def list_catalog(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return CatalogItem.objects.filter(tenant=tenant)


@router.post("/tenants/{tenant_id}/catalog", response=CatalogItemOut)
def create_catalog_item(request, tenant_id: str, payload: CatalogItemIn):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    item = CatalogItem.objects.create(
        tenant=tenant,
        name=payload.name,
        price=payload.price,
        description=payload.description,
        metadata=payload.metadata or {},
    )
    return item


@router.get("/tenants/{tenant_id}/config")
def get_tenant_config(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    configs = TenantConfig.objects.filter(tenant=tenant)
    return {c.key: c.value for c in configs}


@router.post("/tenants/{tenant_id}/config")
def set_tenant_config(request, tenant_id: str, payload: ConfigIn):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    config, created = TenantConfig.objects.update_or_create(
        tenant=tenant, key=payload.key, defaults={"value": payload.value}
    )
    return {
        "ok": True,
        "key": config.key,
        "value": config.value,
        "message": get_message("SUCCESS_CONFIG_SAVED"),
    }


@router.get("/tenants/{tenant_id}/usage", response=TenantUsageOut)
def get_tenant_usage(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    period_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    usage, _ = TenantUsage.objects.get_or_create(
        tenant=tenant,
        period_start=period_start,
        defaults={"last_reported_at": timezone.now()},
    )
    return {
        "tenant_id": str(tenant.id),
        "period_start": usage.period_start.isoformat(),
        "conversations_used": usage.conversations_used,
        "messages_used": usage.messages_used,
        "transcription_seconds_used": usage.transcription_seconds_used,
        "catalog_items_used": usage.catalog_items_used,
        "storage_bytes_used": usage.storage_bytes_used,
    }


@router.post("/tenants/{tenant_id}/usage/report", response=TenantUsageOut)
def report_tenant_usage(request, tenant_id: str, payload: TenantUsageIn):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    period_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    usage, _ = TenantUsage.objects.get_or_create(
        tenant=tenant, period_start=period_start
    )
    usage.conversations_used += max(payload.conversations_used, 0)
    usage.messages_used += max(payload.messages_used, 0)
    usage.transcription_seconds_used += max(payload.transcription_seconds_used, 0)
    usage.catalog_items_used += max(payload.catalog_items_used, 0)
    usage.storage_bytes_used += max(payload.storage_bytes_used, 0)
    usage.last_reported_at = timezone.now()
    usage.save()

    return {
        "tenant_id": str(tenant.id),
        "period_start": usage.period_start.isoformat(),
        "conversations_used": usage.conversations_used,
        "messages_used": usage.messages_used,
        "transcription_seconds_used": usage.transcription_seconds_used,
        "catalog_items_used": usage.catalog_items_used,
        "storage_bytes_used": usage.storage_bytes_used,
    }


# --- CREATOR OVERRIDE (GOD MODE) ENDPOINTS ---


@router.post("/auth/init-challenge")
def init_challenge(request, tenant_id: str):
    """
    Called by Agent Zero when the Creator trigger phrase is detected.
    Generates a random 4-digit PIN for the dashboard.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not (is_service_request(request) or check_tenant_access(request, tenant)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    pin = str(secrets.randbelow(9000) + 1000)
    tenant.creator_session_pin = pin
    tenant.pin_expires_at = timezone.now() + timedelta(minutes=5)
    tenant.save()
    return {"ok": True, "message": "Challenge initiated."}


@router.post("/auth/verify-challenge")
def verify_challenge(request, payload: ChallengeIn):
    """
    Validates the Creator Password and the Session PIN.
    """
    if not (is_service_request(request) or check_sysadmin(request)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    tenant = get_object_or_404(Tenant, id=payload.tenant_id)
    credential = get_service_credential(request)
    if credential and credential.tenant_id != tenant.id:
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    # 1. Verify Global Master Password
    master_pass_config = GlobalConfig.objects.filter(
        key="MASTER_CREATOR_PASSWORD"
    ).first()
    stored_password = str(master_pass_config.value) if master_pass_config else ""
    is_valid_password = False
    if stored_password.startswith(("pbkdf2_", "argon2", "bcrypt")):
        is_valid_password = check_password(str(payload.password), stored_password)
    elif stored_password:
        # Backward-compatible read path. New deployments should store a hash or Vault ref.
        is_valid_password = hmac.compare_digest(stored_password, str(payload.password))
    if not is_valid_password:
        return {"ok": False, "message": "Invalid Master Password."}

    # 2. Verify Session PIN
    if not tenant.creator_session_pin or tenant.creator_session_pin != payload.pin:
        return {"ok": False, "message": "Invalid or expired Session PIN."}

    if not tenant.pin_expires_at or tenant.pin_expires_at < timezone.now():
        return {"ok": False, "message": "Session PIN has expired."}

    # Success - clear the PIN
    tenant.creator_session_pin = None
    tenant.pin_expires_at = None
    tenant.save()
    audit_event(
        request, "creator_override.verified", tenant=tenant, target_id=str(tenant.id)
    )

    return {"ok": True, "message": "Creator access granted."}


@router.get("/tenants/{tenant_id}/status", response=TenantStatusOut)
def get_tenant_status(request, tenant_id: str):
    """
    Poll the tenant's Agent Zero container health endpoint and report status.
    """
    if not (is_service_request(request) or check_sysadmin(request)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    tenant = get_object_or_404(Tenant, id=tenant_id)
    credential = get_service_credential(request)
    if credential and credential.tenant_id != tenant.id:
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    # Defaults
    container_status = "unknown"
    last_heartbeat = None
    whisper_ok = False

    # Attempt to reach the tenant VM's Agent Zero health endpoint
    if tenant.assigned_port and tenant.status in ("active", "suspended"):
        # In VPC-only mode we query the Vultr API for the instance's
        # PRIVATE IP (within the VPC), not the public IP.
        try:
            from .vultr_service import VULTR_API_BASE, _vultr_headers

            vultr_resp = requests.get(
                f"{VULTR_API_BASE}/instances/{tenant.vultr_instance_id}",
                headers=_vultr_headers(),
                timeout=10,
            )
            if vultr_resp.status_code == 200:
                instance_data = vultr_resp.json().get("instance", {})
                # Use VPC private IP for health checks (not public IP)
                vpc_ip = ""
                vpcs = instance_data.get("vpcs", [])
                if vpcs:
                    vpc_ip = vpcs[0].get("ip_address", "")

                target_ip = vpc_ip or instance_data.get("main_ip", "")
                if target_ip:
                    health_url = f"http://{target_ip}:{tenant.assigned_port}"
                    try:
                        health_resp = requests.get(health_url, timeout=10)
                        if health_resp.status_code == 200:
                            container_status = "healthy"
                            last_heartbeat = timezone.now().isoformat()
                        else:
                            container_status = "unhealthy"
                    except requests.RequestException:
                        container_status = "unreachable"

                    # Whisper runs inside each tenant agent. A healthy tenant
                    # container means the isolated local STT runtime is reachable
                    # to the agent process; no central proxy is checked here.
                    whisper_ok = container_status == "healthy"
        except (requests.RequestException, ValueError, KeyError):
            container_status = "error"

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "status": tenant.status,
        "container_status": container_status,
        "last_heartbeat": last_heartbeat,
        "whisper_connection_ok": whisper_ok,
        "assigned_port": tenant.assigned_port,
    }


@router.get("/auth/pending-challenges", response=list[PendingChallengeOut])
def list_pending_challenges(request):
    """
    Returns active challenges for the Dashboard UI to display.
    """
    if not (is_service_request(request) or check_sysadmin(request)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    active_tenants = Tenant.objects.filter(
        creator_session_pin__isnull=False, pin_expires_at__gt=timezone.now()
    )
    return [
        {
            "tenant_id": str(t.id),
            "tenant_name": t.name,
            "pin": t.creator_session_pin,
            "expires_at": t.pin_expires_at.isoformat(),
        }
        for t in active_tenants
    ]
