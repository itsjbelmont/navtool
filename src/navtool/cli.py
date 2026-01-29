import click
from pathlib import Path
from navtool.db import get_connection

DEFAULT_DB_PATH = "~/.navtool.db"

# ----------------- Top-level CLI -----------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli(ctx):
    """
    navtool – navigate directories by associating short keys to commonly accessed directory paths. Keys can be organized into sets to support switching between projects.
    """
    db_path = str(Path(DEFAULT_DB_PATH).expanduser())
    ctx.ensure_object(dict)
    ctx.obj["conn"] = get_connection(db_path)


# ----------------- `path` command
@cli.command("path")
@click.argument("key_name", metavar="<KEY_NAME>")
@click.pass_context
def get_path(ctx, key_name):
    conn = ctx.obj["conn"]
    try:
      rows = conn.execute(
          """
          SELECT e.entry_key, e.entry_value, e.set_name
          FROM entries e
          JOIN sets s ON e.set_name = s.set_name
          WHERE e.entry_key = ?
            AND s.is_active = 1
          """,
          (key_name,),
      ).fetchall()
      if len(rows) == 0:
          click.echo(f"Error: Could not find the key: {key_name}")
      elif len(rows) > 1:
          click.echo(f"Warning: Found the key {key_name} in multiple active sets. This is not yet handled properly.")
      else:
          click.echo(rows[0][1])

    except Exception as e:
        raise click.ClickException(str(e))


# ----------------- 'create' command group for creating new sets-----------------
@cli.command("create")
@click.argument("set_name", metavar="<SET_NAME>")
@click.option(
    "--desc",
    "-d",
    "description",
    default=None,
    help="Optional description for the set",
)
@click.pass_context
def create_set(ctx, set_name, description):
    """Create a new set that directory keys can be associated with"""
    conn = ctx.obj["conn"]
    try:
        conn.execute(
            "INSERT INTO sets (set_name, description) VALUES (?, ?)",
            (set_name, description),
        )
        conn.commit()

        row = conn.execute(
            "SELECT set_name, description FROM sets WHERE set_name = ?", (set_name,)
        ).fetchone()
        saved_name, saved_description = row
        click.echo(
            f"Created new set: {saved_name} - {saved_description if saved_description else "(no description)"}"
        )
        click.echo(
            f" > Add keys to the set and then run `navtool activate {saved_name}` to activate the set."
        )
    except Exception as e:
        raise click.ClickException(str(e))

@cli.command("delete")
@click.argument("set_name", metavar="<NAME>")
@click.pass_context
def set_delete(ctx, set_name):
    """Delete a set and all of the keys associated with that set"""
    conn = ctx.obj["conn"]
    try:
        if click.confirm(
            f"Are you sure you want to delete the set '{set_name}'?", default=False
        ):
            conn.execute("DELETE FROM sets WHERE set_name = ?", (set_name,))
            conn.commit()
            click.echo(f"Deleted the `{set_name}` set.")
    except Exception as e:
        raise click.ClickException(str(e))


# ----------------- 'use' command group -----------------
@cli.command("use")
@click.argument("set_name", metavar="<SET_NAME>")
@click.pass_context
def activate_set(ctx, set_name):
    """Mark a set as "active" so that you can navigate to its keys"""
    conn = ctx.obj["conn"]
    try:
        row = conn.execute(
            "SELECT is_active FROM sets WHERE set_name = ?",
            (set_name,),
        ).fetchone()
        is_active = row[0]
        if is_active:
            click.echo(f"Set already in use: {set_name}")
            return

        conn.execute("UPDATE sets SET is_active = ? WHERE set_name = ?", (1, set_name))
        conn.commit()
    except Exception as e:
        raise click.ClickException(str(e))
    click.echo(f"Activated set: {set_name}")


# ----------------- 'unuse' command group -----------------
@cli.command("unuse")
@click.argument("set_name", metavar="<SET_NAME>")
@click.pass_context
def deactivate_set(ctx, set_name):
    """Mark a set as "inactive" so its keys can no longer be accessed"""
    conn = ctx.obj["conn"]
    try:
        row = conn.execute(
            "SELECT is_active FROM sets WHERE set_name = ?",
            (set_name,),
        ).fetchone()
        is_active = row[0]
        if not is_active:
            click.echo(f"Set is not currently in use: {set_name}")
            return
        conn.execute("UPDATE sets SET is_active = ? WHERE set_name = ?", (0, set_name))
        conn.commit()
    except Exception as e:
        raise click.ClickException(str(e))
    click.echo(f"Deactivated set: {set_name}")


# ----------------- 'key' command -----------------
@cli.command("key")
@click.argument("key_name", metavar="<KEY_NAME>")
@click.argument("directory", metavar="<DIRECTORY>")
@click.pass_context
def key(ctx, key_name, directory):
    """Assign a key to a directory"""
    conn = ctx.obj["conn"]

    full_path = str(Path(directory).expanduser().resolve())
    if not Path(full_path).exists() or not Path(full_path).is_dir():
        raise click.ClickException(f"Directory does not exist: {full_path}")

    active_sets = conn.execute(
        "SELECT set_name FROM sets WHERE is_active=1 ORDER BY set_name"
    ).fetchall()
    if not active_sets:
        raise click.ClickException("No active sets found. Please activate a set first.")

    if len(active_sets) == 1:
        target_set = active_sets[0][0]
    else:
        click.echo("Multiple active sets detected:")
        for i, (set_name,) in enumerate(active_sets, start=1):
            click.echo(f"{i}. {set_name}")

        choice = click.prompt(
            "Select which set to add this entry to:",
            type=click.IntRange(1, len(active_sets)),
        )
        target_set = active_sets[choice - 1][0]

    key_exists_in_set = conn.execute(
        "SELECT 1 FROM entries WHERE set_name=? AND entry_key=?", (target_set, key_name)
    ).fetchone()
    if key_exists_in_set:
        raise click.ClickException(
            f"Key '{key_name}' already exists in set '{target_set}'"
        )

    if not click.confirm(
        f"Register '{key_name}' -> '{full_path}' to set '{target_set}'?", default=True
    ):
        click.echo("Operation cancelled.")
        return
    conn.execute(
        "INSERT INTO entries (set_name, entry_key, entry_value) VALUES (?, ?, ?)",
        (target_set, key_name, full_path),
    )
    conn.commit()
    click.echo(f"Registered entry '{key_name}' -> '{full_path}' to set '{target_set}'")


# ----------------- 'list' command -----------------
@cli.group(invoke_without_command=True)
@click.option(
    "--describe",
    "-d",
    is_flag=True,  # boolean flag
    default=False,
    help="Optionally show the keys for each set",
)
@click.pass_context
def list(ctx, describe):
    """List the available sets (or keys within sets)"""
    
    if ctx.invoked_subcommand is not None:
        return

    conn = ctx.obj["conn"]

    # Fetch description only if requested
    if describe:
        rows = conn.execute(
            "SELECT set_name, is_active, description FROM sets ORDER BY set_name"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT set_name, is_active FROM sets ORDER BY set_name"
        ).fetchall()

    for row in rows:
        name = row[0]
        is_active = row[1]
        color = "green" if is_active else "yellow"
        text = click.style(f"{name}", fg=color)

        if describe:
            description = row[2] or "(no description)"
            click.echo(f"{text} – {description}")
        else:
            click.echo(text)


@list.command("entries")
@click.argument("set_name", metavar="<SET_NAME>")
@click.pass_context
def list_entries(ctx, set_name):
    """List entries for a set"""
    conn = ctx.obj["conn"]
    set_row = conn.execute(
        "SELECT description FROM sets WHERE set_name=?", (set_name,)
    ).fetchone()
    if not set_row:
        raise click.ClickException(f"Set '{set_name}' does not exist.")
    description = set_row[0] or "(no description)"
    click.echo(f"{set_name}: {description}")
    entries_rows = conn.execute(
        "SELECT entry_key, entry_value FROM entries WHERE set_name=? ORDER BY entry_key",
        (set_name,),
    ).fetchall()
    if not entries_rows:
        click.echo("  (no entries)")
        return
    for key, value in entries_rows:
        click.echo(f"  {key} -> {value}")