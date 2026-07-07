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

NavTool also tracks a per-shell directory history — **every `cd`, not just `nav` jumps** — so you can
walk back and forward through where you've been, like a browser's back/forward buttons.

```sh
$ nav -        # go back to the previous directory
$ nav -3       # go back three
$ nav +        # go forward again
$ nav history  # list this shell's history, highlighting the current spot
```

> _History lives only in the current shell session (in memory, never on disk); each terminal keeps its
> own. The number of directories remembered defaults to 25 and is configurable._

For a full list of available commands, run `nav --help` after installation.

## Supported Shells

| Shell | Name navigation | `cd` fallthrough | Tab-completion | Directory history |
|---|:---:|:---:|:---:|:---:|
| **zsh** | ✅ | ✅ | ✅ | ✅ |
| **bash** | ✅ | ✅ | ⚙️ † | ✅ ‡ |
| **fish** | ❌ | ❌ | ❌ | ❌ |
| **PowerShell** | ❌ | ❌ | ❌ | ❌ |

**Legend:** ✅ Supported (works out of the box after `navtool bootstrap`) · ⚙️ Partial (works, but
full functionality needs extra setup) · ❌ Not supported yet

**Notes:**

- **†** In bash, top-level completion works out of the box, but nested `name:sub` completion needs
  the [`bash-completion`](https://github.com/scop/bash-completion) package (on macOS, that means
  `bash-completion@2` and bash 4.2+ — the system bash is 3.2). See
  [docs/troubleshooting/bash.md](docs/troubleshooting/bash.md).
- **‡** In bash, directory history is recorded from `PROMPT_COMMAND` (bash has no `chpwd` hook), so
  several `cd`s within a single compound command record only the final directory. zsh records every
  change via `chpwd`.

fish and PowerShell aren't wired up yet, but the integration is per-shell and self-contained, so
support can be added without touching the core CLI.

## Install From Source

> **Hitting a snag?** See [docs/troubleshooting/README.md](docs/troubleshooting/README.md) for known
> issues and fixes, organized by shell.

### Requirements

- Python 3.11+
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
   - `nav` is a sourced shell function that wraps the main `navtool` CLI — `navtool` resolves the keyword to a path, and `nav` performs the actual `cd` in your shell.

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

## Upgrading From Source

If an older `navtool` is already installed, upgrade it in place from an updated checkout:

1. Pull the latest source into your existing clone:

   ```sh
   cd navtool     # your existing clone
   git pull
   ```

2. Reinstall the CLI over the existing one — `--force` replaces what pipx already has:

   ```sh
   pipx install --force .
   ```

3. Restart your terminals (or re-source your startup file):

   ```sh
   exec $SHELL     # or: source ~/.zshrc  /  source ~/.bashrc
   ```

   The `nav` function is loaded into each shell at startup, so an already-running shell keeps the
   old version until it reloads.

You do **not** need to re-run `navtool bootstrap`. The single managed line it added to your startup
file (`eval "$(navtool init …)"`) is stable across versions and re-reads the freshly installed CLI
on every shell startup — so restarting your shell is all it takes to pick up the new `nav` function,
completion, and history helpers. Re-run `navtool bootstrap` only if you want to switch shells or
toggle tab-completion.
