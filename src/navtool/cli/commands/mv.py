"""`nav mv` — move a name under a new parent and/or rename it."""

import click

from navtool.cli.tree import (_parse_path, _require_node, _resolve,
                              name_path_completer)


@click.command("mv")
@click.argument("name_path", metavar="<NAME|A:B:C>", shell_complete=name_path_completer)
@click.option(
    "--to",
    "-t",
    "to_path",
    default=None,
    help="Move under this existing parent (a name path).",
    shell_complete=name_path_completer,
)
@click.option(
    "--root",
    is_flag=True,
    default=False,
    help="Move to the top level (no parent).",
)
@click.option("--rename", "-r", "new_name", default=None, help="New name.")
@click.pass_context
def mv(ctx, name_path, to_path, root, new_name):
    """Move an entry under a new parent and/or rename it."""
    conn = ctx.obj["conn"]
    if to_path is not None and root:
        raise click.ClickException("Pass either --to or --root, not both.")
    if to_path is None and not root and new_name is None:
        raise click.ClickException("Nothing to do: pass --to, --root, and/or --rename.")
    if new_name is not None and ":" in new_name:
        raise click.ClickException(
            "A name cannot contain ':'. Use --to to change the parent."
        )

    node_id, cur_parent, cur_name, _ = _require_node(conn, name_path)

    reparent = to_path is not None or root
    if root:
        new_parent_id = None
    elif to_path is not None:
        parent = _resolve(conn, _parse_path(to_path))
        if parent is None:
            raise click.ClickException(f"Destination '{to_path}' does not exist.")
        new_parent_id = parent[0]
    else:
        new_parent_id = cur_parent

    # Reject moves that would create a cycle: the new parent must not be the node
    # itself or any of its descendants.
    if reparent and new_parent_id is not None:
        anc = new_parent_id
        while anc is not None:
            if anc == node_id:
                raise click.ClickException(
                    f"Cannot move '{name_path}' under itself or its own descendant."
                )
            row = conn.execute(
                "SELECT parent_id FROM nodes WHERE id = ?", (anc,)
            ).fetchone()
            anc = row[0] if row else None

    final_parent = new_parent_id if reparent else cur_parent
    final_name = new_name if new_name is not None else cur_name

    if conn.execute(
        "SELECT 1 FROM nodes WHERE parent_id IS ? AND name = ? AND id != ?",
        (final_parent, final_name, node_id),
    ).fetchone():
        raise click.ClickException(
            f"A node named '{final_name}' already exists at the destination."
        )

    conn.execute(
        "UPDATE nodes SET parent_id = ?, name = ? WHERE id = ?",
        (final_parent, final_name, node_id),
    )
    conn.commit()
    if root:
        dest = " to the top level"
    elif to_path is not None:
        dest = f" under '{to_path}'"
    else:
        dest = ""
    click.echo(f"Moved '{name_path}' -> '{final_name}'{dest}")
