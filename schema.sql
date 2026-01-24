PRAGMA foreign_keys = ON 

CREATE TABLE IF NOT EXISTS sets {
  set_name TEXT PRIMARY KEY
}

CREATE TABLE IF NOT EXISTS entries {
  set_name TEXT,
  entry_key TEXT,
  entry_value TEXT,
  PRIMARY KEY (set_name, entry_key),
  FOREIGN KEY (set_name) REFERENCES sets(set_name) on DELETE CASCADE
}