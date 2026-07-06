# Development Quickstart

NavTool's CLI is a Python package (`src/navtool/`) built with Click. This guide covers running it
from a local editable install.

Prerequisites: Python 3.10+ and a clone of this repository. All commands assume your working
directory is the repository root.

## Setup

1. Create a virtual environment:

   ```sh
   python3 -m venv .venv
   ```

2. Activate it:

   ```sh
   source .venv/bin/activate
   ```

   Your prompt is now prefixed with `(.venv)`, and `which python3` / `which pip` point into
   `.venv/bin/`.

3. Install NavTool in editable mode with dev dependencies:

   ```sh
   pip install -e ".[dev]"
   ```

   Editable mode means source edits under `src/navtool/` take effect immediately — no reinstall
   needed unless dependencies or `pyproject.toml` change. The `[dev]` extra adds `pytest`,
   `black`, and `isort`.

4. Confirm the dev build is the one on `PATH`:

   ```sh
   which navtool     # -> <repo>/.venv/bin/navtool
   ```

   If `which navtool` points elsewhere (e.g. `~/.local/bin/navtool`), an installed build is
   shadowing the dev one. Run `pipx uninstall navtool` to remove it.

5. Ensure that the `./shell/nav.sh` script is sourced in your environment to hook the `nav` command into your shell.
   To do this, source the script from your shell's startup file (e.g. `~/.zshrc` or `~/.bashrc`):

   ```sh
   source <navtool_root>/shell/nav.sh
   ```

## Databases

The dev and production builds use separate database files, selected automatically:

- Dev (editable) build run from this checkout → `<repo>/.navtool.dev.db` (gitignored)
- Installed (pipx) build → `~/.navtool.db`
- `$NAVTOOL_DB=/path/to/some.db` overrides either one

Run `navtool db info` to see which database is active and why. Tests use `$NAVTOOL_DB` to point at
a throwaway file, so they never touch your real data.

### Schema versioning and migrations

The database schema is versioned with SQLite's `PRAGMA user_version`, tracked separately from the
app version (`pyproject.toml`). The current target is `SCHEMA_VERSION` in
[../src/navtool/db.py](../src/navtool/db.py). When navtool opens a database that is behind, it
writes a timestamped `*.pre-migrate-*` backup next to the file and then applies the pending
migrations in order. A database created by a newer navtool is refused.

Migration 1 is the baseline: it applies `schema.sql` (idempotent), which both initializes a fresh
database and adopts any pre-versioning one.

**Adding a schema migration:**

1. Bump `SCHEMA_VERSION` in `db.py`.
2. Add a `_migration_N(conn)` function and register it in the `MIGRATIONS` dict under version `N`.
   Use `conn.execute(...)` statements (the runner wraps migrations 2+ in a transaction).
3. Update `resources/schema.sql` so a *fresh* install produces the same final schema.
4. Add a test in `tests/test_migrations.py` (fresh apply + upgrade-from-previous-version).

## Running Tests

With the venv active and `[dev]` dependencies installed:

```sh
pytest
```

`pytest` discovers and runs the `tests/test_*.py` files. See [../tests/README.md](../tests/README.md).

## Formatting

```sh
black src tests
isort src tests
```
