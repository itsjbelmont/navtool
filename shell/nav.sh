nav() {
  # Pass through help and flags immediately
  case "$1" in
    ""|-h|--help)
      navtool "$@"
      return
      ;;
  esac

  cmds=$(navtool --help | awk '
    /Commands:/ {f=1; next}
    f && /^[[:space:]]{2}[a-z]/ {print $1}
  ')

  # Known command → pass through
  if echo "$cmds" | grep -qx "$1"; then
    navtool "$@"
    return
  fi

  # Single non-command argument → treat as key
  if [ $# -eq 1 ]; then
    target=$(navtool path "$1") || return
    cd "$target" || return
    return
  fi

  # Fallback
  navtool "$@"
}
