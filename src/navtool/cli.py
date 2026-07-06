import os
from pathlib import Path

import click

from navtool import __version__
from navtool.db import (MEMORY_DB, SCHEMA_VERSION, IncompatibleDatabaseError,
                        NewerDatabaseError, _get_user_version,
                        create_connection, get_connection, migrate)

# The production database, used by installed (pipx) builds.
PROD_DB_PATH = "~/.navtool.db"
# Environment variable that explicitly overrides the database location.
DB_ENV_VAR = "NAVTOOL_DB"


def _running_from_source_checkout() -> bool:
    """True when running as an editable/dev install from the repo checkout.

    Editable installs execute from ``<repo>/src/navtool/cli.py``, so a
    ``pyproject.toml`` sits two directories above this package. A regular
    (pipx / site-packages) install has no such file there.
    """
    return (Path(__file__).resolve().parents[2] / "pyproject.toml").is_file()


def resolve_db() -> tuple[str, str]:
    """Choose the database file to use and explain why.

    Returns ``(path, source)`` where ``source`` is a short human-readable label.

    Priority:
      1. ``$NAVTOOL_DB`` — explicit override, always wins.
      2. Dev build  -> ``<repo>/.navtool.dev.db`` (kept out of prod's data).
      3. Prod build -> ``~/.navtool.db``.
    """
    override = os.environ.get(DB_ENV_VAR)
    if override:
        return str(Path(override).expanduser()), f"override via ${DB_ENV_VAR}"
    if _running_from_source_checkout():
        path = Path(__file__).resolve().parents[2] / ".navtool.dev.db"
        return str(path), "dev build (editable install)"
    return str(Path(PROD_DB_PATH).expanduser()), "prod build (installed)"


def resolve_db_path() -> str:
    """Return just the resolved database path (see :func:`resolve_db`)."""
    return resolve_db()[0]


# ----------------- Helpers -----------------
# Nodes form a single tree. A "name path" addresses a node by walking names from
# the top level down, joined with ':' — e.g. `myproj:tests:unit`. A bare name
# (no ':') addresses a top-level node.


def _parse_path(query: str) -> list[str]:
    """Split a name path into its segments, validating them.

    A single trailing ':' is tolerated (``proj:`` -> ``['proj']``) so the same
    grammar covers "the node itself". Empty or interior-empty segments (``''``,
    ``a::b``, ``:b``) are rejected.
    """
    parts = query.split(":")
    if len(parts) > 1 and parts[-1] == "":
        parts = parts[:-1]
    if not parts or any(p == "" for p in parts):
        raise click.ClickException(f"Invalid name path: '{query}'")
    return parts


def _resolve(conn, segments: list[str]):
    """Walk `segments` from the top level down.

    Returns the final node row ``(id, parent_id, name, path)`` or ``None`` if any
    segment has no match.
    """
    parent_id = None
    node = None
    for seg in segments:
        node = conn.execute(
            "SELECT id, parent_id, name, path FROM nodes "
            "WHERE parent_id IS ? AND name = ?",
            (parent_id, seg),
        ).fetchone()
        if node is None:
            return None
        parent_id = node[0]
    return node


def _require_node(conn, name_path: str):
    """Resolve a name path to a node row, raising a friendly error on a miss."""
    node = _resolve(conn, _parse_path(name_path))
    if node is None:
        raise click.ClickException(f"'{name_path}' does not exist.")
    return node


def _descendant_count(conn, node_id: int) -> int:
    """Number of nodes nested beneath `node_id` (excluding the node itself)."""
    return conn.execute(
        "WITH RECURSIVE sub(id) AS ("
        "  SELECT id FROM nodes WHERE id = ?"
        "  UNION ALL"
        "  SELECT n.id FROM nodes n JOIN sub ON n.parent_id = sub.id"
        ") SELECT COUNT(*) - 1 FROM sub",
        (node_id,),
    ).fetchone()[0]


def _resolve_directory(directory: str) -> str:
    """Expand/resolve a directory argument, ensuring it exists."""
    full_path = str(Path(directory).expanduser().resolve())
    if not Path(full_path).is_dir():
        raise click.ClickException(f"Directory does not exist: {full_path}")
    return full_path


def _node_path(conn, node_id: int) -> str:
    """Build a node's full name path (``a:b:c``) by walking up to the root."""
    names = []
    cur = node_id
    while cur is not None:
        parent_id, name = conn.execute(
            "SELECT parent_id, name FROM nodes WHERE id = ?", (cur,)
        ).fetchone()
        names.append(name)
        cur = parent_id
    return ":".join(reversed(names))


def _render_subtree(conn, node_id, name, path, depth, lines) -> None:
    """Append an indented ``name -> path`` line for a node and its descendants."""
    lines.append(f"{'  ' * depth}{click.style(name, fg='green')} -> {path}")
    for cid, cname, cpath in conn.execute(
        "SELECT id, name, path FROM nodes WHERE parent_id = ? ORDER BY name",
        (node_id,),
    ).fetchall():
        _render_subtree(conn, cid, cname, cpath, depth + 1, lines)


# ----------------- Top-level CLI -----------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="navtool", prog_name="navtool")
@click.pass_context
def cli(ctx):
    """
    Navigate directories by associating short names to commonly accessed
    directory paths. Names form a tree: a name can have nested child names
    addressed with a colon, e.g. `myproj` and `myproj:tests`.
    """
    ctx.ensure_object(dict)
    path = resolve_db_path()
    conn = create_connection(path)
    try:
        # Returns (from_version, to_version); records what this run migrated.
        ctx.obj["migration"] = migrate(conn, path)
    except (NewerDatabaseError, IncompatibleDatabaseError) as e:
        raise click.ClickException(str(e))
    ctx.obj["conn"] = conn


# ----------------- `path` command (shell plumbing) -----------------
@cli.command("path")
@click.argument("query", metavar="<NAME|A:B:C>")
@click.pass_context
def get_path(ctx, query):
    """Resolve a name (or nested a:b:c path) to its directory path.

    Exits non-zero if nothing matches so the shell wrapper can fall back to a
    plain `cd`.
    """
    conn = ctx.obj["conn"]
    node = _resolve(conn, _parse_path(query))
    if node is None:
        raise click.ClickException(f"No entry found for '{query}'.")
    click.echo(node[3])


# ----------------- node management -----------------
@cli.command("add")
@click.argument("name_path", metavar="<NAME|PARENT:NAME>")
@click.argument("directory", metavar="<DIRECTORY>")
@click.pass_context
def add(ctx, name_path, directory):
    """Register a name pointing at a directory.

    A bare NAME creates a top-level entry. A PARENT:NAME path nests the new entry
    under an existing parent (which must already exist).
    """
    conn = ctx.obj["conn"]
    *parent_segments, name = _parse_path(name_path)

    parent_id = None
    if parent_segments:
        parent = _resolve(conn, parent_segments)
        if parent is None:
            raise click.ClickException(
                f"Parent '{':'.join(parent_segments)}' does not exist."
            )
        parent_id = parent[0]

    if conn.execute(
        "SELECT 1 FROM nodes WHERE parent_id IS ? AND name = ?",
        (parent_id, name),
    ).fetchone():
        where = ":".join(parent_segments) if parent_segments else "the top level"
        raise click.ClickException(f"'{name}' already exists under {where}.")

    full_path = _resolve_directory(directory)
    conn.execute(
        "INSERT INTO nodes (parent_id, name, path) VALUES (?, ?, ?)",
        (parent_id, name, full_path),
    )
    conn.commit()
    click.echo(f"Added '{name_path}' -> {full_path}")


@cli.command("rm")
@click.argument("name_path", metavar="<NAME|A:B:C>")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt for nested entries.",
)
@click.pass_context
def rm(ctx, name_path, yes):
    """Remove an entry. Nested children are removed with it."""
    conn = ctx.obj["conn"]
    node = _require_node(conn, name_path)
    node_id = node[0]

    nested = _descendant_count(conn, node_id)
    if nested > 0 and not yes:
        if not click.confirm(
            f"'{name_path}' has {nested} nested entr"
            f"{'y' if nested == 1 else 'ies'} that will also be removed. Continue?",
            default=False,
        ):
            click.echo("Operation cancelled.")
            return

    conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
    conn.commit()
    suffix = (
        f" and {nested} nested entr{'y' if nested == 1 else 'ies'}" if nested else ""
    )
    click.echo(f"Removed '{name_path}'{suffix}")


@cli.command("mv")
@click.argument("name_path", metavar="<NAME|A:B:C>")
@click.option(
    "--to",
    "-t",
    "to_path",
    default=None,
    help="Move under this existing parent (a name path).",
)
@click.option(
    "--root",
    is_flag=True,
    default=False,
    help="Move to the top level (no parent).",
)
@click.option("--rename", "-r", "new_name", default=None, help="New name.")
@click.pass_context
def mv(ctx, name_path, to_path, root, new_name):
    """Move an entry under a new parent and/or rename it."""
    conn = ctx.obj["conn"]
    if to_path is not None and root:
        raise click.ClickException("Pass either --to or --root, not both.")
    if to_path is None and not root and new_name is None:
        raise click.ClickException("Nothing to do: pass --to, --root, and/or --rename.")
    if new_name is not None and ":" in new_name:
        raise click.ClickException(
            "A name cannot contain ':'. Use --to to change the parent."
        )

    node_id, cur_parent, cur_name, _ = _require_node(conn, name_path)

    reparent = to_path is not None or root
    if root:
        new_parent_id = None
    elif to_path is not None:
        parent = _resolve(conn, _parse_path(to_path))
        if parent is None:
            raise click.ClickException(f"Destination '{to_path}' does not exist.")
        new_parent_id = parent[0]
    else:
        new_parent_id = cur_parent

    # Reject moves that would create a cycle: the new parent must not be the node
    # itself or any of its descendants.
    if reparent and new_parent_id is not None:
        anc = new_parent_id
        while anc is not None:
            if anc == node_id:
                raise click.ClickException(
                    f"Cannot move '{name_path}' under itself or its own descendant."
                )
            row = conn.execute(
                "SELECT parent_id FROM nodes WHERE id = ?", (anc,)
            ).fetchone()
            anc = row[0] if row else None

    final_parent = new_parent_id if reparent else cur_parent
    final_name = new_name if new_name is not None else cur_name

    if conn.execute(
        "SELECT 1 FROM nodes WHERE parent_id IS ? AND name = ? AND id != ?",
        (final_parent, final_name, node_id),
    ).fetchone():
        raise click.ClickException(
            f"A node named '{final_name}' already exists at the destination."
        )

    conn.execute(
        "UPDATE nodes SET parent_id = ?, name = ? WHERE id = ?",
        (final_parent, final_name, node_id),
    )
    conn.commit()
    if root:
        dest = " to the top level"
    elif to_path is not None:
        dest = f" under '{to_path}'"
    else:
        dest = ""
    click.echo(f"Moved '{name_path}' -> '{final_name}'{dest}")


@cli.command("update")
@click.argument("name_path", metavar="<NAME|A:B:C>")
@click.argument("directory", metavar="<NEW_DIRECTORY>")
@click.pass_context
def update(ctx, name_path, directory):
    """Repoint an existing entry at a new directory."""
    conn = ctx.obj["conn"]
    node = _require_node(conn, name_path)
    full_path = _resolve_directory(directory)
    conn.execute("UPDATE nodes SET path = ? WHERE id = ?", (full_path, node[0]))
    conn.commit()
    click.echo(f"Updated '{name_path}' -> {full_path}")


@cli.command("ls")
@click.argument("name_path", metavar="<NAME|A:B:C>", required=False)
@click.pass_context
def ls(ctx, name_path):
    """List entries as a tree. With a name path, list only that subtree."""
    conn = ctx.obj["conn"]
    lines: list[str] = []
    if name_path:
        node = _require_node(conn, name_path)
        _render_subtree(conn, node[0], node[2], node[3], 0, lines)
    else:
        for tid, tname, tpath in conn.execute(
            "SELECT id, name, path FROM nodes WHERE parent_id IS NULL ORDER BY name"
        ).fetchall():
            _render_subtree(conn, tid, tname, tpath, 0, lines)
    if not lines:
        click.echo("(no entries)")
        return
    for line in lines:
        click.echo(line)


@cli.command("which")
@click.argument("directory", metavar="<DIRECTORY>", required=False)
@click.pass_context
def which(ctx, directory):
    """Show which name(s) point at a directory (default: the current directory).

    Normalizes the directory the same way `add` does (expanding `~` and
    resolving symlinks), then lists every name whose target matches it. Exits
    non-zero if none do, so it can be used as a check.
    """
    conn = ctx.obj["conn"]
    target = str(Path(directory or ".").expanduser().resolve())

    ids = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM nodes WHERE path = ?", (target,)
        ).fetchall()
    ]
    if not ids:
        click.echo(f"No name points at {target}.")
        ctx.exit(1)

    for name_path in sorted(_node_path(conn, node_id) for node_id in ids):
        click.echo(click.style(name_path, fg="green"))


# ================= `db` command group =================
@cli.group("db")
def db_group():
    """Inspect the database file navtool is using."""


@db_group.command("path")
def db_path():
    """Print the path of the database file currently in use."""
    click.echo(resolve_db_path())


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024


@db_group.command("info")
@click.pass_context
def db_info(ctx):
    """Show which database is in use, why, and a quick summary of its contents."""
    conn = ctx.obj["conn"]
    path, source = resolve_db()

    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    top_count = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE parent_id IS NULL"
    ).fetchone()[0]
    size = _format_size(Path(path).stat().st_size) if Path(path).exists() else "0 B"

    db_version = _get_user_version(conn)
    if db_version == SCHEMA_VERSION:
        schema = f"version {db_version} (up to date)"
    else:
        schema = f"version {db_version} -> {SCHEMA_VERSION} pending"

    label = click.style(path, fg="cyan")
    click.echo(f"Database:  {label}")
    click.echo(f"Source:    {source}")
    click.echo(f"Size:      {size}")
    click.echo(f"Schema:    {schema}")
    click.echo(f"NavTool:   {__version__}")
    click.echo(f"Nodes:     {node_count}")
    click.echo(f"Top-level: {top_count}")


@db_group.command("schema")
def db_schema():
    """Print the current database schema.

    Generated by building a fresh in-memory database from the migration chain and
    dumping its definitions, so it always reflects the real schema — there is no
    hand-maintained schema file that could drift.
    """
    conn = get_connection(MEMORY_DB)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL "
            "ORDER BY type = 'index', name"
        ).fetchall()
    finally:
        conn.close()
    for (sql,) in rows:
        click.echo(f"{sql};")


@db_group.command("migrate")
@click.pass_context
def db_migrate(ctx):
    """Apply any pending schema migrations to the database.

    Migrations also run automatically whenever navtool opens the database, so
    this is mainly an explicit, transparent way to trigger and report them.
    """
    # The top-level group already migrated the database on connect; report what
    # that did on this run.
    from_version, to_version = ctx.obj["migration"]
    if from_version == to_version:
        click.echo(f"Database already up to date (schema version {to_version}).")
    else:
        click.echo(
            f"Migrated database from schema version {from_version} to {to_version}."
        )
