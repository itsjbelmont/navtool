import sqlite3

import pytest

from navtool.db import (SCHEMA_VERSION, IncompatibleDatabaseError,
                        NewerDatabaseError, _get_user_version,
                        _set_user_version, create_connection, get_connection,
                        migrate)


def test_fresh_memory_db_is_migrated_to_current():
    conn = get_connection(":memory:")
    try:
        assert _get_user_version(conn) == SCHEMA_VERSION
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "nodes" in tables
    finally:
        conn.close()


def test_migrate_reports_transition():
    conn = create_connection(":memory:")
    try:
        assert _get_user_version(conn) == 0
        assert migrate(conn, ":memory:") == (0, SCHEMA_VERSION)
        # Second run is a no-op.
        assert migrate(conn, ":memory:") == (SCHEMA_VERSION, SCHEMA_VERSION)
    finally:
        conn.close()


def test_no_backup_for_fresh_db(tmp_path):
    """A brand-new/empty database has nothing to back up."""
    db_path = tmp_path / "data.db"
    get_connection(str(db_path)).close()  # creates + initializes from scratch
    assert list(tmp_path.glob("data.db.pre-migrate-*")) == []

    get_connection(str(db_path)).close()  # already current -> still no backup
    assert list(tmp_path.glob("data.db.pre-migrate-*")) == []


def test_legacy_set_key_database_is_rejected(tmp_path):
    """A pre-overhaul database (with a `sets` table) is refused, not migrated."""
    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE sets (set_name TEXT PRIMARY KEY, description TEXT, root TEXT);
        CREATE TABLE entries (
          set_name TEXT, entry_key TEXT, entry_value TEXT,
          PRIMARY KEY (set_name, entry_key)
        );
        INSERT INTO sets (set_name) VALUES ('default');
        """)
    _set_user_version(conn, 2)
    conn.commit()
    conn.close()

    with pytest.raises(IncompatibleDatabaseError):
        get_connection(db_path)


def test_newer_database_is_rejected(tmp_path):
    db_path = str(tmp_path / "future.db")
    conn = create_connection(db_path)
    _set_user_version(conn, SCHEMA_VERSION + 1)
    conn.commit()
    conn.close()

    with pytest.raises(NewerDatabaseError):
        get_connection(db_path)
