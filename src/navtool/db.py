import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# Path to schema.sql (the baseline schema applied by migration 1).
SCHEMA_PATH = Path(__file__).parent / "resources" / "schema.sql"

# The always-present set that unqualified keywords resolve against.
DEFAULT_SET = "default"

# Current target schema version. Bump this (and add a migration below) whenever
# the schema changes. Stored in each database via `PRAGMA user_version`.
SCHEMA_VERSION = 2

# In-memory databases use this sentinel path and are never backed up.
MEMORY_DB = ":memory:"


class NewerDatabaseError(RuntimeError):
    """Raised when a database was created by a newer navtool than this one."""


def create_connection(db_path: str) -> sqlite3.Connection:
    """
    Create a SQLite connection with foreign keys enabled.
    Does NOT run migrations. `PRAGMA foreign_keys` is set here, before any
    transaction, because it is a no-op inside one.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _get_user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _set_user_version(conn: sqlite3.Connection, version: int) -> None:
    # PRAGMA does not accept bound parameters, so interpolate a validated int.
    conn.execute(f"PRAGMA user_version = {int(version)}")


# ----------------- Migrations -----------------
# Each migration upgrades a database from version N-1 to N. Register it under
# its target version in MIGRATIONS. Keep them ordered and never renumber a
# migration that has shipped.


def _migration_1(conn: sqlite3.Connection) -> None:
    """
    Baseline schema (v0 -> v1).

    Applies schema.sql, which creates the `sets` and `entries` tables and seeds
    the `default` set. Every statement is idempotent (`CREATE TABLE IF NOT
    EXISTS`, `INSERT OR IGNORE`), so this both initializes a fresh database and
    adopts a pre-versioning database without altering its data.
    """
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())


def _migration_2(conn: sqlite3.Connection) -> None:
    """
    Add the `root` column to `sets` (v1 -> v2).

    A set's ``root`` is an optional directory the set navigates to by its own
    name, so ``nav myproject`` can jump to a project's top-level directory
    without needing a keyword. NULL means the set has no root.
    """
    conn.execute("ALTER TABLE sets ADD COLUMN root TEXT")


MIGRATIONS = {
    1: _migration_1,
    2: _migration_2,
}


def _has_tables(conn: sqlite3.Connection) -> bool:
    """True if the database already contains user tables (i.e. prior data)."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1"
    ).fetchone()
    return row is not None


def _backup_path(db_path: str, from_version: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return Path(f"{db_path}.pre-migrate-v{from_version}-{timestamp}")


def migrate(conn: sqlite3.Connection, db_path: str) -> tuple[int, int]:
    """
    Bring `conn` up to SCHEMA_VERSION, running any pending migrations in order.

    Returns ``(from_version, to_version)`` describing what happened (equal when
    already up to date).

    For file-based databases that are behind, the file is copied to a
    timestamped ``*.pre-migrate-*`` backup before any migration runs, so a
    failed or unexpected migration can always be rolled back by hand.

    Raises :class:`NewerDatabaseError` if the database is ahead of this build.
    """
    from_version = _get_user_version(conn)

    if from_version > SCHEMA_VERSION:
        raise NewerDatabaseError(
            f"Database schema version {from_version} is newer than this navtool "
            f"supports (version {SCHEMA_VERSION}). Update navtool to continue."
        )
    if from_version == SCHEMA_VERSION:
        return (from_version, from_version)

    # Behind: back up file-based databases that already hold data before
    # touching them. A fresh/empty file has no tables and nothing to lose.
    if db_path != MEMORY_DB and Path(db_path).exists() and _has_tables(conn):
        shutil.copy2(db_path, _backup_path(db_path, from_version))

    for target in range(from_version + 1, SCHEMA_VERSION + 1):
        migration = MIGRATIONS[target]
        # Migration 1 uses executescript() (which self-commits) and is
        # idempotent; stamp the version immediately after. Later migrations run
        # inside an explicit transaction so the change and the version bump
        # commit atomically.
        if target == 1:
            migration(conn)
            _set_user_version(conn, target)
            conn.commit()
        else:
            try:
                conn.execute("BEGIN")
                migration(conn)
                _set_user_version(conn, target)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    return (from_version, SCHEMA_VERSION)


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Public entry point.

    Returns a SQLite connection, migrated up to SCHEMA_VERSION (which also
    initializes a fresh database and guarantees the `default` set exists).

    Works for file-based databases and ':memory:' databases (used in tests).
    """
    conn = create_connection(db_path)
    migrate(conn, db_path)
    return conn
