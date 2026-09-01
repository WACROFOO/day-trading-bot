#!/usr/bin/env bash
# Start the momentum workstation.
#
#   bash scripts/start.sh                # decide automatically
#   bash scripts/start.sh AAPL,TSLA      # live, these symbols
#   bash scripts/start.sh --scan         # live, today's movers
#   bash scripts/start.sh --replay       # recorded session, no network needed
#
# Checks Alpaca first. If the live feed is not available it says exactly why
# and opens the recorded session instead, so the desk always comes up.
set -uo pipefail

cd "$(dirname "$0")/.."
G=$'\033[92m'; Y=$'\033[93m'; R=$'\033[91m'; D=$'\033[2m'; B=$'\033[1m'; O=$'\033[0m'
say()  { printf '%s\n' "$*"; }
head2(){ printf '\n%s%s%s\n' "$D" "── $* ─────────────────────────" "$O"; }
good() { printf '  %sok%s   %s\n' "$G" "$O" "$*"; }
warn() { printf '  %swarn%s %s\n' "$Y" "$O" "$*"; }
bad()  { printf '  %sxx%s   %s\n' "$R" "$O" "$*"; }
note() { printf '       %s%s%s\n' "$D" "$*" "$O"; }

MODE="auto"; SYMBOLS=""
case "${1:-}" in
  --replay) MODE="replay" ;;
  --scan)   MODE="scan" ;;
  "")       : ;;
  -*)       say "unknown option: $1"; exit 2 ;;
  *)        MODE="symbols"; SYMBOLS="$1" ;;
esac

printf '\n%sMomentum workstation%s\n' "$B" "$O"

# ---------------------------------------------------------------- python ----
PY=""
for c in python3 python python3.13 python3.12 python3.11; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null) || continue
    if [ "${v%%.*}" -eq 3 ] && [ "${v##*.}" -ge 11 ]; then PY="$c"; break; fi
  fi
done
if [ -z "$PY" ]; then
  bad "Python 3.11+ not found. Install it, then run: bash scripts/setup.sh"
  exit 1
fi

# ------------------------------------------------------------------ port ----
head2 "port"
PORT=8787
for try in 8787 8788 8789 8790; do
  if $PY - "$try" <<'PYPORT' >/dev/null 2>&1
import socket, sys
s = socket.socket()
try:
    s.bind(("127.0.0.1", int(sys.argv[1])))
finally:
    s.close()
PYPORT
  then PORT=$try; break; fi
done
if [ "$PORT" != 8787 ]; then
  warn "port 8787 is already in use — using $PORT instead"
  note "something else is on 8787, most likely a desk you already started"
else
  good "port 8787 is free"
fi

# --------------------------------------------------------------- alpaca ----
if [ "$MODE" = "replay" ]; then
  LIVE=1
  head2 "data source"
  good "recorded session (you asked for --replay)"
else
  head2 "checking the live feed"
  PREFLIGHT=$($PY scripts/preflight.py 2>&1); LIVE=$?
  case $LIVE in
    0) good "$PREFLIGHT" ;;
    1) warn "no credentials on this machine yet"
       note "run 'bash scripts/setup.sh' once to add them" ;;
    2) bad  "Alpaca rejected the key pair"
       note "$PREFLIGHT"
       note "generate a fresh PAPER pair and re-run: bash scripts/setup.sh" ;;
    3) bad  "this network cannot reach Alpaca"
       note "$PREFLIGHT"
       note "a VPN, company network or cloud container will do this;"
       note "your keys are probably fine — try again on home wifi" ;;
    *) bad  "$PREFLIGHT" ;;
  esac
fi

# --------------------------------------------------------------- symbols ----
ARGS=()
if [ $LIVE -eq 0 ]; then
  if [ "$MODE" = "scan" ]; then
    head2 "scanning for today's movers"
    SYMBOLS=$($PY scripts/alpaca_watchlist.py --top 6 2>/dev/null | tail -1)
    if [ -z "$SYMBOLS" ]; then
      warn "nothing passed the pillars right now — that is a normal morning"
      note "falling back to two liquid names so you can learn the layout"
      SYMBOLS="AAPL,TSLA"
    else
      good "candidates: $SYMBOLS"
    fi
  elif [ -z "$SYMBOLS" ]; then
    SYMBOLS="AAPL,TSLA,NVDA"
  fi
  ARGS=(--alpaca "$SYMBOLS")
  BANNER="live IEX feed — $SYMBOLS"
else
  ARGS=()
  BANNER="recorded session (no network needed)"
  if [ "$MODE" != "replay" ]; then
    head2 "falling back"
    say "  The live feed is not available, so the desk will open on a"
    say "  ${B}recorded trading session${O} instead. Every card, chart, scanner"
    say "  and the verdict engine work exactly the same — only the data is"
    say "  from a saved day rather than from today. This is the right place"
    say "  to learn the platform while you sort the connection out."
  fi
fi

# ----------------------------------------------------------------- serve ----
head2 "starting"
say "  ${B}Open this in your browser:  http://127.0.0.1:$PORT${O}"
say "  ${D}$BANNER${O}"
say "  ${D}Leave this terminal window open. Press Ctrl-C here to stop the desk.${O}"
say ""
PYTHONPATH=src exec $PY -m momentum_platform.dashboard.server \
  --host 127.0.0.1 --port "$PORT" "${ARGS[@]+"${ARGS[@]}"}"
