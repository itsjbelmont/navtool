# NavTool

NavTool is a "quick jump" CLI that maps long directory paths to memorable keywords for rapid access
from any location in your terminal. Navigation is performed using the `nav` command.

```sh
$ nav add myproj /path/to/myproj    # Add a new keyword mapping for "myproj" → /path/to/myproj
$ nav myproj                        # quick jump to /path/to/myproj
```

> _NavTool uses a SQLite database for persistent storage on disk, ensuring that any navigation shortcuts
>  you create are instantly available across terminal sessions and persist between restarts._

Keyword mappings support "parent relationships" to other keywords, allowing you to create hierarchical
navigation paths. This is particularly useful for managing duplicate keywords (such as `tests`, `src`, or `build`)
that exist for multiple projects, but can also be used simply as an organization scheme to cluster related paths. When
using the CLI, the keyword hierarchy is specified by using a colon (`:`) separator between keywords.

```sh
$ nav add myproj:build ~/path/to/myproj/build # the "myproj" parent keyword must already exist or this will fail
$ nav myproj:build                            # quick jump to ~/path/to/myproj/build
```

> _Although nothing is stopping you from creating deeply nested hierarchy paths by continuously chaining keywords 
> with colons, it is recommended that you avoid doing this as it can be difficult to maintain._

The nav command falls through to `cd` for navigating the directory tree, making it a pure extension of the `cd` command if
you wish to use it as such.

```sh
$ nav /path/to/directory # not special navtool syntax → falls through to `cd /path/to/directory`
```

For a full list of available commands, run `nav --help` after installation.

## Manual Installation

> **Hitting a snag?** See [docs/troubleshooting/README.md](docs/troubleshooting/README.md) for known
> issues and fixes, organized by shell.

### Requirements

- Python 3.10+
- [pipx](https://pipx.pypa.io/) (for installing the CLI)

### Steps

1. Clone the repository:

   ```sh
   git clone https://github.com/itsjbelmont/navtool.git
   cd navtool
   ```

2. Install the `navtool` CLI with pipx:

   ```sh
   pipx install .
   ```

3. Hook the `nav` function (and tab-completion) into your shell:

   ```sh
   navtool bootstrap
   ```

   > This detects your shell from `$SHELL` and adds a single, managed line to its
   > startup file (`~/.zshrc`, `~/.bashrc`, …). It is safe to re-run — the block is
   > updated in place, never duplicated — and it backs up the file before editing.
   > Pass `--shell zsh` to be explicit, or `--dry-run` to preview the change.

4. Restart your terminals (or re-source your startup file).

5. Verify:

   ```sh
   which navtool     # -> ~/.local/bin/navtool
   nav -h            # prints the help menu
   nav <TAB>         # lists commands and top-level names
   ```

To uninstall the CLI: `pipx uninstall navtool` (and remove the `navtool` block
from your startup file).

## How It Works

### Names and the tree

> `nav` is a sourced shell function that wraps the navtool CLI — navtool resolves the keyword to a path, and nav performs the actual `cd` in your shell.

A **name** maps a short label to a directory. You navigate to it with `nav <name>`:

```sh
$ nav add myproj ~/projects/myproj   # register "myproj" -> ~/projects/myproj
$ nav myproj                         # cd to ~/projects/myproj
```

### Nested names

Any name can have nested child names, addressed with a colon (`parent:child`). The parent must
already exist. There is no depth limit:

```sh
$ nav add myproj:tests ~/projects/myproj/tests   # "tests" nested under "myproj"
$ nav myproj:tests                               # cd to ~/projects/myproj/tests
$ nav add myproj:tests:unit ~/projects/myproj/tests/unit
$ nav myproj:tests:unit
```

A bare `nav <name>` (no colon) only matches **top-level** names, so bare names are always
unambiguous. The same child name can be reused under different parents (`proj:tests`,
`other:tests`) without collision.

### Falling through to `cd`

If an argument doesn't resolve to a registered name, `nav` passes it straight to `cd`, so it
works as a drop-in replacement:

```sh
$ nav ~/Downloads                       # not a name -> behaves like `cd ~/Downloads`
```

## Command Summary

| Command | Purpose |
|---|---|
| `nav <name>` / `nav <a>:<b>:<c>` | Navigate to a registered directory. |
| `nav add <name-path> <dir>` | Register a name (nest it with `parent:name`). |
| `nav rm <name-path>` | Remove a name (and any nested children). |
| `nav mv <name-path> [--to P] [--root] [--rename N]` | Reparent and/or rename. |
| `nav update <name-path> <dir>` | Repoint a name at a new directory. |
| `nav ls [<name-path>] [-l/--level N]` | List the tree, or one entry's subtree; `--level` caps the depth shown. |
| `nav which [<dir>]` | Show which name(s) point at a directory (default: current). |
| `nav db path` / `info` / `schema` | Inspect the database file and schema. |
| `nav path <name-path>` | Resolve a name to its path (used internally by `nav`). |
| `navtool bootstrap [--shell N] [--dry-run]` | Set up the shell integration in your startup file. |
| `navtool init <shell>` | Print the integration snippet (used by `bootstrap` / manual setup). |

See [docs/cli-usage.md](docs/cli-usage.md) for the full command reference and examples.

## Data Storage

Names are stored as a single self-referential tree in one SQLite file. The location is chosen
automatically:

- Installed (pipx) build → `~/.navtool.db`
- Dev/editable build run from the repo → `<repo>/.navtool.dev.db`
- `$NAVTOOL_DB` overrides both.

Run `nav db info` to see which file is in use. See [docs/dev-quickstart.md](docs/dev-quickstart.md)
for the development setup.
