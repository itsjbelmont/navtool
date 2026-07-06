# NavTool CLI Usage

NavTool maps short names to directories so you can `cd` to them by name. Names form a **tree**:
any name can have nested child names. This guide is the full command reference.

The `navtool` CLI is invoked through the `nav` shell function (see [../shell/nav.sh](../shell/nav.sh)),
which performs the actual `cd`. Commands that don't navigate can also be run as `navtool ...`
directly.

## Concepts

- **Name** — a short label bound to a directory path.
- **Name path** — a name addressed within the tree by joining names with `:`, e.g.
  `myproj:tests:unit`. A bare name (no `:`) addresses a **top-level** name.
- **Tree** — every name is a node with an optional parent. A name with children is just a name
  other names point at as their parent; there is no separate "set" or "group" concept.
- **Top-level names are unambiguous** — a bare `nav <name>` only ever matches a top-level name, and
  top-level names are unique. Nested names are reached by their full path (`parent:child`), so the
  same child name can be reused under different parents.
- `:` is reserved as the path delimiter and is rejected inside individual names.

## Navigation

```sh
nav <name>               # cd to a top-level name
nav <a>:<b>:<c>          # cd to a nested name, walking the tree
nav <name>:              # trailing colon is tolerated -> the name itself
nav <path>               # not a name -> passed straight to cd
```

When an argument doesn't resolve to a registered name, `nav` falls back to a plain `cd`, so
`nav ../sibling` or `nav /some/path` behaves like `cd`.

Because the shell function treats the first word as a subcommand when it matches one (`add`, `rm`,
`mv`, `update`, `ls`, `which`, `db`, `path`), a top-level name should not share a name with a
command. Nested names are always addressed with a `:` path, so they never collide with commands.

## Managing names

| Command | Description |
|---|---|
| `nav add <name-path> <directory>` | Register a name pointing at a directory. A bare name is top-level; a `parent:name` path nests it under an existing parent. The directory must exist. |
| `nav rm <name-path> [--yes/-y]` | Remove a name. Nested children are removed with it; prompts for confirmation when children exist unless `--yes`. |
| `nav mv <name-path> [--to/-t PARENT] [--root] [--rename/-r NEW]` | Move a name under a new parent (`--to`) or to the top level (`--root`), and/or rename it (`--rename`). Rejects moves that would create a cycle. |
| `nav update <name-path> <new-directory>` | Repoint an existing name at a new directory. |
| `nav ls [<name-path>]` | List names as an indented tree. With a name path, list only that subtree. |
| `nav which [<directory>]` | Reverse lookup: show which name(s) point at a directory (defaults to the current directory). Exits non-zero if none do. |

## `nav db` — inspect the database

The database file is chosen automatically: an installed (pipx) build uses `~/.navtool.db`, a
dev/editable build run from the repo uses `<repo>/.navtool.dev.db`, and `$NAVTOOL_DB` overrides
both.

| Command | Description |
|---|---|
| `nav db path` | Print the path of the database file in use. |
| `nav db info` | Show the path, why it was chosen (dev/prod/override), size, schema/app version, and node counts. |
| `nav db schema` | Print the current database schema, generated from the migration chain (never hand-maintained, so it can't drift). |
| `nav db migrate` | Apply any pending schema migrations and report the result. Migrations also run automatically on connect, so this is mainly an explicit control point. |

The database is versioned with SQLite's `PRAGMA user_version`. When navtool opens a database that
is behind the current schema, it first writes a timestamped `*.pre-migrate-*` backup next to the
file, then applies the pending migrations. A database created by a *newer* navtool is refused, and
a pre-overhaul database (from the old set/key model) is rejected with instructions to delete it.

## `nav --version`

`nav --version` prints the installed navtool version. (Name/database data is unaffected by
version; the two are tracked separately — see [dev-quickstart.md](dev-quickstart.md).)

## `nav path` — resolve a name

`nav path <name-path>` prints the absolute path a name resolves to, and exits non-zero if nothing
matches. The `nav` shell function calls this internally and falls back to `cd` on a non-zero exit.

## Examples

### Everyday names

```sh
$ cd ~/projects/myproj
$ nav add myproj .
Added 'myproj' -> /Users/me/projects/myproj

$ cd /somewhere/else
$ nav myproj
# now in /Users/me/projects/myproj

$ nav update myproj ~/projects/myproj-v2
Updated 'myproj' -> /Users/me/projects/myproj-v2

$ nav rm myproj
Removed 'myproj'
```

### Nesting names under a project

The parent must already exist. Nest as deep as you like:

```sh
$ nav add myproj ~/projects/myproj
Added 'myproj' -> /Users/me/projects/myproj

$ nav add myproj:tests ~/projects/myproj/tests
Added 'myproj:tests' -> /Users/me/projects/myproj/tests

$ nav add myproj:tests:unit ~/projects/myproj/tests/unit
Added 'myproj:tests:unit' -> /Users/me/projects/myproj/tests/unit

$ nav myproj:tests        # cd to ~/projects/myproj/tests
$ nav myproj              # cd to ~/projects/myproj
```

### Reusing a name under different parents

A bare name only matches the top level, so nested names never clash with each other:

```sh
$ nav add api ~/code/api
$ nav add api:tests ~/code/api/tests
$ nav add web ~/code/web
$ nav add web:tests ~/code/web/tests

$ nav api:tests        # /Users/me/code/api/tests
$ nav web:tests        # /Users/me/code/web/tests
```

### Moving and renaming

```sh
$ nav add scratch ~/code/api/tmp
Added 'scratch' -> /Users/me/code/api/tmp

# Nest an existing top-level name under a parent:
$ nav mv scratch --to api
Moved 'scratch' -> 'scratch' under 'api'

# Rename it:
$ nav mv api:scratch --rename tmp
Moved 'api:scratch' -> 'tmp'

# Promote a nested name back to the top level:
$ nav mv api:tmp --root
Moved 'api:tmp' -> 'tmp' to the top level
```

A move is rejected if it would create a cycle (moving a name under one of its own descendants) or
if the destination already has a child with that name.

### Listing

```sh
$ nav ls
api -> /Users/me/code/api
  tests -> /Users/me/code/api/tests
web -> /Users/me/code/web
  tests -> /Users/me/code/web/tests

$ nav ls api
api -> /Users/me/code/api
  tests -> /Users/me/code/api/tests
```

`nav ls` with no argument prints the whole tree; `nav ls <name>` prints just that name and its
subtree.

### Finding the name(s) for a directory

`nav which` is the reverse of navigation: given a directory, it prints the name path(s) that point
at it. With no argument it checks the current directory. The directory is normalized the same way
`add` normalizes it (expanding `~`, resolving symlinks and trailing slashes), so it matches
regardless of how you spell it. More than one name can point at the same directory, and all are
listed:

```sh
$ nav which ~/code/api
api

$ cd ~/code/api/tests
$ nav which
api:tests

$ nav which ~/not/registered
No name points at /Users/me/not/registered      # exits non-zero
```

### Removing a subtree

```sh
$ nav rm api
'api' has 1 nested entry that will also be removed. Continue? [y/N]: y
Removed 'api' and 1 nested entry
```

### Inspecting the database

```sh
$ nav db info
Database:  /Users/me/.navtool.db
Source:    prod build (installed)
Size:      20.0 KB
Schema:    version 1 (up to date)
NavTool:   0.1.0
Nodes:     4
Top-level: 2

$ nav db schema
CREATE TABLE nodes (
  id         INTEGER PRIMARY KEY,
  ...
);
```
