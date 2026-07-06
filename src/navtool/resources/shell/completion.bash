# Tab-completion for `nav` and `navtool` (bash).
#
# Source this after nav.sh from your ~/.bashrc:
#     source /path/to/navtool/shell/completion.bash
#
# All candidates come from `navtool __complete`, which knows the command tree
# and the name tree. Nested name completion across ':' works reliably when the
# `bash-completion` package is installed (it supplies the colon-aware helpers
# used below); without it, top-level commands and names still complete.

_navtool_emit() {
  # $1: "--nav" for the nav wrapper, "" for navtool itself.
  # Expects `cur`, `words`, `cword` to be set (colon-aware) by the caller.
  local nav_flag="$1"
  local -a args
  args=("${words[@]:1:cword}")   # everything after the command, incl. current word

  local IFS=$'\n'
  local -a out
  out=($(navtool __complete $nav_flag -- "${args[@]}" 2>/dev/null))

  # Filesystem argument → let the shell enumerate paths.
  case "${out[0]}" in
    $'\x1f__navtool_dirs__')
      if declare -F _filedir >/dev/null 2>&1; then _filedir -d
      else COMPREPLY=($(compgen -d -- "$cur")); compopt -o nospace 2>/dev/null; fi
      return ;;
    $'\x1f__navtool_files__')
      if declare -F _filedir >/dev/null 2>&1; then _filedir
      else COMPREPLY=($(compgen -f -- "$cur")); compopt -o nospace 2>/dev/null; fi
      return ;;
  esac

  # Emit candidates verbatim — never append ':' or a space, so the user adds the
  # next separator. `complete -o nospace` stops bash from adding one either.
  COMPREPLY=("${out[@]}")

  # Realign candidates with what bash considers the current word when it broke
  # the word on ':' (no-op if bash-completion isn't loaded).
  if declare -F __ltrim_colon_completions >/dev/null 2>&1; then
    __ltrim_colon_completions "$cur"
  fi
}

_navtool_words() {
  # Populate cur/words/cword, keeping ':' inside words when possible.
  if declare -F _get_comp_words_by_ref >/dev/null 2>&1; then
    _get_comp_words_by_ref -n : cur words cword
  else
    cur="${COMP_WORDS[COMP_CWORD]}"
    words=("${COMP_WORDS[@]}")
    cword=$COMP_CWORD
  fi
}

_nav_complete() {
  local cur cword; local -a words
  _navtool_words
  _navtool_emit --nav
}

_navtool_complete() {
  local cur cword; local -a words
  _navtool_words
  _navtool_emit ""
}

complete -o nospace -F _nav_complete nav
complete -o nospace -F _navtool_complete navtool
