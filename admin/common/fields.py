"""
Symmetric encryption fields using Django's SECRET_KEY as Fernet key material.

These fields transparently encrypt data at the Django ORM layer before it
reaches PostgreSQL, and decrypt on read. This protects PII at rest without
requiring application-level encrypt/decrypt calls.

Key derivation: SHA-256 of Django SECRET_KEY → Fernet-compatible 32-byte key.
Algorithm: Fernet (AES-128-CBC + HMAC-SHA256) via the ``cryptography`` package.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    """Derive a Fernet instance from Django's SECRET_KEY."""
    key_material = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))


class EncryptedTextField(models.TextField):
    """TextField that stores ciphertext in PostgreSQL and returns plaintext to Python."""

    def get_prep_value(self, value: str | None) -> str | None:
        if value is None:
            return value
        return _get_fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def from_db_value(
        self, value: str | None, expression: Any, connection: Any
    ) -> str | None:
        if value is None:
            return value
        try:
            return _get_fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError):
            # Graceful degradation: return raw value if decryption fails
            # (e.g., pre-migration unencrypted data still in the table).
            return value


class EncryptedJSONField(models.TextField):
    """
    JSONField-like that stores Fernet-encrypted JSON text in PostgreSQL.

    Values are serialized to JSON, encrypted, then stored as text.
    On read, the ciphertext is decrypted and deserialized back to Python objects.
    """

    def get_prep_value(self, value: Any) -> str | None:
        if value is None:
            return value
        plaintext = json.dumps(value, ensure_ascii=False)
        return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")

    def from_db_value(
        self, value: str | None, expression: Any, connection: Any
    ) -> Any:
        if value is None:
            return value
        # Already a dict/list (e.g., test fixture or default value)
        if isinstance(value, (dict, list)):
            return value
        try:
            plaintext = _get_fernet().decrypt(value.encode("ascii")).decode("utf-8")
            return json.loads(plaintext)
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError):
            # Graceful degradation for pre-migration unencrypted JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

    def get_default(self) -> Any:
        default = super().get_default()
        if default is None and self.has_default():
            default = self.default
            if callable(default):
                default = default()
        return default
