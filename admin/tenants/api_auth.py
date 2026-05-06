import secrets
import hmac
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.hashers import check_password
from ninja import Router
from .models import Tenant, GlobalConfig
from .schemas import ChallengeIn, PendingChallengeOut
from .security import check_sysadmin, check_tenant_access, check_rate_limit, is_service_request, get_service_credential, audit_event
from common.messages import get_message

router = Router()

@router.post("/auth/init-challenge")
def init_challenge(request, tenant_id: str):
    """
    Called by Agent Zero when the Creator trigger phrase is detected.
    Generates a random 4-digit PIN for the dashboard.
    """
    if not check_rate_limit(request, scope="challenge"):
        return {"ok": False, "message": get_message("ERR_RATE_LIMITED")}
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if not (is_service_request(request) or check_tenant_access(request, tenant)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    pin = str(secrets.randbelow(9000) + 1000)
    tenant.set_creator_pin(pin)
    tenant.pin_expires_at = timezone.now() + timedelta(minutes=5)
    tenant.save()
    return {"ok": True, "pin": pin, "message": get_message("SUCCESS_CHALLENGE_INITIATED")}

@router.post("/auth/verify-challenge")
def verify_challenge(request, payload: ChallengeIn):
    """
    Validates the Creator Password and the Session PIN.
    """
    if not check_rate_limit(request, scope="challenge"):
        return {"ok": False, "message": get_message("ERR_RATE_LIMITED")}
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
        is_valid_password = hmac.compare_digest(stored_password, str(payload.password))
    if not is_valid_password:
        return {"ok": False, "message": get_message("ERR_MASTER_PASSWORD_INVALID")}

    # 2. Check expiry FIRST
    if not tenant.pin_expires_at or tenant.pin_expires_at < timezone.now():
        return {"ok": False, "message": get_message("ERR_PIN_EXPIRED")}

    # 3. Verify Session PIN hash
    if not tenant.check_creator_pin(payload.pin):
        return {"ok": False, "message": get_message("ERR_PIN_INVALID")}

    # Success - clear the PIN
    tenant.clear_creator_pin()
    tenant.save()
    audit_event(
        request, "creator_override.verified", tenant=tenant, target_id=str(tenant.id)
    )

    return {"ok": True, "message": get_message("SUCCESS_CREATOR_ACCESS")}

@router.get("/auth/pending-challenges", response=list[PendingChallengeOut])
def list_pending_challenges(request):
    """
    Returns active challenges for the Dashboard UI to display.
    """
    if not (is_service_request(request) or check_sysadmin(request)):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))

    active_tenants = Tenant.objects.filter(
        creator_session_pin_hash__isnull=False, pin_expires_at__gt=timezone.now()
    )
    return [
        {
            "tenant_id": str(t.id),
            "tenant_name": t.name,
            "pin": "****",
            "expires_at": t.pin_expires_at.isoformat(),
        }
        for t in active_tenants
    ]
