"""
Vultr Infrastructure Service — Real API integration.
Docs: https://www.vultr.com/api/#tag/instances
"""

import base64
import os
import shlex

import requests

from .models import Tenant

VULTR_API_BASE = "https://api.vultr.com/v2"


def get_vultr_api_key() -> str:
    """
    Retrieve the Vultr API key from environment.
    In production, this should be sourced from HashiCorp Vault via the
    hvac client. For now we enforce it exists as an env var — no fallback,
    no fake tokens.
    """
    key = os.environ.get("VULTR_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "VULTR_API_KEY environment variable is not set. "
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
      2. Pulls the Agent Zero image
      3. Creates a per-tenant Docker named volume
      4. Starts the container with resource limits and security hardening
      5. Runs a health-check loop to confirm startup
    """
    # Build env file contents with safe shell quoting
    env_lines = []
    for key, value in bootstrap_env.items():
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
# 2. Write tenant environment file
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
# 4. Pull Agent Zero image
# --------------------------------------------------------------------------
echo "[$(date -Iseconds)] Pulling image ${{A0_IMAGE:-agent0ai/agent-zero:latest}}..."
docker pull "${{A0_IMAGE:-agent0ai/agent-zero:latest}}"

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
CONTAINER_NAME="agent-zero-${{TENANT_ID}}"
if docker ps -a --format '{{{{.Names}}}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "[$(date -Iseconds)] Removing existing container $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME" || true
    docker rm "$CONTAINER_NAME" || true
fi

# --------------------------------------------------------------------------
# 7. Run the Agent Zero container
# --------------------------------------------------------------------------
echo "[$(date -Iseconds)] Starting container $CONTAINER_NAME on port ${{ASSIGNED_PORT}}..."
docker run -d \\
  --name "$CONTAINER_NAME" \\
  --restart unless-stopped \\
  --memory "${{A0_MEMORY_LIMIT:-3g}}" \\
  --cpus "${{A0_CPU_LIMIT:-2.0}}" \\
  --memory-reservation "${{A0_MEMORY_RESERVATION:-1g}}" \\
  --cpus "${{A0_CPU_RESERVATION:-1.0}}" \\
  --pids-limit 1000 \\
  --no-new-privileges \\
  --security-opt no-new-privileges:true \\
  --log-driver json-file \\
  --log-opt max-size=20m \\
  --log-opt max-file=5 \\
  -v "$VOLUME_NAME:/a0/usr/workdir" \\
  -p "${{ASSIGNED_PORT}}:80" \\
  -e "TENANT_ID=${{TENANT_ID}}" \\
  -e "AVENDER_SETUP_TOKEN=${{AVENDER_SETUP_TOKEN}}" \\
  -e "SYSADMIN_API_URL=${{SYSADMIN_API_URL}}" \\
  -e "SYSADMIN_API_KEY=${{SYSADMIN_API_KEY}}" \\
  -e "WHISPER_API_URL=${{WHISPER_API_URL}}" \\
  -e "WHISPER_API_KEY=${{WHISPER_API_KEY}}" \\
  -e "MCP_SERVER_TOKEN=${{MCP_SERVER_TOKEN}}" \\
  -e "WEB_UI_HOST=0.0.0.0" \\
  "${{A0_IMAGE:-agent0ai/agent-zero:latest}}"

# --------------------------------------------------------------------------
# 8. Health check loop
# --------------------------------------------------------------------------
echo "[$(date -Iseconds)] Waiting for Agent Zero health check..."
sleep 15

HEALTHY=false
for i in {{1..30}}; do
    if curl -sf "http://localhost:${{ASSIGNED_PORT}}" > /dev/null 2>&1; then
        echo "[$(date -Iseconds)] Agent Zero is healthy on port ${{ASSIGNED_PORT}}"
        HEALTHY=true
        break
    fi
    echo "[$(date -Iseconds)] Health check attempt $i/30..."
    sleep 10
done

if [ "$HEALTHY" != "true" ]; then
    echo "[$(date -Iseconds)] CRITICAL: Agent Zero failed to start. Check logs:"
    docker logs "$CONTAINER_NAME" | tail -n 50
    exit 1
fi

echo "[$(date -Iseconds)] Bootstrap complete."
"""
    return script


def deploy_tenant_pod(
    tenant: Tenant, bootstrap_env: dict[str, str] | None = None
) -> dict:
    """
    Deploy a new Vultr instance for this tenant using the Vultr REST API.
    https://www.vultr.com/api/#operation/create-instance

    Returns the Vultr API response dict on success, raises on failure.
    """
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
        "plan": os.environ.get("VULTR_PLAN", "vc2-1c-1gb"),
        "os_id": int(os.environ.get("VULTR_OS_ID", "2136")),  # Docker on Ubuntu
        "label": f"avender-{tenant.name[:30]}-{tenant.id.hex[:8]}",
        "hostname": f"avender-{tenant.id.hex[:12]}",
        "tag": "avender-saas",
        "user_data": "",
    }
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
    return {"status": "deleted"}
