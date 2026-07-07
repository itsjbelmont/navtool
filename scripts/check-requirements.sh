#!/bin/sh
# check-requirements.sh — verify this system has everything NavTool needs.
#
# Usage (from the repo root):
#   sh scripts/check-requirements.sh
#
# Checks the requirements from README.md § Install From Source:
#   required : python3 (3.11+ with sqlite3), pipx, a supported login shell
#   optional : git (for cloning/upgrading), and for bash users the pieces
#              needed for nested tab-completion (bash 4.2+, bash-completion)
#
# Exits 0 when every required check passes (warnings are informational),
# 1 when something marked FAIL needs fixing first.

fails=0
warns=0

if [ -t 1 ]; then
    green='\033[32m' yellow='\033[33m' red='\033[31m' reset='\033[0m'
else
    green='' yellow='' red='' reset=''
fi

ok()   { printf "  ${green}[ ok ]${reset} %s\n" "$1"; }
warn() { printf "  ${yellow}[warn]${reset} %s\n" "$1"; warns=$((warns + 1)); }
fail() { printf "  ${red}[FAIL]${reset} %s\n" "$1"; fails=$((fails + 1)); }

echo "Checking NavTool system requirements..."
echo

# --- Python 3.11+ -----------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
    pyver=$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        ok "Python $pyver (3.11+ required)"
    else
        fail "Python $pyver found, but NavTool requires 3.11+ — upgrade python3"
    fi
    if python3 -c 'import sqlite3' 2>/dev/null; then
        ok "Python sqlite3 module available (used for persistent storage)"
    else
        fail "Python was built without the sqlite3 module — reinstall Python with SQLite support"
    fi
else
    fail "python3 not found on PATH — install Python 3.11+"
fi

# --- pipx --------------------------------------------------------------------
if command -v pipx >/dev/null 2>&1; then
    ok "pipx $(pipx --version 2>/dev/null || echo '(version unknown)')"
else
    fail "pipx not found on PATH — install it first: https://pipx.pypa.io/"
fi

# --- git (needed to clone / upgrade from source) ------------------------------
if command -v git >/dev/null 2>&1; then
    ok "$(git --version)"
else
    warn "git not found — you'll need it to clone the repo and pull upgrades"
fi

# --- Login shell ---------------------------------------------------------------
login_shell=$(basename "${SHELL:-}")
case "$login_shell" in
    zsh)
        ok "login shell is zsh — fully supported"
        ;;
    bash)
        ok "login shell is bash — supported (checking completion extras below)"
        ;;
    '')
        warn "\$SHELL is not set — bootstrap can't auto-detect your shell; use 'navtool bootstrap --shell <zsh|bash>'"
        ;;
    *)
        warn "login shell is '$login_shell' — not supported yet (zsh and bash are); see README.md § Supported Shells"
        ;;
esac

# --- bash extras: nested tab-completion (nav proj:sub<TAB>) --------------------
if [ "$login_shell" = "bash" ]; then
    bashver=$(bash -c 'printf %s "$BASH_VERSION"' 2>/dev/null)
    bashmaj=${bashver%%.*}
    bashrest=${bashver#*.}
    bashmin=${bashrest%%.*}
    if [ "${bashmaj:-0}" -gt 4 ] 2>/dev/null || { [ "${bashmaj:-0}" -eq 4 ] && [ "${bashmin:-0}" -ge 2 ]; } 2>/dev/null; then
        ok "bash $bashver (4.2+ — new enough for bash-completion v2)"
    else
        warn "bash $bashver is older than 4.2 — nested 'name:sub' completion needs a newer bash (macOS: 'brew install bash'); see docs/troubleshooting/bash.md"
    fi

    bc_found=''
    for f in /usr/share/bash-completion/bash_completion /etc/profile.d/bash_completion.sh; do
        [ -r "$f" ] && bc_found=$f && break
    done
    if [ -z "$bc_found" ] && command -v brew >/dev/null 2>&1; then
        f="$(brew --prefix)/etc/profile.d/bash_completion.sh"
        [ -r "$f" ] && bc_found=$f
    fi
    if [ -n "$bc_found" ]; then
        ok "bash-completion found ($bc_found) — nested 'name:sub' completion will work"
    else
        warn "bash-completion package not found — top-level completion still works, but 'name:sub' completion won't; see docs/troubleshooting/bash.md"
    fi
fi

# --- Summary -------------------------------------------------------------------
echo
if [ "$fails" -gt 0 ]; then
    printf "${red}%s required check(s) failed.${reset} Fix the items marked FAIL above, then re-run this script.\n" "$fails"
    exit 1
elif [ "$warns" -gt 0 ]; then
    printf "${green}All required checks passed${reset} (%s warning(s) — some optional functionality may be limited).\n" "$warns"
else
    printf "${green}All checks passed.${reset} You're good to go — continue with README.md § Install From Source.\n"
fi
