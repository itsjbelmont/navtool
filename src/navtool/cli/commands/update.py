"""`nav update` — repoint an existing name at a new directory."""

import click

from navtool.cli.tree import _require_node, _resolve_directory


@click.command("update")
@click.argument("name_path", metavar="<NAME|A:B:C>")
@click.argument("directory", metavar="<NEW_DIRECTORY>")
@click.pass_context
def update(ctx, name_path, directory):
    """Repoint an existing entry at a new directory."""
    conn = ctx.obj["conn"]
    node = _require_node(conn, name_path)
    full_path = _resolve_directory(directory)
    conn.execute("UPDATE nodes SET path = ? WHERE id = ?", (full_path, node[0]))
    conn.commit()
    click.echo(f"Updated '{name_path}' -> {full_path}")
