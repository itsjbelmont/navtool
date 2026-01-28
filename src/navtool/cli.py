import click
from pathlib import Path
from navtool.db import get_connection

DEFAULT_DB_PATH = "~/.navtool.db"

# ----------------- Top-level CLI -----------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli(ctx):
    """
    navtool – navigate directories by associating short keys to commonly accessed directory paths. Keys can be organized into sets for multiple projects.
    """
    db_path = str(Path(DEFAULT_DB_PATH).expanduser())
    ctx.ensure_object(dict)
    ctx.obj["conn"] = get_connection(db_path)

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
    """Create a new navtool set to organize keys inside of"""
    conn = ctx.obj["conn"]
    try:
        conn.execute(
            "INSERT INTO sets (set_name, description) VALUES (?, ?)",
            (set_name, description),
        )
        conn.commit()

        row = conn.execute(
            "SELECT set_name, description FROM sets WHERE set_name = ?",
            (set_name,)
        ).fetchone()
        saved_name, saved_description = row
        click.echo(f"Created new set: {saved_name} - {saved_description if saved_description else "(no description)"}")
        click.echo(f" > Add keys to the set and then run `navtool activate {saved_name}` to activate the set.")
    except Exception as e:
        raise click.ClickException(str(e))


# ----------------- 'activate' command group -----------------
@cli.command("activate")
@click.argument("set_name", metavar="<SET_NAME>")
@click.pass_context
def activate_set(ctx, set_name):
    """Activate a set so that you can easily navigate to its keys"""
    conn = ctx.obj["conn"]
    try:
        row = conn.execute(
            "SELECT is_active FROM sets WHERE set_name = ?",
            (set_name,),
        ).fetchone()
        is_active = row[0]
        if is_active:
            click.echo(f"Set already active: {set_name}")
            return

        conn.execute(
            "UPDATE sets SET is_active = ? WHERE set_name = ?",
            (1, set_name)
        )
        conn.commit()
    except Exception as e:
        raise click.ClickException(str(e))
    click.echo(f"Activated set: {set_name}")


# ----------------- 'deactivate' command group -----------------
@cli.command("deactivate")
@click.argument("set_name", metavar="<SET_NAME>")
@click.pass_context
def deactivate_set(ctx, set_name):
    """Deactivate a set so the keys can no longer be accessed"""
    conn = ctx.obj["conn"]
    try:
        row = conn.execute(
            "SELECT is_active FROM sets WHERE set_name = ?",
            (set_name,),
        ).fetchone()
        is_active = row[0]
        if not is_active:
            click.echo(f"Set already inactive: {set_name}")
            return
        conn.execute(
            "UPDATE sets SET is_active = ? WHERE set_name = ?",
            (0, set_name)
        )
        conn.commit()
    except Exception as e:
        raise click.ClickException(str(e))
    click.echo(f"Deactivated set: {set_name}")


# ----------------- 'add' command group -----------------
@cli.command()
@click.argument("key_name", metavar="<KEY_NAME>")
@click.argument("directory", metavar="<DIRECTORY>")
@click.pass_context
def add(ctx, key_name, directory):
    """Add a new key/value navigation entry to a set"""
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
        "SELECT 1 FROM entries WHERE set_name=? AND entry_key=?",
        (target_set, key_name)
    ).fetchone()
    if key_exists_in_set:
        raise click.ClickException(f"Key '{key_name}' already exists in set '{target_set}'")

    if not click.confirm(f"Add entry '{key_name}' -> '{full_path}' to set '{target_set}'?", default=True):
        click.echo("Operation cancelled.")
        return
    conn.execute(
        "INSERT INTO entries (set_name, entry_key, entry_value) VALUES (?, ?, ?)",
        (target_set, key_name, full_path)
    )
    conn.commit()
    click.echo(f"Added entry '{key_name}' -> '{full_path}' to set '{target_set}'")


# ----------------- 'sets' command group -----------------
@cli.group()
@click.pass_context
def sets(ctx):
    """Manage sets that have already been created"""
    pass

@sets.command("delete")
@click.argument("set_name", metavar="<NAME>")
@click.pass_context
def set_delete(ctx, set_name):
    """Delete a set"""
    conn = ctx.obj["conn"]
    try:
      if click.confirm(f"Are you sure you want to delete the set '{set_name}'?", default=False):
        conn.execute("DELETE FROM sets WHERE set_name = ?", (set_name,))
        conn.commit()
        click.echo(f"Deleted the `{set_name}` set.")
    except Exception as e:
        raise click.ClickException(str(e))


@sets.command("list")
@click.option(
    "--desc",
    "-d",
    is_flag=True,  # boolean flag
    help="Optionally output the descriptions for the set",
)
@click.pass_context
def set_list(ctx, desc):
    """List all sets"""
    conn = ctx.obj["conn"]

    # Fetch description only if requested
    if desc:
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

        if desc:
            description = row[2] or "(no description)"
            click.echo(f"{text} – {description}")
        else:
            click.echo(text)



@sets.command("info")
@click.argument("set_name", metavar="<NAME>")
@click.pass_context
def set_info(ctx, set_name):
    """List all info for a set"""
    conn = ctx.obj["conn"]
    set_row = conn.execute(
        "SELECT description FROM sets WHERE set_name=?",
        (set_name,)
    ).fetchone()
    if not set_row:
        raise click.ClickException(f"Set '{set_name}' does not exist.")
    description = set_row[0] or "(no description)"
    click.echo(f"{set_name}: {description}")
    entries_rows = conn.execute(
        "SELECT entry_key, entry_value FROM entries WHERE set_name=? ORDER BY entry_key",
        (set_name,)
    ).fetchall()
    if not entries_rows:
        click.echo("  (no entries)")
        return
    for key, value in entries_rows:
        click.echo(f"  {key} -> {value}")


# ----------------- 'entry' command group -----------------
@cli.group()
@click.pass_context
def entry(ctx):
    """Manage entries in sets"""
    pass


@entry.command("add")
@click.argument("set_name", metavar="<SET_NAME>")
@click.argument("key", metavar="<KEY_NAME>")
@click.argument("value", metavar="<DIRECTORY>")
@click.pass_context
def entry_add(ctx, set_name, key, value):
    """Add an entry to a set"""
    conn = ctx.obj["conn"]
    try:
        conn.execute(
            "INSERT INTO entries (set_name, entry_key, entry_value) VALUES (?, ?, ?)",
            (set_name, key, value),
        )
        conn.commit()
    except Exception as e:
        raise click.ClickException(str(e))
    click.echo(f"Entry '{key}' added to set '{set_name}'.")


@entry.command("get")
@click.argument("set_name", metavar="<SET_NAME>")
@click.argument("key", metavar="<KEY_NAME>")
@click.pass_context
def entry_get(ctx, set_name, key):
    """Get the value of an entry in a set"""
    conn = ctx.obj["conn"]
    row = conn.execute(
        "SELECT entry_value FROM entries WHERE set_name=? AND entry_key=?",
        (set_name, key),
    ).fetchone()
    if not row:
        raise click.ClickException(f"No entry '{key}' in set '{set_name}'")
    click.echo(row[0])
