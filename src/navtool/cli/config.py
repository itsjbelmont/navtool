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
# Filename of the (optional, hand-edited) TOML config within the data directory.
CONFIG_FILENAME = "config.toml"

# Default number of directories each shell session remembers for `nav <`/`nav >`.
DEFAULT_HISTORY_SIZE = 25


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


def resolve_config_path() -> str:
    """Path to the TOML config file within the active data directory.

    The file is optional and hand-edited; navtool never writes it. See
    :func:`load_config` for how a missing or malformed file is handled.
    """
    data_dir, _ = resolve_data_dir()
    return str(data_dir / CONFIG_FILENAME)


def load_config() -> dict:
    """Read the TOML config file, or return ``{}`` if absent or unreadable.

    Deliberately total: a missing file, a permission error, or a syntax error
    all yield ``{}`` so callers fall back to defaults. This matters because
    ``navtool init`` (which bakes config into the shell snippet) is eval'd on
    every shell startup and must never fail or print noise over a bad config.
    """
    import tomllib

    try:
        with open(resolve_config_path(), "rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def history_size() -> int:
    """Configured directory-history cap, or :data:`DEFAULT_HISTORY_SIZE`.

    Reads ``history_size`` from the config file; any missing, non-integer, or
    non-positive value falls back to the default rather than raising.
    """
    value = load_config().get("history_size", DEFAULT_HISTORY_SIZE)
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return DEFAULT_HISTORY_SIZE
