"""`nav db path` — print the database file in use."""

import click

from navtool.cli.config import resolve_db_path


@click.command("path")
def db_path():
    """Print the path of the database file currently in use."""
    click.echo(resolve_db_path())
