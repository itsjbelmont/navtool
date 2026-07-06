PRAGMA foreign_keys = ON;

-- A single self-referential tree of navigable nodes. Every node maps a short
-- `name` to a directory `path`; `parent_id` links it to its parent (NULL for
-- top-level nodes). There is no separate notion of a "set" — a node that has
-- children is simply a node that other nodes point at as their parent.
CREATE TABLE IF NOT EXISTS nodes (
  id         INTEGER PRIMARY KEY,
  parent_id  INTEGER,
  name       TEXT NOT NULL,
  path       TEXT NOT NULL,
  FOREIGN KEY (parent_id)
    REFERENCES nodes(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

-- Sibling names must be unique. SQLite treats each NULL as distinct, so a plain
-- UNIQUE(parent_id, name) would NOT constrain top-level rows (parent_id IS
-- NULL). Two partial unique indexes cover both cases: one for children, one for
-- the top level. Top-level uniqueness is what keeps bare `nav <name>` lookups
-- unambiguous.
CREATE UNIQUE INDEX IF NOT EXISTS ux_nodes_child
  ON nodes(parent_id, name) WHERE parent_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_nodes_root
  ON nodes(name) WHERE parent_id IS NULL;

-- Speeds up child lookups during path resolution and cascade deletes.
CREATE INDEX IF NOT EXISTS ix_nodes_parent ON nodes(parent_id);
