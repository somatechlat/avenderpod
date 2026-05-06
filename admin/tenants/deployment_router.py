"""
Deployment Router — Routes tenant pod operations to the correct backend.

Reads DEPLOYMENT_MODE from GlobalConfig to determine which backend
(Docker or Vultr) handles new deployments. Each tenant also records
which backend deployed it, so suspend/reactivate/delete always route
to the correct backend regardless of the current global mode.
"""

from .models import GlobalConfig, Tenant


def get_deployment_mode() -> str:
    """
    Return the current deployment mode from GlobalConfig.
    Defaults to 'vultr' if not set.
    """
    config = GlobalConfig.objects.filter(key="DEPLOYMENT_MODE").first()
    if config and config.value in ("docker", "vultr"):
        return config.value
    return "vultr"


def set_deployment_mode(mode: str) -> None:
    """Persist the deployment mode to GlobalConfig."""
    GlobalConfig.objects.update_or_create(
        key="DEPLOYMENT_MODE",
        defaults={"value": mode, "description": "Active deployment backend"},
    )


def deploy_tenant_pod(
    tenant: Tenant, bootstrap_env: dict[str, str] | None = None
) -> dict:
    """
    Deploy a tenant pod using the CURRENT global deployment mode.
    Records the backend on the tenant for future operations.
    """
    mode = get_deployment_mode()
    if mode == "docker":
        from . import docker_service

        return docker_service.deploy_tenant_pod(tenant, bootstrap_env)
    else:
        from . import vultr_service

        return vultr_service.deploy_tenant_pod(tenant, bootstrap_env)


def suspend_tenant_pod(tenant: Tenant) -> dict:
    """
    Suspend a tenant pod using the backend that DEPLOYED it.
    Uses tenant.deployment_backend, not the global mode.
    """
    if tenant.deployment_backend == "docker":
        from . import docker_service

        return docker_service.suspend_tenant_pod(tenant)
    else:
        from . import vultr_service

        return vultr_service.suspend_tenant_pod(tenant)


def reactivate_tenant_pod(tenant: Tenant) -> dict:
    """
    Reactivate a tenant pod using the backend that DEPLOYED it.
    """
    if tenant.deployment_backend == "docker":
        from . import docker_service

        return docker_service.reactivate_tenant_pod(tenant)
    else:
        from . import vultr_service

        return vultr_service.reactivate_tenant_pod(tenant)


def delete_tenant_pod(tenant: Tenant) -> dict:
    """
    Delete a tenant pod using the backend that DEPLOYED it.
    """
    if tenant.deployment_backend == "docker":
        from . import docker_service

        return docker_service.delete_tenant_pod(tenant)
    else:
        from . import vultr_service

        return vultr_service.delete_tenant_pod(tenant)


def get_container_status(tenant: Tenant) -> dict:
    """
    Get live container status from the backend that manages this tenant.
    """
    if tenant.deployment_backend == "docker":
        from . import docker_service

        return docker_service.get_container_status(tenant)
    else:
        # Vultr status requires SSH or API polling — return DB state
        return {
            "state": "active" if tenant.status == "active" else tenant.status,
            "running": tenant.status == "active",
            "vultr_instance_id": tenant.vultr_instance_id or "",
        }


def get_container_logs(tenant: Tenant, tail: int = 100) -> str:
    """
    Get container logs. Only available for Docker-deployed tenants.
    """
    if tenant.deployment_backend == "docker":
        from . import docker_service

        return docker_service.get_container_logs(tenant, tail=tail)
    else:
        return (
            "Container logs are not available for Vultr-deployed tenants "
            "from the SysAdmin dashboard. Use SSH to access the VM directly."
        )
