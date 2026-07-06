"""`nav db info` — summarize the database in use."""

from pathlib import Path

import click

from navtool import __version__
from navtool.cli.config import resolve_db
from navtool.db import SCHEMA_VERSION, _get_user_version


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024


@click.command("info")
@click.pass_context
def db_info(ctx):
    """Show which database is in use, why, and a quick summary of its contents."""
    conn = ctx.obj["conn"]
    path, source = resolve_db()

    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    top_count = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE parent_id IS NULL"
    ).fetchone()[0]
    size = _format_size(Path(path).stat().st_size) if Path(path).exists() else "0 B"

    db_version = _get_user_version(conn)
    if db_version == SCHEMA_VERSION:
        schema = f"version {db_version} (up to date)"
    else:
        schema = f"version {db_version} -> {SCHEMA_VERSION} pending"

    label = click.style(path, fg="cyan")
    click.echo(f"Database:  {label}")
    click.echo(f"Source:    {source}")
    click.echo(f"Size:      {size}")
    click.echo(f"Schema:    {schema}")
    click.echo(f"NavTool:   {__version__}")
    click.echo(f"Nodes:     {node_count}")
    click.echo(f"Top-level: {top_count}")
