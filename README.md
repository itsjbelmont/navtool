# NavTool

NavTool is a command line utility for efficiently navigating between commonly accessed pre-known directory paths.

## NavTool Quickstart

NavTool functions by allowing you to save key/directory pairs for commonly accessed directories and easily navigate to these directories via their key.
The utility is run via the `nav` command.

In the simplest form, a NavTool workflow looks like this:

```sh
$ cd /my/path/to/project-root
$ nav --save proj . # Save the CWD into the `proj` key
$ cd /some/other/path
$ nav proj # Navigate to the saved directory via the `proj` key
```

When working on multiple projects you can associate a set of keys with each project via "nav sets."
This allows you to automatically load/unload the keys for a given set when working on each of your individual projects.
This aims to solve two primary use cases:

1. Avoids key pollution by using a key only when working on the specific project that needs it
1. Allows using the same key for multiple projects (such as using the `build` key to access a project's build artifacts)

```sh
# List the keys currently in use
$ nav --keys
No keys available

# List the available sets
$ nav --sets
default
proj1
proj2

# Load one of the project sets
$ nav --load proj1

# List the keys currently in use
$ nav --keys
proj1:proj    -> /path/to/proj
proj1:build   -> /path/to/proj/build/release
proj1:logs    -> /path/to/installed_application/proj1/logs

# Navigate to a key
$ nav build 
cwd: /path/to/proj/build/release
```

When using multiple loaded NavSets simultaneously you can specify unique keys without a set-specifier.
If duplicate keys exist you can specify which project's key to use by including its prefix.
If no set is specified and you try to navigate to a duplicate key you will be prompted to select which set's key should be used.

```
$ nav --load proj1
$ nav --load proj2
$ nav --keys
proj1:proj    -> /path/to/proj1
proj1:build   -> /path/to/proj1/build/release
proj1:logs    -> /path/to/installed_application/proj1/logs

proj2:proj    -> /path/to/proj2
proj2:output  -> /path/to/proj2/output/dir

$ nav output
cwd: /path/to/proj2/output/dir

$ nav proj1:proj
cwd: /path/to/proj1
```


## System Requirements

* `Python3`
  * Run `python3 --version` to validate that python3 is installed

## Get Started

1. Pick a directory on your PC where the tool can live and `cd` to that location

1. Clone the repository: `git clone https://github.com/itsjbelmont/navtool.git`

1. **TODO:** Bootstrap the shell entry point (and restart terminals?)

1. Validate installation: `nav --version`

1. See navtool help menu: `nav -h` or `nav --help`


## Idea Scratch Space

* By default navtool maintains a generic set that is always active

* Allow loading nav sets for different projects via `nav use <PROJ>`

* Allow listing nav sets that are available via `nav list sets`

* Allow adding / removing nav sets

* Use a SQLite database to support saving the sets/keys (overkill but good learning opportunity)

    ```
    CREATE TABLE IF NOT EXISTS sets (
      name TEXT PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS entries (
      set_name TEXT,
      key TEXT,
      value TEXT,
      PRIMARY KEY (set_name, key),
      FOREIGN KEY (set_name) REFERENCES sets(name) ON DELETE CASCADE
    );
    ```

    **NOTE:**
    SQLite does not enforce foreign keys by default. You must do this after connecting:
    `conn.execute("PRAGMA foreign_keys = ON")`