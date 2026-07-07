"""The navtool command-line interface.

This package mirrors the command tree: the root :data:`cli` group lives here,
shared plumbing sits in :mod:`config` and :mod:`tree`, and each subcommand has
its own module under :mod:`commands` (with the nested ``db`` group as a
sub-package).
"""

import click

from navtool.cli.commands import register_commands
from navtool.cli.config import resolve_db_path
from navtool.db import (IncompatibleDatabaseError, NewerDatabaseError,
                        create_connection, migrate)

# Subcommands that must not have the root group open/migrate the database for
# them. `init`/`bootstrap` only emit shell config (critical for `init`, eval'd on
# every shell startup). `__route` runs on every `nav` call and opens its own
# connection lazily — only when it actually resolves a name — so passthrough
# routing stays a cheap, DB-free classification. `config` only reads the TOML
# config file and never touches the database.
DB_FREE_COMMANDS = {"init", "bootstrap", "__route", "config"}


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="navtool", prog_name="navtool")
@click.pass_context
def cli(ctx):
    """
    Navigate directories by associating short names to commonly accessed
    directory paths. Names form a tree: a name can have nested child names
    addressed with a colon, e.g. `myproj` and `myproj:tests`.
    """
    ctx.ensure_object(dict)
    # During shell completion Click parses resiliently and no command actually
    # runs; skip opening/migrating the DB so a TAB press stays cheap and can't
    # fail on a migration error. Completers open their own connections.
    if ctx.resilient_parsing:
        return
    # Setup commands emit shell config and never touch the database. `init` in
    # particular is eval'd on every shell startup, so it must not create or
    # migrate the DB (nor risk polluting its stdout with migration output).
    if ctx.invoked_subcommand in DB_FREE_COMMANDS:
        return
    path = resolve_db_path()
    conn = create_connection(path)
    try:
        # Returns (from_version, to_version); records what this run migrated.
        ctx.obj["migration"] = migrate(conn, path)
    except (NewerDatabaseError, IncompatibleDatabaseError) as e:
        raise click.ClickException(str(e))
    ctx.obj["conn"] = conn


# Attach every subcommand (and the `db` group) to the root group.
register_commands(cli)

__all__ = ["cli"]
