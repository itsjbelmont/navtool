"""Shell-integration tests for directory history (`nav -` / `nav +` / `nav history`).

The history feature is pure shell (state lives in the shell session), so it can't
be exercised through the Python CLI. These tests drive the packaged snippets in a
real zsh/bash and assert the browser-style back/forward behaviour. A shell that
isn't installed is skipped rather than failed.

The shell starts in dir ``a`` (so ``a`` is the seed / oldest entry). Directory
changes are recorded by zsh's ``chpwd`` hook automatically, but bash records from
``PROMPT_COMMAND`` which never fires in a non-interactive ``bash -c`` — so every
body calls ``_nav_record`` after a ``cd`` to simulate the prompt. In zsh that
manual call is a harmless no-op (it dedupes against the current entry).
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

SHELL_DIR = Path(__file__).resolve().parents[1] / "src" / "navtool" / "resources" / "shell"

# (shell binary, its history resource file, invocation flags for a clean shell).
SHELLS = [
    ("zsh", "history.zsh", ["-f"]),
    ("bash", "history.bash", ["--noprofile", "--norc"]),
]


@pytest.fixture
def dirs(tmp_path):
    """Create sibling dirs a..e under tmp_path; return the mapping."""
    made = {}
    for name in "abcde":
        d = tmp_path / name
        d.mkdir()
        made[name] = d
    return made


def _run(shell, hist_file, flags, start_dir, body, size=25):
    """Source the snippet in `shell`, run `body`, return the CompletedProcess.

    The shell starts in `start_dir`, so that directory is the seeded oldest entry.
    """
    script = textwrap.dedent(
        f"""
        _NAV_HISTORY_SIZE={size}
        source "{SHELL_DIR / 'nav.sh'}"
        source "{SHELL_DIR / hist_file}"
        """
    ) + body
    return subprocess.run(
        [shell, *flags, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(start_dir),
    )


def _results(proc):
    """Basenames printed via `echo RESULT=<name>` lines, in order."""
    return [
        line[len("RESULT="):]
        for line in proc.stdout.splitlines()
        if line.startswith("RESULT=")
    ]


def _shell_or_skip(shell):
    if shutil.which(shell) is None:
        pytest.skip(f"{shell} not installed")


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
def test_back_then_forward(shell, hist_file, flags, dirs):
    _shell_or_skip(shell)
    body = textwrap.dedent(
        f"""
        cd "{dirs['b']}"; _nav_record
        cd "{dirs['c']}"; _nav_record
        nav -2; echo "RESULT=${{PWD##*/}}"
        nav +1; echo "RESULT=${{PWD##*/}}"
        """
    )
    proc = _run(shell, hist_file, flags, dirs["a"], body)
    assert proc.returncode == 0, proc.stderr
    # a (start) -> b -> c; back 2 lands on a, forward 1 lands on b. Tokens are
    # unquoted here on purpose: `-`/`+` aren't shell metacharacters (unlike the
    # old `<`/`>`), so this exercises exactly what a user types.
    assert _results(proc) == ["a", "b"]


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
def test_cap_trims_oldest(shell, hist_file, flags, dirs):
    _shell_or_skip(shell)
    body = textwrap.dedent(
        f"""
        cd "{dirs['b']}"; _nav_record
        cd "{dirs['c']}"; _nav_record
        nav -9; echo "RESULT=${{PWD##*/}}"
        nav history
        """
    )
    # size 2: visiting a,b,c keeps only b,c — a is trimmed and unreachable.
    proc = _run(shell, hist_file, flags, dirs["a"], body, size=2)
    assert proc.returncode == 0, proc.stderr
    assert _results(proc) == ["b"]  # clamped at the oldest surviving entry
    history_lines = [ln for ln in proc.stdout.splitlines() if ln and not ln.startswith("RESULT=")]
    assert len(history_lines) == 2  # exactly the cap


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
def test_new_cd_truncates_forward(shell, hist_file, flags, dirs):
    _shell_or_skip(shell)
    body = textwrap.dedent(
        f"""
        cd "{dirs['b']}"; _nav_record
        cd "{dirs['c']}"; _nav_record
        nav -2; echo "RESULT=${{PWD##*/}}"
        cd "{dirs['d']}"; _nav_record
        nav history
        nav +1; echo "RESULT=${{PWD##*/}}"
        """
    )
    proc = _run(shell, hist_file, flags, dirs["a"], body)
    assert proc.returncode == 0, proc.stderr
    # Back to a, then a new cd to d drops the forward trail (b, c).
    hist = proc.stdout
    assert "/a" in hist and "/d" in hist
    assert "/b" not in hist and "/c" not in hist
    # `nav -2` lands on a; after the truncating cd to d we're at the newest
    # entry, so `nav +1` can't move and stays on d.
    assert _results(proc) == ["a", "d"]
    assert "already at the newest directory" in proc.stderr


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
def test_history_list_marks_position(shell, hist_file, flags, dirs):
    _shell_or_skip(shell)
    body = textwrap.dedent(
        f"""
        cd "{dirs['b']}"; _nav_record
        nav history
        """
    )
    proc = _run(shell, hist_file, flags, dirs["a"], body)
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    # Oldest (a) reachable with `nav -1`; current (b) marked with *.
    assert any(ln.startswith("-1") and ln.endswith("/a") for ln in lines)
    assert any(ln.startswith("*") and ln.endswith("/b") for ln in lines)


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
def test_history_list_plain_when_piped(shell, hist_file, flags, dirs):
    _shell_or_skip(shell)
    # The current entry is highlighted on a TTY, but output must stay free of
    # ANSI escapes when piped (as here) so scripts and pipelines aren't corrupted.
    body = f'cd "{dirs["b"]}"; _nav_record\nnav history\n'
    proc = _run(shell, hist_file, flags, dirs["a"], body)
    assert proc.returncode == 0, proc.stderr
    assert "\x1b" not in proc.stdout


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
def test_invalid_offset_errors(shell, hist_file, flags, dirs):
    _shell_or_skip(shell)
    # `-3x` is dispatched as a history offset (digit after the sign) but has a
    # non-numeric tail, so _nav_go rejects it.
    proc = _run(shell, hist_file, flags, dirs["a"], "nav -3x\n")
    assert proc.returncode != 0
    assert "invalid history offset" in proc.stderr


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
@pytest.mark.parametrize("flag", ["-h", "--help", "--version"])
def test_option_flags_are_not_history_offsets(shell, hist_file, flags, dirs, flag):
    _shell_or_skip(shell)
    # Option flags start with '-' but have a letter (not a digit) next, so the
    # dispatch must route them to navtool, never to _nav_go. A stub navtool
    # stands in: `__route` returns "passthrough", the real call echoes its args.
    body = textwrap.dedent(
        f"""
        navtool() {{ [ "$1" = "__route" ] && return 1; echo "NAVTOOL $*"; }}
        nav {flag}
        """
    )
    proc = _run(shell, hist_file, flags, dirs["a"], body)
    assert proc.returncode == 0, proc.stderr
    assert f"NAVTOOL {flag}" in proc.stdout
    assert "invalid history offset" not in proc.stderr


@pytest.mark.parametrize("shell,hist_file,flags", SHELLS)
def test_repeated_same_dir_not_duplicated(shell, hist_file, flags, dirs):
    _shell_or_skip(shell)
    body = textwrap.dedent(
        f"""
        cd "{dirs['b']}"; _nav_record
        cd "{dirs['b']}"; _nav_record
        nav history
        """
    )
    proc = _run(shell, hist_file, flags, dirs["a"], body)
    assert proc.returncode == 0, proc.stderr
    history_lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(history_lines) == 2  # a and b, not a b b
