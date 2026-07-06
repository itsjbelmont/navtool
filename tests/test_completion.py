"""Tests for tab-completion: the name-path helper and the `__complete` backend."""

import pytest
from click.testing import CliRunner

from navtool.cli import cli
from navtool.cli.commands.complete import DIRS_SENTINEL
from navtool.cli.tree import _complete_name_path
from navtool.db import create_connection, migrate


@pytest.fixture
def runner(tmp_path, monkeypatch):
    db_path = tmp_path / "navtool.db"
    monkeypatch.setenv("NAVTOOL_DB", str(db_path))
    return CliRunner()


@pytest.fixture
def run(runner):
    def _run(*args, **kwargs):
        return runner.invoke(cli, [str(a) for a in args], **kwargs)

    return _run


@pytest.fixture
def tree(run, tmp_path):
    """A small name tree: myproj{src, tests{unit}}, other."""
    run("add", "myproj", str(tmp_path))
    run("add", "myproj:src", str(tmp_path))
    run("add", "myproj:tests", str(tmp_path))
    run("add", "myproj:tests:unit", str(tmp_path))
    run("add", "other", str(tmp_path))
    return tmp_path


def _conn(db_path):
    conn = create_connection(str(db_path))
    migrate(conn, str(db_path))
    return conn


# ----------------- _complete_name_path (unit) -----------------
def test_complete_top_level_by_prefix(tree, tmp_path):
    conn = _conn(tmp_path / "navtool.db")
    assert _complete_name_path(conn, "my") == ["myproj"]


def test_complete_top_level_empty_lists_all_roots(tree, tmp_path):
    conn = _conn(tmp_path / "navtool.db")
    assert _complete_name_path(conn, "") == ["myproj", "other"]


def test_complete_children_after_colon(tree, tmp_path):
    conn = _conn(tmp_path / "navtool.db")
    assert _complete_name_path(conn, "myproj:") == ["myproj:src", "myproj:tests"]


def test_complete_nested_prefix(tree, tmp_path):
    conn = _conn(tmp_path / "navtool.db")
    assert _complete_name_path(conn, "myproj:te") == ["myproj:tests"]


def test_complete_deep_children(tree, tmp_path):
    conn = _conn(tmp_path / "navtool.db")
    assert _complete_name_path(conn, "myproj:tests:") == ["myproj:tests:unit"]


def test_complete_unknown_parent_yields_nothing(tree, tmp_path):
    conn = _conn(tmp_path / "navtool.db")
    assert _complete_name_path(conn, "ghost:") == []


def test_complete_special_chars_treated_literally(run, tmp_path):
    # LIKE metacharacters in the partial must not act as wildcards.
    run("add", "a_b", str(tmp_path))
    run("add", "axb", str(tmp_path))
    conn = _conn(tmp_path / "navtool.db")
    assert _complete_name_path(conn, "a_") == ["a_b"]


# ----------------- __complete backend (integration) -----------------
def _lines(result):
    assert result.exit_code == 0, result.output
    return result.output.split("\n")[:-1]  # drop trailing empty from final \n


def test_nav_first_word_offers_commands_and_names(run, tree):
    lines = _lines(run("__complete", "--nav", "--", ""))
    assert "add" in lines  # subcommand
    assert "other" in lines  # leaf name
    assert "myproj" in lines  # name emitted with no trailing ':'
    assert "myproj:" not in lines


def test_navtool_first_word_has_no_bare_names(run, tree):
    lines = _lines(run("__complete", "--", ""))
    assert "add" in lines
    assert "other" not in lines  # navtool has no bare navigation


def test_nav_prefix_unions_command_and_name(run, tree):
    lines = _lines(run("__complete", "--nav", "--", "o"))
    assert "other" in lines


def test_children_completed_without_suffix(run, tree):
    lines = _lines(run("__complete", "--nav", "--", "myproj:"))
    assert "myproj:src" in lines  # leaf
    assert "myproj:tests" in lines  # has children, but still no trailing ':'
    assert "myproj:tests:" not in lines


def test_completion_after_subcommand_routes_to_names(run, tree):
    lines = _lines(run("__complete", "--", "rm", "myproj:"))
    assert "myproj:src" in lines
    assert "myproj:tests" in lines
    assert "add" not in lines  # not offering subcommands mid-command


def test_directory_argument_emits_sentinel(run, tree):
    lines = _lines(run("__complete", "--", "add", "newname", "/tm"))
    assert lines == [DIRS_SENTINEL]
