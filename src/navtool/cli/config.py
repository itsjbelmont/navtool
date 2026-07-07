"""Selection of the directory (and files) navtool operates on.

navtool keeps all of its state in a single data directory so that additional
files (a config file, caches, …) can live alongside the database without each
one needing its own dev/prod resolution. The dev/prod split therefore chooses
the *directory*; the files inside always have the same names.

    <data dir>/navtool.db      the SQLite database
    <data dir>/...             room to grow (config, etc.)
"""

import os
from pathlib import Path

# The production data directory, used by installed (pipx) builds.
PROD_DIR = "~/.navtool"
# Name of the dev data directory, created inside the repo checkout.
DEV_DIR_NAME = ".navtool.dev"
# Environment variable that explicitly overrides the data directory location.
DIR_ENV_VAR = "NAVTOOL_DIR"

# Filename of the SQLite database within the data directory.
DB_FILENAME = "navtool.db"


def _running_from_source_checkout() -> bool:
    """True when running as an editable/dev install from the repo checkout.

    Editable installs execute from ``<repo>/src/navtool/cli/config.py``, so a
    ``pyproject.toml`` sits three directories above this module. A regular
    (pipx / site-packages) install has no such file there.
    """
    return (Path(__file__).resolve().parents[3] / "pyproject.toml").is_file()


def resolve_data_dir() -> tuple[Path, str]:
    """Choose the data directory to use and explain why.

    Returns ``(dir, source)`` where ``source`` is a short human-readable label.

    Priority:
      1. ``$NAVTOOL_DIR`` — explicit override, always wins.
      2. Dev build  -> ``<repo>/.navtool.dev`` (kept out of prod's data).
      3. Prod build -> ``~/.navtool``.
    """
    override = os.environ.get(DIR_ENV_VAR)
    if override:
        return Path(override).expanduser(), f"override via ${DIR_ENV_VAR}"
    if _running_from_source_checkout():
        path = Path(__file__).resolve().parents[3] / DEV_DIR_NAME
        return path, "dev build (editable install)"
    return Path(PROD_DIR).expanduser(), "prod build (installed)"


def resolve_db() -> tuple[str, str]:
    """Choose the database file to use and explain why.

    Returns ``(path, source)``; the database is ``navtool.db`` inside the
    directory chosen by :func:`resolve_data_dir` (whose ``source`` is reused).
    """
    data_dir, source = resolve_data_dir()
    return str(data_dir / DB_FILENAME), source


def resolve_db_path() -> str:
    """Return just the resolved database path (see :func:`resolve_db`)."""
    return resolve_db()[0]
