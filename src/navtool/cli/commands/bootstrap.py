"""`navtool bootstrap` — wire the shell integration into a startup file.

Adds a single ``eval "$(navtool init <shell>)"`` line to the user's startup file
(``~/.zshrc``, ``~/.bashrc``, …) inside a sentinel-delimited block. Re-running is
safe: an existing block is replaced in place rather than duplicated, so the file
never accumulates stale copies (see :func:`navtool.cli.shells.apply_block`).
"""

import datetime
import os
import tempfile
from pathlib import Path

import click

from navtool.cli.shells import (SHELLS, apply_block, build_block, detect_shell,
                                supported_shells)


def _backup(path: Path) -> Path:
    """Copy ``path`` to a timestamped ``*.navtool-bak-*`` sibling and return it.

    Mirrors the pre-migration backup habit in :mod:`navtool.db`: never modify a
    user file in place without leaving a restorable copy behind first.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.navtool-bak-{stamp}")
    backup.write_text(path.read_text())
    return backup


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (temp file + replace)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


@click.command("bootstrap")
@click.option(
    "--shell",
    "shell_name",
    metavar="NAME",
    help="Shell to configure (default: detected from $SHELL).",
)
@click.option(
    "--rc",
    "rc_file",
    metavar="PATH",
    type=click.Path(dir_okay=False),
    help="Startup file to edit (default: the shell's standard file).",
)
@click.option("--no-completion", is_flag=True, help="Configure without tab-completion.")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
@click.option(
    "--print",
    "print_only",
    is_flag=True,
    help="Print the managed block to stdout and exit; edit nothing.",
)
def bootstrap(shell_name, rc_file, no_completion, dry_run, print_only):
    """Set up navtool's shell integration in your startup file.

    Detects your shell (override with --shell), then adds an `eval "$(navtool
    init ...)"` line to its startup file inside a managed block. Safe to re-run:
    an existing block is updated in place, never duplicated. After it finishes,
    restart your shell or re-source the file.
    """
    name = shell_name or detect_shell()
    if name not in SHELLS:
        supported = ", ".join(supported_shells())
        if shell_name:
            raise click.ClickException(
                f"Unsupported shell '{shell_name}'. Supported shells: {supported}."
            )
        raise click.ClickException(
            "Could not detect your shell from $SHELL. "
            f"Pass one explicitly: navtool bootstrap --shell <{supported}>."
        )

    shell = SHELLS[name]
    block = build_block(shell, completion=not no_completion)

    if print_only:
        click.echo(block)
        return

    target = Path(rc_file).expanduser() if rc_file else shell.rc_path()
    content = target.read_text() if target.exists() else ""
    new_content, action = apply_block(content, block)

    if action == "unchanged":
        click.echo(f"navtool is already configured in {target}. Nothing to do.")
        return

    if dry_run:
        would = (
            "add the navtool block to"
            if action == "added"
            else "update the navtool block in"
        )
        click.echo(f"Would {would} {target}:")
        click.echo(block)
        return

    if target.exists():
        backup = _backup(target)
        click.echo(f"Backed up {target} -> {backup}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)

    _atomic_write(target, new_content)

    verb = "Added" if action == "added" else "Updated"
    click.echo(f"{verb} navtool integration in {target}.")
    click.echo(f"Restart your shell or run:  source {target}")
