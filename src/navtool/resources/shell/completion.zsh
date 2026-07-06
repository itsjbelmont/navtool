#compdef nav navtool
#
# Tab-completion for `nav` and `navtool` (zsh).
#
# Source this after nav.sh from your ~/.zshrc (compinit must have run):
#     source /path/to/navtool/shell/completion.zsh
#
# All candidates come from `navtool __complete`, which knows both the command
# tree and the name tree. zsh keeps ':' inside a word, so nested name
# completion (`nav proj:tests:<TAB>`) works out of the box.

_navtool_complete() {
  local nav_flag=""
  [[ "$words[1]" == "nav" ]] && nav_flag="--nav"

  # Args after the command, including the current (possibly empty) word.
  local -a comp_args
  comp_args=("${(@)words[2,CURRENT]}")

  local -a out
  out=("${(@f)$(navtool __complete $nav_flag -- "${comp_args[@]}" 2>/dev/null)}")

  # Filesystem argument → hand off to zsh's path completion.
  if [[ "$out[1]" == $'\x1f__navtool_dirs__' ]]; then
    _path_files -/
    return
  fi
  if [[ "$out[1]" == $'\x1f__navtool_files__' ]]; then
    _path_files -f
    return
  fi

  # Emit candidates verbatim with no suffix (-S '') — never append ':' or a
  # space, so the user types the next separator themselves.
  (( ${#out} )) && compadd -S '' -- "$out[@]"
}

compdef _navtool_complete nav navtool
