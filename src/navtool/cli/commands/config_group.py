"""The `nav config` group — inspect navtool's configuration.

Mirrors the `nav db` group. The config file (``config.toml`` in the data
directory) is optional and hand-edited; these commands just report where it
lives and what values are in effect, so you can confirm what `navtool init`
will bake into the shell integration.
"""

from pathlib import Path

import click

from navtool.cli.config import (history_size, load_config, resolve_config_path,
                                resolve_data_dir)


@click.group("config")
def config_group():
    """Inspect navtool's configuration."""


@config_group.command("path")
def config_path():
    """Print the path of the config file (whether or not it exists yet)."""
    click.echo(resolve_config_path())


@config_group.command("show")
def config_show():
    """Show the resolved configuration and where each value comes from."""
    path = resolve_config_path()
    _, source = resolve_data_dir()
    present = Path(path).is_file()

    # Distinguish an explicitly-set value from the fallback default.
    raw = load_config().get("history_size")
    size = history_size()
    origin = "from config file" if raw == size else "default"

    click.echo(f"Config:        {click.style(path, fg='cyan')}")
    click.echo(f"Source:        {source}")
    click.echo(f"Status:        {'present' if present else 'not present (using defaults)'}")
    click.echo(f"history_size:  {size} ({origin})")
