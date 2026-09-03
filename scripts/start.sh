#!/usr/bin/env bash
# Start the momentum workstation.
#
#   bash scripts/start.sh                # decide automatically
#   bash scripts/start.sh AAPL,TSLA      # live, these symbols
#   bash scripts/start.sh --scan         # live, today's movers
#   bash scripts/start.sh --replay       # recorded session, no network needed
#   bash scripts/start.sh --ibkr         # live IBKR data over TWS, scanner picks the desk
#   bash scripts/start.sh --ibkr CHPT,AEHL   # live IBKR data, these symbols to start
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
  --ibkr)   MODE="ibkr"; SYMBOLS="${2:-}" ;;
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

# ----------------------------------------------------------------- ibkr ----
if [ "$MODE" = "ibkr" ]; then
  head2 "checking TWS (Interactive Brokers)"
  PREFLIGHT=$($PY scripts/ibkr_preflight.py 2>&1); IBKR=$?
  printf '%s\n' "$PREFLIGHT" | sed 's/^/       /'
  case $IBKR in
    0) good "IBKR live data confirmed — read-only" ;;
    1) bad  "ib_async is missing";       note "run:  $PY -m pip install ib_async==2.1.0" ;;
    2) bad  "TWS is not reachable";      note "start TWS, enable the read-only API on port 7496, then rerun" ;;
    3) bad  "IBKR data is DELAYED";      note "the desk refuses delayed data; subscribe to NASDAQ real-time" ;;
    4) warn "no real-time bars arrived"; note "outside 04:00-20:00 ET this is normal; the desk will still connect" ;;
    5) warn "the scanner answered with nothing"; note "the desk starts with the symbols you gave, if any" ;;
    *) bad  "preflight failed: $PREFLIGHT" ;;
  esac
  if [ $IBKR -eq 0 ] || [ $IBKR -ge 4 ]; then
    head2 "starting"
    say "  ${B}Open this in your browser:  http://127.0.0.1:$PORT${O}"
    say "  ${D}live IBKR feed over TWS, read-only — ${SYMBOLS:-scanner picks the desk}${O}"
    say ""
    say "  ${B}This window is now busy running the desk.${O}  Ctrl-C stops it."
    say ""
    # shellcheck disable=SC2086
    PYTHONPATH=src exec $PY -m momentum_platform.dashboard.server \
      --host 127.0.0.1 --port "$PORT" --ibkr "$SYMBOLS" ${DESK_SERVER_ARGS:-}
  fi
  bad "not starting the IBKR desk; fix the point above and run:  bash scripts/start.sh --ibkr"
  exit 1
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
    5) bad  "this Python cannot verify HTTPS certificates"
       note "Your keys and your network are both fine. The request never left"
       note "this computer. Python from python.org ships its own certificate"
       note "store and ignores the macOS keychain, so it must be filled once:"
       note ""
       note "    open the Applications folder, find your Python 3.x folder,"
       note "    and double-click 'Install Certificates.command'"
       note ""
       note "or from a terminal:  $PY -m pip install --upgrade certifi"
       note "then run this again." ;;
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
if [ $LIVE -eq 0 ]; then
  say "  ${D}live: the session rebuilds every 60s; the page follows the newest bar on its own${O}"
  [ -n "${DESK_SERVER_ARGS:-}" ] && say "  ${D}server flags: ${DESK_SERVER_ARGS}${O}"
fi
say ""
say "  ${B}This window is now busy running the desk.${O}"
say "  ${D}It will not accept commands, and anything you type here is ignored.${O}"
say "  ${D}That is normal — it means the desk is up.${O}"
say ""
say "  ${D}To run anything else  open a new tab:  Cmd-T on a Mac, Ctrl-Shift-T on Linux${O}"
say "  ${D}To stop the desk      press Ctrl-C here  (typing 'q' or 'exit' does nothing)${O}"
say ""
# DESK_SERVER_ARGS lets a caller (morning.sh) add server flags such as
# --rescan without every launcher growing its own option parser.
# shellcheck disable=SC2086
PYTHONPATH=src exec $PY -m momentum_platform.dashboard.server \
  --host 127.0.0.1 --port "$PORT" "${ARGS[@]+"${ARGS[@]}"}" ${DESK_SERVER_ARGS:-}
