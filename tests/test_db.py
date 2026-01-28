import sqlite3

import pytest

from navtool.db import get_connection


@pytest.fixture
def db():
    """
    Provides a fresh in-memory SQLite database for each test,
    with schema initialized and foreign keys enabled.
    """
    conn = get_connection(":memory:")
    yield conn
    conn.close()


def test_insert_set_with_description(db):
    db.execute(
        "INSERT INTO sets (set_name, description) VALUES (?, ?)",
        ("projects", "Work-related directories"),
    )

    row = db.execute(
        "SELECT set_name, description, is_active FROM sets WHERE set_name = ?",
        ("projects",),
    ).fetchone()

    assert row == ("projects", "Work-related directories", 0)


def test_insert_set_without_description(db):
    db.execute(
        "INSERT INTO sets (set_name) VALUES (?)",
        ("personal",),
    )

    row = db.execute(
        "SELECT description FROM sets WHERE set_name = ?",
        ("personal",),
    ).fetchone()

    assert row[0] is None
  

def test_insert_active_set(db):
    db.execute(
        "INSERT INTO sets (set_name, is_active) VALUES (?, ?)",
        ("active_set", 1)
    )

    row = db.execute(
        "SELECT is_active FROM sets WHERE set_name = ?",
        ("active_set",),
    ).fetchone()

    assert row[0] == 1


def test_insert_set_then_activate(db):
    db.execute(
        "INSERT INTO sets (set_name) VALUES (?)",
        ("test_activation",),
    )
    row = db.execute(
        "SELECT is_active FROM sets WHERE set_name = ?",
        ("test_activation",),
    ).fetchone()
    assert row[0] == 0
    db.execute(
        "UPDATE sets SET is_active = ? WHERE set_name = ?",
        (1, "test_activation")
    ) 
    row = db.execute(
        "SELECT is_active FROM sets WHERE set_name = ?",
        ("test_activation",),
    ).fetchone()
    assert row[0] == 1


def test_insert_entry(db):
    db.execute(
        "INSERT INTO sets (set_name, description) VALUES (?, ?)",
        ("projects", None),
    )

    db.execute(
        """
        INSERT INTO entries (set_name, entry_key, entry_value)
        VALUES (?, ?, ?)
        """,
        ("projects", "navtool", "/home/me/navtool"),
    )

    row = db.execute(
        """
        SELECT entry_value
        FROM entries
        WHERE set_name = ? AND entry_key = ?
        """,
        ("projects", "navtool"),
    ).fetchone()

    assert row[0] == "/home/me/navtool"


def test_duplicate_entry_key_in_same_set_fails(db):
    db.execute("INSERT INTO sets (set_name, description) VALUES (?, ?)", ("projects", None))

    db.execute(
        "INSERT INTO entries VALUES (?, ?, ?)",
        ("projects", "a", "/path/a"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO entries VALUES (?, ?, ?)",
            ("projects", "a", "/path/b"),
        )


def test_same_entry_key_in_different_sets_allowed(db):
    db.execute("INSERT INTO sets (set_name, description) VALUES (?, ?)", ("projects", None))
    db.execute("INSERT INTO sets (set_name, description) VALUES (?, ?)", ("personal", None))

    db.execute(
        "INSERT INTO entries VALUES (?, ?, ?)",
        ("projects", "a", "/projects/a"),
    )
    db.execute(
        "INSERT INTO entries VALUES (?, ?, ?)",
        ("personal", "a", "/personal/a"),
    )

    rows = db.execute(
        "SELECT set_name, entry_value FROM entries ORDER BY set_name"
    ).fetchall()

    assert rows == [
        ("personal", "/personal/a"),
        ("projects", "/projects/a"),
    ]


def test_foreign_key_enforced(db):
    """
    Inserting an entry referencing a non-existent set should fail.
    """
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO entries (set_name, entry_key, entry_value)
            VALUES (?, ?, ?)
            """,
            ("missing_set", "x", "y"),
        )


def test_cascade_delete_removes_entries(db):
    db.execute(
        "INSERT INTO sets (set_name, description) VALUES (?, ?)",
        ("projects", "Temporary set"),
    )
    db.execute(
        "INSERT INTO entries VALUES (?, ?, ?)",
        ("projects", "a", "/path/a"),
    )

    db.execute("DELETE FROM sets WHERE set_name = ?", ("projects",))

    row = db.execute("SELECT * FROM entries").fetchone()
    assert row is None
