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

import io
import json
import os
import tarfile
import time

import docker
from docker.errors import APIError, NotFound
import requests

from .models import Tenant
from .pod_registry import register_pod_deployment, set_pod_lifecycle
from .vault_service import SECRET_BOOTSTRAP_KEYS

# Network that all avender containers share (created by docker-compose).
AVENDER_NETWORK = "avender_network"

# Default image for Avender Pods. In local dev, this is the image built by
# docker-compose from DockerfileLocal. Overridden by Plan.a0_image.
DEFAULT_AVENDER_POD_IMAGE = "avenderpod:latest"


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


def _vault_container_name(tenant: Tenant) -> str:
    return f"avender-vault-{tenant.id.hex[:12]}"


def _vault_data_volume_name(tenant: Tenant) -> str:
    return f"avender_vault_data_{tenant.id.hex[:12]}"


def _vault_token_volume_name(tenant: Tenant) -> str:
    return f"avender_vault_token_{tenant.id.hex[:12]}"


def _put_secret_file(container, directory: str, filename: str, value: str) -> None:
    payload = value.encode("utf-8")
    stream = io.BytesIO()
    info = tarfile.TarInfo(filename)
    info.size = len(payload)
    info.mode = 0o400
    with tarfile.open(fileobj=stream, mode="w") as archive:
        archive.addfile(info, io.BytesIO(payload))
    stream.seek(0)
    if not container.put_archive(directory, stream.read()):
        raise RuntimeError(f"Could not write {filename} into tenant secret volume.")


def _exec_json(container, command: list[str], allow_exit_codes: tuple[int, ...] = (0,)) -> dict:
    result = container.exec_run(command)
    output = result.output.decode("utf-8", errors="replace")
    if result.exit_code not in allow_exit_codes:
        raise RuntimeError(f"Tenant Vault command failed: {output}")
    return json.loads(output) if output.strip().startswith("{") else {}


def _vault_request(
    vault_name: str,
    token: str,
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict:
    response = requests.request(
        method,
        f"http://{vault_name}:8200/v1/{path.lstrip('/')}",
        headers={"X-Vault-Token": token, "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"Tenant Vault request failed {response.status_code}: {response.text}"
        )
    return response.json() if response.content else {}


def _start_tenant_vault(
    client: docker.DockerClient,
    tenant: Tenant,
    secrets_bundle: dict[str, str],
) -> dict[str, str]:
    vault_name = _vault_container_name(tenant)
    data_volume = _vault_data_volume_name(tenant)
    token_volume = _vault_token_volume_name(tenant)

    try:
        existing = client.containers.get(vault_name)
        existing.stop(timeout=10)
        existing.remove(force=True)
    except NotFound:
        pass

    for volume_name in (data_volume, token_volume):
        try:
            client.volumes.get(volume_name)
        except NotFound:
            client.volumes.create(name=volume_name)

    # Build the Vault config file inline and start the server.
    # NOTE: We use printf + command list instead of heredoc + entrypoint
    # because heredoc via entrypoint=['/bin/sh', '-lc'] fails silently
    # when launched from inside another container via Docker SDK.
    vault_cmd = (
        'printf \'storage "file" { path = "/vault/file" }\n'
        'listener "tcp" { address = "0.0.0.0:8200" tls_disable = 1 }\n'
        'disable_mlock = true\n'
        'api_addr = "http://127.0.0.1:8200"\n'
        "' > /tmp/vault.hcl && vault server -config=/tmp/vault.hcl"
    )
    vault = client.containers.run(
        image="hashicorp/vault:1.16",
        name=vault_name,
        command=["/bin/sh", "-c", vault_cmd],
        detach=True,
        restart_policy={"Name": "unless-stopped"},
        cap_add=["IPC_LOCK"],
        environment={"VAULT_ADDR": "http://127.0.0.1:8200"},
        labels={
            "avender.tenant_id": str(tenant.id),
            "avender.pod_name": vault_name,
            "avender.managed_by": "sysadmin",
            "avender.role": "tenant-vault",
        },
        volumes={
            data_volume: {"bind": "/vault/file", "mode": "rw"},
            token_volume: {"bind": "/avender/token", "mode": "rw"},
        },
        network=AVENDER_NETWORK,
        log_config={
            "type": "json-file",
            "config": {"max-size": "20m", "max-file": "5"},
        },
    )

    for _ in range(30):
        status = vault.exec_run(["vault", "status", "-format=json"])
        if status.exit_code in (0, 2):
            break
        time.sleep(1)
    else:
        raise RuntimeError("Tenant Vault did not become reachable.")

    state = _exec_json(vault, ["vault", "status", "-format=json"], allow_exit_codes=(0, 2))
    if state.get("initialized"):
        raise RuntimeError(
            "Tenant Vault data volume is already initialized; refusing to overwrite tenant secrets."
        )

    init_state = _exec_json(
        vault,
        [
            "vault",
            "operator",
            "init",
            "-key-shares=1",
            "-key-threshold=1",
            "-format=json",
        ],
    )
    root_token = init_state["root_token"]
    unseal_key = init_state["unseal_keys_b64"][0]
    vault.exec_run(["vault", "operator", "unseal", unseal_key])

    _vault_request(vault_name, root_token, "POST", "sys/mounts/secret", {"type": "kv-v2"})
    _vault_request(
        vault_name,
        root_token,
        "POST",
        f"secret/data/avender/tenants/{tenant.id}",
        {"data": secrets_bundle},
    )
    policy = f"""
path "secret/data/avender/tenants/{tenant.id}" {{
  capabilities = ["read"]
}}
"""
    _vault_request(
        vault_name,
        root_token,
        "PUT",
        "sys/policies/acl/tenant-runtime",
        {"policy": policy},
    )
    token_response = _vault_request(
        vault_name,
        root_token,
        "POST",
        "auth/token/create",
        {"policies": ["tenant-runtime"], "renewable": True, "ttl": "720h"},
    )
    tenant_token = token_response.get("auth", {}).get("client_token", "")
    if not tenant_token:
        raise RuntimeError("Tenant Vault did not return a runtime token.")
    _put_secret_file(vault, "/avender/token", "tenant_vault_token", tenant_token)
    return {
        "container_id": vault.id,
        "container_name": vault_name,
        "token_volume": token_volume,
        "state": "healthy",
    }


def deploy_tenant_pod(
    tenant: Tenant,
    bootstrap_env: dict[str, str] | None = None,
    tenant_secrets: dict[str, str] | None = None,
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
    if not tenant_secrets:
        raise ValueError(
            "Tenant secret bundle is required for Docker tenant Vault provisioning."
        )

    # ---- Image Selection ----
    # Use the Plan's image if set and different from the default
    image = DEFAULT_AVENDER_POD_IMAGE
    if tenant.plan and tenant.plan.a0_image:
        plan_image = tenant.plan.a0_image
        # Only override if the plan specifies a non-default custom image
        if plan_image != DEFAULT_AVENDER_POD_IMAGE:
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
        "TENANT_VAULT_TOKEN_FILE": "/run/secrets/tenant_vault_token",
    }
    # Merge only non-secret deployment config. Secrets must stay in Vault and
    # must never appear in docker inspect environment output.
    if bootstrap_env:
        for key, value in bootstrap_env.items():
            if key in SECRET_BOOTSTRAP_KEYS:
                raise ValueError(f"Secret key {key} cannot be passed to Docker env.")
            env_vars[key] = str(value)

    volume_binds = {}
    # Workspace volume
    vol_name = _volume_name(tenant)
    volume_binds[vol_name] = {"bind": "/a0/usr/workdir", "mode": "rw"}
    vault_result = _start_tenant_vault(client, tenant, tenant_secrets)
    volume_binds[vault_result["token_volume"]] = {
        "bind": "/run/secrets",
        "mode": "ro",
    }

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
        labels={
            "avender.tenant_id": str(tenant.id),
            "avender.pod_name": name,
            "avender.managed_by": "sysadmin",
        },
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
    register_pod_deployment(
        tenant=tenant,
        pod_name=name,
        backend="docker",
        provider_resource_id=container.id,
        avender_container_id=container.id,
        image_tag=image,
        assigned_port=port,
        private_url=f"http://127.0.0.1:{port}",
        deployment_config=bootstrap_env,
        lifecycle_state="active",
        provider_health_state="healthy",
        tenant_vault_container_id=vault_result["container_id"],
        tenant_vault_state=vault_result["state"],
    )

    return {
        "container_id": container.id,
        "container_name": name,
        "port": port,
        "image": image,
        "mem_limit": mem_limit,
        "cpu_limit": str(cpu_limit),
        "status": "running",
        "tenant_vault_container_id": vault_result["container_id"],
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
    set_pod_lifecycle(tenant, action="suspend", lifecycle_state="suspended")
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
    set_pod_lifecycle(tenant, action="reactivate", lifecycle_state="active")
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

    try:
        vault = client.containers.get(_vault_container_name(tenant))
        vault.stop(timeout=10)
        vault.remove(force=True)
    except NotFound:
        pass

    for vol_name in (
        _volume_name(tenant),
        _vault_data_volume_name(tenant),
        _vault_token_volume_name(tenant),
    ):
        try:
            volume = client.volumes.get(vol_name)
            volume.remove(force=True)
        except NotFound:
            pass

    tenant.status = "deleted"
    tenant.docker_container_id = None
    tenant.assigned_port = None
    tenant.save(update_fields=["status", "docker_container_id", "assigned_port"])
    set_pod_lifecycle(tenant, action="delete", lifecycle_state="deleted")
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
        try:
            vault = client.containers.get(_vault_container_name(tenant))
            vault_state = vault.attrs.get("State", {})
            tenant_vault_state = "healthy" if vault_state.get("Running", False) else "unhealthy"
        except NotFound:
            tenant_vault_state = "missing"
        return {
            "state": state.get("Status", "unknown"),
            "running": state.get("Running", False),
            "started_at": state.get("StartedAt", ""),
            "finished_at": state.get("FinishedAt", ""),
            "exit_code": state.get("ExitCode", -1),
            "oom_killed": state.get("OOMKilled", False),
            "container_id": container.short_id,
            "container_name": container.name,
            "tenant_vault_state": tenant_vault_state,
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
