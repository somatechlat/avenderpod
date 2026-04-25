"""Shared storage paths for the WhatsApp bridge."""

import os
import re
from helpers import files


def _scope_component() -> str:
    raw = (
        os.environ.get("WHATSAPP_NUMBER_ID")
        or os.environ.get("TENANT_ID")
        or "default"
    )
    value = str(raw).strip()
    if not value:
        value = "default"
    # Keep path-safe chars only.
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)[:80]


def get_bridge_session_dir() -> str:
    scope = _scope_component()
    return files.get_abs_path("usr", "plugins", "_whatsapp_integration", "session", scope)


def get_bridge_media_dir() -> str:
    scope = _scope_component()
    return files.get_abs_path("usr", "plugins", "_whatsapp_integration", "media", scope)
