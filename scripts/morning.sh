#!/usr/bin/env bash
# The whole pre-market routine in one command.
#
#   bash scripts/morning.sh
#
# Scans the market, grades the catalyst behind each survivor, then opens the
# desk on them. Reads only. Places no orders and sizes no positions.
set -uo pipefail

cd "$(dirname "$0")/.."
G=$'\033[92m'; Y=$'\033[93m'; R=$'\033[91m'; D=$'\033[2m'; B=$'\033[1m'; O=$'\033[0m'
say()   { printf '%s\n' "$*"; }
step()  { printf '\n%s%s%s\n' "$B" "$*" "$O"; }
note()  { printf '  %s%s%s\n' "$D" "$*" "$O"; }

PY=""
for c in python3 python python3.14 python3.13 python3.12 python3.11; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null) || continue
    if [ "${v%%.*}" -eq 3 ] && [ "${v##*.}" -ge 11 ]; then PY="$c"; break; fi
  fi
done
[ -z "$PY" ] && { say "Python 3.11+ not found. Run: bash scripts/setup.sh"; exit 1; }

printf '\n%sMorning routine%s  %s%s%s\n' "$B" "$O" "$D" "$(date '+%A %d %B, %H:%M')" "$O"
note "read-only — nothing here places an order or sizes a position"

# ---------------------------------------------------------------- step 1 ----
step "1 of 3 — scanning the market"
note "roughly 11,000 US equities against price \$2-20, gain >=10%, RVOL >=5x"
note "this takes a minute or two"
SCAN=$($PY scripts/alpaca_watchlist.py --top 8 2>&1); SCAN_RC=$?
echo "$SCAN" | sed 's/^/  /'

# A scan that FAILED is not a scan that found nothing. Reporting a broken
# connection as "a normal quiet morning" would hide an outage behind a
# reassuring sentence, on the one morning you most need to know.
if [ $SCAN_RC -ne 0 ]; then
  step "The scan did not complete"
  say "  ${R}This is not a quiet market — the scan itself failed.${O}"
  say "  ${D}The reason is printed above. Until it is fixed you have no${O}"
  say "  ${D}candidate list, so do not treat the silence as information.${O}"
  say ""
  say "  Check the connection with:  ${B}$PY scripts/verify_alpaca.py${O}"
  say "  Rehearse meanwhile with:    ${B}bash scripts/start.sh --replay${O}"
  say ""
  exit 1
fi

SYMBOLS=$(printf '%s\n' "$SCAN" | tail -1 | tr -d '[:space:]')
case "$SYMBOLS" in
  *[!A-Za-z0-9,.]*|"") SYMBOLS="" ;;
esac

if [ -z "$SYMBOLS" ]; then
  step "Nothing passed the pillars"
  say "  ${Y}That is a normal morning.${O} Ross passes on most days too."
  say "  ${D}Do not widen the filter to manufacture a candidate — that habit"
  say "  is how people lose money.${O}"
  say ""
  say "  Two useful things you can still do:"
  say "    ${B}bash scripts/start.sh --replay${O}   rehearse on a recorded session"
  say "    ${B}bash scripts/morning.sh${O}          run again in 20 minutes"
  say ""
  exit 0
fi

# ---------------------------------------------------------------- step 2 ----
step "2 of 3 — why is each one moving?"
note "news age gives the flame; SEC filings say whether shares are being sold"
$PY scripts/catalyst_score.py $(printf '%s' "$SYMBOLS" | tr ',' ' ')

# ---------------------------------------------------------------- step 3 ----
step "3 of 3 — opening the desk"
say "  Candidates: ${B}$SYMBOLS${O}"
say ""
say "  ${D}Read the verdicts above before you look at a single chart.${O}"
say "  ${D}AVOID means the company is printing shares into the move — the${O}"
say "  ${D}chart cannot rescue that. QUALIFIED earns a look, nothing more.${O}"
say ""
exec bash scripts/start.sh "$SYMBOLS"
