import asyncio
import os
import sqlite3
import threading
from typing import Any, cast

from flask import Flask

from usr.plugins.avender.api.onboarding_api import AvenderOnboardingHandler

AVENDER_DB = os.path.join(os.path.dirname(__file__), "..", "usr", "workdir", "avender.db")


def _reset_db() -> None:
    try:
        conn = sqlite3.connect(AVENDER_DB, timeout=30)
        c = conn.cursor()
        c.execute("DELETE FROM tenant_config WHERE key='onboarding_complete'")
        conn.commit()
        conn.close()
    except Exception:
        pass


def _handler() -> AvenderOnboardingHandler:
    return AvenderOnboardingHandler(Flask(__name__), threading.Lock())


def _valid_payload() -> dict:
    return {
        "idType": "RUC",
        "idNumber": "1790012345001",
        "tradeName": "Valid Business",
        "headquarters": "Quito Centro",
        "archetype": "restaurant",
        "whatsappNumber": "+593997202547",
        "adminPassword": "SecureAdminPass123!",
        "catalogItems": [
            {"name": "Item", "price": 1, "description": "", "metadata": {}}
        ],
    }


def test_onboarding_requires_headquarters():
    _reset_db()
    payload = _valid_payload()
    payload["headquarters"] = ""

    result = cast(
        dict[str, Any],
        asyncio.run(
            _handler().process(payload, request=cast(Any, object()))
        ),
    )
    assert result["ok"] is False
    assert "headquarters" in result["error"]


def test_onboarding_requires_allowed_numbers_when_restricted():
    _reset_db()
    payload = _valid_payload()
    payload["restrictAccess"] = True
    payload["allowedNumbers"] = ""

    result = cast(
        dict[str, Any],
        asyncio.run(
            _handler().process(payload, request=cast(Any, object()))
        ),
    )
    assert result["ok"] is False
    assert "Lista Blanca" in result["error"]


def test_onboarding_requires_setup_token_when_configured(monkeypatch):
    _reset_db()
    monkeypatch.setenv("AVENDER_SETUP_TOKEN", "t" * 32)

    result = cast(
        dict[str, Any],
        asyncio.run(_handler().process(_valid_payload(), request=cast(Any, object()))),
    )

    assert result["ok"] is False
    assert "Token de activación" in result["error"]


def test_onboarding_accepts_setup_token_when_configured(monkeypatch):
    _reset_db()
    monkeypatch.setenv("AVENDER_SETUP_TOKEN", "t" * 32)
    payload = _valid_payload()
    payload["setupToken"] = "t" * 32

    result = cast(
        dict[str, Any],
        asyncio.run(_handler().process(payload, request=cast(Any, object()))),
    )

    assert result["ok"] is True
