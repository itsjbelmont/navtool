"""`nav add` — register a name pointing at a directory."""

import click

from navtool.cli.tree import _parse_path, _resolve, _resolve_directory


@click.command("add")
@click.argument("name_path", metavar="<NAME|PARENT:NAME>")
@click.argument("directory", metavar="<DIRECTORY>")
@click.pass_context
def add(ctx, name_path, directory):
    """Register a name pointing at a directory.

    A bare NAME creates a top-level entry. A PARENT:NAME path nests the new entry
    under an existing parent (which must already exist).
    """
    conn = ctx.obj["conn"]
    *parent_segments, name = _parse_path(name_path)

    parent_id = None
    if parent_segments:
        parent = _resolve(conn, parent_segments)
        if parent is None:
            raise click.ClickException(
                f"Parent '{':'.join(parent_segments)}' does not exist."
            )
        parent_id = parent[0]

    if conn.execute(
        "SELECT 1 FROM nodes WHERE parent_id IS ? AND name = ?",
        (parent_id, name),
    ).fetchone():
        where = ":".join(parent_segments) if parent_segments else "the top level"
        raise click.ClickException(f"'{name}' already exists under {where}.")

    full_path = _resolve_directory(directory)
    conn.execute(
        "INSERT INTO nodes (parent_id, name, path) VALUES (?, ?, ?)",
        (parent_id, name, full_path),
    )
    conn.commit()
    click.echo(f"Added '{name_path}' -> {full_path}")
