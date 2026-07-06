# NavTool Tests

This directory contains NavTool's test suite:

- `test_db.py` — database schema and behavior (default set seeding, constraints, cascades).
- `test_cli.py` — command-level tests that invoke the CLI against a throwaway database.

The CLI tests set `$NAVTOOL_DB` to a temporary file, so running them never touches your real
NavTool data.

## Running

From the repository root, with the virtual environment active and dev dependencies installed
(see [../docs/dev-quickstart.md](../docs/dev-quickstart.md)):

```sh
pytest
```

`pytest` discovers and runs every `test_*.py` file in this directory.
