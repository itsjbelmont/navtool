# Contributing to NavTool

Thanks for your interest in improving NavTool! Contributions of all kinds — bug reports, fixes,
docs, and features — are welcome.

## Development setup

Requires Python 3.11+.

```sh
git clone https://github.com/itsjbelmont/navtool.git
cd navtool
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"     # installs navtool plus pytest, isort, black
```

This gives you an editable install: the `navtool` CLI runs from your checkout, and a dev build
keeps its data in `<repo>/.navtool.dev/` so it never touches your real `~/.navtool/`. Run
`navtool db info` to confirm which data directory is active.

For a deeper tour of the architecture (the command tree, migrations, shell integration, and the
directory-history internals), see [docs/dev-quickstart.md](docs/dev-quickstart.md).

## Running the tests

```sh
pytest
```

The suite includes shell-integration tests that drive the packaged snippets in real `zsh` and
`bash`. They **auto-skip** when a shell isn't installed, so a partial run is expected locally if you
only have one shell — CI runs both. Please make sure `pytest` is green before opening a PR.

## Code style

- Imports are sorted with **isort**; run `isort .` before committing (CI enforces
  `isort --check-only`).
- Match the surrounding style of the file you're editing — comment density, naming, and idioms.
- Shell code lives under `src/navtool/resources/shell/`. `history.bash`/`completion.bash` target the
  bash **3.2** that ships with macOS, so avoid features newer than that (e.g. negative-offset array
  slicing, associative arrays, `PROMPT_COMMAND` arrays).

## Pull requests

1. Branch off `main`.
2. Keep changes focused; add or update tests for behavior changes.
3. Ensure `pytest` and `isort --check-only .` pass.
4. Describe **what** changed and **why** in the PR description.

## Reporting bugs & requesting features

Open an issue using the [bug report](.github/ISSUE_TEMPLATE/bug_report.md) or
[feature request](.github/ISSUE_TEMPLATE/feature_request.md) template. For bugs, please include your
OS, shell (and version — `zsh --version` / `bash --version`), and the output of `navtool db info`.
