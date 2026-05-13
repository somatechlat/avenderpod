from __future__ import annotations

import re
from typing import Any

from ninja.errors import HttpError

from common.messages import get_message


NON_NEGATIVE_INT_FIELDS = (
    "trial_days",
    "trial_message_limit",
    "max_conversations",
    "max_numbers",
    "max_messages_per_day",
    "max_messages_per_minute",
    "max_catalog_items",
    "max_transcription_minutes",
    "max_storage_mb",
    "max_users",
    "max_agent_contexts",
)

MEMORY_RE = re.compile(r"^[1-9]\d*(b|k|m|g)$", re.IGNORECASE)
IMAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,254}$")
VULTR_PLAN_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,63}$")


def validate_plan_payload(data: dict[str, Any]) -> None:
    for field in NON_NEGATIVE_INT_FIELDS:
        if field in data and data[field] is not None and int(data[field]) < 0:
            raise HttpError(400, get_message("ERR_INVALID_PLAN_LIMIT", field=field))

    for field in ("a0_cpu_limit", "a0_cpu_reservation"):
        if field in data and data[field] is not None:
            try:
                value = float(data[field])
            except (TypeError, ValueError):
                raise HttpError(400, get_message("ERR_INVALID_PLAN_CPU", field=field))
            if value <= 0:
                raise HttpError(400, get_message("ERR_INVALID_PLAN_CPU", field=field))

    for field in ("a0_memory_limit", "a0_memory_reservation"):
        if field in data and data[field] is not None:
            value = str(data[field]).strip()
            if not MEMORY_RE.match(value):
                raise HttpError(400, get_message("ERR_INVALID_PLAN_MEMORY", field=field))

    if "a0_image" in data and data["a0_image"] is not None:
        if not IMAGE_RE.match(str(data["a0_image"]).strip()):
            raise HttpError(400, get_message("ERR_INVALID_PLAN_IMAGE"))

    if "vultr_plan" in data and data["vultr_plan"] is not None:
        if not VULTR_PLAN_RE.match(str(data["vultr_plan"]).strip()):
            raise HttpError(400, get_message("ERR_INVALID_VULTR_PLAN"))
