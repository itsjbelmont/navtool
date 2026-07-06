PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sets (
  set_name TEXT PRIMARY KEY,
  description TEXT
);

CREATE TABLE IF NOT EXISTS entries (
  set_name TEXT,
  entry_key TEXT,
  entry_value TEXT,
  PRIMARY KEY (set_name, entry_key),
  FOREIGN KEY (set_name)
    REFERENCES sets(set_name)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

-- The `default` set is always present and is the target for unqualified keywords.
INSERT OR IGNORE INTO sets (set_name, description) VALUES ('default', NULL);
