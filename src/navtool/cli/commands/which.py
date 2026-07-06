"""`nav which` — reverse lookup: which name(s) point at a directory."""

from pathlib import Path

import click

from navtool.cli.tree import _node_path


@click.command("which")
@click.argument(
    "directory",
    metavar="<DIRECTORY>",
    required=False,
    type=click.Path(file_okay=False),
)
@click.pass_context
def which(ctx, directory):
    """Show which name(s) point at a directory (default: the current directory).

    Normalizes the directory the same way `add` does (expanding `~` and
    resolving symlinks), then lists every name whose target matches it. Exits
    non-zero if none do, so it can be used as a check.
    """
    conn = ctx.obj["conn"]
    target = str(Path(directory or ".").expanduser().resolve())

    ids = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM nodes WHERE path = ?", (target,)
        ).fetchall()
    ]
    if not ids:
        click.echo(f"No name points at {target}.")
        ctx.exit(1)

    for name_path in sorted(_node_path(conn, node_id) for node_id in ids):
        click.echo(click.style(name_path, fg="green"))
