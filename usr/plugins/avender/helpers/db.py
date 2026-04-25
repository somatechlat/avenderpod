import sqlite3
import json
import threading
from pathlib import Path

# The DB will live inside the user's workspace, perfectly isolated for this tenant.
DB_PATH = Path("usr/workdir/avender.db")

_db_initialized = False
_db_lock = threading.Lock()
SQLITE_TIMEOUT_SECONDS = 30
SQLITE_BUSY_TIMEOUT_MS = SQLITE_TIMEOUT_SECONDS * 1000


def get_connection():
    """Returns a connection to the SQLite database.
    Lazily initializes the schema on first call (thread-safe)."""
    global _db_initialized
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=SQLITE_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    with _db_lock:
        if not _db_initialized:
            _init_schema(conn)
            _db_initialized = True
    return conn


def _init_schema(conn):
    """Initializes the Omni-Industry Database schema."""
    cursor = conn.cursor()

    # 1. Tenant Config (Key-Value for Onboarding Data)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tenant_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """
    )

    # 2. Universal Catalog (EAV / JSONB style)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS catalog_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            metadata TEXT DEFAULT '{}',
            image_url TEXT DEFAULT ''
        )
    """
    )

    # 3. Universal Interaction Record (Orders, Bookings, Leads)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS interaction_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_wa_id TEXT NOT NULL,
            archetype TEXT NOT NULL,
            status TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """
    )

    # Indexes for performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_interaction_created_at ON interaction_record(created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_interaction_customer ON interaction_record(customer_wa_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_sessions_token ON auth_sessions(token)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at)"
    )

    conn.commit()


def save_tenant_config(config_dict: dict):
    """Saves the onboarding wizard data."""
    conn = get_connection()
    cursor = conn.cursor()
    for key, value in config_dict.items():
        val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        cursor.execute(
            "INSERT INTO tenant_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, val_str),
        )
    conn.commit()
    conn.close()


def get_tenant_config(key: str | None = None):
    """Retrieves config. If key is None, returns all as dict."""
    conn = get_connection()
    cursor = conn.cursor()
    if key:
        cursor.execute("SELECT value FROM tenant_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row else None
    else:
        cursor.execute("SELECT key, value FROM tenant_config")
        rows = cursor.fetchall()
        conn.close()
        return {row["key"]: row["value"] for row in rows}


def delete_tenant_config(key: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tenant_config WHERE key = ?", (key,))
    conn.commit()
    conn.close()


def is_onboarding_complete() -> bool:
    """Atomic check for onboarding completion status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM tenant_config WHERE key = 'onboarding_complete' AND value = 'true'"
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None
