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

  # A sentinel may stand alone (a pure filesystem argument) or sit alongside real
  # candidates (a bare `nav <word>` that could be a name *or* a directory). So
  # sift every line: collect plain candidates, and note which path completions to
  # union in. `_path_files` merges into the same menu as the compadd below.
  local -a cands
  local want_dirs="" want_files="" line
  for line in "$out[@]"; do
    case "$line" in
      $'\x1f__navtool_dirs__')  want_dirs=1 ;;
      $'\x1f__navtool_files__') want_files=1 ;;
      "") ;;  # command substitution yields one empty element for no output
      *) cands+=("$line") ;;
    esac
  done

  # Emit candidates verbatim with no suffix (-S '') — never append ':' or a
  # space, so the user types the next separator themselves.
  (( ${#cands} )) && compadd -S '' -- "$cands[@]"
  [[ -n "$want_dirs" ]] && _path_files -/
  [[ -n "$want_files" ]] && _path_files -f
}

compdef _navtool_complete nav navtool
