"""
Docker Deployment Service — Local Avender Pod container management via Docker SDK.

Deploys real Avender Pod containers on the local Docker host.
Mirrors the vultr_service.py interface for production-parity:
- deploy_tenant_pod()
- suspend_tenant_pod()
- reactivate_tenant_pod()
- delete_tenant_pod()
- get_container_status()
- get_container_logs()

All Plan rate-limiting fields are injected as A0_* environment variables
into the container. Resource limits (memory, CPU) are enforced at the
Docker runtime level from Plan.a0_memory_limit / a0_cpu_limit.
"""

import os

import docker
from docker.errors import APIError, NotFound

from .models import Tenant

# Network that all avender containers share (created by docker-compose).
AVENDER_NETWORK = "avender_network"

# Default image for Avender Pods. In local dev, this is the image built by
# docker-compose from DockerfileLocal. Overridden by Plan.a0_image.
DEFAULT_AVENDER_POD_IMAGE = "avender-agent_zero:latest"


def _get_client() -> docker.DockerClient:
    """
    Connect to the local Docker daemon.
    The SysAdmin container must have the Docker socket mounted:
      -v /var/run/docker.sock:/var/run/docker.sock
    """
    return docker.from_env()


def _container_name(tenant: Tenant) -> str:
    """Deterministic container name for a tenant's Avender Pod."""
    return f"avender-pod-{tenant.id.hex[:12]}"


def _volume_name(tenant: Tenant) -> str:
    """Named volume for tenant Avender Pod workspace persistence."""
    return f"avender_pod_{tenant.id.hex[:12]}"


def deploy_tenant_pod(
    tenant: Tenant, bootstrap_env: dict[str, str] | None = None
) -> dict:
    """
    Deploy a new Avender Pod container for this tenant on the local Docker host.

    The container receives:
    - Resource limits (memory, CPU) from the tenant's Plan
    - All A0_* rate-limiting env vars from bootstrap_env (built by vault_service)
    - Secrets mounted as read-only files under /run/secrets/
    - A named volume for workspace persistence
    - Connection to avender_network for service-to-service comms

    Returns a dict with container info on success, raises on failure.
    """
    client = _get_client()
    name = _container_name(tenant)

    # ---- Image Selection ----
    # Use the Plan's image if set, otherwise default to the locally built image
    image = DEFAULT_AVENDER_POD_IMAGE
    if tenant.plan and tenant.plan.a0_image:
        # Check if the Plan's image is the default upstream one or a custom one
        plan_image = tenant.plan.a0_image
        # If it's the generic upstream default, use the local build instead
        if plan_image != "agent0ai/agent-zero-tenant:latest":
            image = plan_image

    # ---- Resource Limits from Plan ----
    mem_limit = "3g"
    cpu_limit = 2.0
    mem_reservation = "1g"
    if tenant.plan:
        mem_limit = tenant.plan.a0_memory_limit or "3g"
        cpu_limit = float(tenant.plan.a0_cpu_limit or "2.0")
        mem_reservation = tenant.plan.a0_memory_reservation or "1g"

    # ---- Port Validation ----
    if not tenant.assigned_port:
        raise ValueError(
            f"Tenant {tenant.name} has no assigned_port. "
            "Port must be allocated before container deployment."
        )
    port = tenant.assigned_port

    # ---- Environment Variables ----
    # Base env vars every Avender Pod needs
    env_vars = {
        "TENANT_ID": str(tenant.id),
        "WEB_UI_HOST": "0.0.0.0",
        "STT_MODEL_SIZE": "base",
        "STT_LANGUAGE": "es",
        "SYSADMIN_API_URL": "http://avender_sysadmin:8000/api/saas",
    }
    # Merge ALL bootstrap env vars (includes A0_MAX_*, A0_ALLOW_*, etc.)
    # Secrets are passed as env vars for Docker-local mode since we can't
    # always bind-mount the same secret files into dynamically created containers.
    if bootstrap_env:
        for key, value in bootstrap_env.items():
            env_vars[key] = str(value)

    volume_binds = {}
    # Workspace volume
    vol_name = _volume_name(tenant)
    volume_binds[vol_name] = {"bind": "/a0/usr/workdir", "mode": "rw"}

    # ---- Cleanup any existing container with same name ----
    try:
        existing = client.containers.get(name)
        existing.stop(timeout=10)
        existing.remove(force=True)
    except NotFound:
        pass

    # ---- Ensure named volume exists ----
    try:
        client.volumes.get(vol_name)
    except NotFound:
        client.volumes.create(name=vol_name)

    # ---- Pull image (best-effort, use local cache if pull fails) ----
    try:
        client.images.pull(image)
    except APIError:
        pass

    # ---- Deploy the Avender Pod ----
    container = client.containers.run(
        image=image,
        name=name,
        detach=True,
        restart_policy={"Name": "unless-stopped"},
        mem_limit=mem_limit,
        memswap_limit=mem_limit,  # Disable swap
        mem_reservation=mem_reservation,
        nano_cpus=int(cpu_limit * 1e9),
        pids_limit=1000,
        security_opt=["no-new-privileges:true"],
        environment=env_vars,
        ports={"80/tcp": ("127.0.0.1", port)},
        volumes=volume_binds,
        network=AVENDER_NETWORK,
        log_config={
            "type": "json-file",
            "config": {"max-size": "20m", "max-file": "5"},
        },
    )

    # ---- Update tenant record ----
    tenant.docker_container_id = container.id
    tenant.deployment_backend = "docker"
    tenant.status = "active"
    tenant.save(
        update_fields=["docker_container_id", "deployment_backend", "status"]
    )

    return {
        "container_id": container.id,
        "container_name": name,
        "port": port,
        "image": image,
        "mem_limit": mem_limit,
        "cpu_limit": str(cpu_limit),
        "status": "running",
    }


def suspend_tenant_pod(tenant: Tenant) -> dict:
    """Stop an Avender Pod container for a suspended tenant."""
    container_id = tenant.docker_container_id
    if not container_id:
        raise ValueError(
            f"Tenant {tenant.name} has no Avender Pod container to suspend."
        )

    client = _get_client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=30)
    except NotFound:
        # Container already gone — just update status
        pass

    tenant.status = "suspended"
    tenant.save(update_fields=["status"])
    return {"status": "stopped", "container_id": container_id}


def reactivate_tenant_pod(tenant: Tenant) -> dict:
    """Start a previously stopped Avender Pod container."""
    container_id = tenant.docker_container_id
    if not container_id:
        raise ValueError(
            f"Tenant {tenant.name} has no Avender Pod container to start."
        )

    client = _get_client()
    container = client.containers.get(container_id)
    container.start()

    tenant.status = "active"
    tenant.save(update_fields=["status"])
    return {"status": "started", "container_id": container_id}


def delete_tenant_pod(tenant: Tenant) -> dict:
    """Permanently destroy an Avender Pod container and its named volume."""
    container_id = tenant.docker_container_id
    if not container_id:
        raise ValueError(
            f"Tenant {tenant.name} has no Avender Pod container to delete."
        )

    client = _get_client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=10)
        container.remove(force=True)
    except NotFound:
        pass  # Already gone

    # Clean up named volume
    vol_name = _volume_name(tenant)
    try:
        volume = client.volumes.get(vol_name)
        volume.remove(force=True)
    except NotFound:
        pass

    tenant.status = "deleted"
    tenant.docker_container_id = None
    tenant.assigned_port = None
    tenant.save(update_fields=["status", "docker_container_id", "assigned_port"])
    return {"status": "deleted"}


def get_container_status(tenant: Tenant) -> dict:
    """
    Get the live status of a tenant's Avender Pod container.
    Returns state, memory usage, and uptime from the Docker daemon.
    """
    container_id = tenant.docker_container_id
    if not container_id:
        return {"state": "unknown", "detail": "No container ID assigned"}

    client = _get_client()
    try:
        container = client.containers.get(container_id)
        attrs = container.attrs
        state = attrs.get("State", {})
        return {
            "state": state.get("Status", "unknown"),
            "running": state.get("Running", False),
            "started_at": state.get("StartedAt", ""),
            "finished_at": state.get("FinishedAt", ""),
            "exit_code": state.get("ExitCode", -1),
            "oom_killed": state.get("OOMKilled", False),
            "container_id": container.short_id,
            "container_name": container.name,
        }
    except NotFound:
        return {"state": "removed", "detail": "Container no longer exists"}
    except APIError as e:
        return {"state": "error", "detail": str(e)}


def get_container_logs(tenant: Tenant, tail: int = 100) -> str:
    """Get the last N lines of logs from a tenant's Avender Pod container."""
    container_id = tenant.docker_container_id
    if not container_id:
        return "No container ID assigned for this tenant."

    client = _get_client()
    try:
        container = client.containers.get(container_id)
        logs = container.logs(tail=tail, timestamps=True)
        return logs.decode("utf-8", errors="replace")
    except NotFound:
        return "Container no longer exists."
    except APIError as e:
        return f"Error retrieving logs: {e}"
