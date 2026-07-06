"""`navtool init` — print the shell integration snippet for a shell.

The snippet (the `nav` function plus, by default, tab-completion) is meant to be
evaluated from a startup file, e.g. `eval "$(navtool init zsh)"` in `~/.zshrc`.
`navtool bootstrap` wires that line in automatically. This command emits nothing
but the snippet on stdout so it is safe to `eval` on every shell startup — it
never touches the database (see the DB-free skip in :mod:`navtool.cli`).
"""

import click

from navtool.cli.shells import (SHELLS, detect_shell, render_snippet,
                                supported_shells)


@click.command("init")
@click.argument("shell", metavar="[SHELL]", required=False)
@click.option(
    "--no-completion",
    is_flag=True,
    help="Omit the tab-completion setup from the snippet.",
)
def init(shell, no_completion):
    """Print the shell integration snippet for SHELL (default: detected shell).

    SHELL is one of the supported shells (currently zsh, bash). Put the output in
    your startup file via `eval "$(navtool init zsh)"`, or let `navtool bootstrap`
    do it for you.
    """
    name = shell or detect_shell()
    if name not in SHELLS:
        supported = ", ".join(supported_shells())
        if shell:
            raise click.ClickException(
                f"Unsupported shell '{shell}'. Supported shells: {supported}."
            )
        raise click.ClickException(
            "Could not detect your shell from $SHELL. "
            f"Pass one explicitly: navtool init <{supported}>."
        )

    click.echo(render_snippet(SHELLS[name], completion=not no_completion), nl=False)
