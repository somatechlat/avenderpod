"""
Vultr Infrastructure Service — Real API integration.
Docs: https://www.vultr.com/api/#tag/instances
"""
import os
import requests
from django.conf import settings
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


def deploy_tenant_pod(tenant: Tenant) -> dict:
    """
    Deploy a new Vultr instance for this tenant using the Vultr REST API.
    https://www.vultr.com/api/#operation/create-instance

    Returns the Vultr API response dict on success, raises on failure.
    """
    # Determine the port for this tenant's Agent Zero pod
    # Each tenant gets a unique port in the 45001+ range
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
        "user_data": "",  # Base64 startup script would go here
    }

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
        raise RuntimeError(
            f"Vultr halt failed {response.status_code}: {response.text}"
        )

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
    Permanently destroy a Vultr instance.
    https://www.vultr.com/api/#operation/delete-instance
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
    tenant.save()
    return {"status": "deleted"}
