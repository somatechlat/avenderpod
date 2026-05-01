#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://vault:8200").rstrip("/")
MOUNT = os.environ.get("VAULT_KV_MOUNT", "secret").strip("/") or "secret"
SECRETS_DIR = Path(os.environ.get("AVENDER_SECRETS_DIR", "/avender/secrets"))
BOOTSTRAP_DIR = Path(os.environ.get("VAULT_BOOTSTRAP_DIR", "/avender/secrets/vault"))


def request(method: str, path: str, payload: dict | None = None, token: str = "") -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    req = Request(f"{VAULT_ADDR}{path}", data=body, headers=headers, method=method)
    with urlopen(req, timeout=10) as response:
        data = response.read()
    return json.loads(data.decode("utf-8")) if data else {}


def health() -> tuple[int, dict]:
    req = Request(f"{VAULT_ADDR}/v1/sys/health", method="GET")
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def wait_for_vault() -> dict:
    for _ in range(60):
        try:
            _, payload = health()
            return payload
        except (URLError, TimeoutError, ConnectionError):
            time.sleep(1)
    raise SystemExit("Vault did not become reachable.")


def read_file(name: str) -> str:
    return (SECRETS_DIR / name).read_text(encoding="utf-8").strip()


def write_secret_file(name: str, value: str) -> None:
    SECRETS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = SECRETS_DIR / name
    target.write_text(value, encoding="utf-8")
    target.chmod(0o600)


def root_token(initialized: bool) -> str:
    token_file = SECRETS_DIR / "vault_token"
    if initialized and token_file.exists() and token_file.read_text(encoding="utf-8").strip():
        return token_file.read_text(encoding="utf-8").strip()

    payload = request(
        "POST", "/v1/sys/init", {"secret_shares": 1, "secret_threshold": 1}
    )
    BOOTSTRAP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    unseal_key = payload["keys_base64"][0]
    token = payload["root_token"]
    (BOOTSTRAP_DIR / "unseal_key").write_text(unseal_key, encoding="utf-8")
    (BOOTSTRAP_DIR / "root_token").write_text(token, encoding="utf-8")
    (BOOTSTRAP_DIR / "unseal_key").chmod(0o600)
    (BOOTSTRAP_DIR / "root_token").chmod(0o600)
    write_secret_file("vault_token", token)
    return token


def unseal_if_needed(token: str) -> None:
    payload = health()
    if payload[1].get("sealed") is False:
        return

    unseal_file = BOOTSTRAP_DIR / "unseal_key"
    if not unseal_file.exists():
        raise SystemExit("Vault is sealed and no unseal key exists.")
    request("POST", "/v1/sys/unseal", {"key": unseal_file.read_text().strip()})


def enable_kv(token: str) -> None:
    try:
        mounts = request("GET", "/v1/sys/mounts", token=token)
        if f"{MOUNT}/" in mounts:
            return
        request(
            "POST",
            f"/v1/sys/mounts/{MOUNT}",
            {"type": "kv", "options": {"version": "2"}},
            token=token,
        )
    except HTTPError as exc:
        if exc.code != 400:
            raise


def write_kv(token: str, path: str, data: dict[str, str]) -> None:
    request("POST", f"/v1/{MOUNT}/data/{path}", {"data": data}, token=token)


def seed_secrets(token: str) -> None:
    write_kv(
        token,
        "avender/sysadmin",
        {
            "POSTGRES_PASSWORD": read_file("postgres_password"),
            "DJANGO_SECRET_KEY": read_file("django_secret_key"),
            "DJANGO_SUPERUSER_PASSWORD": read_file("django_superuser_password"),
            "SYSADMIN_API_KEY": read_file("sysadmin_api_key"),
            "VULTR_API_KEY": read_file("vultr_api_key"),
        },
    )
    write_kv(
        token,
        "avender/dev-agent",
        {"AVENDER_SETUP_TOKEN": read_file("avender_setup_token")},
    )


def main() -> None:
    state = wait_for_vault()
    token = root_token(bool(state.get("initialized")))
    unseal_if_needed(token)
    enable_kv(token)
    seed_secrets(token)


if __name__ == "__main__":
    main()
