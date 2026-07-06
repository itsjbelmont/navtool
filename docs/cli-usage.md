# NavTool CLI Usage

NavTool maps short keywords to directories so you can `cd` to them by name. Keywords are grouped
into **sets**. This guide is the full command reference.

The `navtool` CLI is invoked through the `nav` shell function (see [../shell/nav.sh](../shell/nav.sh)),
which performs the actual `cd`. Commands that don't navigate can also be run as `navtool ...`
directly.

## Concepts

- **Keyword** — a short name bound to a directory path.
- **Set** — a named collection of keywords.
- **`default` set** — always present; cannot be renamed or removed. Unqualified keywords resolve
  against it: `nav <keyword>`.
- **Qualified keyword** — `<set>:<keyword>` (e.g. `nav work:api`). Required for every set other
  than `default`. Because each set is reached only through its own qualifier, the same keyword
  name can exist in multiple sets.
- `:` is reserved as the set/keyword delimiter and is rejected in set and keyword names.

## Navigation

```sh
nav <keyword>            # cd to a keyword in the default set
nav <set>:<keyword>      # cd to a keyword in a specific set
nav <path>               # not a keyword -> passed straight to cd
```

When an argument doesn't resolve to a registered keyword, `nav` falls back to a plain `cd`, so
`nav ../sibling` or `nav /some/path` behaves like `cd`.

Because the shell function treats the first word as a subcommand when it matches one (`set`, `key`,
`db`, `path`), a `default`-set keyword should not share a name with a top-level command. Keywords
in other sets are always qualified (`set:keyword`), so they never collide with command names.

## `nav set` — manage sets

| Command | Description |
|---|---|
| `nav set list [--describe/-d]` | List all sets. `--describe` also prints each set's description. |
| `nav set show <name>` | Show a set's description and every keyword entry (with its path). |
| `nav set add <name> [--desc/-d TEXT]` | Create a new set. |
| `nav set remove <name> [--yes/-y]` | Delete a set and all its keys. Prompts for confirmation unless `--yes`. Blocked for `default`. |
| `nav set update <name> [--rename NEW_NAME] [--desc/-d TEXT]` | Rename a set and/or change its description. Blocked for `default`. |

## `nav key` — manage keyword entries

| Command | Description |
|---|---|
| `nav key list [--set/-s SET_NAME]` | List keywords grouped by set. With `--set`, list only that set. |
| `nav key add <keyword> <directory> [--set/-s SET_NAME]` | Register a keyword. Defaults to the `default` set. The directory must exist. |
| `nav key remove <keyword> [--set/-s SET_NAME]` | Remove a keyword. Defaults to `default`. |
| `nav key update <keyword> <new-directory> [--set/-s SET_NAME]` | Point an existing keyword at a new directory. Defaults to `default`. |
| `nav key move <keyword> --to/-t SET_NAME [--from/-f SET_NAME]` | Move a keyword (and its path) between sets. `--from` defaults to `default`. |

## `nav db` — inspect the database

The database file is chosen automatically: an installed (pipx) build uses `~/.navtool.db`, a
dev/editable build run from the repo uses `<repo>/.navtool.dev.db`, and `$NAVTOOL_DB` overrides
both.

| Command | Description |
|---|---|
| `nav db path` | Print the path of the database file in use. |
| `nav db info` | Show the path, why it was chosen (dev/prod/override), its size, and set/entry counts. |

## `nav path` — resolve a keyword

`nav path <keyword>` (or `nav path <set>:<keyword>`) prints the absolute path a keyword resolves
to, and exits non-zero if nothing matches. The `nav` shell function calls this internally and
falls back to `cd` on a non-zero exit.

## Examples

### Everyday keywords (default set)

```sh
$ cd ~/Projects/navtool
$ nav key add navtool .
Registered 'navtool' -> '/Users/me/Projects/navtool' in set 'default'

$ cd /somewhere/else
$ nav navtool
# now in /Users/me/Projects/navtool

$ nav key update navtool ~/Projects/navtool-v2
Updated 'navtool' -> '/Users/me/Projects/navtool-v2' in set 'default'

$ nav key remove navtool
Removed 'navtool' from set 'default'
```

### Project set

```sh
$ nav set add work --desc "work project shortcuts"
Created set: work - work project shortcuts

$ nav key add api ~/code/api --set work
Registered 'api' -> '/Users/me/code/api' in set 'work'

$ nav work:api
# now in /Users/me/code/api
```

### Reusing a keyword across sets

```sh
$ nav key add api ~/code/other-api --set personal
Registered 'api' -> '/Users/me/code/other-api' in set 'personal'

$ nav work:api        # /Users/me/code/api
$ nav personal:api    # /Users/me/code/other-api
```

### Moving a keyword between sets

`--from` defaults to `default`, so moving out of `default` only needs `--to`. Moving between two
non-default sets needs both. A move fails if the destination already has a keyword with that name.

```sh
$ nav key add scratch ~/code/api/tmp
Registered 'scratch' -> '/Users/me/code/api/tmp' in set 'default'

$ nav key move scratch --to work
Moved 'scratch' -> '/Users/me/code/api/tmp' from set 'default' to set 'work'

$ nav key move api --from work --to archive
Moved 'api' -> '/Users/me/code/api' from set 'work' to set 'archive'
```

### Listing

```sh
$ nav set list --describe
default – (no description)
work – work project shortcuts
personal – (no description)

$ nav key list
default:
  (no entries)
work:
  api -> /Users/me/code/api
personal:
  api -> /Users/me/code/other-api

$ nav set show work
work: work project shortcuts
  api -> /Users/me/code/api
```

`nav set show <name>` and `nav key list --set <name>` return the same entries. `set show` also
prints the set's description; `key list` can list every set at once.

### Renaming and removing sets

```sh
$ nav set update work --rename w
Renamed set 'work' -> 'w'

$ nav w:api
# now in /Users/me/code/api

$ nav set remove personal
Are you sure you want to delete the set 'personal'? [y/N]: y
Deleted the 'personal' set.
```

### Inspecting the database

```sh
$ nav db info
Database: /Users/me/.navtool.db
Source:   prod build (installed)
Size:     20.0 KB
Sets:     3
Entries:  4
```
