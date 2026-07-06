nav() {
  # No args, help, or version → pass straight through to navtool.
  case "$1" in
    ""|-h|--help|--version)
      navtool "$@"
      return
      ;;
  esac

  # Discover navtool's top-level subcommands (add, rm, mv, ls, path, ...).
  local cmds
  cmds=$(navtool --help | awk '
    /Commands:/ {f=1; next}
    f && /^[[:space:]]{2}[a-z]/ {print $1}
  ')

  # Known subcommand → pass through to navtool.
  if echo "$cmds" | grep -qx "$1"; then
    navtool "$@"
    return
  fi

  # Single non-command argument → treat it as a name to navigate to.
  # `navtool path` accepts both bare `name` and nested `a:b:c` forms and exits
  # non-zero when nothing matches, in which case we fall back to a plain `cd`
  # so `nav <path>` still behaves like `cd <path>`.
  if [ $# -eq 1 ]; then
    local target
    if target=$(navtool path "$1" 2>/dev/null); then
      cd "$target" || return
    else
      cd "$1"
    fi
    return
  fi

  # Anything else → pass through to navtool.
  navtool "$@"
}
