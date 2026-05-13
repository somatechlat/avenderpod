"""
Vultr Infrastructure Service — Real API integration.
Docs: https://www.vultr.com/api/#tag/instances
"""

import base64
import os
import shlex

import requests

from .models import Tenant
from .pod_registry import register_pod_deployment, set_pod_lifecycle
from .secret_values import read_secret
from .vault_service import SECRET_BOOTSTRAP_KEYS

VULTR_API_BASE = "https://api.vultr.com/v2"


def get_vultr_api_key() -> str:
    """
    Retrieve the Vultr API key from a Vault/Docker secret file.
    """
    key = read_secret("VULTR_API_KEY")
    if not key:
        raise EnvironmentError(
            "VULTR_API_KEY_FILE is not set. "
            "Cannot perform infrastructure operations without it."
        )
    return key


def _vultr_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_vultr_api_key()}",
        "Content-Type": "application/json",
    }


def _build_user_data_script(tenant: Tenant, bootstrap_env: dict[str, str]) -> str:
    """
    Build a complete cloud-init user-data script that:
      1. Installs Docker Engine
      2. Pulls the Avender Pod image
      3. Creates a per-tenant Docker named volume
      4. Starts the container with resource limits and security hardening
      5. Runs a health-check loop to confirm startup
    """
    env_lines = []
    for key, value in bootstrap_env.items():
        if key in SECRET_BOOTSTRAP_KEYS:
            raise ValueError(f"Secret key {key} cannot be passed in Vultr user_data.")
        env_lines.append(f"{key}={shlex.quote(str(value))}")
    env_file_contents = "\n".join(env_lines)

    script = f"""#!/bin/bash
set -euo pipefail

# ============================================================================
# Avender Tenant Bootstrap — Cloud-Init User Data
# Tenant: {tenant.name} ({tenant.id})
# ============================================================================

LOG_FILE="/var/log/avender-bootstrap.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[$(date -Iseconds)] Starting Avender tenant bootstrap..."

# --------------------------------------------------------------------------
# 1. Install Docker Engine (if not present)
# --------------------------------------------------------------------------
if ! command -v docker &> /dev/null; then
    echo "[$(date -Iseconds)] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[$(date -Iseconds)] Docker already installed."
fi

# Wait for Docker to be ready
for i in {{1..30}}; do
    if docker info &> /dev/null; then
        break
    fi
    echo "[$(date -Iseconds)] Waiting for Docker daemon..."
    sleep 2
done

# --------------------------------------------------------------------------
	# 2. Write tenant non-secret config
# --------------------------------------------------------------------------
	install -d -m 700 /etc/avender
	cat >/etc/avender/tenant.env <<'EOF'
	{env_file_contents}
	EOF
	chmod 600 /etc/avender/tenant.env

	echo 'tenant={tenant.id}' >/etc/avender/provisioned.info

# --------------------------------------------------------------------------
# 3. Load environment
# --------------------------------------------------------------------------
set -a
source /etc/avender/tenant.env
set +a

# --------------------------------------------------------------------------
# 4. Pull Avender Pod image
# --------------------------------------------------------------------------
echo "[$(date -Iseconds)] Pulling image ${{A0_IMAGE:-avenderpod:latest}}..."
docker pull "${{A0_IMAGE:-avenderpod:latest}}"

# --------------------------------------------------------------------------
# 5. Create per-tenant named volume
# --------------------------------------------------------------------------
VOLUME_NAME="a0_${{TENANT_ID}}"
if ! docker volume inspect "$VOLUME_NAME" &> /dev/null; then
    echo "[$(date -Iseconds)] Creating Docker volume $VOLUME_NAME..."
    docker volume create "$VOLUME_NAME"
else
    echo "[$(date -Iseconds)] Volume $VOLUME_NAME already exists."
fi

# --------------------------------------------------------------------------
# 6. Stop and remove any existing container for this tenant
# --------------------------------------------------------------------------
CONTAINER_NAME="avenderpod-${{TENANT_ID}}"
if docker ps -a --format '{{{{.Names}}}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "[$(date -Iseconds)] Removing existing container $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME" || true
    docker rm "$CONTAINER_NAME" || true
fi

# --------------------------------------------------------------------------
# 7. Run the Avender Pod container
# --------------------------------------------------------------------------
echo "[$(date -Iseconds)] Starting container $CONTAINER_NAME on port ${{ASSIGNED_PORT}}..."
docker run -d \\
  --name "$CONTAINER_NAME" \\
  --restart unless-stopped \\
  --memory "${{A0_MEMORY_LIMIT:-3g}}" \\
  --cpus "${{A0_CPU_LIMIT:-2.0}}" \\
  --memory-reservation "${{A0_MEMORY_RESERVATION:-1g}}" \\
  --pids-limit 1000 \\
  --no-new-privileges \\
  --security-opt no-new-privileges:true \\
  --log-driver json-file \\
  --log-opt max-size=20m \\
  --log-opt max-file=5 \\
  -v "$VOLUME_NAME:/a0/usr/workdir" \\
  -p "${{ASSIGNED_PORT}}:80" \\
  -e "TENANT_ID=${{TENANT_ID}}" \\
  -e "A0_PLAN_ID=${{A0_PLAN_ID:-}}" \\
  -e "A0_PLAN_NAME=${{A0_PLAN_NAME:-}}" \\
  -e "A0_MAX_CONVERSATIONS_PER_MONTH=${{A0_MAX_CONVERSATIONS_PER_MONTH:-0}}" \\
  -e "A0_MAX_MESSAGES_PER_DAY=${{A0_MAX_MESSAGES_PER_DAY:-0}}" \\
  -e "A0_MAX_MESSAGES_PER_MINUTE=${{A0_MAX_MESSAGES_PER_MINUTE:-0}}" \\
  -e "A0_MAX_WHATSAPP_NUMBERS=${{A0_MAX_WHATSAPP_NUMBERS:-0}}" \\
  -e "A0_MAX_CATALOG_ITEMS=${{A0_MAX_CATALOG_ITEMS:-0}}" \\
  -e "A0_MAX_TRANSCRIPTION_MINUTES_PER_MONTH=${{A0_MAX_TRANSCRIPTION_MINUTES_PER_MONTH:-0}}" \\
  -e "A0_MAX_STORAGE_MB=${{A0_MAX_STORAGE_MB:-0}}" \\
  -e "A0_MAX_USERS=${{A0_MAX_USERS:-0}}" \\
  -e "A0_MAX_AGENT_CONTEXTS=${{A0_MAX_AGENT_CONTEXTS:-0}}" \\
  -e "A0_ALLOW_CATALOG_UPLOAD=${{A0_ALLOW_CATALOG_UPLOAD:-False}}" \\
  -e "A0_ALLOW_VOICE_MESSAGES=${{A0_ALLOW_VOICE_MESSAGES:-False}}" \\
  -e "A0_ALLOW_HUMAN_HANDOFF=${{A0_ALLOW_HUMAN_HANDOFF:-False}}" \\
  -e "A0_ALLOW_CREATOR_OVERRIDE=${{A0_ALLOW_CREATOR_OVERRIDE:-False}}" \\
  -e "A0_ALLOW_CUSTOM_DOMAIN=${{A0_ALLOW_CUSTOM_DOMAIN:-False}}" \\
  -e "A0_ALLOW_INTEGRATIONS=${{A0_ALLOW_INTEGRATIONS:-False}}" \\
	  -e "SYSADMIN_API_URL=${{SYSADMIN_API_URL}}" \\
	  -e "TENANT_VAULT_ADDR=${{TENANT_VAULT_ADDR}}" \\
	  -e "TENANT_VAULT_KV_MOUNT=${{TENANT_VAULT_KV_MOUNT}}" \\
	  -e "TENANT_VAULT_SECRET_PATH=${{TENANT_VAULT_SECRET_PATH}}" \\
	  -e "STT_MODEL_SIZE=${{STT_MODEL_SIZE:-base}}" \\
	  -e "STT_LANGUAGE=${{STT_LANGUAGE:-es}}" \\
	  -e "WEB_UI_HOST=0.0.0.0" \\
	  "${{A0_IMAGE:-avenderpod:latest}}"

# --------------------------------------------------------------------------
# 8. Health check loop
# --------------------------------------------------------------------------
echo "[$(date -Iseconds)] Waiting for Avender Pod health check..."
sleep 15

HEALTHY=false
for i in {{1..30}}; do
    if curl -sf "http://localhost:${{ASSIGNED_PORT}}" > /dev/null 2>&1; then
        echo "[$(date -Iseconds)] Avender Pod is healthy on port ${{ASSIGNED_PORT}}"
        HEALTHY=true
        break
    fi
    echo "[$(date -Iseconds)] Health check attempt $i/30..."
    sleep 10
done

if [ "$HEALTHY" != "true" ]; then
    echo "[$(date -Iseconds)] CRITICAL: Avender Pod failed to start. Check logs:"
    docker logs "$CONTAINER_NAME" | tail -n 50
    exit 1
fi

# --------------------------------------------------------------------------
# 9. Disk cleanup — keep image as small as possible
# --------------------------------------------------------------------------
echo "[$(date -Iseconds)] Running disk cleanup..."
docker image prune -af --filter "until=1h" || true
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

echo "[$(date -Iseconds)] Bootstrap complete."
"""
    return script


def deploy_tenant_pod(
    tenant: Tenant,
    bootstrap_env: dict[str, str] | None = None,
    tenant_secrets: dict[str, str] | None = None,
) -> dict:
    """
    Deploy a new Vultr instance for this tenant using the Vultr REST API.
    https://www.vultr.com/api/#operation/create-instance

    Returns the Vultr API response dict on success, raises on failure.
    """
    if tenant_secrets:
        raise RuntimeError(
            "Vultr tenant-local Vault provisioning requires a secure post-boot "
            "secret delivery channel. Refusing to place tenant secrets in cloud-init."
        )
    # Use pre-assigned port if available (set by api.py during bootstrap).
    # Otherwise compute a unique port in the 45001+ range.
    if tenant.assigned_port:
        assigned_port = tenant.assigned_port
    else:
        existing_ports = set(
            Tenant.objects.exclude(id=tenant.id)
            .exclude(assigned_port__isnull=True)
            .values_list("assigned_port", flat=True)
        )
        assigned_port = 45001
        while assigned_port in existing_ports:
            assigned_port += 1
        tenant.assigned_port = assigned_port

    payload = {
        "region": os.environ.get("VULTR_REGION", "mia"),
        "plan": (
            tenant.plan.vultr_plan
            if tenant.plan
            else os.environ.get("VULTR_PLAN", "vc2-2c-4gb")
        ),
        "os_id": int(os.environ.get("VULTR_OS_ID", "2136")),  # Docker on Ubuntu
        "label": f"avender-{tenant.name[:30]}-{tenant.id.hex[:8]}",
        "hostname": f"avender-{tenant.id.hex[:12]}",
        "tag": "avender-saas",
        "user_data": "",
    }

    # Attach to VPC and firewall group if configured
    vpc_id = os.environ.get("VULTR_VPC_ID", "").strip()
    if vpc_id:
        payload["vpc_id"] = vpc_id
    firewall_group_id = os.environ.get("VULTR_FIREWALL_GROUP_ID", "").strip()
    if firewall_group_id:
        payload["firewall_group_id"] = firewall_group_id
    if bootstrap_env:
        script = _build_user_data_script(tenant, bootstrap_env)
        payload["user_data"] = base64.b64encode(script.encode("utf-8")).decode("ascii")

    response = requests.post(
        f"{VULTR_API_BASE}/instances",
        headers=_vultr_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201, 202):
        tenant.status = "pending"
        tenant.save()
        raise RuntimeError(
            f"Vultr API returned {response.status_code}: {response.text}"
        )

    data = response.json()
    instance = data.get("instance", {})

    tenant.vultr_instance_id = instance.get("id", "")
    tenant.status = "active"
    tenant.save()
    register_pod_deployment(
        tenant=tenant,
        pod_name=f"avenderpod-{tenant.id}",
        backend="vultr",
        provider_resource_id=tenant.vultr_instance_id,
        image_tag=(tenant.plan.a0_image if tenant.plan else "avenderpod:latest"),
        assigned_port=tenant.assigned_port,
        deployment_config=bootstrap_env,
        lifecycle_state="active",
        provider_health_state="unknown",
        tenant_vault_state="unknown",
    )

    return data


def suspend_tenant_pod(tenant: Tenant) -> dict:
    """
    Halt (stop) a Vultr instance for a suspended tenant.
    https://www.vultr.com/api/#operation/halt-instances
    """
    if not tenant.vultr_instance_id:
        raise ValueError(f"Tenant {tenant.name} has no Vultr instance to suspend.")

    response = requests.post(
        f"{VULTR_API_BASE}/instances/{tenant.vultr_instance_id}/halt",
        headers=_vultr_headers(),
        timeout=30,
    )

    if response.status_code not in (200, 204):
        raise RuntimeError(f"Vultr halt failed {response.status_code}: {response.text}")

    tenant.status = "suspended"
    tenant.save()
    set_pod_lifecycle(tenant, action="suspend", lifecycle_state="suspended")
    return {"status": "halted", "instance_id": tenant.vultr_instance_id}


def reactivate_tenant_pod(tenant: Tenant) -> dict:
    """
    Start a previously halted Vultr instance.
    https://www.vultr.com/api/#operation/start-instance
    """
    if not tenant.vultr_instance_id:
        raise ValueError(f"Tenant {tenant.name} has no Vultr instance to start.")

    response = requests.post(
        f"{VULTR_API_BASE}/instances/{tenant.vultr_instance_id}/start",
        headers=_vultr_headers(),
        timeout=30,
    )

    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"Vultr start failed {response.status_code}: {response.text}"
        )

    tenant.status = "active"
    tenant.save()
    set_pod_lifecycle(tenant, action="reactivate", lifecycle_state="active")
    return {"status": "started", "instance_id": tenant.vultr_instance_id}


def delete_tenant_pod(tenant: Tenant) -> dict:
    """
    Permanently destroy a Vultr instance and clean up Docker volumes.
    """
    if not tenant.vultr_instance_id:
        raise ValueError(f"Tenant {tenant.name} has no Vultr instance to delete.")

    response = requests.delete(
        f"{VULTR_API_BASE}/instances/{tenant.vultr_instance_id}",
        headers=_vultr_headers(),
        timeout=30,
    )

    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"Vultr delete failed {response.status_code}: {response.text}"
        )

    tenant.status = "deleted"
    tenant.vultr_instance_id = ""
    tenant.assigned_port = None
    tenant.save()
    set_pod_lifecycle(tenant, action="delete", lifecycle_state="deleted")
    return {"status": "deleted"}
