import click
from pathlib import Path

from navtool.db import get_connection, DEFAULT_SET

DEFAULT_DB_PATH = "~/.navtool.db"


# ----------------- Helpers -----------------
def _validate_name(name: str, kind: str) -> None:
    """Reject names that would collide with the set:key delimiter."""
    if ":" in name:
        raise click.ClickException(
            f"Invalid {kind} name '{name}': ':' is reserved as the set:key delimiter."
        )


def _require_set(conn, set_name: str) -> None:
    """Raise a friendly error if the given set does not exist."""
    row = conn.execute(
        "SELECT 1 FROM sets WHERE set_name = ?", (set_name,)
    ).fetchone()
    if row is None:
        raise click.ClickException(f"Set '{set_name}' does not exist.")


def _resolve_directory(directory: str) -> str:
    """Expand/resolve a directory argument, ensuring it exists."""
    full_path = str(Path(directory).expanduser().resolve())
    if not Path(full_path).is_dir():
        raise click.ClickException(f"Directory does not exist: {full_path}")
    return full_path


# ----------------- Top-level CLI -----------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli(ctx):
    """
    Navigate directories by associating short keywords to commonly accessed
    directory paths. Keywords can be organized into sets to support switching
    between projects.
    """
    db_path = str(Path(DEFAULT_DB_PATH).expanduser())
    ctx.ensure_object(dict)
    ctx.obj["conn"] = get_connection(db_path)


# ----------------- `path` command (shell plumbing) -----------------
@cli.command("path")
@click.argument("query", metavar="<KEYWORD|SET:KEYWORD>")
@click.pass_context
def get_path(ctx, query):
    """Resolve a keyword (or set:keyword) to its directory path.

    Exits non-zero if nothing matches so the shell wrapper can fall back to a
    plain `cd`.
    """
    conn = ctx.obj["conn"]
    if ":" in query:
        set_name, _, entry_key = query.partition(":")
    else:
        set_name, entry_key = DEFAULT_SET, query

    row = conn.execute(
        "SELECT entry_value FROM entries WHERE set_name = ? AND entry_key = ?",
        (set_name, entry_key),
    ).fetchone()
    if row is None:
        raise click.ClickException(
            f"No keyword '{entry_key}' found in set '{set_name}'."
        )
    click.echo(row[0])


# ================= `set` command group =================
@cli.group("set")
def set_group():
    """Manage sets (named collections of keywords)."""


@set_group.command("list")
@click.option(
    "--describe",
    "-d",
    is_flag=True,
    default=False,
    help="Also show each set's description.",
)
@click.pass_context
def set_list(ctx, describe):
    """List all sets."""
    conn = ctx.obj["conn"]
    rows = conn.execute(
        "SELECT set_name, description FROM sets "
        "ORDER BY set_name = ? DESC, set_name",
        (DEFAULT_SET,),
    ).fetchall()
    for set_name, description in rows:
        color = "cyan" if set_name == DEFAULT_SET else "green"
        text = click.style(set_name, fg=color)
        if describe:
            click.echo(f"{text} – {description or '(no description)'}")
        else:
            click.echo(text)


@set_group.command("show")
@click.argument("set_name", metavar="<NAME>")
@click.pass_context
def set_show(ctx, set_name):
    """Show a set's description and all of its keyword entries."""
    conn = ctx.obj["conn"]
    row = conn.execute(
        "SELECT description FROM sets WHERE set_name = ?", (set_name,)
    ).fetchone()
    if row is None:
        raise click.ClickException(f"Set '{set_name}' does not exist.")
    click.echo(f"{set_name}: {row[0] or '(no description)'}")
    _echo_entries(conn, set_name)


@set_group.command("add")
@click.argument("set_name", metavar="<NAME>")
@click.option(
    "--desc",
    "-d",
    "description",
    default=None,
    help="Optional description for the set.",
)
@click.pass_context
def set_add(ctx, set_name, description):
    """Create a new set."""
    conn = ctx.obj["conn"]
    _validate_name(set_name, "set")
    if conn.execute(
        "SELECT 1 FROM sets WHERE set_name = ?", (set_name,)
    ).fetchone():
        raise click.ClickException(f"Set '{set_name}' already exists.")
    conn.execute(
        "INSERT INTO sets (set_name, description) VALUES (?, ?)",
        (set_name, description),
    )
    conn.commit()
    click.echo(f"Created set: {set_name} - {description or '(no description)'}")


@set_group.command("remove")
@click.argument("set_name", metavar="<NAME>")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt.",
)
@click.pass_context
def set_remove(ctx, set_name, yes):
    """Delete a set and all of its keywords."""
    conn = ctx.obj["conn"]
    if set_name == DEFAULT_SET:
        raise click.ClickException("The 'default' set cannot be removed.")
    _require_set(conn, set_name)
    if not yes and not click.confirm(
        f"Are you sure you want to delete the set '{set_name}'?", default=False
    ):
        click.echo("Operation cancelled.")
        return
    conn.execute("DELETE FROM sets WHERE set_name = ?", (set_name,))
    conn.commit()
    click.echo(f"Deleted the '{set_name}' set.")


@set_group.command("update")
@click.argument("set_name", metavar="<NAME>")
@click.option("--rename", "new_name", default=None, help="New name for the set.")
@click.option(
    "--desc",
    "-d",
    "description",
    default=None,
    help="New description for the set.",
)
@click.pass_context
def set_update(ctx, set_name, new_name, description):
    """Rename a set and/or change its description."""
    conn = ctx.obj["conn"]
    if set_name == DEFAULT_SET:
        raise click.ClickException("The 'default' set cannot be modified.")
    _require_set(conn, set_name)
    if new_name is None and description is None:
        raise click.ClickException("Nothing to update: pass --rename and/or --desc.")

    if new_name is not None:
        _validate_name(new_name, "set")
        if new_name == DEFAULT_SET:
            raise click.ClickException("Cannot rename a set to 'default'.")
        if conn.execute(
            "SELECT 1 FROM sets WHERE set_name = ?", (new_name,)
        ).fetchone():
            raise click.ClickException(f"Set '{new_name}' already exists.")

    if description is not None:
        conn.execute(
            "UPDATE sets SET description = ? WHERE set_name = ?",
            (description, set_name),
        )
    if new_name is not None:
        # ON UPDATE CASCADE carries the rename through to the entries table.
        conn.execute(
            "UPDATE sets SET set_name = ? WHERE set_name = ?",
            (new_name, set_name),
        )
    conn.commit()

    if new_name is not None:
        click.echo(f"Renamed set '{set_name}' -> '{new_name}'")
    if description is not None:
        click.echo(f"Updated description for set '{new_name or set_name}'")


# ================= `key` command group =================
@cli.group("key")
def key_group():
    """Manage keyword entries within sets."""


def _echo_entries(conn, set_name: str) -> None:
    """Print the entries of a set (indented), or a placeholder if empty."""
    entries = conn.execute(
        "SELECT entry_key, entry_value FROM entries "
        "WHERE set_name = ? ORDER BY entry_key",
        (set_name,),
    ).fetchall()
    if not entries:
        click.echo("  (no entries)")
        return
    for entry_key, entry_value in entries:
        click.echo(f"  {entry_key} -> {entry_value}")


@key_group.command("list")
@click.option(
    "--set",
    "-s",
    "set_name",
    default=None,
    help="Only list keywords in this set.",
)
@click.pass_context
def key_list(ctx, set_name):
    """List keywords, grouped by set."""
    conn = ctx.obj["conn"]
    if set_name is not None:
        _require_set(conn, set_name)
        set_names = [set_name]
    else:
        set_names = [
            r[0]
            for r in conn.execute(
                "SELECT set_name FROM sets ORDER BY set_name = ? DESC, set_name",
                (DEFAULT_SET,),
            ).fetchall()
        ]

    for name in set_names:
        color = "cyan" if name == DEFAULT_SET else "green"
        click.echo(click.style(f"{name}:", fg=color))
        _echo_entries(conn, name)


@key_group.command("add")
@click.argument("keyword", metavar="<KEYWORD>")
@click.argument("directory", metavar="<DIRECTORY>")
@click.option(
    "--set",
    "-s",
    "set_name",
    default=DEFAULT_SET,
    show_default=True,
    help="Set to register the keyword in.",
)
@click.pass_context
def key_add(ctx, keyword, directory, set_name):
    """Register a keyword pointing at a directory."""
    conn = ctx.obj["conn"]
    _validate_name(keyword, "keyword")
    _require_set(conn, set_name)
    full_path = _resolve_directory(directory)

    if conn.execute(
        "SELECT 1 FROM entries WHERE set_name = ? AND entry_key = ?",
        (set_name, keyword),
    ).fetchone():
        raise click.ClickException(
            f"Keyword '{keyword}' already exists in set '{set_name}'."
        )

    conn.execute(
        "INSERT INTO entries (set_name, entry_key, entry_value) VALUES (?, ?, ?)",
        (set_name, keyword, full_path),
    )
    conn.commit()
    click.echo(f"Registered '{keyword}' -> '{full_path}' in set '{set_name}'")


@key_group.command("remove")
@click.argument("keyword", metavar="<KEYWORD>")
@click.option(
    "--set",
    "-s",
    "set_name",
    default=DEFAULT_SET,
    show_default=True,
    help="Set the keyword belongs to.",
)
@click.pass_context
def key_remove(ctx, keyword, set_name):
    """Remove a keyword from a set."""
    conn = ctx.obj["conn"]
    cur = conn.execute(
        "DELETE FROM entries WHERE set_name = ? AND entry_key = ?",
        (set_name, keyword),
    )
    conn.commit()
    if cur.rowcount == 0:
        raise click.ClickException(
            f"No keyword '{keyword}' found in set '{set_name}'."
        )
    click.echo(f"Removed '{keyword}' from set '{set_name}'")


@key_group.command("update")
@click.argument("keyword", metavar="<KEYWORD>")
@click.argument("directory", metavar="<NEW_DIRECTORY>")
@click.option(
    "--set",
    "-s",
    "set_name",
    default=DEFAULT_SET,
    show_default=True,
    help="Set the keyword belongs to.",
)
@click.pass_context
def key_update(ctx, keyword, directory, set_name):
    """Repoint an existing keyword at a new directory."""
    conn = ctx.obj["conn"]
    full_path = _resolve_directory(directory)
    cur = conn.execute(
        "UPDATE entries SET entry_value = ? WHERE set_name = ? AND entry_key = ?",
        (full_path, set_name, keyword),
    )
    conn.commit()
    if cur.rowcount == 0:
        raise click.ClickException(
            f"No keyword '{keyword}' found in set '{set_name}'."
        )
    click.echo(f"Updated '{keyword}' -> '{full_path}' in set '{set_name}'")


@key_group.command("move")
@click.argument("keyword", metavar="<KEYWORD>")
@click.option("--to", "-t", "to_set", required=True, help="Destination set.")
@click.option(
    "--from",
    "-f",
    "from_set",
    default=DEFAULT_SET,
    show_default=True,
    help="Source set.",
)
@click.pass_context
def key_move(ctx, keyword, to_set, from_set):
    """Move a keyword (and its path) from one set to another."""
    conn = ctx.obj["conn"]
    if from_set == to_set:
        raise click.ClickException("Source and destination sets are the same.")
    _require_set(conn, from_set)
    _require_set(conn, to_set)

    row = conn.execute(
        "SELECT entry_value FROM entries WHERE set_name = ? AND entry_key = ?",
        (from_set, keyword),
    ).fetchone()
    if row is None:
        raise click.ClickException(
            f"No keyword '{keyword}' found in set '{from_set}'."
        )
    value = row[0]

    if conn.execute(
        "SELECT 1 FROM entries WHERE set_name = ? AND entry_key = ?",
        (to_set, keyword),
    ).fetchone():
        raise click.ClickException(
            f"Keyword '{keyword}' already exists in set '{to_set}'."
        )

    conn.execute(
        "UPDATE entries SET set_name = ? WHERE set_name = ? AND entry_key = ?",
        (to_set, from_set, keyword),
    )
    conn.commit()
    click.echo(
        f"Moved '{keyword}' -> '{value}' from set '{from_set}' to set '{to_set}'"
    )
