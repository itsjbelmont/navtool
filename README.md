# NavTool

NavTool is a command-line tool that extends `cd`. You map short keywords to directories, then
jump to them from anywhere with `nav <keyword>`. Keywords are organized into **sets** so you can
keep per-project shortcuts separate.

```sh
$ nav proj      # cd to the directory registered under the keyword "proj"
```

NavTool has two parts:

- **`navtool`** — a Python CLI (built with [Click](https://click.palletsprojects.com/)) that
  stores keyword/directory mappings in a SQLite database.
- **`nav`** — a shell function ([shell/nav.sh](shell/nav.sh)) that wraps `navtool`. It runs the
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

3. Hook the `nav` function into your shell by sourcing [shell/nav.sh](shell/nav.sh) from your
   shell's startup file (e.g. `~/.zshrc` or `~/.bashrc`):

   ```sh
   source /path/to/navtool/shell/nav.sh
   ```

4. Restart your terminals (or re-source your startup file).

5. Verify:

   ```sh
   which navtool     # -> ~/.local/bin/navtool
   nav -h            # prints the help menu
   ```

To uninstall the CLI: `pipx uninstall navtool`.

## How It Works

### Keywords and the `default` set

A **keyword** maps a short name to a directory. Keywords live in **sets**. The `default` set
always exists and is what unqualified keywords resolve against:

```sh
$ nav key add proj ~/Projects/navtool   # registers "proj" in the default set
$ nav proj                              # cd to ~/Projects/navtool
```

### Project sets and qualified keywords

Any set other than `default` is addressed with a `set:keyword` qualifier. There is no "active
set" state — a set's keywords are reachable by qualifier as soon as they exist:

```sh
$ nav set add work
$ nav key add api ~/code/api --set work
$ nav work:api                          # cd to ~/code/api
```

Because each non-`default` set is only reached through its own qualifier, the same keyword name
can be reused across sets without collision (`work:api`, `personal:api`, etc.).

### Falling through to `cd`

If an argument doesn't resolve to a registered keyword, `nav` passes it straight to `cd`, so it
works as a drop-in replacement:

```sh
$ nav ~/Downloads                       # not a keyword -> behaves like `cd ~/Downloads`
```

## Command Summary

| Command | Purpose |
|---|---|
| `nav <keyword>` / `nav <set>:<keyword>` | Navigate to a registered directory. |
| `nav set list` / `show` / `add` / `remove` / `update` | Manage sets. |
| `nav key list` / `add` / `remove` / `update` / `move` | Manage keyword entries. |
| `nav db path` / `info` | Inspect the database file in use. |
| `nav path <keyword>` | Resolve a keyword to its path (used internally by `nav`). |

See [docs/cli-usage.md](docs/cli-usage.md) for the full command reference and examples.

## Data Storage

Keywords and sets are stored in a single SQLite file. The location is chosen automatically:

- Installed (pipx) build → `~/.navtool.db`
- Dev/editable build run from the repo → `<repo>/.navtool.dev.db`
- `$NAVTOOL_DB` overrides both.

Run `nav db info` to see which file is in use. See [docs/dev-quickstart.md](docs/dev-quickstart.md)
for the development setup.
