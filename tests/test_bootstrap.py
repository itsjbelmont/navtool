"""Tests for `navtool init` and `navtool bootstrap` shell integration."""

import pytest
from click.testing import CliRunner

from navtool.cli import cli
from navtool.cli.shells import BLOCK_BEGIN, BLOCK_END


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def run(runner):
    def _run(*args, **kwargs):
        return runner.invoke(cli, [str(a) for a in args], **kwargs)

    return _run


# ----------------- init -----------------
def test_init_zsh_emits_function_and_completion(run):
    result = run("init", "zsh")
    assert result.exit_code == 0
    assert "nav()" in result.output  # nav.sh function
    assert "compdef" in result.output  # zsh completion


def test_init_no_completion_omits_completion(run):
    result = run("init", "zsh", "--no-completion")
    assert result.exit_code == 0
    assert "nav()" in result.output
    assert "compdef" not in result.output


def test_init_bash_differs_from_zsh(run):
    bash = run("init", "bash").output
    zsh = run("init", "zsh").output
    assert "complete -o nospace" in bash  # bash completion
    assert bash != zsh


def test_init_unknown_shell_errors(run):
    result = run("init", "fish")
    assert result.exit_code != 0
    assert "Unsupported shell" in result.output


def test_init_detects_from_shell_env(run, monkeypatch):
    monkeypatch.setenv("SHELL", "/bin/zsh")
    result = run("init")
    assert result.exit_code == 0
    assert "nav()" in result.output


def test_init_no_detect_no_arg_errors(run, monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    result = run("init")
    assert result.exit_code != 0
    assert "Could not detect" in result.output


# ----------------- bootstrap -----------------
def _count_blocks(text):
    return text.count(BLOCK_BEGIN)


def test_bootstrap_adds_block_to_new_file(run, tmp_path):
    rc = tmp_path / ".zshrc"
    result = run("bootstrap", "--shell", "zsh", "--rc", rc)
    assert result.exit_code == 0
    content = rc.read_text()
    assert _count_blocks(content) == 1
    assert BLOCK_END in content
    assert 'eval "$(navtool init zsh)"' in content


def test_bootstrap_preserves_existing_content(run, tmp_path):
    rc = tmp_path / ".zshrc"
    rc.write_text("export FOO=bar\n")
    run("bootstrap", "--shell", "zsh", "--rc", rc)
    content = rc.read_text()
    assert "export FOO=bar" in content
    assert _count_blocks(content) == 1


def test_bootstrap_is_idempotent(run, tmp_path):
    rc = tmp_path / ".zshrc"
    run("bootstrap", "--shell", "zsh", "--rc", rc)
    first = rc.read_text()
    result = run("bootstrap", "--shell", "zsh", "--rc", rc)
    assert result.exit_code == 0
    assert "already configured" in result.output
    assert rc.read_text() == first  # unchanged, no second block
    assert _count_blocks(rc.read_text()) == 1


def test_bootstrap_updates_stale_block_in_place(run, tmp_path):
    rc = tmp_path / ".zshrc"
    stale = f'{BLOCK_BEGIN}\neval "$(navtool init bash)"\n{BLOCK_END}\n'
    rc.write_text(f"# top\n{stale}# bottom\n")
    result = run("bootstrap", "--shell", "zsh", "--rc", rc)
    assert result.exit_code == 0
    content = rc.read_text()
    assert _count_blocks(content) == 1  # replaced, not duplicated
    assert 'eval "$(navtool init zsh)"' in content
    assert 'eval "$(navtool init bash)"' not in content
    assert "# top" in content and "# bottom" in content  # surrounding lines kept


def test_bootstrap_no_completion_line(run, tmp_path):
    rc = tmp_path / ".zshrc"
    run("bootstrap", "--shell", "zsh", "--rc", rc, "--no-completion")
    assert 'eval "$(navtool init zsh --no-completion)"' in rc.read_text()


def test_bootstrap_dry_run_writes_nothing(run, tmp_path):
    rc = tmp_path / ".zshrc"
    result = run("bootstrap", "--shell", "zsh", "--rc", rc, "--dry-run")
    assert result.exit_code == 0
    assert "Would add" in result.output
    assert not rc.exists()


def test_bootstrap_print_writes_nothing(run, tmp_path):
    rc = tmp_path / ".zshrc"
    result = run("bootstrap", "--shell", "zsh", "--rc", rc, "--print")
    assert result.exit_code == 0
    assert BLOCK_BEGIN in result.output
    assert not rc.exists()


def test_bootstrap_backs_up_existing_file(run, tmp_path):
    rc = tmp_path / ".zshrc"
    rc.write_text("original\n")
    result = run("bootstrap", "--shell", "zsh", "--rc", rc)
    assert result.exit_code == 0
    backups = list(tmp_path.glob(".zshrc.navtool-bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "original\n"


def test_bootstrap_unknown_shell_errors(run, tmp_path):
    result = run("bootstrap", "--shell", "fish", "--rc", tmp_path / ".x")
    assert result.exit_code != 0
    assert "Unsupported shell" in result.output


def test_bootstrap_no_detect_errors(run, tmp_path, monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    result = run("bootstrap", "--rc", tmp_path / ".x")
    assert result.exit_code != 0
    assert "Could not detect" in result.output
