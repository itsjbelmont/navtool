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


# ----------------- bootstrapping -----------------
def test_empty_ls_on_first_run(run):
    result = run("ls")
    assert result.exit_code == 0
    assert "(no entries)" in result.output


# ----------------- add -----------------
def test_add_top_level_and_navigate(run, tmp_path):
    result = run("add", "proj", str(tmp_path))
    assert result.exit_code == 0
    assert run("path", "proj").output.strip() == str(tmp_path)


def test_add_nested_under_parent(run, tmp_path):
    sub = tmp_path / "tests"
    sub.mkdir()
    run("add", "proj", str(tmp_path))
    result = run("add", "proj:tests", str(sub))
    assert result.exit_code == 0
    assert run("path", "proj:tests").output.strip() == str(sub)


def test_add_deeply_nested(run, tmp_path):
    a = tmp_path / "a"
    b = a / "b"
    b.mkdir(parents=True)
    run("add", "a", str(a))
    run("add", "a:b", str(b))
    result = run("add", "a:b:c", str(b))
    assert result.exit_code == 0
    assert run("path", "a:b:c").output.strip() == str(b)


def test_add_missing_parent_rejected(run, tmp_path):
    result = run("add", "ghost:child", str(tmp_path))
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_add_duplicate_sibling_rejected(run, tmp_path):
    run("add", "proj", str(tmp_path))
    result = run("add", "proj", str(tmp_path))
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_add_rejects_missing_directory(run, tmp_path):
    result = run("add", "proj", str(tmp_path / "nope"))
    assert result.exit_code != 0
    assert "Directory does not exist" in result.output


def test_same_name_under_different_parents(run, tmp_path):
    run("add", "a", str(tmp_path))
    run("add", "b", str(tmp_path))
    assert run("add", "a:tests", str(tmp_path)).exit_code == 0
    assert run("add", "b:tests", str(tmp_path)).exit_code == 0


# ----------------- path resolution -----------------
def test_path_trailing_colon_resolves_node(run, tmp_path):
    run("add", "proj", str(tmp_path))
    assert run("path", "proj:").output.strip() == str(tmp_path)


def test_path_miss_exits_nonzero(run):
    assert run("path", "nonexistent").exit_code != 0
    assert run("path", "a:b:c").exit_code != 0


def test_bare_name_does_not_match_nested(run, tmp_path):
    """A nested name is not reachable as a bare top-level name."""
    run("add", "proj", str(tmp_path))
    run("add", "proj:tests", str(tmp_path))
    assert run("path", "tests").exit_code != 0
    assert run("path", "proj:tests").exit_code == 0


# ----------------- rm -----------------
def test_rm_leaf(run, tmp_path):
    run("add", "proj", str(tmp_path))
    assert run("rm", "proj").exit_code == 0
    assert run("path", "proj").exit_code != 0


def test_rm_missing(run):
    result = run("rm", "ghost")
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_rm_with_children_prompts_and_declines(run, tmp_path):
    run("add", "proj", str(tmp_path))
    run("add", "proj:tests", str(tmp_path))
    result = run("rm", "proj", input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output.lower()
    # Nothing removed.
    assert run("path", "proj:tests").exit_code == 0


def test_rm_cascades_with_yes(run, tmp_path):
    run("add", "proj", str(tmp_path))
    run("add", "proj:tests", str(tmp_path))
    run("add", "proj:tests:unit", str(tmp_path))
    result = run("rm", "proj", "--yes")
    assert result.exit_code == 0
    assert "2 nested" in result.output
    assert run("path", "proj").exit_code != 0
    assert run("path", "proj:tests").exit_code != 0


# ----------------- mv -----------------
def test_mv_rename(run, tmp_path):
    run("add", "proj", str(tmp_path))
    assert run("mv", "proj", "--rename", "p").exit_code == 0
    assert run("path", "p").output.strip() == str(tmp_path)
    assert run("path", "proj").exit_code != 0


def test_mv_reparent(run, tmp_path):
    run("add", "a", str(tmp_path))
    run("add", "b", str(tmp_path))
    run("add", "a:child", str(tmp_path))
    assert run("mv", "a:child", "--to", "b").exit_code == 0
    assert run("path", "b:child").output.strip() == str(tmp_path)
    assert run("path", "a:child").exit_code != 0


def test_mv_to_root(run, tmp_path):
    run("add", "a", str(tmp_path))
    run("add", "a:child", str(tmp_path))
    assert run("mv", "a:child", "--root").exit_code == 0
    assert run("path", "child").output.strip() == str(tmp_path)


def test_mv_cycle_rejected(run, tmp_path):
    run("add", "a", str(tmp_path))
    run("add", "a:b", str(tmp_path))
    # Cannot move `a` under its own descendant `a:b`.
    result = run("mv", "a", "--to", "a:b")
    assert result.exit_code != 0
    assert "descendant" in result.output


def test_mv_destination_collision_rejected(run, tmp_path):
    run("add", "a", str(tmp_path))
    run("add", "b", str(tmp_path))
    run("add", "a:x", str(tmp_path))
    run("add", "b:x", str(tmp_path))
    result = run("mv", "a:x", "--to", "b")
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_mv_to_and_root_conflict(run, tmp_path):
    run("add", "a", str(tmp_path))
    result = run("mv", "a", "--to", "a", "--root")
    assert result.exit_code != 0
    assert "not both" in result.output


# ----------------- update -----------------
def test_update_repoints(run, tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    run("add", "proj", str(tmp_path))
    assert run("update", "proj", str(sub)).exit_code == 0
    assert run("path", "proj").output.strip() == str(sub)


# ----------------- ls -----------------
def test_ls_renders_tree(run, tmp_path):
    run("add", "proj", str(tmp_path))
    run("add", "proj:tests", str(tmp_path))
    result = run("ls")
    assert result.exit_code == 0
    assert "proj" in result.output
    assert "tests" in result.output


def test_ls_subtree(run, tmp_path):
    run("add", "a", str(tmp_path))
    run("add", "a:child", str(tmp_path))
    run("add", "b", str(tmp_path))
    result = run("ls", "a")
    assert result.exit_code == 0
    assert "child ->" in result.output
    # The sibling top-level node `b` is outside the requested subtree.
    assert "b ->" not in result.output


# ----------------- db group -----------------
def test_db_path_matches_env_override(run, tmp_path):
    result = run("db", "path")
    assert result.exit_code == 0
    assert result.output.strip() == str(tmp_path / "navtool.db")


def test_db_info_reports_counts(run, tmp_path):
    run("add", "proj", str(tmp_path))
    run("add", "proj:tests", str(tmp_path))
    result = run("db", "info")
    assert result.exit_code == 0
    assert str(tmp_path / "navtool.db") in result.output
    assert "override via $NAVTOOL_DB" in result.output
    assert "Nodes:     2" in result.output
    assert "Top-level: 1" in result.output


def test_db_info_reports_schema_version(run):
    from navtool.db import SCHEMA_VERSION

    result = run("db", "info")
    assert result.exit_code == 0
    assert f"version {SCHEMA_VERSION} (up to date)" in result.output
    assert "NavTool:" in result.output


def test_db_schema_dumps_nodes_table(run):
    result = run("db", "schema")
    assert result.exit_code == 0
    assert "CREATE TABLE" in result.output
    assert "nodes" in result.output


def test_db_migrate_reports_up_to_date(run):
    run("db", "info")
    result = run("db", "migrate")
    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_version_flag(run):
    result = run("--version")
    assert result.exit_code == 0
    assert "navtool" in result.output.lower()
