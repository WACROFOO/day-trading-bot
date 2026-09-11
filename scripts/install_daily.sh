#!/usr/bin/env bash
# Install (or remove) a macOS launchd agent that runs scripts/day.py at
# 06:55 America/New_York on weekdays. Logging in to the Gateway (paper
# account, port 4002) stays a human step (2FA); the agent only starts the day
# once you have. Single-login design: the desk reads and the executor writes
# on the same paper session, so IBKR_PORT=4002 is set here for the desk.
# The job waits up to two minutes for the network (a Mac waking at 12:55 has
# no DNS for a while — 2026-09-09: "Could not resolve host: github.com" and
# the gap scan and probes failed), pulls the branch (the code changes most
# days), and a failed pull runs what is on disk rather than skipping the day.
#
#   bash scripts/install_daily.sh           # install / refresh
#   bash scripts/install_daily.sh --remove  # uninstall
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd)"
LABEL="com.day-trading-bot.day"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOGDIR="$HOME/Library/Logs/day-trading-bot"
PY="$(command -v python3)"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"; echo "removed $LABEL"; exit 0
fi

# 06:55 ET expressed in the machine's local clock, computed at install time.
# France is ET+6 in summer and ET+6 in winter too (both shift), so this is
# normally 12:55 local; recomputed on every install rather than hard-coded.
read -r HH MM < <("$PY" - <<'PYX'
from datetime import datetime, time
from zoneinfo import ZoneInfo
et = datetime.now(ZoneInfo("America/New_York")).replace(hour=6, minute=55, second=0, microsecond=0)
loc = et.astimezone()
print(loc.hour, loc.minute)
PYX
)
mkdir -p "$LOGDIR" "$(dirname "$PLIST")"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>-lc</string>
    <string>cd "$REPO" &amp;&amp; for i in 1 2 3 4 5 6 7 8 9 10 11 12; do nslookup github.com >/dev/null 2>&amp;1 &amp;&amp; break; echo "waiting for the network (\$i)"; sleep 10; done; (git pull -q origin claude/playbook-pullback-explanation-tg5c33 || echo "pull failed - running what is on disk"); exec "$PY" scripts/day.py</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>EnvironmentVariables</key><dict>
    <key>JOURNAL_DB</key><string>$REPO/data/journal.sqlite</string>
    <key>IBKR_PORT</key><string>4002</string>
    <key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartCalendarInterval</key><array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>$HH</integer><key>Minute</key><integer>$MM</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>$HH</integer><key>Minute</key><integer>$MM</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>$HH</integer><key>Minute</key><integer>$MM</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>$HH</integer><key>Minute</key><integer>$MM</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>$HH</integer><key>Minute</key><integer>$MM</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$LOGDIR/day.out.log</string>
  <key>StandardErrorPath</key><string>$LOGDIR/day.err.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed $LABEL — weekdays at $HH:$MM local (06:55 ET) · logs in $LOGDIR"
echo "log the Gateway in on the PAPER account before then (TWS logged out); the agent does not."
