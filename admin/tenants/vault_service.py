from __future__ import annotations

import os
import secrets
from typing import Any

import requests

from .models import ServiceCredential, Tenant, VaultRecord
from .secret_values import read_secret


def _get_env(name: str, *, required: bool = True, default: str = "") -> str:
    value = read_secret(name, default=default)
    if required and not value:
        raise EnvironmentError(
            f"{name} environment variable is required for Vault provisioning."
        )
    return value


def _vault_headers(token: str, namespace: str) -> dict[str, str]:
    headers = {"X-Vault-Token": token, "Content-Type": "application/json"}
    if namespace:
        headers["X-Vault-Namespace"] = namespace
    return headers


def _vault_kv_mount() -> str:
    return _get_env("VAULT_KV_MOUNT", required=False, default="secret")


def _tenant_secret_path(tenant: Tenant) -> str:
    return f"avender/tenants/{tenant.id}"


def _sysadmin_api_key() -> str:
    key = _get_env("SYSADMIN_API_KEY")
    if len(key) < 32:
        raise EnvironmentError("SYSADMIN_API_KEY must be at least 32 characters.")
    return key


def build_tenant_secret_bundle(tenant: Tenant) -> dict[str, str]:
    tenant_api_key = secrets.token_urlsafe(48)
    ServiceCredential.objects.update_or_create(
        tenant=tenant,
        name="tenant-runtime",
        defaults={
            "key_prefix": tenant_api_key[:12],
            "key_hash": ServiceCredential.hash_key(tenant_api_key),
            "is_active": True,
            "scopes": [
                "tenant:status",
                "tenant:usage",
                "creator_override:init",
                "creator_override:verify",
            ],
        },
    )
    return {
        "TENANT_ID": str(tenant.id),
        "AVENDER_SETUP_TOKEN": secrets.token_hex(32),
        "MCP_SERVER_TOKEN": secrets.token_hex(32),
        "SYSADMIN_TENANT_API_KEY": tenant_api_key,
    }


def write_tenant_secrets_to_vault(
    tenant: Tenant, secrets_bundle: dict[str, Any]
) -> str:
    addr = _get_env("VAULT_ADDR")
    token = _get_env("VAULT_TOKEN")
    namespace = _get_env("VAULT_NAMESPACE", required=False, default="")
    timeout = float(_get_env("VAULT_TIMEOUT_SECONDS", required=False, default="10"))
    mount = _vault_kv_mount()
    path = _tenant_secret_path(tenant)
    url = f"{addr.rstrip('/')}/v1/{mount}/data/{path}"

    response = requests.post(
        url,
        headers=_vault_headers(token, namespace),
        json={"data": secrets_bundle},
        timeout=timeout,
    )
    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"Vault write failed ({response.status_code}): {response.text}"
        )

    full_path = f"{mount}/{path}"
    VaultRecord.objects.update_or_create(
        tenant=tenant,
        vault_path=full_path,
        defaults={"description": "Tenant bootstrap/runtime secrets"},
    )
    return full_path


def provision_tenant_secrets(tenant: Tenant) -> dict[str, str]:
    secrets_bundle = build_tenant_secret_bundle(tenant)
    write_tenant_secrets_to_vault(tenant, secrets_bundle)
    return secrets_bundle


def build_tenant_bootstrap_env(
    tenant: Tenant,
    tenant_secrets: dict[str, str],
    assigned_port: int,
) -> dict[str, str]:
    # Cluster VPC IP is the private IP of the cluster control plane VM.
    # All tenant-to-cluster communication happens over the Vultr VPC.
    cluster_vpc_ip = os.environ.get("CLUSTER_VPC_IP", "").strip()

    # SysAdmin API is on port 45000 of the cluster VM
    sysadmin_url = _get_env(
        "SYSADMIN_API_URL",
        required=False,
        default=f"http://{cluster_vpc_ip}:45000/api/saas" if cluster_vpc_ip else "",
    )
    if not sysadmin_url:
        raise EnvironmentError(
            "CLUSTER_VPC_IP (or SYSADMIN_API_URL) must be set for tenant bootstrap."
        )

    plan = tenant.plan
    a0_image = (
        plan.a0_image
        if plan
        else _get_env(
            "A0_IMAGE", required=False, default="agent0ai/agent-zero-tenant:latest"
        )
    )

    return {
        "TENANT_ID": str(tenant.id),
        "A0_PLAN_ID": str(plan.id) if plan else "",
        "A0_PLAN_NAME": plan.name if plan else "",
        "A0_MAX_CONVERSATIONS_PER_MONTH": str(plan.max_conversations if plan else 0),
        "A0_MAX_MESSAGES_PER_DAY": str(plan.max_messages_per_day if plan else 0),
        "A0_MAX_MESSAGES_PER_MINUTE": str(plan.max_messages_per_minute if plan else 0),
        "A0_MAX_WHATSAPP_NUMBERS": str(plan.max_numbers if plan else 0),
        "A0_MAX_CATALOG_ITEMS": str(plan.max_catalog_items if plan else 0),
        "A0_MAX_TRANSCRIPTION_MINUTES_PER_MONTH": str(
            plan.max_transcription_minutes if plan else 0
        ),
        "A0_MAX_STORAGE_MB": str(plan.max_storage_mb if plan else 0),
        "A0_MAX_USERS": str(plan.max_users if plan else 0),
        "A0_MAX_AGENT_CONTEXTS": str(plan.max_agent_contexts if plan else 0),
        "A0_ALLOW_CATALOG_UPLOAD": str(plan.allow_catalog_upload if plan else False),
        "A0_ALLOW_VOICE_MESSAGES": str(plan.allow_voice_messages if plan else False),
        "A0_ALLOW_HUMAN_HANDOFF": str(plan.allow_human_handoff if plan else False),
        "A0_ALLOW_CREATOR_OVERRIDE": str(
            plan.allow_creator_override if plan else False
        ),
        "A0_ALLOW_CUSTOM_DOMAIN": str(plan.allow_custom_domain if plan else False),
        "A0_ALLOW_INTEGRATIONS": str(plan.allow_integrations if plan else False),
        "A0_ALLOW_MOBILE_APP": str(plan.allow_mobile_app if plan else False),
        "A0_ALLOW_MULTICHANNEL": str(plan.allow_multichannel if plan else False),
        "A0_ALLOW_OUTBOUND_REACTIVATION": str(
            plan.allow_outbound_reactivation if plan else False
        ),
        "A0_ALLOW_CALL_HANDLING": str(plan.allow_call_handling if plan else False),
        "SYSADMIN_API_URL": sysadmin_url,
        "SYSADMIN_API_KEY": tenant_secrets.get("SYSADMIN_TENANT_API_KEY")
        or _sysadmin_api_key(),
        "AVENDER_SETUP_TOKEN": tenant_secrets["AVENDER_SETUP_TOKEN"],
        "MCP_SERVER_TOKEN": tenant_secrets["MCP_SERVER_TOKEN"],
        "STT_MODEL_SIZE": "base",
        "STT_LANGUAGE": "es",
        "ASSIGNED_PORT": str(assigned_port),
        "A0_IMAGE": a0_image,
        "A0_MEMORY_LIMIT": plan.a0_memory_limit if plan else "3g",
        "A0_CPU_LIMIT": plan.a0_cpu_limit if plan else "2.0",
        "A0_MEMORY_RESERVATION": plan.a0_memory_reservation if plan else "1g",
        "A0_CPU_RESERVATION": plan.a0_cpu_reservation if plan else "1.0",
    }
