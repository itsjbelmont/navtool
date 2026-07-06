"""`nav rm` — remove a name and any nested children."""

import click

from navtool.cli.tree import _descendant_count, _require_node


@click.command("rm")
@click.argument("name_path", metavar="<NAME|A:B:C>")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt for nested entries.",
)
@click.pass_context
def rm(ctx, name_path, yes):
    """Remove an entry. Nested children are removed with it."""
    conn = ctx.obj["conn"]
    node = _require_node(conn, name_path)
    node_id = node[0]

    nested = _descendant_count(conn, node_id)
    if nested > 0 and not yes:
        if not click.confirm(
            f"'{name_path}' has {nested} nested entr"
            f"{'y' if nested == 1 else 'ies'} that will also be removed. Continue?",
            default=False,
        ):
            click.echo("Operation cancelled.")
            return

    conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
    conn.commit()
    suffix = (
        f" and {nested} nested entr{'y' if nested == 1 else 'ies'}" if nested else ""
    )
    click.echo(f"Removed '{name_path}'{suffix}")
