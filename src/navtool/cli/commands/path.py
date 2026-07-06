"""`nav path` — resolve a name to its directory (shell plumbing)."""

import click

from navtool.cli.tree import _parse_path, _resolve, name_path_completer


@click.command("path")
@click.argument("query", metavar="<NAME|A:B:C>", shell_complete=name_path_completer)
@click.pass_context
def get_path(ctx, query):
    """Resolve a name (or nested a:b:c path) to its directory path.

    Exits non-zero if nothing matches so the shell wrapper can fall back to a
    plain `cd`.
    """
    conn = ctx.obj["conn"]
    node = _resolve(conn, _parse_path(query))
    if node is None:
        raise click.ClickException(f"No entry found for '{query}'.")
    click.echo(node[3])
