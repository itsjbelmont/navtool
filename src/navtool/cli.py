import click
from pathlib import Path
from navtool.db import get_connection

DEFAULT_DB_PATH = "~/.navtool.db"

# ----------------- Top-level CLI -----------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli(ctx):
    """
    navtool – navigate directories using named sets and entries.
    """
    db_path = str(Path(DEFAULT_DB_PATH).expanduser())
    ctx.ensure_object(dict)
    ctx.obj["conn"] = get_connection(db_path)


# ----------------- 'set' command group -----------------
@cli.group()
@click.pass_context
def set(ctx):
    """Manage sets"""
    pass


@set.command("add")
@click.argument("set_name")
@click.pass_context
def set_add(ctx, set_name):
    """Add a new set"""
    conn = ctx.obj["conn"]
    try:
        conn.execute("INSERT INTO sets (set_name) VALUES (?)", (set_name,))
        conn.commit()
    except Exception as e:
        raise click.ClickException(str(e))
    click.echo(f"Set '{set_name}' added.")


@set.command("delete")
@click.argument("set_name")
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
        raise click.ClickExceptionk(str(e))


@set.command("list")
@click.pass_context
def set_list(ctx):
    """List all sets"""
    conn = ctx.obj["conn"]
    rows = conn.execute("SELECT set_name FROM sets ORDER BY set_name").fetchall()
    for (name,) in rows:
        click.echo(name)


# ----------------- 'entry' command group -----------------
@cli.group()
@click.pass_context
def entry(ctx):
    """Manage entries in sets"""
    pass


@entry.command("add")
@click.argument("set_name")
@click.argument("key")
@click.argument("value")
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
@click.argument("set_name")
@click.argument("key")
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
