import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "resources" / "schema.sql"

def create_connection(db_path=":memory:"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_schema(conn):
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
