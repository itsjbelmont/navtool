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

5. Hook the `nav` function (and tab-completion) into your shell. The integration
   snippet ships inside the package, so the same command works for the editable
   dev build — add this to your startup file (e.g. `~/.zshrc` or `~/.bashrc`):

   ```sh
   eval "$(navtool init zsh)"   # or: navtool init bash
   ```

   Or let navtool edit the startup file for you (idempotent, backs up first):

   ```sh
   navtool bootstrap
   ```

   Append `--no-completion` to either command to skip tab-completion.

## Tab-completion

Completion for both `nav` and `navtool` is backed by a single hidden command,
`navtool __complete` ([../src/navtool/cli/commands/complete.py](../src/navtool/cli/commands/complete.py)),
so there is one code path instead of per-shell logic. The shell functions in
[../src/navtool/resources/shell/completion.zsh](../src/navtool/resources/shell/completion.zsh) and
[../src/navtool/resources/shell/completion.bash](../src/navtool/resources/shell/completion.bash) collect the words typed so
far and call it; it drives Click's own completion engine (subcommands, options,
directories) and, for the `nav` wrapper's first word, unions in navigable names.

Name completion is segment-by-segment: candidates come from
`_complete_name_path` in [../src/navtool/cli/tree.py](../src/navtool/cli/tree.py),
which also powers the Click `shell_complete` callbacks on the name-path
arguments. Candidates are emitted verbatim — the wrappers run with "nospace" and
never append a trailing `:` or space, so the user types the next separator.
Directory arguments emit a sentinel that tells the wrapper to fall back to the
shell's native path completion. Tests live in
[../tests/test_completion.py](../tests/test_completion.py).

## Shell integration (`init` / `bootstrap`)

`navtool init <shell>` prints the integration snippet (the `nav` function plus
completion) read from the packaged scripts under
[../src/navtool/resources/shell/](../src/navtool/resources/shell/), and
`navtool bootstrap` writes an `eval "$(navtool init …)"` line into the shell's
startup file inside a sentinel-delimited, idempotent block. Both are DB-free —
[../src/navtool/cli/__init__.py](../src/navtool/cli/__init__.py) skips the
connect/migrate step for them, which matters because `init` is eval'd on every
shell startup.

All per-shell knowledge lives in one registry,
[../src/navtool/cli/shells.py](../src/navtool/cli/shells.py). **To add a shell
(e.g. PowerShell):** drop its resource script(s) under `resources/shell/`, add a
`Shell(...)` entry to `SHELLS`, and — if its comment syntax isn't `#` — generalize
the `BLOCK_BEGIN`/`BLOCK_END` markers. The `init`/`bootstrap` commands need no
changes. Tests live in [../tests/test_bootstrap.py](../tests/test_bootstrap.py).

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
migrations in order. A database created by a newer navtool is refused, and a pre-overhaul database
(the old set/key model) is rejected with instructions to delete it.

**The migration chain is the single source of truth for the schema.** Migration 1 is the baseline:
it applies `schema.sql`. Every later change is its own numbered migration — there is no separate
declarative schema file to keep in sync (and therefore nothing that can drift). To see the current
shape of the schema at any time, run `navtool db schema`, which builds a fresh in-memory database
from the migrations and dumps its definitions.

**Adding a schema migration:**

1. Bump `SCHEMA_VERSION` in `db.py`.
2. Add a `_migration_N(conn)` function and register it in the `MIGRATIONS` dict under version `N`.
   Use `conn.execute(...)` statements (the runner wraps migrations 2+ in a transaction). For
   structural changes SQLite's `ALTER TABLE` can't express, use the create-new / copy / drop /
   rename rebuild pattern inside the migration.
3. Add a test in `tests/test_migrations.py` (fresh apply + upgrade-from-previous-version).

`schema.sql` stays as the migration-1 baseline; do **not** edit it to reflect later migrations.

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
