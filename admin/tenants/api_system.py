from django.http import HttpResponseForbidden
from ninja import Router
from ninja.errors import HttpError
from .models import VaultRecord, InteractionRecord
from .schemas import VaultRecordOut, InteractionRecordOut, DeploymentModeIn
from .security import check_sysadmin, audit_event
from .deployment_router import get_deployment_mode, set_deployment_mode as _set_deployment_mode
from common.messages import get_message

router = Router()

@router.get("/health", auth=None)
def health_check(request):
    """Unauthenticated health probe for container orchestration."""
    db_ok = False
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass
    status = "ok" if db_ok else "degraded"
    return {"status": status, "db": db_ok}

@router.get("/vault", response=list[VaultRecordOut])
def list_vault_records(request):
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    records = VaultRecord.objects.select_related("tenant").all().order_by("-created_at")[:100]
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
    records = InteractionRecord.objects.select_related("tenant").order_by("-created_at")[:100]
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

@router.get("/system/deployment-mode")
def get_deployment_mode_endpoint(request):
    """Returns the current deployment mode: 'docker' or 'vultr'."""
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return {"mode": get_deployment_mode()}

@router.post("/system/deployment-mode")
def set_deployment_mode_endpoint(request, payload: DeploymentModeIn):
    """SysAdmin-only. Switches between 'docker' and 'vultr'."""
    if not check_sysadmin(request):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    mode = payload.mode.strip().lower()
    if mode not in ("docker", "vultr"):
        raise HttpError(400, get_message("ERR_INVALID_DEPLOYMENT_MODE"))
    _set_deployment_mode(mode)
    audit_event(
        request,
        "system.deployment_mode_changed",
        metadata={"mode": mode},
    )
    return {
        "ok": True,
        "mode": mode,
        "message": get_message("SUCCESS_DEPLOYMENT_MODE_CHANGED", mode=mode),
    }
