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


def _add(db, name, path, parent_id=None):
    cur = db.execute(
        "INSERT INTO nodes (parent_id, name, path) VALUES (?, ?, ?)",
        (parent_id, name, path),
    )
    return cur.lastrowid


def test_fresh_db_has_nodes_table_and_no_rows(db):
    assert db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
    ).fetchone() == ("nodes",)
    assert db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == 0


def test_insert_top_level_node(db):
    _add(db, "navtool", "/home/me/navtool")
    row = db.execute(
        "SELECT parent_id, path FROM nodes WHERE name = ?", ("navtool",)
    ).fetchone()
    assert row == (None, "/home/me/navtool")


def test_insert_child_node(db):
    root = _add(db, "navtool", "/proj/navtool")
    _add(db, "tests", "/proj/navtool/tests", parent_id=root)
    row = db.execute(
        "SELECT path FROM nodes WHERE parent_id = ? AND name = ?", (root, "tests")
    ).fetchone()
    assert row == ("/proj/navtool/tests",)


def test_duplicate_top_level_name_fails(db):
    """The partial unique index constrains top-level (NULL-parent) names."""
    _add(db, "proj", "/a")
    with pytest.raises(sqlite3.IntegrityError):
        _add(db, "proj", "/b")


def test_duplicate_sibling_name_fails(db):
    root = _add(db, "proj", "/proj")
    _add(db, "tests", "/proj/tests", parent_id=root)
    with pytest.raises(sqlite3.IntegrityError):
        _add(db, "tests", "/proj/other", parent_id=root)


def test_same_name_under_different_parents_allowed(db):
    a = _add(db, "a", "/a")
    b = _add(db, "b", "/b")
    _add(db, "tests", "/a/tests", parent_id=a)
    _add(db, "tests", "/b/tests", parent_id=b)
    rows = db.execute(
        "SELECT path FROM nodes WHERE name = 'tests' ORDER BY path"
    ).fetchall()
    assert rows == [("/a/tests",), ("/b/tests",)]


def test_same_name_at_top_and_nested_allowed(db):
    """A top-level name and a nested name may coincide (different parents)."""
    _add(db, "tests", "/top/tests")
    root = _add(db, "proj", "/proj")
    _add(db, "tests", "/proj/tests", parent_id=root)
    assert (
        db.execute("SELECT COUNT(*) FROM nodes WHERE name = 'tests'").fetchone()[0] == 2
    )


def test_foreign_key_enforced(db):
    """A child referencing a non-existent parent should fail."""
    with pytest.raises(sqlite3.IntegrityError):
        _add(db, "orphan", "/x", parent_id=9999)


def test_cascade_delete_removes_subtree(db):
    root = _add(db, "proj", "/proj")
    child = _add(db, "tests", "/proj/tests", parent_id=root)
    _add(db, "unit", "/proj/tests/unit", parent_id=child)

    db.execute("DELETE FROM nodes WHERE id = ?", (root,))

    assert db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == 0
