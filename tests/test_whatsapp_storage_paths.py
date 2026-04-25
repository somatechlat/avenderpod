import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helpers import files
from plugins._whatsapp_integration.helpers.storage_paths import (
    get_bridge_media_dir,
    get_bridge_session_dir,
)


def test_whatsapp_bridge_storage_paths_are_plugin_owned_and_scoped(monkeypatch):
    monkeypatch.setenv("TENANT_ID", "tenant/one")
    assert get_bridge_session_dir() == files.get_abs_path(
        "usr", "plugins", "_whatsapp_integration", "session", "tenant_one"
    )
    assert get_bridge_media_dir() == files.get_abs_path(
        "usr", "plugins", "_whatsapp_integration", "media", "tenant_one"
    )
