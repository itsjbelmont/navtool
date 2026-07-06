"""Helpers for navigating the ``nodes`` tree.

Nodes form a single tree. A "name path" addresses a node by walking names from
the top level down, joined with ':' — e.g. ``myproj:tests:unit``. A bare name
(no ':') addresses a top-level node.
"""

from pathlib import Path

import click


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
