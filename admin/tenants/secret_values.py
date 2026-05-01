from __future__ import annotations

import os
from pathlib import Path


def read_secret(name: str, *, default: str = "", required: bool = False) -> str:
    file_name = f"{name}_FILE"
    file_path = os.environ.get(file_name, "").strip()
    if file_path:
        value = Path(file_path).read_text(encoding="utf-8").strip()
    else:
        value = os.environ.get(name, default).strip()
    if required and not value:
        raise EnvironmentError(f"{name} or {file_name} is required.")
    return value
