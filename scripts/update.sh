#!/usr/bin/env bash
# Pull the latest version of the desk, safely.
#
#   bash scripts/update.sh
#
# Never loses work: local commits are snapshotted to a backup branch and
# uncommitted edits are stashed before anything moves. Your .env is
# git-ignored, so nothing here can touch your credentials.
set -uo pipefail

cd "$(dirname "$0")/.."
G=$'\033[92m'; Y=$'\033[93m'; R=$'\033[91m'; D=$'\033[2m'; B=$'\033[1m'; O=$'\033[0m'
good() { printf '  %sok%s   %s\n' "$G" "$O" "$*"; }
warn() { printf '  %swarn%s %s\n' "$Y" "$O" "$*"; }
bad()  { printf '  %sxx%s   %s\n' "$R" "$O" "$*"; }
note() { printf '       %s%s%s\n' "$D" "$*" "$O"; }

BRANCH="${1:-claude/playbook-pullback-explanation-tg5c33}"   # the working branch (CLAUDE.md, "Git")
printf '\n%sUpdating the desk%s  %s%s%s\n\n' "$B" "$O" "$D" "$BRANCH" "$O"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  bad "This is not a git folder. Are you in the right directory?"
  note "try: cd ~/day-trading-bot"
  exit 1
fi

# -- keep everything the user has ---------------------------------------------
STAMP=$(date +%Y%m%d-%H%M%S)

if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  git stash push -u -m "before update $STAMP" >/dev/null 2>&1 \
    && good "your uncommitted edits are stashed as 'before update $STAMP'" \
    && note "get them back with: git stash pop"
fi

CURRENT=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  git branch "backup-$STAMP" >/dev/null 2>&1 \
    && good "your current commits are saved on branch backup-$STAMP"
fi

# -- fetch with retry ----------------------------------------------------------
delay=2
for attempt in 1 2 3 4 5; do
  if git fetch origin "$BRANCH" >/dev/null 2>&1; then
    good "fetched $BRANCH from GitHub"
    FETCHED=1
    break
  fi
  if [ $attempt -lt 5 ]; then
    warn "fetch failed, retrying in ${delay}s (attempt $attempt of 5)"
    sleep $delay
    delay=$((delay * 2))
  fi
done
if [ -z "${FETCHED:-}" ]; then
  bad "could not reach GitHub after 5 tries. Check your connection and retry."
  exit 1
fi

# -- move onto it --------------------------------------------------------------
BEFORE=$(git rev-parse --short HEAD 2>/dev/null || echo "none")
if git checkout -B "$BRANCH" "origin/$BRANCH" >/dev/null 2>&1; then
  AFTER=$(git rev-parse --short HEAD)
  if [ "$BEFORE" = "$AFTER" ]; then
    good "already up to date at $AFTER"
  else
    good "updated $BEFORE -> $AFTER"
    printf '\n%s%s%s\n' "$D" "what changed:" "$O"
    git log --oneline "$BEFORE..$AFTER" 2>/dev/null | head -10 | sed 's/^/       /'
  fi
else
  bad "could not switch to $BRANCH"
  note "your work is safe on backup-$STAMP"
  exit 1
fi

# -- prove the credentials survived --------------------------------------------
if [ -f .env ]; then
  good ".env is untouched (git-ignored, as it should be)"
else
  warn "no .env found — run 'bash scripts/setup.sh' to add your keys"
fi

# scripts/go.sh runs this, then the day: the hints below would only repeat it.
if [ -z "${GO_SH:-}" ]; then
  printf '\n%sUpdate and start in one command next time:%s  bash scripts/go.sh\n' "$B" "$O"
  printf '%sThe platform alone:%s  IBKR_PORT=4002 python3 scripts/day.py   (any hour; Ctrl+C stops it)\n' "$B" "$O"
  printf '%sAlready running?%s  python3 scripts/day.py --restart-desk   (the desk restarts on the new\n' "$B" "$O"
  printf 'code, the bot keeps running). The page loads the new files at once; the desk runs its new\n'
  printf 'code only after a restart, and the page says RESTART THE DESK until then.\n\n'
fi
