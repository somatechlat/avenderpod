from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from helpers.api import Request
from usr.plugins.avender.helpers.db import (
    get_connection,
    get_tenant_config,
    save_tenant_config,
)


SESSION_HOURS = 12
PASSWORD_KEY = "admin_password_hash"
LEGACY_PASSWORD_KEY = "adminPassword"


def _hash_password(password: str, *, salt: str | None = None) -> str:
    if not password:
        raise ValueError("Password is required")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), 200_000
    )
    return f"pbkdf2_sha256$200000${salt}${digest.hex()}"


def _verify_hash(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("ascii"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def set_admin_password(password: str) -> None:
    save_tenant_config({PASSWORD_KEY: _hash_password(password)})


def verify_admin_password(password: str) -> bool:
    encoded = get_tenant_config(PASSWORD_KEY)
    if isinstance(encoded, str) and _verify_hash(password, encoded):
        return True

    legacy = get_tenant_config(LEGACY_PASSWORD_KEY)
    if legacy and hmac.compare_digest(str(password), str(legacy)):
        set_admin_password(password)
        return True

    return False


def create_session(role: str = "owner") -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=SESSION_HOURS)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO auth_sessions (token, role, expires_at) VALUES (?, ?, ?)",
        (token, role, expires_at.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    return token


def verify_session(token: str) -> tuple[bool, str]:
    if not token:
        return False, ""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, expires_at FROM auth_sessions WHERE token = ?", (token,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, ""
    expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires_at:
        cursor.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return False, ""
    role = str(row["role"])
    conn.close()
    return True, role


def delete_session(token: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def token_from_request(input_data: dict, request: Request) -> str:
    header = request.headers.get("X-Avender-Admin-Token", "")
    return header or input_data.get("admin_token", "") or input_data.get("token", "")


def require_admin_session(input_data: dict, request: Request) -> dict | None:
    ok, role = verify_session(token_from_request(input_data, request))
    if not ok:
        return {"ok": False, "error": "Sesión inválida o expirada."}
    return None
