"""`navtool __complete` — completion backend for the shell wrappers.

Both the ``nav`` and ``navtool`` shell completion functions call this hidden
command instead of Click's generated completion scripts, so there is a single
code path. It drives Click's own completion engine over an arbitrary argument
list (giving subcommand, option, name-path and directory completion for free)
Candidates are emitted verbatim: no trailing ':' or space is ever added, so the
completed word ends exactly at the name/command and the user types the next
separator themselves. The wrappers run with "nospace" so the shell agrees.

Filesystem arguments (``add``/``update``/``which`` directories) are special:
Click delegates the actual file/directory enumeration to its own generated
shell scripts, which we bypass. So instead of a value we emit a sentinel
(:data:`DIRS_SENTINEL` / :data:`FILES_SENTINEL`); the wrapper sees it and hands
off to the shell's native path completion.
"""

import click
from click.shell_completion import ShellComplete

from navtool.cli.tree import _name_completion_items

# Emitted (in place of real candidates) to tell the wrapper to run the shell's
# own directory/file completion for this word.
DIRS_SENTINEL = "\x1f__navtool_dirs__"
FILES_SENTINEL = "\x1f__navtool_files__"


def _looks_like_path(word: str) -> bool:
    """True if ``word`` is a filesystem path rather than a name/command.

    `nav <path>` falls through to `cd`, so the first word can be a directory. A
    leading `~`/`/`/`.` or any `/` marks it as a path (names have no slashes and
    nest with `:`), which lets us offer `cd`-style directory completion for it.
    """
    return word.startswith(("~", "/", ".")) or "/" in word


@click.command(
    "__complete",
    hidden=True,
    context_settings={"ignore_unknown_options": True},
)
@click.option(
    "--nav",
    "nav_wrapper",
    is_flag=True,
    help="Completing the `nav` wrapper: offer navigable names at the first word.",
)
@click.argument("words", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def complete(ctx, nav_wrapper, words):
    """Emit completion candidates for the current command line.

    WORDS are the arguments typed after ``nav``/``navtool``, with the current
    (possibly empty) word being completed as the last element.
    """
    words = list(words)
    incomplete = words[-1] if words else ""
    args = words[:-1]

    root = ctx.find_root().command
    engine = ShellComplete(root, {}, "navtool", "_NAVTOOL_COMPLETE")
    items = list(engine.get_completions(args, incomplete))

    # `nav <name>` navigates, so the first word is also a name target. (For
    # plain `navtool` there is no bare navigation, hence the --nav gate.)
    if nav_wrapper and not args:
        # A path-like first word means `nav` will fall through to `cd`; defer to
        # the shell for `cd`-style directory completion (e.g. `nav ~/Down<TAB>`).
        if _looks_like_path(incomplete):
            click.echo(DIRS_SENTINEL)
            return
        items += _name_completion_items(ctx.obj["conn"], incomplete)

    # A filesystem argument can't be enumerated here; defer to the shell.
    types = {item.type for item in items}
    if "dir" in types:
        click.echo(DIRS_SENTINEL)
        return
    if "file" in types:
        click.echo(FILES_SENTINEL)
        return

    seen: set[str] = set()
    for item in items:
        if item.value not in seen:
            seen.add(item.value)
            click.echo(item.value)
