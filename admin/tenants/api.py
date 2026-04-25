import random
import hmac
import os
from django.utils import timezone
from datetime import timedelta
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from .models import Tenant, Plan, CatalogItem, TenantConfig, InteractionRecord, VaultRecord, GlobalConfig
from .vultr_service import deploy_tenant_pod, suspend_tenant_pod, reactivate_tenant_pod
from .vault_service import provision_tenant_secrets, build_tenant_bootstrap_env
from common.messages import get_message

class SessionOrServiceAuth:
    """
    Accept either:
    - authenticated Django session user
    - X-API-KEY matching SYSADMIN_API_KEY (service-to-service)
    """

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return user

        expected = os.environ.get("SYSADMIN_API_KEY", "").strip()
        provided = request.headers.get("X-API-KEY", "").strip()
        # Fail closed for weak keys.
        if len(expected) >= 32 and provided and hmac.compare_digest(expected, provided):
            return "service"
        return None


router = Router(auth=SessionOrServiceAuth())


def is_service_request(request) -> bool:
    return getattr(request, "auth", None) == "service"

def check_sysadmin(request):
    """Ensure user is a superuser (SysAdmin)"""
    if is_service_request(request):
        return False
    if not request.user.is_superuser:
        return False
    return True

def check_tenant_access(request, tenant: Tenant):
    """Ensure user is a SysAdmin OR the owner of the tenant."""
    if is_service_request(request):
        return False
    if request.user.is_superuser:
        return True
    if tenant.owner == request.user:
        return True
    return False

# --- SCHEMAS ---

class TenantIn(Schema):
    name: str
    email: str
    plan_name: str

class TenantOut(Schema):
    id: str
    name: str
    email: str
    status: str
    assigned_port: int | None

class CatalogItemIn(Schema):
    name: str
    price: float
    description: str | None = None
    metadata: dict | None = None

class CatalogItemOut(Schema):
    id: str
    name: str
    price: float
    description: str | None
    metadata: dict

class ConfigIn(Schema):
    key: str
    value: str

class PlanOut(Schema):
    id: str
    name: str
    price_monthly: float
    max_conversations: int

class VaultRecordOut(Schema):
    id: str
    tenant_name: str
    vault_path: str
    created_at: str

class InteractionRecordOut(Schema):
    id: str
    tenant_name: str
    customer_wa_id: str
    archetype: str
    status: str
    created_at: str

class ChallengeIn(Schema):
    tenant_id: str
    password: str
    pin: str

class PendingChallengeOut(Schema):
    tenant_id: str
    tenant_name: str
    pin: str
    expires_at: str

# --- SYSTEM ENDPOINTS (SysAdmin Only) ---

@router.get("/plans", response=list[PlanOut])
def list_plans(request):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return Plan.objects.all()

@router.get("/vault", response=list[VaultRecordOut])
def list_vault_records(request):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    records = VaultRecord.objects.select_related('tenant').all().order_by('-created_at')[:100]
    return [{"id": str(r.id), "tenant_name": r.tenant.name, "vault_path": r.vault_path, "created_at": r.created_at.isoformat()} for r in records]

@router.get("/interactions", response=list[InteractionRecordOut])
def list_interactions(request):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    records = InteractionRecord.objects.select_related('tenant').order_by('-created_at')[:100]
    return [{"id": str(r.id), "tenant_name": r.tenant.name, "customer_wa_id": r.customer_wa_id, "archetype": r.archetype, "status": r.status, "created_at": r.created_at.isoformat()} for r in records]

# --- TENANT LIFECYCLE (SysAdmin Only) ---

@router.post("/tenants", response=TenantOut)
def create_tenant(request, payload: TenantIn):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    plan = Plan.objects.filter(name__iexact=payload.plan_name).first()

    tenant = Tenant.objects.create(
        name=payload.name,
        email=payload.email,
        plan=plan,
        status='pending',
        owner=request.user # The sysadmin creating it is assigned owner for now, can be changed later
    )

    try:
        tenant_secrets = provision_tenant_secrets(tenant)
        bootstrap_env = build_tenant_bootstrap_env(tenant, tenant_secrets)
        deploy_tenant_pod(tenant, bootstrap_env=bootstrap_env)
    except (EnvironmentError, RuntimeError, ValueError) as e:
        tenant.status = 'pending'
        tenant.save()
        # Continuing despite error per original logic
        return tenant

    return tenant

@router.get("/tenants", response=list[TenantOut])
def list_tenants(request):
    if request.user.is_superuser:
        return Tenant.objects.all()
    # If not superuser, return only their tenants
    return Tenant.objects.filter(owner=request.user)

@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(request, tenant_id: str):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = suspend_tenant_pod(tenant)
        return {"ok": True, "message": get_message("SUCCESS_POD_SUSPENDED", name=tenant.name), "detail": result}
    except (EnvironmentError, RuntimeError, ValueError) as e:
        tenant.status = 'suspended'
        tenant.save()
        return {"ok": True, "message": get_message("ERR_VULTR_API_FAILED", detail=str(e))}

@router.post("/tenants/{tenant_id}/reactivate")
def reactivate_tenant(request, tenant_id: str):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        result = reactivate_tenant_pod(tenant)
        return {"ok": True, "message": get_message("SUCCESS_POD_REACTIVATED", name=tenant.name), "detail": result}
    except (EnvironmentError, RuntimeError, ValueError) as e:
        return {"ok": False, "message": get_message("ERR_VULTR_API_FAILED", detail=str(e))}

# --- TENANT DATA (SysAdmin or Tenant Owner) ---

@router.get("/tenants/{tenant_id}/catalog", response=list[CatalogItemOut])
def list_catalog(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return tenant.catalog_items.all()

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
        metadata=payload.metadata or {}
    )
    return item

@router.get("/tenants/{tenant_id}/config")
def get_tenant_config(request, tenant_id: str):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    configs = tenant.configs.all()
    return {c.key: c.value for c in configs}

@router.post("/tenants/{tenant_id}/config")
def set_tenant_config(request, tenant_id: str, payload: ConfigIn):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not check_tenant_access(request, tenant):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    config, created = TenantConfig.objects.update_or_create(
        tenant=tenant, key=payload.key,
        defaults={'value': payload.value}
    )
    return {"ok": True, "key": config.key, "value": config.value, "message": get_message("SUCCESS_CONFIG_SAVED")}

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
    pin = str(random.randint(1000, 9999))
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
    
    # 1. Verify Global Master Password
    master_pass_config = GlobalConfig.objects.filter(key="MASTER_CREATOR_PASSWORD").first()
    if not master_pass_config or not hmac.compare_digest(
        str(master_pass_config.value), str(payload.password)
    ):
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
    
    return {"ok": True, "message": "Creator access granted."}

@router.get("/auth/pending-challenges", response=list[PendingChallengeOut])
def list_pending_challenges(request):
    """
    Returns active challenges for the Dashboard UI to display.
    """
    if not (is_service_request(request) or check_sysadmin(request)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    active_tenants = Tenant.objects.filter(
        creator_session_pin__isnull=False,
        pin_expires_at__gt=timezone.now()
    )
    return [
        {
            "tenant_id": str(t.id),
            "tenant_name": t.name,
            "pin": t.creator_session_pin,
            "expires_at": t.pin_expires_at.isoformat()
        }
        for t in active_tenants
    ]
