"""Shell integration registry.

Knowledge about *which shells navtool can hook into* lives here and nowhere else:
each supported shell is one :class:`Shell` entry describing its startup file and
the packaged resource scripts that make up its integration snippet. Adding a new
shell (e.g. PowerShell) is a matter of dropping a resource file under
``resources/shell/`` and registering one more :class:`Shell` — the ``init`` and
``bootstrap`` commands are otherwise shell-agnostic.

The snippet is emitted by ``navtool init <shell>`` and evaluated from the user's
startup file via a single line (``eval "$(navtool init zsh)"``), so the shipped
package — not a repo checkout — is the source of truth at runtime.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Directory of packaged shell scripts (mirrors db.SCHEMA_PATH's layout).
RESOURCES_DIR = Path(__file__).parent.parent / "resources" / "shell"

# Sentinel markers wrapping the block navtool manages inside a startup file.
# '#' is a comment in every shell we target (sh-family and PowerShell), so the
# markers stay valid as more shells are added.
BLOCK_BEGIN = "# >>> navtool >>>"
BLOCK_END = "# <<< navtool <<<"


@dataclass(frozen=True)
class Shell:
    """A shell navtool knows how to integrate with."""

    name: str  # canonical name, e.g. "zsh"
    rc_filename: str  # startup file under the home directory, e.g. ".zshrc"
    # Packaged resource files that form the base integration, in emit order.
    base_files: tuple[str, ...]
    # Packaged completion script, or None if the shell has no completion support.
    completion_file: str | None = None

    def rc_path(self) -> Path:
        """Absolute path to this shell's startup file in the user's home."""
        return Path.home() / self.rc_filename

    def resource_files(self, completion: bool = True) -> list[str]:
        """Resource filenames to concatenate for this shell's snippet."""
        files = list(self.base_files)
        if completion and self.completion_file:
            files.append(self.completion_file)
        return files


# Supported shells, keyed by canonical name. Register new shells here.
SHELLS: dict[str, Shell] = {
    "zsh": Shell(
        name="zsh",
        rc_filename=".zshrc",
        base_files=("nav.sh", "history.zsh"),
        completion_file="completion.zsh",
    ),
    "bash": Shell(
        name="bash",
        rc_filename=".bashrc",
        base_files=("nav.sh", "history.bash"),
        completion_file="completion.bash",
    ),
}


def supported_shells() -> list[str]:
    """Canonical names of every shell navtool can integrate with."""
    return list(SHELLS)


def detect_shell() -> str | None:
    """Best-effort guess of the current shell from ``$SHELL``.

    ``$SHELL`` names the user's login shell — the reliable signal available to a
    subprocess, since the interactive shell's own ``$ZSH_VERSION`` /
    ``$BASH_VERSION`` are shell (not exported) variables we cannot see. Callers
    let an explicit ``--shell`` override this. Returns ``None`` when ``$SHELL``
    is unset or names a shell we don't support.
    """
    shell_env = os.environ.get("SHELL")
    if not shell_env:
        return None
    name = Path(shell_env).name
    return name if name in SHELLS else None


def render_snippet(shell: Shell, completion: bool = True, history_size: int = 25) -> str:
    """Return the full integration snippet for ``shell``.

    Concatenates the shell's packaged resource files (the ``nav`` function, the
    directory-history helpers and, unless disabled, its completion script) into
    the text that ``navtool init`` prints and the startup file evaluates.

    ``history_size`` (resolved from config by the ``init`` command) is baked into
    a one-line preamble as the default cap for the per-shell history, still
    overridable at runtime via ``$NAV_HISTORY_SIZE``. It is a shell-agnostic
    parameter expansion, valid in every sh-family shell navtool targets.
    """
    preamble = f"_NAV_HISTORY_SIZE=${{NAV_HISTORY_SIZE:-{int(history_size)}}}"
    parts = [preamble]
    parts += [
        (RESOURCES_DIR / name).read_text() for name in shell.resource_files(completion)
    ]
    return "\n".join(part.rstrip("\n") for part in parts) + "\n"


def eval_line(shell: Shell, completion: bool = True) -> str:
    """The single line a startup file runs to load the integration.

    Evaluating ``navtool init`` (rather than sourcing a file) keeps the shipped
    package the source of truth, so the hook survives the repo being moved or
    deleted after a pipx install.
    """
    suffix = "" if completion else " --no-completion"
    return f'eval "$(navtool init {shell.name}{suffix})"'


def build_block(shell: Shell, completion: bool = True) -> str:
    """The full sentinel-delimited block navtool manages in a startup file.

    Returned without a trailing newline so it compares cleanly against a block
    already present in a file (see :func:`apply_block`).
    """
    return "\n".join(
        (
            BLOCK_BEGIN,
            "# Managed by `navtool bootstrap` — do not edit inside this block.",
            eval_line(shell, completion),
            BLOCK_END,
        )
    )


def _find_block(content: str) -> tuple[int, int] | None:
    """Character span ``(start, end)`` of an existing managed block, or None."""
    start = content.find(BLOCK_BEGIN)
    if start == -1:
        return None
    end = content.find(BLOCK_END, start)
    if end == -1:
        return None
    return start, end + len(BLOCK_END)


def apply_block(content: str, block: str) -> tuple[str, str]:
    """Idempotently place ``block`` into startup-file ``content``.

    Returns ``(new_content, action)`` where ``action`` is:

    - ``"unchanged"`` — an identical block already exists (no write needed),
    - ``"updated"``   — an existing block differed and was replaced in place,
    - ``"added"``     — no block existed and one was appended.

    This is what keeps repeated ``navtool bootstrap`` runs from polluting the
    file: the managed region is only ever replaced, never duplicated.
    """
    span = _find_block(content)
    if span is not None:
        start, end = span
        if content[start:end] == block:
            return content, "unchanged"
        return content[:start] + block + content[end:], "updated"

    prefix = content
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix:
        prefix += "\n"  # blank line between prior content and our block
    return prefix + block + "\n", "added"
