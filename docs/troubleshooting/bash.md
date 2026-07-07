# Troubleshooting: bash

## `nav` isn't available in new terminal windows on macOS

**Symptom:** After running `navtool bootstrap --shell bash`, the `nav` command
works if you type `bash` at an existing prompt, but a freshly opened Terminal (or
iTerm) window doesn't recognize `nav`.

**Cause:** `navtool bootstrap --shell bash` writes its integration line to
`~/.bashrc`. On macOS, Terminal starts bash as a *login* shell, and a login shell
reads `~/.bash_profile` (or `~/.profile`) — **not** `~/.bashrc`. So the block is
present but never sourced in new windows. (On most Linux distributions terminals
start non-login interactive shells that do read `~/.bashrc`, so this is mainly a
macOS issue.)

**Fix — pick one:**

1. **Have `~/.bash_profile` source `~/.bashrc`** (the conventional setup). Add this
   to `~/.bash_profile`:

   ```bash
   [ -f ~/.bashrc ] && . ~/.bashrc
   ```

   This is the recommended fix because everything you put in `~/.bashrc` (not just
   navtool) will then load in login shells too.

2. **Point bootstrap at the login file directly:**

   ```sh
   navtool bootstrap --shell bash --rc ~/.bash_profile
   ```

   This writes the managed block straight into `~/.bash_profile`. Simple, but only
   moves navtool — other `~/.bashrc` settings still won't load in login shells.

After either fix, open a new terminal (or `source` the file you edited) and verify:

```sh
type nav        # -> "nav is a function"
```

---

## Nested name completion (`nav proj:sub<TAB>`) doesn't work in bash

**Symptom:** Top-level completion works (`nav <TAB>`, `nav proj<TAB>`), but
completing a child after a colon — `nav proj:te<TAB>` — does nothing.

**Cause:** bash breaks words on `:` by default. navtool's completion relies on the
colon-aware helpers (`_get_comp_words_by_ref`, `__ltrim_colon_completions`) that
ship with the **`bash-completion`** package. Without it, top-level completion still
works, but navtool can't complete across a `:`. (zsh keeps `:` inside a word, so
it needs nothing extra.)

**Fix:** install `bash-completion` and make sure it's sourced.

### macOS (Homebrew)

Two things to know first:

- `bash-completion@2` requires **bash 4.2+**, but macOS ships bash **3.2**. So you
  also need a modern bash. Check yours with `bash --version`.
- Install both, then source the completion script from `~/.bashrc`:

```sh
brew install bash              # modern bash (4.x/5.x); optional if you already have one
brew install bash-completion@2
```

Add to `~/.bashrc` (before navtool's block is fine):

```bash
[[ -r "$(brew --prefix)/etc/profile.d/bash_completion.sh" ]] \
  && . "$(brew --prefix)/etc/profile.d/bash_completion.sh"
```

If you installed Homebrew's bash and want it as your shell, add it to
`/etc/shells` and run `chsh -s "$(brew --prefix)/bin/bash"` — but that's optional;
you can also just run the newer `bash` when you want completion.

### Debian / Ubuntu

```sh
sudo apt install bash-completion
```

Most distros source it automatically from `/etc/bash.bashrc`. If not, add:

```bash
[ -f /usr/share/bash-completion/bash_completion ] && . /usr/share/bash-completion/bash_completion
```

After installing, open a new terminal and test:

```sh
nav <somename>:<TAB>     # should now list children
```
