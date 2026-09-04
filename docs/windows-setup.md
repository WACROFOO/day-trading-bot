# Running the desk on Windows

The Python is portable and runs natively on Windows; only the `.sh` launchers
do not. `scripts/start.ps1` is the PowerShell equivalent of `scripts/start.sh`.
Nothing here places an order, and the IBKR connection is opened read-only.

## 1. Prerequisites

- **Python 3.11 or newer** from python.org. During installation tick
  **Add python.exe to PATH**.
- **Git for Windows** from git-scm.com.
- **TWS** (Trader Workstation) installed and logged in on this same machine.

Check both are on the PATH:

```
python --version
git --version
```

If `python` opens the Microsoft Store instead of printing a version, Windows'
app alias is shadowing it: Settings, Apps, Advanced app settings, App execution
aliases, and turn off both `python.exe` entries.

## 2. Clone and install

```
cd $HOME
git clone https://github.com/WACROFOO/day-trading-bot.git
cd day-trading-bot
git checkout claude/ross-trading-mastery-setup-q4cz29
python -m pip install -r requirements.txt
```

`requirements.txt` already pulls `tzdata` on Windows, which the desk needs for
the ET clock, and `ib_async` for the IBKR connection.

## 3. TWS settings

In TWS: **Edit, Global Configuration, API, Settings**

- Enable ActiveX and Socket Clients: **ON**
- Read-Only API: **ON**
- Socket port: whatever the dialog shows. **7496 is the live-account port and
  7497 is the paper-account port**; IB Gateway uses 4001 and 4002. The desk
  defaults to 7496, so pass `-IbkrPort 7497` if you are logged into paper.
- Trusted IPs: `127.0.0.1`

Then confirm the data path before starting the desk:

```
python scripts\ibkr_preflight.py
```

The last line must read `OK - live, read-only, real-time bars flowing, scanner
answering`. Every failure prints what to fix.

## 4. Start the desk

```
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr
```

or with names you already chose:

```
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr -Symbols CHPT,AEHL
```

and to learn the layout with no market data at all:

```
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Replay
```

Open the address it prints. Ctrl-C in that window stops the desk.

### If PowerShell refuses to run the script

A managed machine may block scripts outright, in which case the two commands
below do the same thing with no script involved:

```
$env:PYTHONPATH="src"
python -m momentum_platform.dashboard.server --host 127.0.0.1 --port 8787 --ibkr ""
```

Pass symbols by putting them in the quotes: `--ibkr "CHPT,AEHL"`.

### "nothing is listening on 127.0.0.1:7496"

The desk found no TWS on this machine. In order of likelihood:

1. **TWS is not running here.** It must be installed, running and logged in on
   the same machine as the desk. Having it on another computer does not count.
2. **You are on a paper login.** Paper TWS listens on **7497**, not 7496.
   Check the port in the API Settings dialog and rerun with
   `-Ibkr -IbkrPort 7497`.
3. **The API is off.** Edit, Global Configuration, API, Settings: Enable
   ActiveX and Socket Clients must be ticked.

To see what is actually listening:

```
netstat -ano | findstr LISTENING | findstr 749
```

No output means no TWS API port is open on this machine.

### Using the TWS on another computer

If TWS runs on a different machine on the same network, point the desk at it
and let that TWS trust this one:

```
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr -IbkrHost 192.168.1.42
```

On the machine running TWS, add this computer's IP under **API, Settings,
Trusted IPs**, and make sure a firewall is not blocking the port. The
connection stays read-only either way.

## 5. The other commands

The bash wrappers have Python behind them, so use that directly:

| Instead of | Run |
|---|---|
| `./now` | `python scripts\now.py` |
| `./now --scan` | `python scripts\now.py --scan` |
| `bash scripts/setup.sh` | copy `.env.example` to `.env` and edit it |
| `bash scripts/start.sh --ibkr` | `powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr` |

## 6. Claude Code on this machine

```
npm install -g @anthropic-ai/claude-code
cd $HOME\day-trading-bot
claude
```

It reads `CLAUDE.md` from the repo root on its own, so it starts with the
project's rules loaded. Keep the desk in one PowerShell window and Claude Code
in another.

## Notes

- `.env` is git-ignored and never leaves the machine. Do not commit it.
- The desk serves on `127.0.0.1` only; nothing is exposed to the network.
- WSL is not needed. If you use it anyway, TWS still runs on Windows, so set
  `IBKR_HOST` to the Windows host address rather than `127.0.0.1`, and add that
  address to TWS's trusted IPs.
