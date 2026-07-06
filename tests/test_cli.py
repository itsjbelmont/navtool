import pytest
from click.testing import CliRunner

from navtool.cli import cli


@pytest.fixture
def runner(tmp_path, monkeypatch):
    """A CliRunner backed by a throwaway on-disk database.

    Each invocation reopens the same DB file, so state persists across the
    multiple `run(...)` calls within a single test.
    """
    db_path = tmp_path / "navtool.db"
    monkeypatch.setenv("NAVTOOL_DB", str(db_path))
    return CliRunner()


@pytest.fixture
def run(runner):
    def _run(*args, **kwargs):
        return runner.invoke(cli, [str(a) for a in args], **kwargs)

    return _run


# ----------------- default set / bootstrapping -----------------
def test_default_set_present_on_first_run(run):
    result = run("set", "list")
    assert result.exit_code == 0
    assert "default" in result.output


# ----------------- set management -----------------
def test_set_add_and_show(run):
    assert run("set", "add", "proj", "--desc", "my project").exit_code == 0

    result = run("set", "show", "proj")
    assert result.exit_code == 0
    assert "proj: my project" in result.output
    assert "(no entries)" in result.output


def test_set_add_rejects_duplicate(run):
    run("set", "add", "proj")
    result = run("set", "add", "proj")
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_set_add_rejects_colon(run):
    result = run("set", "add", "a:b")
    assert result.exit_code != 0
    assert "reserved" in result.output


def test_set_remove_blocked_for_default(run):
    result = run("set", "remove", "default", "--yes")
    assert result.exit_code != 0
    assert "cannot be removed" in result.output


def test_set_remove_with_yes(run):
    run("set", "add", "proj")
    result = run("set", "remove", "proj", "--yes")
    assert result.exit_code == 0
    assert "Deleted" in result.output
    assert "proj" not in run("set", "list").output


def test_set_update_rename_moves_keys(run, tmp_path):
    run("set", "add", "proj")
    run("key", "add", "here", str(tmp_path), "--set", "proj")

    result = run("set", "update", "proj", "--rename", "nt")
    assert result.exit_code == 0

    # Old qualifier gone, new qualifier resolves.
    assert run("path", "proj:here").exit_code != 0
    assert run("path", "nt:here").output.strip() == str(tmp_path)


def test_set_update_default_blocked(run):
    result = run("set", "update", "default", "--desc", "nope")
    assert result.exit_code != 0
    assert "cannot be modified" in result.output


# ----------------- key management -----------------
def test_key_add_defaults_to_default_set(run, tmp_path):
    result = run("key", "add", "proj", str(tmp_path))
    assert result.exit_code == 0
    assert "in set 'default'" in result.output
    assert run("path", "proj").output.strip() == str(tmp_path)


def test_key_add_rejects_missing_directory(run, tmp_path):
    result = run("key", "add", "proj", str(tmp_path / "nope"))
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_key_add_duplicate_in_set(run, tmp_path):
    run("key", "add", "proj", str(tmp_path))
    result = run("key", "add", "proj", str(tmp_path))
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_key_remove(run, tmp_path):
    run("key", "add", "proj", str(tmp_path))
    assert run("key", "remove", "proj").exit_code == 0
    assert run("path", "proj").exit_code != 0


def test_key_remove_missing(run):
    result = run("key", "remove", "ghost")
    assert result.exit_code != 0
    assert "No keyword" in result.output


def test_key_update_repoints(run, tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    run("key", "add", "proj", str(tmp_path))
    assert run("key", "update", "proj", str(sub)).exit_code == 0
    assert run("path", "proj").output.strip() == str(sub)


# ----------------- key move -----------------
def test_key_move_from_default(run, tmp_path):
    run("set", "add", "proj")
    run("key", "add", "scratch", str(tmp_path))

    result = run("key", "move", "scratch", "--to", "proj")
    assert result.exit_code == 0

    assert run("path", "scratch").exit_code != 0
    assert run("path", "proj:scratch").output.strip() == str(tmp_path)


def test_key_move_between_sets(run, tmp_path):
    run("set", "add", "a")
    run("set", "add", "b")
    run("key", "add", "k", str(tmp_path), "--set", "a")

    result = run("key", "move", "k", "--from", "a", "--to", "b")
    assert result.exit_code == 0
    assert run("path", "b:k").output.strip() == str(tmp_path)


def test_key_move_collision_rejected(run, tmp_path):
    run("set", "add", "proj")
    run("key", "add", "k", str(tmp_path))
    run("key", "add", "k", str(tmp_path), "--set", "proj")

    result = run("key", "move", "k", "--to", "proj")
    assert result.exit_code != 0
    assert "already exists" in result.output


# ----------------- db group -----------------
def test_db_path_matches_env_override(run, tmp_path):
    result = run("db", "path")
    assert result.exit_code == 0
    assert result.output.strip() == str(tmp_path / "navtool.db")


def test_db_info_reports_override_and_counts(run, tmp_path):
    run("set", "add", "proj")
    run("key", "add", "k", str(tmp_path), "--set", "proj")

    result = run("db", "info")
    assert result.exit_code == 0
    assert str(tmp_path / "navtool.db") in result.output
    assert "override via $NAVTOOL_DB" in result.output
    # default + proj = 2 sets, 1 entry
    assert "Sets:     2" in result.output
    assert "Entries:  1" in result.output


def test_db_info_reports_schema_version(run):
    from navtool.db import SCHEMA_VERSION

    result = run("db", "info")
    assert result.exit_code == 0
    assert f"version {SCHEMA_VERSION} (up to date)" in result.output
    assert "NavTool:" in result.output


def test_db_migrate_reports_up_to_date(run):
    # The DB is created (and migrated) on the first command, so a later explicit
    # migrate reports it is already current.
    run("db", "info")
    result = run("db", "migrate")
    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_version_flag(run):
    result = run("--version")
    assert result.exit_code == 0
    assert "navtool" in result.output.lower()


# ----------------- path resolution -----------------
def test_path_default_and_qualified(run, tmp_path):
    run("set", "add", "proj")
    run("key", "add", "d", str(tmp_path))
    run("key", "add", "p", str(tmp_path), "--set", "proj")

    assert run("path", "d").output.strip() == str(tmp_path)
    assert run("path", "proj:p").output.strip() == str(tmp_path)


def test_path_miss_exits_nonzero(run):
    result = run("path", "nonexistent")
    assert result.exit_code != 0
