"""`navtool __route` — routing backend for the `nav` shell wrapper.

The `nav` function has to be a shell function so it can change the current
shell's directory, and shell functions print their whole body to `which`/`type`.
To keep that body tiny (and the routing logic unit-testable in Python instead of
in `awk`), all of the "is this a subcommand or a directory to jump to?" decision
lives here. The wrapper is just:

    target=$(navtool __route "$@") && cd "$target" || navtool "$@"

and switches on the exit code:

  * exit 0 — stdout holds a directory; the wrapper runs ``cd "$target"``.
  * exit 1 — the args are an ordinary navtool command; the wrapper reruns them
    as ``navtool "$@"`` with the terminal attached (so prompts and colors work),
    and this command prints nothing.

Only a single, non-option word that is not itself a subcommand counts as a
navigation. That word is resolved as a name path; if it resolves, its directory
is printed, otherwise the word is echoed back verbatim so `cd` can treat it as a
plain filesystem path — mirroring the old ``navtool path … || cd "$1"`` fallback.
"""

import click

from navtool.cli.tree import _parse_path, _resolve

# Exit codes the shell wrapper switches on.
_NAVIGATE = 0
_PASSTHROUGH = 1


def _resolve_target(word: str) -> str:
    """Resolve a single name path to its directory, or echo ``word`` back.

    Any failure — an unknown name, an invalid path, or a one-off/unreadable
    database error — returns ``word`` unchanged so the wrapper's ``cd`` treats it
    as a literal filesystem path, exactly as the previous shell fallback did.
    Opens its own connection (this command is DB-free at the group level) and
    never raises: routing must not be able to break the user's ``cd``.
    """
    from navtool.cli.config import resolve_db_path
    from navtool.db import get_connection

    conn = None
    try:
        conn = get_connection(resolve_db_path())
        node = _resolve(conn, _parse_path(word))
        return node[3] if node is not None else word
    except Exception:
        return word
    finally:
        if conn is not None:
            conn.close()


@click.command(
    "__route",
    hidden=True,
    add_help_option=False,  # `-h`/`--help` are just words to classify, not help.
    context_settings={"ignore_unknown_options": True},
)
@click.argument("words", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def route(ctx, words):
    """Tell the `nav` wrapper whether to `cd` (exit 0) or pass through (exit 1)."""
    words = list(words)

    # Only a lone word can be a navigation target; anything else is a command
    # line for navtool (no args → help, multiple args → a subcommand call).
    if len(words) != 1:
        ctx.exit(_PASSTHROUGH)

    word = words[0]

    # A leading '-' means an option (-h/--help/--version/…) meant for navtool.
    if word.startswith("-"):
        ctx.exit(_PASSTHROUGH)

    # A real subcommand always wins over a same-named entry, matching the old
    # wrapper which passed every known command straight through.
    if word in ctx.find_root().command.commands:
        ctx.exit(_PASSTHROUGH)

    # It's a navigation: print the directory to cd into and exit 0.
    click.echo(_resolve_target(word))
    ctx.exit(_NAVIGATE)
