"""`nav ls` — list entries as a tree."""

import click

from navtool.cli.tree import (_render_subtree, _require_node,
                              name_path_completer)


@click.command("ls")
@click.argument(
    "name_path",
    metavar="<NAME|A:B:C>",
    required=False,
    shell_complete=name_path_completer,
)
@click.option(
    "-l",
    "--level",
    type=click.IntRange(min=1),
    default=None,
    metavar="N",
    help="Show only N levels deep: 1 = top-level only, 2 = plus direct children.",
)
@click.pass_context
def ls(ctx, name_path, level):
    """List entries as a tree. With a name path, list only that subtree.

    Use --level to cap nesting depth, counted from each listed root: --level=1
    shows only top-level names, --level=2 adds their direct children, and so on.
    """
    conn = ctx.obj["conn"]
    lines: list[str] = []
    if name_path:
        node = _require_node(conn, name_path)
        _render_subtree(conn, node[0], node[2], node[3], 0, lines, level)
    else:
        for tid, tname, tpath in conn.execute(
            "SELECT id, name, path FROM nodes WHERE parent_id IS NULL ORDER BY name"
        ).fetchall():
            _render_subtree(conn, tid, tname, tpath, 0, lines, level)
    if not lines:
        click.echo("(no entries)")
        return
    for line in lines:
        click.echo(line)
