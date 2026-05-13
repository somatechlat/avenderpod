from __future__ import annotations

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from common.messages import get_message

from .deployment_router import (
    delete_tenant_pod,
    get_container_logs,
    get_container_status,
    reactivate_tenant_pod,
    suspend_tenant_pod,
)
from .models import PodDeployment
from .schemas import PodDeploymentOut
from .security import audit_event, has_platform_perm

router = Router()


def _pod_out(pod: PodDeployment) -> dict:
    return {
        "id": str(pod.id),
        "tenant_id": str(pod.tenant_id),
        "tenant_name": pod.tenant.name,
        "pod_name": pod.pod_name,
        "is_development": pod.is_development,
        "deployment_backend": pod.deployment_backend,
        "provider_resource_id": pod.provider_resource_id,
        "avender_container_id": pod.avender_container_id,
        "tenant_vault_container_id": pod.tenant_vault_container_id,
        "image_tag": pod.image_tag,
        "assigned_port": pod.assigned_port,
        "public_url": pod.public_url,
        "private_url": pod.private_url,
        "effective_plan_snapshot": pod.effective_plan_snapshot,
        "effective_rate_limits": pod.effective_rate_limits,
        "lifecycle_state": pod.lifecycle_state,
        "provider_health_state": pod.provider_health_state,
        "tenant_vault_state": pod.tenant_vault_state,
        "last_lifecycle_action": pod.last_lifecycle_action,
        "last_health_check_at": (
            pod.last_health_check_at.isoformat() if pod.last_health_check_at else None
        ),
        "last_error": pod.last_error,
        "created_at": pod.created_at.isoformat(),
        "updated_at": pod.updated_at.isoformat(),
    }


def _require(request, codename: str):
    if not has_platform_perm(request, f"tenants.{codename}"):
        return HttpResponseForbidden(get_message("ERR_UNAUTHORIZED"))
    return None


@router.get("/pods", response=list[PodDeploymentOut])
def list_pods(request):
    denied = _require(request, "view_poddeployment")
    if denied:
        return denied
    pods = PodDeployment.objects.select_related("tenant").order_by("-updated_at")
    return [_pod_out(pod) for pod in pods]


@router.get("/pods/{pod_id}", response=PodDeploymentOut)
def get_pod(request, pod_id: str):
    denied = _require(request, "view_poddeployment")
    if denied:
        return denied
    return _pod_out(get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id))


@router.post("/pods/{pod_id}/refresh-health", response=PodDeploymentOut)
def refresh_pod_health(request, pod_id: str):
    denied = _require(request, "view_pod_health")
    if denied:
        return denied
    pod = get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id)
    status = get_container_status(pod.tenant)
    state = status.get("state", "unknown")
    pod.provider_health_state = (
        "healthy" if status.get("running") else "missing" if state == "removed" else "unhealthy"
    )
    if status.get("tenant_vault_state"):
        pod.tenant_vault_state = status["tenant_vault_state"]
    pod.last_health_check_at = timezone.now()
    pod.last_error = status.get("detail", "")
    pod.save(update_fields=["provider_health_state", "tenant_vault_state", "last_health_check_at", "last_error", "updated_at"])
    audit_event(
        request,
        "pod.health_refreshed",
        tenant=pod.tenant,
        target_type="PodDeployment",
        target_id=str(pod.id),
        metadata={"provider_state": state},
    )
    return _pod_out(pod)


@router.post("/pods/{pod_id}/stop", response=PodDeploymentOut)
def stop_pod(request, pod_id: str):
    denied = _require(request, "stop_poddeployment")
    if denied:
        return denied
    pod = get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id)
    suspend_tenant_pod(pod.tenant)
    pod.lifecycle_state = "stopped"
    pod.last_lifecycle_action = "stop"
    pod.last_lifecycle_action_by = request.user
    pod.last_error = ""
    pod.save()
    audit_event(request, "pod.stopped", tenant=pod.tenant, target_type="PodDeployment", target_id=str(pod.id))
    return _pod_out(pod)


@router.post("/pods/{pod_id}/suspend", response=PodDeploymentOut)
def suspend_pod(request, pod_id: str):
    denied = _require(request, "suspend_poddeployment")
    if denied:
        return denied
    pod = get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id)
    suspend_tenant_pod(pod.tenant)
    pod.lifecycle_state = "suspended"
    pod.last_lifecycle_action = "suspend"
    pod.last_lifecycle_action_by = request.user
    pod.last_error = ""
    pod.save()
    audit_event(request, "pod.suspended", tenant=pod.tenant, target_type="PodDeployment", target_id=str(pod.id))
    return _pod_out(pod)


@router.post("/pods/{pod_id}/reactivate", response=PodDeploymentOut)
def reactivate_pod(request, pod_id: str):
    denied = _require(request, "reactivate_poddeployment")
    if denied:
        return denied
    pod = get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id)
    reactivate_tenant_pod(pod.tenant)
    pod.lifecycle_state = "active"
    pod.last_lifecycle_action = "reactivate"
    pod.last_lifecycle_action_by = request.user
    pod.last_error = ""
    pod.save()
    audit_event(request, "pod.reactivated", tenant=pod.tenant, target_type="PodDeployment", target_id=str(pod.id))
    return _pod_out(pod)


@router.post("/pods/{pod_id}/restart", response=PodDeploymentOut)
def restart_pod(request, pod_id: str):
    denied = _require(request, "restart_poddeployment")
    if denied:
        return denied
    pod = get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id)
    pod.lifecycle_state = "restarting"
    pod.last_lifecycle_action = "restart"
    pod.last_lifecycle_action_by = request.user
    pod.save()
    try:
        suspend_tenant_pod(pod.tenant)
        reactivate_tenant_pod(pod.tenant)
        pod.lifecycle_state = "active"
        pod.last_error = ""
    except Exception as exc:
        pod.lifecycle_state = "failed"
        pod.last_error = str(exc)
    pod.save()
    audit_event(request, "pod.restarted", tenant=pod.tenant, target_type="PodDeployment", target_id=str(pod.id))
    return _pod_out(pod)


@router.delete("/pods/{pod_id}", response=PodDeploymentOut)
def delete_pod(request, pod_id: str):
    denied = _require(request, "delete_poddeployment")
    if denied:
        return denied
    pod = get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id)
    pod.lifecycle_state = "deleting"
    pod.last_lifecycle_action = "delete"
    pod.last_lifecycle_action_by = request.user
    pod.save()
    try:
        delete_tenant_pod(pod.tenant)
        pod.lifecycle_state = "deleted"
        pod.last_error = ""
    except Exception as exc:
        pod.lifecycle_state = "failed"
        pod.last_error = str(exc)
    pod.save()
    audit_event(request, "pod.deleted", tenant=pod.tenant, target_type="PodDeployment", target_id=str(pod.id))
    return _pod_out(pod)


@router.post("/pods/reconcile")
def reconcile_pods(request, auto_repair: bool = False):
    denied = _require(request, "reconcile_poddeployment")
    if denied:
        return denied
    changed = 0
    repaired = 0
    for pod in PodDeployment.objects.select_related("tenant").exclude(lifecycle_state="deleted"):
        status = get_container_status(pod.tenant)
        if status.get("state") == "removed":
            pod.lifecycle_state = "drifted"
            pod.provider_health_state = "missing"
            pod.last_error = status.get("detail", "")
            pod.last_health_check_at = timezone.now()
            pod.save()
            changed += 1

            # Auto-repair: re-deploy only if tenant is active and repair is requested
            if auto_repair and pod.tenant.status == "active":
                try:
                    from .deployment_router import deploy_tenant_pod
                    deploy_tenant_pod(pod.tenant)
                    pod.lifecycle_state = "active"
                    pod.provider_health_state = "healthy"
                    pod.last_error = ""
                    pod.last_lifecycle_action = "auto_repair"
                    pod.save()
                    repaired += 1
                except Exception as exc:
                    pod.last_error = f"Auto-repair failed: {exc}"
                    pod.save(update_fields=["last_error", "updated_at"])

    audit_event(
        request, "pod.reconciled",
        metadata={"changed": changed, "repaired": repaired, "auto_repair": auto_repair},
    )
    return {"ok": True, "changed": changed, "repaired": repaired}


@router.get("/pods/{pod_id}/logs")
def pod_logs(request, pod_id: str, tail: int = 100):
    denied = _require(request, "view_pod_logs")
    if denied:
        return denied
    pod = get_object_or_404(PodDeployment.objects.select_related("tenant"), id=pod_id)
    return {"pod_id": str(pod.id), "logs": get_container_logs(pod.tenant, tail=min(tail, 500))}
