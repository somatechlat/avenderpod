from __future__ import annotations

import json
from typing import Any

from usr.plugins.avender.helpers.db import get_tenant_config, save_tenant_config


AGE_GATE_ARCHETYPES = {"liquor", "licoreria", "cbd", "cannabis"}


CANONICAL_KEYS = {
    "id_type",
    "id_number",
    "legal_name",
    "trade_name",
    "headquarters",
    "hours",
    "delivery_rules",
    "payments_transfer",
    "payments_cash",
    "payments_link",
    "payment_link_url",
    "archetype",
    "policies",
    "promotions",
    "agent_name",
    "agent_language",
    "agent_tone",
    "agent_slang",
    "agent_emoji_density",
    "whatsapp_number",
    "restrict_access",
    "allowed_numbers",
    "require_age_verification",
    "onboarding_complete",
}


LEGACY_TO_CANONICAL = {
    "idType": "id_type",
    "idNumber": "id_number",
    "legalName": "legal_name",
    "tradeName": "trade_name",
    "headquarters": "headquarters",
    "hours": "hours",
    "deliveryRules": "delivery_rules",
    "payTransfer": "payments_transfer",
    "payCash": "payments_cash",
    "payLink": "payments_link",
    "paymentUrl": "payment_link_url",
    "archetype": "archetype",
    "policies": "policies",
    "promotions": "promotions",
    "agentName": "agent_name",
    "language": "agent_language",
    "tone": "agent_tone",
    "useSlang": "agent_slang",
    "emojis": "agent_emoji_density",
    "whatsappNumber": "whatsapp_number",
    "restrictAccess": "restrict_access",
    "allowedNumbers": "allowed_numbers",
    "requireAgeVerification": "require_age_verification",
    "onboarding_complete": "onboarding_complete",
}


CANONICAL_TO_LEGACY = {value: key for key, value in LEGACY_TO_CANONICAL.items()}


def _parse_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value in {"true", "false"}:
        return value == "true"
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def normalize_settings(input_data: dict[str, Any]) -> dict[str, Any]:
    """Convert wizard/admin payloads to Avender's canonical tenant config keys."""
    normalized: dict[str, Any] = {}
    for key, value in input_data.items():
        canonical = LEGACY_TO_CANONICAL.get(key, key)
        if canonical in CANONICAL_KEYS:
            normalized[canonical] = value

    archetype = str(normalized.get("archetype", "")).lower()
    if archetype in AGE_GATE_ARCHETYPES:
        normalized["require_age_verification"] = True

    return normalized


def get_settings() -> dict[str, Any]:
    raw = get_tenant_config() or {}
    result: dict[str, Any] = {}
    for key, value in raw.items():
        canonical = LEGACY_TO_CANONICAL.get(key, key)
        result[canonical] = _parse_value(value)
    return result


def save_settings(input_data: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_settings(input_data)
    save_tenant_config(normalized)
    return normalized


def get_setting(key: str, default: Any = None) -> Any:
    settings = get_settings()
    canonical = LEGACY_TO_CANONICAL.get(key, key)
    return settings.get(canonical, default)


def settings_for_ui() -> dict[str, Any]:
    settings = get_settings()
    for canonical, legacy in CANONICAL_TO_LEGACY.items():
        if canonical in settings and legacy not in settings:
            settings[legacy] = settings[canonical]
    return settings
