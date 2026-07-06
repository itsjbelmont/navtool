# NavTool CLI Usage Guide (Modernized)

**Status:** design draft — describes the target CLI structure, not the current implementation.
This doc is meant to be read end-to-end, agreed on, and then used as the spec for an overhaul.

## Goals

- Get rid of stateful "active sets" (`use` / `unuse`). Sets no longer have an on/off state.
- One implicit, always-searched set — **`default`** — for everyday keywords used via `nav <keyword>`.
- All other sets are namespaced and only reachable via an explicit `<setname>:<keyword>` qualifier.
  This removes the "duplicate key across active sets" ambiguity entirely — there is nothing left
  to disambiguate, since only `default` is ever searched unqualified.
- Replace the flat list of top-level verbs (`create`, `delete`, `key`, `list`, ...) with two verb
  groups that mirror the two things you actually manage: **`nav set`** and **`nav key`**.

## Core Concepts

- **Keyword** — a short name bound to a directory path.
- **Set** — a named collection of keywords. Every set except `default` must be addressed by name.
- **`default` set** — created automatically, always present, cannot be removed or renamed.
  Keywords in it are reachable directly: `nav <keyword>`.
- **Qualified keyword** — `<setname>:<keyword>`, e.g. `nav navtool:proj`. Required for every set
  other than `default`.
- No set is ever "active" or "inactive" anymore. A set either exists (and is reachable via
  qualification, or unqualified if it's `default`) or it doesn't.

## Command Reference

### Navigation (not a subcommand — this is the everyday path)

```sh
nav <keyword>              # cd to a keyword registered in the `default` set
nav <setname>:<keyword>    # cd to a keyword registered in a specific (non-default) set
nav <path-or-anything-else># falls through to a plain `cd`, same as today
```

If `<keyword>` (or `<setname>:<keyword>`) doesn't resolve to anything registered, `nav` falls
back to passing the argument straight to `cd` — so `nav ../sibling-dir` or `nav some/real/path`
still behaves like plain `cd`.

### `nav set` — manage sets

| Command | Description |
|---|---|
| `nav set list [--describe/-d]` | List all sets. `--describe` also prints each set's description. |
| `nav set show <name>` | Show a set's description plus every keyword entry (and its path) registered under it. |
| `nav set add <name> [--desc/-d TEXT]` | Create a new (non-default) set. |
| `nav set remove <name>` | Delete a set and all its keys (confirmation prompt). Blocked for `default`. |
| `nav set update <name> [--rename NEW_NAME] [--desc/-d TEXT]` | Rename a set and/or change its description. Blocked for `default`. |

### `nav key` — manage key entries

| Command | Description |
|---|---|
| `nav key list [--set/-s SET_NAME]` | List keys. Omit `--set` to list every set's keys, grouped by set. |
| `nav key add <keyword> <directory> [--set/-s SET_NAME]` | Register a keyword. Defaults to the `default` set if `--set` is omitted. |
| `nav key remove <keyword> [--set/-s SET_NAME]` | Remove a keyword. Defaults to `default`. |
| `nav key update <keyword> <new-directory> [--set/-s SET_NAME]` | Repoint an existing keyword at a new directory. Defaults to `default`. |
| `nav key move <keyword> --to/-t SET_NAME [--from/-f SET_NAME]` | Move a keyword (and its path) from one set to another. `--from` defaults to `default`. |

### `nav path` — internal plumbing (used by `shell/nav.sh`)

`nav path <arg>` resolves either a bare keyword or a `set:key` qualified keyword to an absolute
path and prints it, exiting non-zero if nothing matches. This is what the shell wrapper calls
under the hood — you generally won't type this yourself, but it's a normal top-level command.

### `nav db` — inspect the database

The database file is chosen automatically: a dev/editable build run from the repo uses
`<repo>/.navtool.dev.db`, an installed (pipx) build uses `~/.navtool.db`, and `$NAVTOOL_DB`
overrides either one. These commands report what's actually in effect.

| Command | Description |
|---|---|
| `nav db path` | Print just the path of the database file in use (scriptable). |
| `nav db info` | Show the path, why it was chosen (dev/prod/override), its size, and set/entry counts. |

```sh
$ nav db info
Database: /Users/me/Projects/navtool/.navtool.dev.db
Source:   dev build (editable install)
Size:     20.0 KB
Sets:     3
Entries:  6
```

## Reserved Top-Level Words

`shell/nav.sh` decides whether your first argument is a subcommand (`set`, `key`, `path`, `help`,
...) or a keyword to navigate to. That means an **unqualified `default`-set keyword can't share a
name with a top-level command** (e.g. don't name a default keyword `set` or `key`).

This constraint disappears for every other set: because qualified lookups always take the
`setname:keyword` form (with a colon), they never collide with a bare command name. So
`nav proj:key` and `nav proj:set` are both perfectly fine keywords inside the `proj` set.

## Example Workflows

### Fresh install

```sh
$ nav set list
default
```

The `default` set exists from the start — nothing to create.

### Everyday keywords (default set)

```sh
$ cd ~/Projects/navtool
$ nav key add navtool .
Registered 'navtool' -> '/Users/me/Projects/navtool' in set 'default'

$ cd /somewhere/else
$ nav navtool
cwd: /Users/me/Projects/navtool

$ nav key update navtool ~/Projects/navtool-v2
Updated 'navtool' -> '/Users/me/Projects/navtool-v2' in set 'default'

$ nav key remove navtool
Removed 'navtool' from set 'default'
```

### Project-specific set

```sh
$ nav set add navtool --desc "navtool repo shortcuts"
Created set: navtool - navtool repo shortcuts

$ nav key add proj ~/Projects/navtool --set navtool
Registered 'proj' -> '/Users/me/Projects/navtool' in set 'navtool'

$ nav key add docs ~/Projects/navtool/docs --set navtool
Registered 'docs' -> '/Users/me/Projects/navtool/docs' in set 'navtool'

$ nav navtool:proj
cwd: /Users/me/Projects/navtool

$ nav navtool:docs
cwd: /Users/me/Projects/navtool/docs
```

Note there's no `nav set use navtool` step — the set is reachable via qualification the moment
it has keys, with no activation step required.

### Reusing a keyword name across sets

```sh
$ nav key add proj ~/Projects/other-repo --set other
Registered 'proj' -> '/Users/me/Projects/other-repo' in set 'other'

$ nav navtool:proj
cwd: /Users/me/Projects/navtool

$ nav other:proj
cwd: /Users/me/Projects/other-repo
```

Both sets can use the keyword `proj` with zero ambiguity, since each is only ever reached through
its own qualifier.

### Moving a keyword to a different set

A keyword created in the wrong place (or a project that's growing out of `default`) can be moved
without re-typing its path:

```sh
$ nav key add scratch ~/Projects/navtool/tmp
Registered 'scratch' -> '/Users/me/Projects/navtool/tmp' in set 'default'

$ nav key move scratch --to navtool
Moved 'scratch' -> '/Users/me/Projects/navtool/tmp' from set 'default' to set 'navtool'

$ nav navtool:scratch
cwd: /Users/me/Projects/navtool/tmp
```

`--from` defaults to `default`, so moving out of `default` only needs `--to`. Moving between two
non-default sets requires both:

```sh
$ nav key move proj --from navtool --to navtool2
Moved 'proj' -> '/Users/me/Projects/navtool' from set 'navtool' to set 'navtool2'
```

If the destination set already has a keyword with that name, the move is rejected (same
already-exists error as `nav key add`) — resolve the collision (e.g. `nav key remove` or
`nav key update` the conflicting entry) before retrying.

### Listing

```sh
$ nav set list --describe
default – (no description)
navtool – navtool repo shortcuts
other – (no description)

$ nav key list
default:
  (no entries)
navtool:
  proj -> /Users/me/Projects/navtool
  docs -> /Users/me/Projects/navtool/docs
other:
  proj -> /Users/me/Projects/other-repo

$ nav key list --set navtool
navtool:
  proj -> /Users/me/Projects/navtool
  docs -> /Users/me/Projects/navtool/docs

$ nav set show navtool
navtool: navtool repo shortcuts
  proj -> /Users/me/Projects/navtool
  docs -> /Users/me/Projects/navtool/docs
```

`nav set show <name>` and `nav key list --set <name>` return the same entries — `set show` is the
one-stop "tell me about this set" view (description + entries together), while `key list` is the
entry-focused query, usable with or without a `--set` filter.

### Renaming / cleaning up a set

```sh
$ nav set update navtool --rename nt
Renamed set 'navtool' -> 'nt'

$ nav nt:proj
cwd: /Users/me/Projects/navtool

$ nav set remove other
Are you sure you want to delete the set 'other'? [y/N]: y
Deleted the 'other' set.
```

### Falling through to plain `cd`

```sh
$ nav ~/Downloads
cwd: /Users/me/Downloads   # 'Downloads' isn't a registered keyword, so nav behaves like cd
```

## Command Mapping (current → proposed)

| Current | Proposed |
|---|---|
| `nav create <set> [--desc]` | `nav set add <set> [--desc]` |
| `nav delete <set>` | `nav set remove <set>` |
| `nav use <set>` | *(removed — no activation step; qualify with `set:key` instead)* |
| `nav unuse <set>` | *(removed)* |
| `nav key <key> <dir>` | `nav key add <key> <dir> [--set <set>]` (defaults to `default`) |
| `nav list [--describe]` | `nav set list [--describe]` |
| `nav list entries <set>` | `nav set show <set>` (or `nav key list --set <set>`) |
| `nav path <key>` | `nav path <key>` — unchanged shape, now also accepts `set:key` |
| *(none today)* | `nav key remove <key> [--set <set>]` |
| *(none today)* | `nav key update <key> <dir> [--set <set>]` |
| *(none today)* | `nav set update <set> [--rename] [--desc]` |
| *(none today)* | `nav key move <key> --to <set> [--from <set>]` |
| *(none today)* | `nav set show <set>` |

## Open Decisions Before Implementation

These are reasonable defaults assumed above — flag anything you'd rather do differently:

1. **`default` is immutable**: cannot be renamed or removed via `nav set update|remove`.
2. **`:` is disallowed in set and keyword names** (validated on `set add` / `key add`), since it's
   the qualifier delimiter.
3. **`nav key list` with no `--set`** prints every set grouped by name (shown above), rather than
   just `default`.
4. **Case sensitivity**: keys/sets stay case-sensitive, matching current behavior.
5. **Scriptability**: worth adding a `--yes/-y` flag to `set remove` to skip the confirmation
   prompt for non-interactive use? Not in the table above yet.
6. **Failed resolution behavior**: today `nav path <key>` prints an error message but exits `0`,
   so the current `shell/nav.sh` would actually try to `cd` into that error string rather than
   falling back to a plain `cd`. The overhaul should make `nav path` exit non-zero on a miss so
   `shell/nav.sh` can catch it and fall back to `cd "$1"` as intended.
