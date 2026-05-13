from __future__ import annotations

from typing import Any

from django.utils import timezone

from .models import Plan, PodDeployment, Tenant


RATE_LIMIT_KEYS = (
    "A0_MAX_CONVERSATIONS_PER_MONTH",
    "A0_MAX_MESSAGES_PER_DAY",
    "A0_MAX_MESSAGES_PER_MINUTE",
    "A0_MAX_WHATSAPP_NUMBERS",
    "A0_MAX_CATALOG_ITEMS",
    "A0_MAX_TRANSCRIPTION_MINUTES_PER_MONTH",
    "A0_MAX_STORAGE_MB",
    "A0_MAX_USERS",
    "A0_MAX_AGENT_CONTEXTS",
)

FEATURE_FLAG_KEYS = (
    "A0_ALLOW_CATALOG_UPLOAD",
    "A0_ALLOW_VOICE_MESSAGES",
    "A0_ALLOW_HUMAN_HANDOFF",
    "A0_ALLOW_CREATOR_OVERRIDE",
    "A0_ALLOW_CUSTOM_DOMAIN",
    "A0_ALLOW_INTEGRATIONS",
    "A0_ALLOW_MOBILE_APP",
    "A0_ALLOW_MULTICHANNEL",
    "A0_ALLOW_OUTBOUND_REACTIVATION",
    "A0_ALLOW_CALL_HANDLING",
)


def plan_snapshot(plan: Plan | None) -> dict[str, Any]:
    if not plan:
        return {}
    return {
        "id": str(plan.id),
        "name": plan.name,
        "slug": plan.slug,
        "vultr_plan": plan.vultr_plan,
        "a0_image": plan.a0_image,
        "a0_memory_limit": plan.a0_memory_limit,
        "a0_cpu_limit": plan.a0_cpu_limit,
        "a0_memory_reservation": plan.a0_memory_reservation,
        "a0_cpu_reservation": plan.a0_cpu_reservation,
    }


def rate_limit_snapshot(deployment_config: dict[str, Any] | None) -> dict[str, str]:
    config = deployment_config or {}
    keys = RATE_LIMIT_KEYS + FEATURE_FLAG_KEYS
    return {key: str(config[key]) for key in keys if key in config}


def register_pod_deployment(
    *,
    tenant: Tenant,
    pod_name: str,
    backend: str,
    provider_resource_id: str = "",
    avender_container_id: str = "",
    tenant_vault_container_id: str = "",
    image_tag: str = "",
    assigned_port: int | None = None,
    public_url: str = "",
    private_url: str = "",
    deployment_config: dict[str, Any] | None = None,
    lifecycle_state: str = "active",
    provider_health_state: str = "unknown",
    tenant_vault_state: str = "unknown",
    is_development: bool = False,
    last_error: str = "",
) -> PodDeployment:
    pod, _ = PodDeployment.objects.update_or_create(
        tenant=tenant,
        pod_name=pod_name,
        defaults={
            "is_development": is_development,
            "deployment_backend": backend,
            "provider_resource_id": provider_resource_id,
            "avender_container_id": avender_container_id,
            "tenant_vault_container_id": tenant_vault_container_id,
            "image_tag": image_tag,
            "assigned_port": assigned_port,
            "public_url": public_url,
            "private_url": private_url,
            "effective_plan_snapshot": plan_snapshot(tenant.plan),
            "effective_rate_limits": rate_limit_snapshot(deployment_config),
            "lifecycle_state": lifecycle_state,
            "provider_health_state": provider_health_state,
            "tenant_vault_state": tenant_vault_state,
            "last_error": last_error,
            "last_health_check_at": timezone.now(),
        },
    )
    return pod


def set_pod_lifecycle(
    tenant: Tenant,
    *,
    action: str,
    lifecycle_state: str,
    actor=None,
    last_error: str = "",
) -> None:
    updates = {
        "last_lifecycle_action": action,
        "lifecycle_state": lifecycle_state,
        "last_error": last_error,
    }
    if actor is not None and getattr(actor, "is_authenticated", False):
        updates["last_lifecycle_action_by"] = actor
    PodDeployment.objects.filter(tenant=tenant).exclude(
        lifecycle_state="deleted"
    ).update(**updates)
