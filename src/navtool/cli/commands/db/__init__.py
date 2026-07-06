"""The `nav db` group — inspect the database navtool is using.

Each subcommand lives in its own module and is attached to :data:`db_group`
here, mirroring how the top-level commands are wired in the parent package.
"""

import click

from navtool.cli.commands.db.info import db_info
from navtool.cli.commands.db.migrate import db_migrate
from navtool.cli.commands.db.path import db_path
from navtool.cli.commands.db.schema import db_schema


@click.group("db")
def db_group():
    """Inspect the database file navtool is using."""


for _command in (db_path, db_info, db_schema, db_migrate):
    db_group.add_command(_command)
