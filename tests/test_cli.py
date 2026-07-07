import pytest
from click.testing import CliRunner

from navtool.cli import cli


@pytest.fixture
def runner(tmp_path, monkeypatch):
    """A CliRunner backed by a throwaway on-disk data directory.

    ``$NAVTOOL_DIR`` points navtool at ``tmp_path`` (so the database lands at
    ``tmp_path/navtool.db``). Each invocation reopens the same file, so state
    persists across the multiple `run(...)` calls within a single test.
    """
    monkeypatch.setenv("NAVTOOL_DIR", str(tmp_path))
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


@pytest.fixture
def three_levels(run, tmp_path):
    """proj{tests{unit}} plus a sibling top-level `other`."""
    run("add", "proj", str(tmp_path))
    run("add", "proj:tests", str(tmp_path))
    run("add", "proj:tests:unit", str(tmp_path))
    run("add", "other", str(tmp_path))


def test_ls_level_1_shows_top_level_only(run, three_levels):
    result = run("ls", "--level", "1")
    assert result.exit_code == 0
    assert "proj ->" in result.output
    assert "other ->" in result.output
    assert "tests ->" not in result.output
    assert "unit ->" not in result.output


def test_ls_level_2_shows_direct_children(run, three_levels):
    result = run("ls", "--level", "2")
    assert result.exit_code == 0
    assert "proj ->" in result.output
    assert "tests ->" in result.output  # direct child
    assert "unit ->" not in result.output  # grandchild excluded


def test_ls_no_level_shows_full_depth(run, three_levels):
    result = run("ls")
    assert result.exit_code == 0
    assert "unit ->" in result.output


def test_ls_level_with_subtree_counts_from_root(run, three_levels):
    # --level is counted from the listed root, so `ls proj --level 1` shows only
    # `proj`, and `--level 2` adds its direct child `tests`.
    assert "tests ->" not in run("ls", "proj", "--level", "1").output
    assert "tests ->" in run("ls", "proj", "--level", "2").output


def test_ls_short_flag_l(run, three_levels):
    assert "tests ->" not in run("ls", "-l", "1").output


def test_ls_level_zero_rejected(run, three_levels):
    result = run("ls", "--level", "0")
    assert result.exit_code != 0


# ----------------- which (reverse lookup) -----------------
def test_which_finds_single_key(run, tmp_path):
    run("add", "proj", str(tmp_path))
    result = run("which", str(tmp_path))
    assert result.exit_code == 0
    assert result.output.strip() == "proj"


def test_which_returns_full_name_path_for_nested(run, tmp_path):
    sub = tmp_path / "tests"
    sub.mkdir()
    run("add", "proj", str(tmp_path))
    run("add", "proj:tests", str(sub))
    result = run("which", str(sub))
    assert result.exit_code == 0
    assert result.output.strip() == "proj:tests"


def test_which_lists_all_matching_keys(run, tmp_path):
    run("add", "a", str(tmp_path))
    run("add", "b", str(tmp_path))  # same directory, second key
    result = run("which", str(tmp_path))
    assert result.exit_code == 0
    assert result.output.split() == ["a", "b"]


def test_which_exits_nonzero_when_unkeyed(run, tmp_path):
    result = run("which", str(tmp_path))
    assert result.exit_code != 0
    assert "No name points at" in result.output


def test_which_normalizes_trailing_slash_and_tilde(run, tmp_path):
    run("add", "proj", str(tmp_path))
    # A trailing slash resolves to the same normalized path.
    result = run("which", str(tmp_path) + "/")
    assert result.exit_code == 0
    assert result.output.strip() == "proj"


def test_which_defaults_to_cwd(runner, tmp_path, monkeypatch):
    from navtool.cli import cli

    run_add = runner.invoke(cli, ["add", "here", str(tmp_path)])
    assert run_add.exit_code == 0
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli, ["which"])
    assert result.exit_code == 0
    assert result.output.strip() == "here"


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
    assert "override via $NAVTOOL_DIR" in result.output
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
