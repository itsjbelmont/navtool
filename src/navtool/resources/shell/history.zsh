# navtool directory history (zsh).
#
# Records every directory change through zsh's `chpwd` hook — so plain `cd`,
# `pushd`, IDE jumps and `nav <name>` are all captured — and lets `nav -` /
# `nav +` walk that history like a browser's back/forward buttons. All state is
# per shell session and lives only in memory (a shell array); nothing is written
# to disk and other shells are unaffected.

# Cap on remembered directories. The `navtool init` preamble sets this from your
# config; the fallback here only matters if this file is sourced on its own.
: ${_NAV_HISTORY_SIZE:=25}

# Visited directories oldest -> newest (`_NAV_STACK`) with a 1-based cursor at
# the current position (`_NAV_POS`). `_NAV_SUPPRESS` tells the hook to ignore the
# `cd` that our own back/forward jump triggers. Seed once so a re-source keeps
# the existing history.
typeset -ga _NAV_STACK
typeset -gi _NAV_POS _NAV_SUPPRESS
if (( ${#_NAV_STACK} == 0 )); then
  _NAV_STACK=("$PWD")
  _NAV_POS=1
  _NAV_SUPPRESS=0
fi

# chpwd hook: fold the new $PWD into the history.
_nav_record() {
  if (( _NAV_SUPPRESS )); then
    _NAV_SUPPRESS=0
    return
  fi
  # A no-op change that lands on the current entry (e.g. `cd .`) isn't a visit.
  [[ ${_NAV_STACK[$_NAV_POS]} == "$PWD" ]] && return
  # A genuinely new directory: drop any forward history, append, trim the oldest
  # entries back to the cap, and point the cursor at the new tail.
  (( _NAV_POS < ${#_NAV_STACK} )) && _NAV_STACK=("${(@)_NAV_STACK[1,_NAV_POS]}")
  _NAV_STACK+=("$PWD")
  (( ${#_NAV_STACK} > _NAV_HISTORY_SIZE )) && \
    _NAV_STACK=("${(@)_NAV_STACK[-_NAV_HISTORY_SIZE,-1]}")
  _NAV_POS=${#_NAV_STACK}
}

# `nav -` / `nav -N` / `nav +` / `nav +N`: move the cursor N steps (default 1)
# back (`-`) or forward (`+`) and cd there. Clamps at the ends.
_nav_go() {
  local token=$1 dir=${1[1]} n=${1[2,-1]}
  [[ -z $n ]] && n=1
  if [[ $n != <-> ]]; then
    print -ru2 -- "nav: invalid history offset: $token"
    return 1
  fi
  local pos=$_NAV_POS len=${#_NAV_STACK} target
  if [[ $dir == "-" ]]; then
    target=$(( pos - n )); (( target < 1 )) && target=1
  else
    target=$(( pos + n )); (( target > len )) && target=len
  fi
  if (( target == pos )); then
    [[ $dir == "-" ]] && print -ru2 -- "nav: already at the oldest directory" \
                      || print -ru2 -- "nav: already at the newest directory"
    return 0
  fi
  _NAV_SUPPRESS=1
  if cd -- "${_NAV_STACK[$target]}"; then
    _NAV_POS=$target
  else
    _NAV_SUPPRESS=0
    return 1
  fi
}

# `nav history`: list the stack oldest -> newest. The current spot is marked `*`;
# other rows show the command that reaches them (`-2` back, `+1` forward).
_nav_history_list() {
  local i tag hl="" reset=""
  # Highlight the current line on a terminal; stay plain when piped or NO_COLOR.
  if [[ -t 1 && -z $NO_COLOR ]]; then hl=$'\e[1;36m'; reset=$'\e[0m'; fi
  for (( i = 1; i <= ${#_NAV_STACK}; i++ )); do
    if (( i < _NAV_POS )); then tag="-$(( _NAV_POS - i ))"
    elif (( i > _NAV_POS )); then tag="+$(( i - _NAV_POS ))"
    else tag="*"; fi
    if (( i == _NAV_POS )); then
      printf '%s%-4s %s%s\n' "$hl" "$tag" "${_NAV_STACK[$i]}" "$reset"
    else
      printf '%-4s %s\n' "$tag" "${_NAV_STACK[$i]}"
    fi
  done
}

# Register the recorder as a chpwd hook (falling back to the raw array).
autoload -Uz add-zsh-hook 2>/dev/null
if (( $+functions[add-zsh-hook] )); then
  add-zsh-hook chpwd _nav_record
elif [[ -z ${chpwd_functions[(r)_nav_record]} ]]; then
  chpwd_functions+=(_nav_record)
fi
