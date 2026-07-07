# `nav` must be a shell function so it can change the current shell's directory
# (a subprocess can't). All routing lives in `navtool __route`, which prints a
# directory to cd into (exit 0) or defers to a plain navtool command (exit
# non-zero) — so this wrapper stays small and legible under `which nav`.
nav() {
  local target
  if target=$(navtool __route "$@"); then
    cd "$target" || return
  else
    navtool "$@"
  fi
}
