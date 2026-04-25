from __future__ import annotations

import os
import secrets
from typing import Any

import requests

from .models import Tenant, VaultRecord


def _get_env(name: str, *, required: bool = True, default: str = "") -> str:
    value = os.environ.get(name, default).strip()
    if required and not value:
        raise EnvironmentError(f"{name} environment variable is required for Vault provisioning.")
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
    return {
        "TENANT_ID": str(tenant.id),
        "AVENDER_SETUP_TOKEN": secrets.token_hex(32),
        "MCP_SERVER_TOKEN": secrets.token_hex(32),
    }


def write_tenant_secrets_to_vault(tenant: Tenant, secrets_bundle: dict[str, Any]) -> str:
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
        raise RuntimeError(f"Vault write failed ({response.status_code}): {response.text}")

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


def build_tenant_bootstrap_env(tenant: Tenant, tenant_secrets: dict[str, str]) -> dict[str, str]:
    public_sysadmin_url = _get_env(
        "SYSADMIN_API_PUBLIC_URL",
        required=False,
        default=os.environ.get("SYSADMIN_API_URL", ""),
    )
    if not public_sysadmin_url:
        raise EnvironmentError(
            "SYSADMIN_API_PUBLIC_URL (or SYSADMIN_API_URL) must be set for tenant bootstrap."
        )

    return {
        "TENANT_ID": str(tenant.id),
        "SYSADMIN_API_URL": public_sysadmin_url,
        "SYSADMIN_API_KEY": _sysadmin_api_key(),
        "AVENDER_SETUP_TOKEN": tenant_secrets["AVENDER_SETUP_TOKEN"],
        "MCP_SERVER_TOKEN": tenant_secrets["MCP_SERVER_TOKEN"],
    }
