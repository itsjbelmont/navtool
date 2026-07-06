# NavTool

NavTool is a command-line tool that extends `cd`. You map short names to directories, then
jump to them from anywhere with `nav <name>`. Names form a **tree** — any name can have nested
child names — so you can keep a project and its sub-directories together.

```sh
$ nav myproj            # cd to the directory registered under the name "myproj"
$ nav myproj:tests      # cd to "tests" nested under "myproj"
```

NavTool has two parts:

- **`navtool`** — a Python CLI (built with [Click](https://click.palletsprojects.com/)) that
  stores name/directory mappings as a tree in a SQLite database.
- **`nav`** — a shell function ([src/navtool/resources/shell/nav.sh](src/navtool/resources/shell/nav.sh))
  that wraps `navtool`. It runs the
  actual `cd`, since a subprocess can't change its parent shell's directory.

## Requirements

- Python 3.10+
- [pipx](https://pipx.pypa.io/) (for installing the CLI)

## Install

1. Clone the repository:

   ```sh
   git clone https://github.com/itsjbelmont/navtool.git
   cd navtool
   ```

2. Install the CLI with pipx:

   ```sh
   pipx install .
   ```

3. Hook the `nav` function (and tab-completion) into your shell:

   ```sh
   navtool bootstrap
   ```

   This detects your shell from `$SHELL` and adds a single, managed line to its
   startup file (`~/.zshrc`, `~/.bashrc`, …). It is safe to re-run — the block is
   updated in place, never duplicated — and it backs up the file before editing.
   Pass `--shell zsh` to be explicit, or `--dry-run` to preview the change.

4. Restart your terminals (or re-source your startup file).

5. Verify:

   ```sh
   which navtool     # -> ~/.local/bin/navtool
   nav -h            # prints the help menu
   nav <TAB>         # lists commands and top-level names
   ```

To uninstall the CLI: `pipx uninstall navtool` (and remove the `navtool` block
from your startup file).

### Manual setup (advanced)

`navtool bootstrap` just writes one line that evaluates the packaged integration
snippet. To wire it in yourself, add this to your startup file instead:

```sh
eval "$(navtool init zsh)"      # or: navtool init bash
```

Because the snippet ships inside the installed package, this keeps working even
if the cloned repo is moved or deleted. Append `--no-completion` to either
command to skip tab-completion.

## Tab-Completion

Once the integration is set up (via `navtool bootstrap`, or manually), `<TAB>`
completes both `nav` and `navtool`:

```sh
$ nav <TAB>              # subcommands (add, rm, ls, …) + top-level names
$ nav myp<TAB>           # -> nav myproj
$ nav myproj:te<TAB>     # -> nav myproj:tests   (completes children at any depth)
$ nav rm myproj:<TAB>    # name completion works after subcommands too
$ nav add proj ~/pr<TAB> # directory arguments fall back to path completion
```

Names are completed **segment-by-segment**: after a `:` you get the children of
the node named so far. Completion never appends a trailing `:` or space — the
word ends exactly at the name, and you type the next `:` (to nest deeper) or a
space yourself.

> **bash note:** nested completion across `:` relies on the `bash-completion`
> package (it provides the colon-aware helpers). Top-level commands and names
> complete without it. zsh needs no extra packages.

## How It Works

### Names and the tree

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
| `nav ls [<name-path>]` | List the tree, or one entry's subtree. |
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
