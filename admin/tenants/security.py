import hmac
import os

from django.utils import timezone

from .models import AuditEvent, ServiceCredential, Tenant
from .secret_values import read_secret


class SessionOrServiceAuth:
    """
    Accept either:
    - authenticated Django session user
    - tenant-scoped ServiceCredential
    - legacy X-API-KEY matching SYSADMIN_API_KEY during migration
    """

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return user

        provided = request.headers.get("X-API-KEY", "").strip()
        if len(provided) >= 32:
            key_hash = ServiceCredential.hash_key(provided)
            credential = (
                ServiceCredential.objects.select_related("tenant")
                .filter(key_hash=key_hash)
                .first()
            )
            if credential and credential.is_valid():
                credential.last_used_at = timezone.now()
                credential.save(update_fields=["last_used_at"])
                return credential

        expected = read_secret("SYSADMIN_API_KEY")
        if len(expected) >= 32 and provided and hmac.compare_digest(expected, provided):
            return "legacy_service"
        return None


def is_service_request(request) -> bool:
    auth = getattr(request, "auth", None)
    return auth == "legacy_service" or isinstance(auth, ServiceCredential)


def get_service_credential(request) -> ServiceCredential | None:
    auth = getattr(request, "auth", None)
    return auth if isinstance(auth, ServiceCredential) else None


def actor_ip(request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit_event(
    request,
    action: str,
    *,
    tenant: Tenant | None = None,
    target_type: str = "",
    target_id: str = "",
    metadata: dict | None = None,
) -> None:
    credential = get_service_credential(request)
    user = getattr(request, "user", None)
    actor_type = "service" if is_service_request(request) else "user"
    AuditEvent.objects.create(
        actor_type=actor_type,
        actor_user=user if getattr(user, "is_authenticated", False) else None,
        actor_service=credential,
        tenant=tenant,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
        ip_address=actor_ip(request),
    )


def has_platform_perm(request, permission: str) -> bool:
    if is_service_request(request):
        return False
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.has_perm(permission)


def check_sysadmin(request):
    return has_platform_perm(request, "tenants.view_tenant")


def check_tenant_access(request, tenant: Tenant):
    credential = get_service_credential(request)
    if credential:
        return credential.tenant_id == tenant.id
    if getattr(request, "auth", None) == "legacy_service":
        return False
    if request.user.is_superuser:
        return True
    return tenant.owner == request.user
