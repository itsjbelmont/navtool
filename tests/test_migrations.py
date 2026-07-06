import sqlite3

import pytest

from navtool.db import (
    SCHEMA_VERSION,
    NewerDatabaseError,
    create_connection,
    get_connection,
    migrate,
    _get_user_version,
    _set_user_version,
)


def test_fresh_memory_db_is_migrated_to_current():
    conn = get_connection(":memory:")
    try:
        assert _get_user_version(conn) == SCHEMA_VERSION
        # Tables exist and the default set is seeded by migration 1.
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"sets", "entries"} <= tables
        assert conn.execute(
            "SELECT 1 FROM sets WHERE set_name = 'default'"
        ).fetchone() == (1,)
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


def test_adopts_legacy_unversioned_db_without_data_loss(tmp_path):
    """A pre-versioning DB (user_version 0, legacy is_active column) is adopted."""
    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sets (
          set_name TEXT PRIMARY KEY,
          description TEXT,
          is_active INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE entries (
          set_name TEXT,
          entry_key TEXT,
          entry_value TEXT,
          PRIMARY KEY (set_name, entry_key),
          FOREIGN KEY (set_name) REFERENCES sets(set_name) ON DELETE CASCADE
        );
        INSERT INTO sets (set_name, description) VALUES ('work', 'legacy set');
        INSERT INTO entries VALUES ('work', 'api', '/code/api');
        """
    )
    conn.commit()
    conn.close()

    migrated = get_connection(db_path)
    try:
        assert _get_user_version(migrated) == SCHEMA_VERSION
        # Existing data preserved.
        assert migrated.execute(
            "SELECT entry_value FROM entries WHERE set_name='work' AND entry_key='api'"
        ).fetchone() == ("/code/api",)
        # default set now present.
        assert migrated.execute(
            "SELECT 1 FROM sets WHERE set_name='default'"
        ).fetchone() == (1,)
    finally:
        migrated.close()


def test_backup_written_when_migrating_existing_db(tmp_path):
    """A DB that already holds data is backed up before migrating."""
    db_path = tmp_path / "data.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        "CREATE TABLE sets (set_name TEXT PRIMARY KEY, description TEXT);"
        "INSERT INTO sets (set_name) VALUES ('work');"
    )
    conn.commit()
    conn.close()

    get_connection(str(db_path)).close()

    backups = list(tmp_path.glob("data.db.pre-migrate-*"))
    assert len(backups) == 1


def test_no_backup_for_fresh_db(tmp_path):
    """A brand-new/empty database has nothing to back up."""
    db_path = tmp_path / "data.db"
    get_connection(str(db_path)).close()  # creates + initializes from scratch
    assert list(tmp_path.glob("data.db.pre-migrate-*")) == []

    get_connection(str(db_path)).close()  # already current -> still no backup
    assert list(tmp_path.glob("data.db.pre-migrate-*")) == []


def test_migration_2_adds_root_column_preserving_data(tmp_path):
    """A v1 database is upgraded to v2 with a `root` column and no data loss."""
    db_path = str(tmp_path / "v1.db")
    conn = sqlite3.connect(db_path)
    # A v1-shaped database: sets/entries without a `root` column, stamped v1.
    conn.executescript(
        """
        CREATE TABLE sets (set_name TEXT PRIMARY KEY, description TEXT);
        CREATE TABLE entries (
          set_name TEXT,
          entry_key TEXT,
          entry_value TEXT,
          PRIMARY KEY (set_name, entry_key),
          FOREIGN KEY (set_name) REFERENCES sets(set_name) ON DELETE CASCADE
        );
        INSERT INTO sets (set_name, description) VALUES ('default', NULL);
        INSERT INTO sets (set_name, description) VALUES ('work', 'legacy');
        INSERT INTO entries VALUES ('work', 'api', '/code/api');
        """
    )
    _set_user_version(conn, 1)
    conn.commit()
    conn.close()

    migrated = get_connection(db_path)
    try:
        assert _get_user_version(migrated) == SCHEMA_VERSION
        columns = {
            r[1] for r in migrated.execute("PRAGMA table_info(sets)").fetchall()
        }
        assert "root" in columns
        # Existing rows preserved; root defaults to NULL.
        assert migrated.execute(
            "SELECT description, root FROM sets WHERE set_name='work'"
        ).fetchone() == ("legacy", None)
        assert migrated.execute(
            "SELECT entry_value FROM entries WHERE set_name='work' AND entry_key='api'"
        ).fetchone() == ("/code/api",)
    finally:
        migrated.close()


def test_newer_database_is_rejected(tmp_path):
    db_path = str(tmp_path / "future.db")
    conn = create_connection(db_path)
    _set_user_version(conn, SCHEMA_VERSION + 1)
    conn.commit()
    conn.close()

    with pytest.raises(NewerDatabaseError):
        get_connection(db_path)
