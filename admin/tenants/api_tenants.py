import re
import requests
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from ninja import Router
from ninja.errors import HttpError

from .models import Tenant, Plan, Subscription, TenantPlanHistory, CatalogItem, TenantConfig, TenantUsage, InteractionRecord
from .schemas import TenantOut, TenantIn, CatalogItemOut, CatalogItemIn, ConfigIn, TenantUsageOut, TenantUsageIn, InteractionRecordOut, TenantStatusOut
from .security import check_sysadmin, check_tenant_access, has_platform_perm, is_service_request, get_service_credential, audit_event
from .deployment_router import deploy_tenant_pod, suspend_tenant_pod, reactivate_tenant_pod, get_container_status as _get_container_status, get_container_logs as _get_container_logs
from .vault_service import provision_tenant_secrets, build_tenant_bootstrap_env
from common.messages import get_message

router = Router()
PHONE_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

@router.post("/tenants", response=TenantOut)
def create_tenant(request, payload: TenantIn):
    if not has_platform_perm(request, "tenants.add_tenant"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    plan = Plan.objects.filter(slug__iexact=payload.plan_name).first() or Plan.objects.filter(name__iexact=payload.plan_name).first()
    if not plan:
        raise HttpError(400, get_message("ERR_PLAN_REQUIRED"))
    if not plan.is_active:
        raise HttpError(400, get_message("ERR_PLAN_INACTIVE"))

    business_name = payload.business_name.strip()
    owner_email = payload.owner_email.strip().lower()
    owner_full_name = payload.owner_full_name.strip()
    owner_phone = payload.owner_phone_e164.strip()
    if not business_name or not owner_full_name:
        raise HttpError(400, get_message("ERR_MISSING_TENANT_INFO"))
    if not PHONE_E164_RE.match(owner_phone):
        raise HttpError(400, get_message("ERR_INVALID_PHONE"))

    with transaction.atomic():
        owner_user, created = User.objects.get_or_create(
            username=owner_email,
            defaults={"email": owner_email, "first_name": owner_full_name[:150]},
        )
        if created:
            owner_user.set_unusable_password()
            owner_user.save(update_fields=["password"])
        elif not owner_user.email:
            owner_user.email = owner_email
            owner_user.save(update_fields=["email"])

        tenant = Tenant.objects.create(
            name=business_name, email=owner_email, owner_full_name=owner_full_name,
            owner_phone_e164=owner_phone, plan=plan, status="pending", owner=owner_user,
        )
        Subscription.objects.create(tenant=tenant, plan=plan, status="active")
        TenantPlanHistory.objects.create(
            tenant=tenant, old_plan=None, new_plan=plan, changed_by=request.user, reason="initial tenant provisioning",
        )

    try:
        tenant_secrets = provision_tenant_secrets(tenant)
        with transaction.atomic():
            existing_ports = set(
                Tenant.objects.select_for_update().exclude(id=tenant.id).exclude(assigned_port__isnull=True).values_list("assigned_port", flat=True)
            )
            assigned_port = 45001
            while assigned_port in existing_ports:
                assigned_port += 1
            tenant.assigned_port = assigned_port
            tenant.save(update_fields=["assigned_port"])
        bootstrap_env = build_tenant_bootstrap_env(tenant, tenant_secrets, assigned_port)
        deploy_tenant_pod(tenant, bootstrap_env=bootstrap_env)
    except (EnvironmentError, RuntimeError, ValueError) as e:
        tenant.status = "pending"
        tenant.save()
        raise HttpError(502, get_message("ERR_PROVISIONING_FAILED", detail=str(e)))

    audit_event(request, "tenant.created", tenant=tenant, target_type="Tenant", target_id=str(tenant.id), metadata={"plan": plan.slug or plan.name})
    return tenant

@router.get("/tenants", response=list[TenantOut])
def list_tenants(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    if request.user.is_superuser:
        return Tenant.objects.all()
    return Tenant.objects.filter(owner=request.user)

@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(request, tenant_id: str):
    if not has_platform_perm(request, "tenants.suspend_tenant"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = suspend_tenant_pod(tenant)
        audit_event(request, "tenant.suspended", tenant=tenant, target_id=str(tenant.id))
        return {"ok": True, "message": get_message("SUCCESS_POD_SUSPENDED", name=tenant.name), "detail": result}
    except (EnvironmentError, RuntimeError, ValueError) as e:
        return {"ok": False, "message": get_message("ERR_VULTR_API_FAILED", detail=str(e))}

@router.post("/tenants/{tenant_id}/reactivate")
def reactivate_tenant(request, tenant_id: str):
    if not has_platform_perm(request, "tenants.reactivate_tenant"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = reactivate_tenant_pod(tenant)
        audit_event(request, "tenant.reactivated", tenant=tenant, target_id=str(tenant.id))
        return {"ok": True, "message": get_message("SUCCESS_POD_REACTIVATED", name=tenant.name), "detail": result}
    except (EnvironmentError, RuntimeError, ValueError) as e:
        return {"ok": False, "message": get_message("ERR_VULTR_API_FAILED", detail=str(e))}

@router.post("/tenants/{tenant_id}/restart")
def restart_tenant(request, tenant_id: str):
    if not has_platform_perm(request, "tenants.deploy_tenant"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        suspend_tenant_pod(tenant)
        result = reactivate_tenant_pod(tenant)
        audit_event(request, "tenant.restarted", tenant=tenant, target_id=str(tenant.id))
        return {"ok": True, "message": get_message("SUCCESS_DOCKER_RESTARTED", name=tenant.name), "detail": result}
    except (EnvironmentError, RuntimeError, ValueError) as e:
        return {"ok": False, "message": get_message("ERR_DOCKER_API_FAILED", detail=str(e))}

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
    item = CatalogItem.objects.create(tenant=tenant, name=payload.name, price=payload.price, description=payload.description, metadata=payload.metadata or {})
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
    config, created = TenantConfig.objects.update_or_create(tenant=tenant, key=payload.key, defaults={"value": payload.value})
    return {"ok": True, "key": config.key, "value": config.value, "message": get_message("SUCCESS_CONFIG_SAVED")}

@router.get("/tenants/{tenant_id}/usage", response=TenantUsageOut)
def get_tenant_usage(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    period_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage, _ = TenantUsage.objects.get_or_create(tenant=tenant, period_start=period_start, defaults={"last_reported_at": timezone.now()})
    return {"tenant_id": str(tenant.id), "period_start": usage.period_start.isoformat(), "conversations_used": usage.conversations_used, "messages_used": usage.messages_used, "transcription_seconds_used": usage.transcription_seconds_used, "catalog_items_used": usage.catalog_items_used, "storage_bytes_used": usage.storage_bytes_used}

@router.post("/tenants/{tenant_id}/usage/report", response=TenantUsageOut)
def report_tenant_usage(request, tenant_id: str, payload: TenantUsageIn):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    period_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage, _ = TenantUsage.objects.get_or_create(tenant=tenant, period_start=period_start)
    usage.conversations_used += max(payload.conversations_used, 0)
    usage.messages_used += max(payload.messages_used, 0)
    usage.transcription_seconds_used += max(payload.transcription_seconds_used, 0)
    usage.catalog_items_used += max(payload.catalog_items_used, 0)
    usage.storage_bytes_used += max(payload.storage_bytes_used, 0)
    usage.last_reported_at = timezone.now()
    usage.save()
    return {"tenant_id": str(tenant.id), "period_start": usage.period_start.isoformat(), "conversations_used": usage.conversations_used, "messages_used": usage.messages_used, "transcription_seconds_used": usage.transcription_seconds_used, "catalog_items_used": usage.catalog_items_used, "storage_bytes_used": usage.storage_bytes_used}

@router.get("/tenants/{tenant_id}/interactions", response=list[InteractionRecordOut])
def list_tenant_interactions(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    records = InteractionRecord.objects.filter(tenant=tenant).order_by("-created_at")[:100]
    return [{"id": str(r.id), "tenant_name": r.tenant.name, "customer_wa_id": r.customer_wa_id, "archetype": r.archetype, "status": r.status, "created_at": r.created_at.isoformat()} for r in records]

@router.get("/tenants/{tenant_id}/status", response=TenantStatusOut)
def get_tenant_status(request, tenant_id: str):
    if not (is_service_request(request) or check_sysadmin(request)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    tenant = get_object_or_404(Tenant, id=tenant_id)
    credential = get_service_credential(request)
    if credential and credential.tenant_id != tenant.id:
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    container_status = "unknown"
    last_heartbeat = None
    stt_available = False

    if tenant.assigned_port and tenant.status in ("active", "suspended"):
        try:
            from .vultr_service import VULTR_API_BASE, _vultr_headers
            vultr_resp = requests.get(f"{VULTR_API_BASE}/instances/{tenant.vultr_instance_id}", headers=_vultr_headers(), timeout=10)
            if vultr_resp.status_code == 200:
                instance_data = vultr_resp.json().get("instance", {})
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
                    stt_available = container_status == "healthy"
        except (requests.RequestException, ValueError, KeyError):
            container_status = "error"

    return {"tenant_id": str(tenant.id), "tenant_name": tenant.name, "status": tenant.status, "container_status": container_status, "last_heartbeat": last_heartbeat, "stt_available": stt_available, "assigned_port": tenant.assigned_port}

@router.get("/tenants/{tenant_id}/container-status")
def container_status(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return _get_container_status(tenant)

@router.get("/tenants/{tenant_id}/container-logs")
def container_logs(request, tenant_id: str, tail: int = 100):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    tenant = get_object_or_404(Tenant, id=tenant_id)
    logs = _get_container_logs(tenant, tail=min(tail, 500))
    return {"tenant_id": str(tenant.id), "logs": logs}
