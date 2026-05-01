#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SECRET_MAP = {
    "postgres_password": ("avender/sysadmin", "POSTGRES_PASSWORD"),
    "django_secret_key": ("avender/sysadmin", "DJANGO_SECRET_KEY"),
    "django_superuser_password": ("avender/sysadmin", "DJANGO_SUPERUSER_PASSWORD"),
    "sysadmin_api_key": ("avender/sysadmin", "SYSADMIN_API_KEY"),
    "vultr_api_key": ("avender/sysadmin", "VULTR_API_KEY"),
    "avender_setup_token": ("avender/dev-agent", "AVENDER_SETUP_TOKEN"),
}


def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def vault_token() -> str:
    token_file = env("VAULT_TOKEN_FILE")
    token = read_file(token_file) if token_file else env("VAULT_TOKEN")
    if not token:
        raise SystemExit("VAULT_TOKEN_FILE is required to materialize secrets.")
    return token


def read_vault_secret(addr: str, token: str, mount: str, namespace: str, path: str) -> dict:
    url = f"{addr.rstrip('/')}/v1/{mount}/data/{path}"
    headers = {"X-Vault-Token": token}
    if namespace:
        headers["X-Vault-Namespace"] = namespace
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=float(env("VAULT_TIMEOUT_SECONDS", "10"))) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Vault read failed for {path}: {exc.code} {detail}") from exc
    return payload["data"]["data"]


def main() -> None:
    addr = env("VAULT_ADDR")
    if not addr:
        raise SystemExit("VAULT_ADDR is required.")
    mount = env("VAULT_KV_MOUNT", "secret")
    namespace = env("VAULT_NAMESPACE")
    token = vault_token()
    output_dir = Path(env("AVENDER_SECRETS_DIR", "./secrets"))
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    cache: dict[str, dict] = {}
    for file_name, (vault_path, field) in SECRET_MAP.items():
        if vault_path not in cache:
            cache[vault_path] = read_vault_secret(addr, token, mount, namespace, vault_path)
        value = str(cache[vault_path].get(field, "")).strip()
        if not value:
            raise SystemExit(f"Vault field {vault_path}.{field} is empty.")
        target = output_dir / file_name
        target.write_text(value, encoding="utf-8")
        target.chmod(0o600)

    vault_token_file = output_dir / "vault_token"
    if env("VAULT_TOKEN_FILE"):
        vault_token_file.write_text(token, encoding="utf-8")
        vault_token_file.chmod(0o600)


if __name__ == "__main__":
    main()
