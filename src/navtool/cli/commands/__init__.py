"""Registration of every navtool subcommand onto the root group.

Each command is defined in its own module with ``@click.command`` (rather than
binding directly to the root group) so the modules stay independent of the group
object and free of import cycles. :func:`register_commands` wires them together.
"""

from navtool.cli.commands.add import add
from navtool.cli.commands.bootstrap import bootstrap
from navtool.cli.commands.complete import complete
from navtool.cli.commands.db import db_group
from navtool.cli.commands.init import init
from navtool.cli.commands.ls import ls
from navtool.cli.commands.mv import mv
from navtool.cli.commands.path import get_path
from navtool.cli.commands.rm import rm
from navtool.cli.commands.update import update
from navtool.cli.commands.which import which

# Top-level commands, in the order they should appear in `--help`. Setup commands
# come first, then the day-to-day navigation commands.
_TOP_LEVEL = (bootstrap, init, get_path, add, rm, mv, update, ls, which)


def register_commands(cli) -> None:
    """Attach all top-level commands and the ``db`` group to ``cli``."""
    for command in _TOP_LEVEL:
        cli.add_command(command)
    cli.add_command(db_group)
    # Hidden completion backend for the shell wrappers (see complete.py).
    cli.add_command(complete)
