# `nav` must be a shell function so it can change the current shell's directory
# (a subprocess can't). History navigation (`nav -`/`nav -N` back, `nav +`/`nav
# +N` forward, `nav history`) is handled entirely in-shell by the helpers in
# history.zsh/history.bash; anything else is routed by `navtool __route`, which
# prints a directory to cd into (exit 0) or defers to a plain navtool command
# (exit non-zero). That keeps this wrapper small and legible under `which nav`.
#
# The back/forward patterns require a digit after the sign (`-3`, `+2`) or the
# sign alone (`-`, `+`); option flags like `-h`/`--help`/`--version` have letters
# after the dash, so they fall through to routing instead of being misread as an
# offset. (`<`/`>` can't be used here — the shell parses them as redirections.)
nav() {
  case "$1" in
    -|-[0-9]*|+|+[0-9]*) _nav_go "$1"; return ;;
    history) [ $# -eq 1 ] && { _nav_history_list; return; } ;;
  esac
  local target
  if target=$(navtool __route "$@"); then
    cd "$target" || return
  else
    navtool "$@"
  fi
}
