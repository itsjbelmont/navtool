# navtool directory history (bash).
#
# bash has no `chpwd` hook, so directory changes are recorded from
# `PROMPT_COMMAND` by comparing $PWD against the last value we saw. `nav -` /
# `nav +` then walk that history like a browser's back/forward buttons. All
# state is per shell session and lives only in memory; nothing is written to
# disk. One consequence of recording at prompt time: several `cd`s inside a
# single compound command capture only the final directory.
#
# Written to run on the bash 3.2 that ships with macOS: only positive-offset
# array slicing and a string-valued PROMPT_COMMAND are used.

# Cap on remembered directories (see the note in history.zsh about the preamble).
: ${_NAV_HISTORY_SIZE:=25}

# Visited directories oldest -> newest (`_NAV_STACK`) with a 0-based cursor
# (`_NAV_POS`). `_NAV_LAST_PWD` is the last directory the recorder observed, used
# both to detect changes and to skip the landing of a back/forward jump.
if [ "${#_NAV_STACK[@]}" -eq 0 ]; then
  _NAV_STACK=("$PWD")
  _NAV_POS=0
  _NAV_LAST_PWD="$PWD"
fi

# Prompt hook: fold the new $PWD into the history.
_nav_record() {
  [ "$PWD" = "$_NAV_LAST_PWD" ] && return
  _NAV_LAST_PWD="$PWD"
  # Landing on the current entry (e.g. after a nav </> jump, or `cd .`) isn't a
  # new visit.
  [ "${_NAV_STACK[$_NAV_POS]}" = "$PWD" ] && return
  # A genuinely new directory: drop any forward history, append, trim the oldest
  # entries back to the cap, and point the cursor at the new tail.
  if [ "$_NAV_POS" -lt $(( ${#_NAV_STACK[@]} - 1 )) ]; then
    _NAV_STACK=("${_NAV_STACK[@]:0:$(( _NAV_POS + 1 ))}")
  fi
  _NAV_STACK+=("$PWD")
  if [ "${#_NAV_STACK[@]}" -gt "$_NAV_HISTORY_SIZE" ]; then
    _NAV_STACK=("${_NAV_STACK[@]:$(( ${#_NAV_STACK[@]} - _NAV_HISTORY_SIZE ))}")
  fi
  _NAV_POS=$(( ${#_NAV_STACK[@]} - 1 ))
}

# `nav -` / `nav -N` / `nav +` / `nav +N`: move the cursor N steps (default 1)
# back (`-`) or forward (`+`) and cd there. Clamps at the ends.
_nav_go() {
  local token=$1 dir=${1:0:1} n=${1:1} pos len target
  [ -z "$n" ] && n=1
  case "$n" in
    *[!0-9]*) echo "nav: invalid history offset: $token" >&2; return 1 ;;
  esac
  pos=$_NAV_POS
  len=${#_NAV_STACK[@]}
  if [ "$dir" = "-" ]; then
    target=$(( pos - n )); [ "$target" -lt 0 ] && target=0
  else
    target=$(( pos + n )); [ "$target" -gt $(( len - 1 )) ] && target=$(( len - 1 ))
  fi
  if [ "$target" -eq "$pos" ]; then
    if [ "$dir" = "-" ]; then echo "nav: already at the oldest directory" >&2
    else echo "nav: already at the newest directory" >&2; fi
    return 0
  fi
  if cd -- "${_NAV_STACK[$target]}"; then
    _NAV_POS=$target
    _NAV_LAST_PWD="$PWD"
  else
    return 1
  fi
}

# `nav history`: list the stack oldest -> newest. The current spot is marked `*`;
# other rows show the command that reaches them (`-2` back, `+1` forward).
_nav_history_list() {
  local i tag hl="" reset=""
  # Highlight the current line on a terminal; stay plain when piped or NO_COLOR.
  if [ -t 1 ] && [ -z "$NO_COLOR" ]; then hl=$'\033[1;36m'; reset=$'\033[0m'; fi
  for (( i = 0; i < ${#_NAV_STACK[@]}; i++ )); do
    if [ "$i" -lt "$_NAV_POS" ]; then tag="-$(( _NAV_POS - i ))"
    elif [ "$i" -gt "$_NAV_POS" ]; then tag="+$(( i - _NAV_POS ))"
    else tag="*"; fi
    if [ "$i" -eq "$_NAV_POS" ]; then
      printf '%s%-4s %s%s\n' "$hl" "$tag" "${_NAV_STACK[$i]}" "$reset"
    else
      printf '%-4s %s\n' "$tag" "${_NAV_STACK[$i]}"
    fi
  done
}

# Record on every prompt, without clobbering an existing PROMPT_COMMAND.
case ";${PROMPT_COMMAND};" in
  *";_nav_record;"*) ;;
  *) PROMPT_COMMAND="_nav_record${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac
