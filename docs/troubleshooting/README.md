# Troubleshooting

Known issues and their fixes, organized by shell. Find your shell below.

| Shell | Known issues |
|---|---|
| [bash](bash.md) | `nav` not loading in new macOS terminals; nested `name:child` tab-completion needs an extra package |
| zsh | None known — zsh works out of the box after `navtool bootstrap`. |

If your problem isn't listed here, first confirm the basics:

```sh
which navtool                 # should print a real path (e.g. ~/.local/bin/navtool)
navtool bootstrap --dry-run   # shows the block and which startup file it targets
```

Then open a **new** terminal (the integration loads at shell startup) and retry.
