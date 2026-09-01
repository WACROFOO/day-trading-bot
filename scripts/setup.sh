#!/usr/bin/env bash
# One-command setup for the momentum workstation.
#
#   bash scripts/setup.sh
#
# Asks for your Alpaca paper keys, writes them to a git-ignored .env file,
# then runs the connection check. Reads only — never places an order.
set -uo pipefail

cd "$(dirname "$0")/.."
G=$'\033[92m'; Y=$'\033[93m'; R=$'\033[91m'; D=$'\033[2m'; B=$'\033[1m'; O=$'\033[0m'

say()  { printf '%s\n' "$*"; }
head2() { printf '\n%s%s%s\n' "$D" "── $* ─────────────────────────" "$O"; }
good() { printf '  %sok%s   %s\n' "$G" "$O" "$*"; }
bad()  { printf '  %sxx%s   %s\n' "$R" "$O" "$*"; }
note() { printf '       %s%s%s\n' "$D" "$*" "$O"; }

printf '\n%sMomentum workstation setup%s\n' "$B" "$O"
say "${D}Nothing here costs money. Nothing here places a real order.${O}"

# ---------------------------------------------------------------- python ----
head2 "1. Python"
PY=""
# Prefer the plain "python3"/"python" the user would pip-install into;
# only fall back to a versioned binary if neither is new enough.
for c in python3 python python3.13 python3.12 python3.11; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null) || continue
    major=${v%%.*}; minor=${v##*.}
    if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then PY="$c"; break; fi
  fi
done
if [ -z "$PY" ]; then
  bad "Python 3.11 or newer was not found."
  note "macOS:   brew install python@3.12"
  note "Windows: install from https://python.org (tick 'Add to PATH')"
  note "Linux:   sudo apt install python3.12"
  exit 1
fi
good "using $PY ($($PY -c 'import sys;print(sys.version.split()[0])'))"

# ------------------------------------------------------------------ .env ----
head2 "2. Credentials"
if [ -f .env ] && grep -q '^ALPACA_SECRET_KEY=.\+' .env 2>/dev/null; then
  existing=$(grep '^ALPACA_KEY_ID=' .env | cut -d= -f2-)
  good ".env already holds key ${existing:0:4}…${existing: -4}"
  printf '       replace it? [y/N] '
  read -r ans
  case "$ans" in [Yy]*) : ;; *) SKIP_KEYS=1 ;; esac
fi

if [ -z "${SKIP_KEYS:-}" ]; then
  say ""
  say "  Get free paper keys at ${B}https://alpaca.markets${O}"
  say "  ${D}Dashboard → make sure the toggle says 'Paper Trading' → API Keys${O}"
  say "  ${D}→ Generate New Key. The secret is shown once, so copy it now.${O}"
  say ""
  printf '  Key ID (starts with PK): '
  read -r KEY_ID
  printf '  Secret Key (hidden as you type or paste): '
  read -rs SECRET; echo

  KEY_ID=$(printf '%s' "$KEY_ID" | tr -d '[:space:]')
  SECRET=$(printf '%s' "$SECRET" | tr -d '[:space:]')

  if [ -z "$KEY_ID" ] || [ -z "$SECRET" ]; then
    bad "Both values are required. Run the script again."
    exit 1
  fi
  case "$KEY_ID" in
    PK*) : ;;
    AK*) bad "That is a LIVE key (starts AK). Switch the dashboard toggle to"
         note "Paper Trading and generate a new pair, then run this again."
         exit 1 ;;
    *)   printf '  %swarn%s  Key ID does not start with PK. Continuing anyway.\n' "$Y" "$O" ;;
  esac

  umask 177
  cat > .env <<ENV
# Local credentials. Git-ignored — never commit, share, or paste these.
ALPACA_KEY_ID=$KEY_ID
ALPACA_SECRET_KEY=$SECRET
ALPACA_FEED=iex
ALPACA_TRADING_BASE=https://paper-api.alpaca.markets
ENV
  chmod 600 .env
  unset SECRET
  good "wrote .env (readable only by you)"
fi

# ---------------------------------------------------------------- ignore ----
head2 "3. Making sure the keys can never be committed"
if git check-ignore -q .env 2>/dev/null; then
  good ".env is git-ignored"
else
  bad ".env is NOT ignored by git — stop and fix .gitignore before committing."
  exit 1
fi
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  bad ".env is TRACKED by git. Run: git rm --cached .env"
  exit 1
fi
good ".env is untracked"

# ----------------------------------------------------------------- tests ----
head2 "4. Checking the code runs on your machine"
PYTEST=""
if $PY -m pytest --version >/dev/null 2>&1; then PYTEST="$PY -m pytest"
elif command -v pytest >/dev/null 2>&1;   then PYTEST="pytest"
fi
if [ -z "$PYTEST" ]; then
  printf '  %swarn%s  pytest is not installed, so the test suite was skipped.\n' "$Y" "$O"
  note "optional — install it with: $PY -m pip install pytest"
elif $PYTEST -q >/tmp/desk-tests.$$ 2>&1; then
  good "test suite passes ($(grep -Eo '[0-9]+ passed' /tmp/desk-tests.$$ | tail -1))"
  rm -f /tmp/desk-tests.$$
else
  printf '  %swarn%s  the test suite did not come back clean:\n' "$Y" "$O"
  grep -E 'ModuleNotFoundError|failed|ERROR ' /tmp/desk-tests.$$ | sort -u | head -6 \
    | while IFS= read -r line; do note "$line"; done
  note "full detail: $PYTEST -q"
  note "a missing module only affects older tests; the desk itself needs no extras."
  rm -f /tmp/desk-tests.$$
fi

# --------------------------------------------------------------- connect ----
head2 "5. Talking to Alpaca"
$PY scripts/verify_alpaca.py
rc=$?

head2 "Next"
if [ $rc -eq 0 ]; then
  say "  Your desk is connected. Start it with real symbols:"
  say ""
  say "    ${B}PYTHONPATH=src $PY -m momentum_platform.dashboard.server --alpaca AAPL,TSLA${O}"
  say ""
  say "  Then open ${B}http://127.0.0.1:8787${O} in your browser."
  say "  To find today's movers instead of naming symbols yourself:"
  say ""
  say "    ${B}$PY scripts/alpaca_watchlist.py --top 8${O}"
  say ""
  say "  ${D}The full walkthrough is in docs/alpaca-setup.md, Step 4 onward.${O}"
else
  say "  The FAIL above names its own fix. The two usual causes:"
  say ""
  say "  ${B}401 / forbidden${O}  the key or secret is wrong. Generate a fresh pair"
  say "                  in the Alpaca dashboard (Paper Trading toggle on),"
  say "                  then re-run this script and paste the new values."
  say "  ${B}could not reach${O}  a network, proxy, VPN or firewall is blocking"
  say "                  api.alpaca.markets. Try again off the corporate"
  say "                  network, or with the VPN switched off."
  say ""
  say "  Re-run any time with: ${B}bash scripts/setup.sh${O}"
fi
say ""
exit $rc
