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

### Cleanup Virtual Environment

To deactivate the virtual environment when you're done:

```sh
deactivate
```

## Tab-completion

Completion for both `nav` and `navtool` is backed by a single hidden command,
`navtool __complete` ([../src/navtool/cli/commands/complete.py](../src/navtool/cli/commands/complete.py)),
so there is one code path instead of per-shell logic. The shell functions in
[../src/navtool/resources/shell/completion.zsh](../src/navtool/resources/shell/completion.zsh) and
[../src/navtool/resources/shell/completion.bash](../src/navtool/resources/shell/completion.bash) collect the words typed so
far and call it; it drives Click's own completion engine (subcommands, options,
directories) and, for the `nav` wrapper's first word, unions in navigable names.
Because `nav <word>` navigates to a name *or* falls through to `cd`, a bare
first word also unions in the shell's directory completion — so `nav src<TAB>`
completes the `src/` directory just like `cd` would, without needing a `./`
prefix.

Name completion is segment-by-segment: candidates come from
`_complete_name_path` in [../src/navtool/cli/tree.py](../src/navtool/cli/tree.py),
which also powers the Click `shell_complete` callbacks on the name-path
arguments. Candidates are emitted verbatim — the wrappers run with "nospace" and
never append a trailing `:` or space, so the user types the next separator.
Directory arguments emit a sentinel that tells the wrapper to fall back to the
shell's native path completion — either on its own (a pure path argument) or
alongside name candidates (the bare `nav <dir>` case above), so the wrapper
scans every emitted line for it. Tests live in
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

The `nav` function itself stays deliberately tiny: it must be a shell function
(only a function can `cd` the current shell), and shells reprint a function's
whole body under `which`/`type`. So all of its "is this a subcommand or a
directory to jump to?" routing lives in a hidden backend, `navtool __route`
([../src/navtool/cli/commands/route.py](../src/navtool/cli/commands/route.py)),
which prints a directory to `cd` into (exit 0) or defers to a plain `navtool`
command (exit non-zero). Like `__complete` it's DB-free at the group level and
opens its own connection only when it actually resolves a name.

**Directory history** (`nav -`/`nav +`/`nav history`) is pure shell, because its
state (the per-session stack of visited directories) lives in the shell and the
recording path — a `chpwd` hook in zsh, `PROMPT_COMMAND` in bash — must not pay
Python startup on every `cd`. The logic lives in `resources/shell/history.zsh`
and `history.bash` (separate files: the array syntax differs, and `history.bash`
is written for the bash 3.2 that ships with macOS). The `nav` wrapper intercepts
the `-`/`+`/`history` forms before routing. The history cap is resolved from
config by `navtool init` (via `history_size()`) and baked into a one-line
preamble in the emitted snippet, still overridable at runtime with
`$NAV_HISTORY_SIZE`. These shells can't be unit-tested from Python, so they have
their own subprocess-driven tests in
[../tests/test_shell_history.py](../tests/test_shell_history.py) (skipped when the
shell isn't installed).

All per-shell knowledge lives in one registry,
[../src/navtool/cli/shells.py](../src/navtool/cli/shells.py). **To add a shell
(e.g. PowerShell):** drop its resource script(s) under `resources/shell/`, add a
`Shell(...)` entry to `SHELLS`, and — if its comment syntax isn't `#` — generalize
the `BLOCK_BEGIN`/`BLOCK_END` markers. The `init`/`bootstrap` commands need no
changes. Tests live in [../tests/test_bootstrap.py](../tests/test_bootstrap.py).

## Databases

navtool stores its state in a data directory (the database is `navtool.db` inside it). The dev and
production builds use separate directories, selected automatically:

- Dev (editable) build run from this checkout → `<repo>/.navtool.dev/` (gitignored)
- Installed (pipx) build → `~/.navtool/`
- `$NAVTOOL_DIR=/path/to/some/dir` overrides either one

Run `navtool db info` to see which database is active and why. Tests use `$NAVTOOL_DIR` to point at
a throwaway directory, so they never touch your real data.

The same directory also holds the optional `config.toml` (see `navtool config show`). It's read via
stdlib `tomllib` in [../src/navtool/cli/config.py](../src/navtool/cli/config.py) — hence the
`requires-python = ">=3.11"` floor — and reads are total: a missing or malformed file yields `{}`
so `navtool init`, which is eval'd on every shell startup, can never fail on a bad config.

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
