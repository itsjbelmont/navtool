import sqlite3
from pathlib import Path

# Path to schema.sql
SCHEMA_PATH = Path(__file__).parent / "resources" / "schema.sql"


def create_connection(db_path: str) -> sqlite3.Connection:
    """
    Create a SQLite connection with foreign keys enabled.
    Does NOT actually initialize the schema.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def schema_initialized(conn: sqlite3.Connection) -> bool:
    """
    Return True if the database schema has already been initialized.
    We check for a known table instead of checking filesystem state
    so this works for both file-based and :memory: databases.
    """
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='sets';
        """
    ).fetchone()
    return row is not None


def initialize_schema(conn: sqlite3.Connection) -> None:
    """
    Apply the schema.sql file to the database.
    Safe to call only when schema is not already present.
    """
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()


def initialize_schema_if_needed(conn: sqlite3.Connection) -> None:
    """
    Initialize the schema only if it has not already been applied.
    """
    if not schema_initialized(conn):
        initialize_schema(conn)


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Public entry point.

    Returns a SQLite connection and guarantees that the schema
    has been initialized.

    Works for:
      - file-based databases
      - ':memory:' databases (used in tests)
    """
    conn = create_connection(db_path)
    initialize_schema_if_needed(conn)
    return conn
