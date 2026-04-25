from __future__ import annotations

# ruff: noqa: E402

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from usr.plugins.avender.helpers import db
from usr.plugins.avender.helpers.auth import (
    create_session,
    set_admin_password,
    verify_admin_password,
    verify_session,
)
from usr.plugins.avender.helpers.config import (
    get_setting,
    normalize_settings,
    save_settings,
)


def _use_temp_db(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "avender.db")
    monkeypatch.setattr(db, "_db_initialized", False)


def test_normalize_settings_maps_onboarding_payload_and_forces_age_gate(
    monkeypatch, tmp_path
):
    _use_temp_db(monkeypatch, tmp_path)

    normalized = normalize_settings(
        {
            "tradeName": "Tienda Uno",
            "payTransfer": True,
            "agentName": "Sofia",
            "archetype": "liquor",
            "requireAgeVerification": False,
        }
    )

    assert normalized["trade_name"] == "Tienda Uno"
    assert normalized["payments_transfer"] is True
    assert normalized["agent_name"] == "Sofia"
    assert normalized["require_age_verification"] is True


def test_save_settings_supports_legacy_and_canonical_reads(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    save_settings({"tradeName": "Local", "agent_name": "Ana"})

    assert get_setting("trade_name") == "Local"
    assert get_setting("tradeName") == "Local"
    assert get_setting("agentName") == "Ana"


def test_admin_password_is_hashed_and_sessions_verify(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)

    set_admin_password("correct horse")

    assert verify_admin_password("correct horse") is True
    assert verify_admin_password("wrong") is False

    token = create_session()
    ok, role = verify_session(token)
    assert ok is True
    assert role == "owner"
