#!/usr/bin/env bash
# Restart the trading day on the code on disk — the second half of the one
# command after an update (owner, 2026-10-09: "including if a trading day
# already started"):
#
#   cd ~/day-trading-bot && bash scripts/update.sh && bash scripts/restart.sh
#
#   * no day running            → starts it, as scripts/go.sh does after its update;
#   * a day running, bot flat   → stops it cleanly (SIGINT, the same as Ctrl-C:
#                                 the bot and the desk stop, the day is settled at
#                                 the next start), waits for those processes to be
#                                 gone, and starts the day again on the new code;
#   * a day running and the bot holding a position or a working entry
#                               → the day is NOT stopped: a stopped runner leaves
#                                 a monitored stop unwatched. The desk alone
#                                 restarts on the new code (the screens update);
#                                 run this again once the bot is flat.
#
# Run it in a NEW terminal tab: the day then runs in that tab. Wrapped in main()
# so an update that rewrites this file cannot change it mid-run (bash reads a
# script as it goes). ${1+"$@"} keeps macOS bash 3.2 happy with no arguments.
set -uo pipefail

DAY_RE="python.*scripts/day\.py"                 # the day command — not an editor holding the file
DESK_RE="momentum_platform\.dashboard\.server --host 127\.0\.0\.1 --port .* --ibkr"

say()  { printf '  %s\n' "$1"; }
warn() { printf '  \033[93m!!\033[0m   %s\n' "$1"; }

pids_of() { pgrep -if "$1" 2>/dev/null | tr '\n' ' '; }

alive_pid() {            # running, and not a zombie its parent has not reaped yet
  local st
  st=$(ps -o stat= -p "$1" 2>/dev/null) || return 1
  case "$st" in Z*|"") return 1 ;; esac
  return 0
}

wait_pids() {            # seconds, pids…: true once none of them is alive
  local limit=$1 i=0 p alive
  shift
  while [ "$i" -lt "$limit" ]; do
    alive=""
    for p in "$@"; do alive_pid "$p" && alive=1; done
    [ -z "$alive" ] && return 0
    sleep 1; i=$((i + 1))
  done
  return 1
}

start_day() {
  exec env IBKR_PORT="${IBKR_PORT:-4002}" python3 scripts/day.py ${1+"$@"}
}

main() {
  cd "$(dirname "$0")/.." || exit 1
  local day_pids desk_pids rc
  day_pids=$(pids_of "$DAY_RE")
  if [ -z "$day_pids" ]; then
    say "no trading day running — starting it on the code on disk"
    start_day ${1+"$@"}
  fi
  python3 scripts/exercise.py busy
  rc=$?
  if [ "$rc" -ne 0 ]; then
    if [ "$rc" -eq 3 ]; then
      warn "the bot holds a position or a working entry — the day keeps running"
    else
      warn "could not read the ledger (exit $rc) — the day keeps running"
    fi
    say "restarting the desk alone on the new code; run this again once the bot is flat"
    exec python3 scripts/day.py --restart-desk
  fi
  say "stopping the running day cleanly (the same as Ctrl-C)…"
  # shellcheck disable=SC2086
  kill -INT $day_pids 2>/dev/null
  # shellcheck disable=SC2086
  if ! wait_pids "${RESTART_WAIT_S:-90}" $day_pids; then
    warn "the day did not stop within ${RESTART_WAIT_S:-90} s — nothing started; stop it with Ctrl-C in its tab, then run this again"
    exit 1
  fi
  desk_pids=$(pids_of "$DESK_RE")                # a desk left behind would hold client 27
  if [ -n "$desk_pids" ]; then
    # shellcheck disable=SC2086
    kill -INT $desk_pids 2>/dev/null
    # shellcheck disable=SC2086
    if ! wait_pids 30 $desk_pids; then
      kill -TERM $desk_pids 2>/dev/null
      wait_pids 15 $desk_pids || { warn "the desk did not stop — nothing started"; exit 1; }
    fi
  fi
  if [ -n "$(pids_of "$DAY_RE")" ]; then
    say "the scheduled job started the day again by itself, on the new code — nothing more to do"
    exit 0
  fi
  say "stopped — starting the day again on the new code"
  start_day ${1+"$@"}
}

main ${1+"$@"}
