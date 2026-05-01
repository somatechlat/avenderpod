from usr.plugins.avender.helpers import db


def test_schema_recreated_after_db_file_deleted(tmp_path, monkeypatch):
    db_path = tmp_path / "avender.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "_db_initialized", False)

    conn = db.get_connection()
    conn.execute("INSERT INTO tenant_config(key, value) VALUES('k', 'v')")
    conn.commit()
    conn.close()

    assert db_path.exists()
    db_path.unlink()
    assert not db_path.exists()

    conn2 = db.get_connection()
    cursor = conn2.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tenant_config'"
    )
    assert cursor.fetchone() is not None
    conn2.close()
