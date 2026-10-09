#!/usr/bin/env bash
# One command: update the code, then bring the trading day up (owner,
# 2026-10-09: "update command and day start at one command").
#
#   bash scripts/go.sh                  # update, then scripts/day.py
#   bash scripts/go.sh --symbols X,Y    # any day.py flag passes through
#
# 1. scripts/update.sh — your uncommitted edits are stashed and your commits
#    backed up before anything moves. If it fails (no network, GitHub down),
#    the day starts on the code on disk, as the scheduled 06:55 job does.
# 2. scripts/day.py, on the paper Gateway's port unless IBKR_PORT says
#    otherwise — whatever this hour calls for: the bot's day 06:55–11:30 ET,
#    the desk alone at any other time, until Ctrl+C.
#    A day already running is never replaced: you get its link, and its desk
#    is restarted on the new code when the bot is not trading (it records
#    nothing then); during the bot's window you are told the command instead.
#
# Everything sits in main(), read whole before it runs: the update rewrites
# this very file, and bash reads a script as it goes.
set -uo pipefail

main() {
  cd "$(dirname "$0")/.." || exit 1
  if ! GO_SH=1 bash scripts/update.sh; then
    printf '\n  \033[93m!!\033[0m   update failed — starting on the code on disk\n'
  fi
  # ${1+"$@"}: macOS's bash 3.2 calls an empty "$@" unbound under set -u
  exec env IBKR_PORT="${IBKR_PORT:-4002}" python3 scripts/day.py ${1+"$@"}
}
main ${1+"$@"}
