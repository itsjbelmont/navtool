"""Selection of the SQLite database file navtool operates on."""

import os
from pathlib import Path

# The production database, used by installed (pipx) builds.
PROD_DB_PATH = "~/.navtool.db"
# Environment variable that explicitly overrides the database location.
DB_ENV_VAR = "NAVTOOL_DB"


def _running_from_source_checkout() -> bool:
    """True when running as an editable/dev install from the repo checkout.

    Editable installs execute from ``<repo>/src/navtool/cli/config.py``, so a
    ``pyproject.toml`` sits three directories above this module. A regular
    (pipx / site-packages) install has no such file there.
    """
    return (Path(__file__).resolve().parents[3] / "pyproject.toml").is_file()


def resolve_db() -> tuple[str, str]:
    """Choose the database file to use and explain why.

    Returns ``(path, source)`` where ``source`` is a short human-readable label.

    Priority:
      1. ``$NAVTOOL_DB`` — explicit override, always wins.
      2. Dev build  -> ``<repo>/.navtool.dev.db`` (kept out of prod's data).
      3. Prod build -> ``~/.navtool.db``.
    """
    override = os.environ.get(DB_ENV_VAR)
    if override:
        return str(Path(override).expanduser()), f"override via ${DB_ENV_VAR}"
    if _running_from_source_checkout():
        path = Path(__file__).resolve().parents[3] / ".navtool.dev.db"
        return str(path), "dev build (editable install)"
    return str(Path(PROD_DB_PATH).expanduser()), "prod build (installed)"


def resolve_db_path() -> str:
    """Return just the resolved database path (see :func:`resolve_db`)."""
    return resolve_db()[0]
