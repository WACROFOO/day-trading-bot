<#
    Momentum workstation launcher for Windows PowerShell.

    The Python is portable; only the bash launchers are not, so this mirrors
    scripts/start.sh: find a usable Python, pick a free port, run the IBKR
    preflight, then serve the desk on 127.0.0.1. It places no orders, and the
    IBKR connection it starts is read-only.

        powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr
        powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr -Symbols CHPT,AEHL
        powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr -IbkrPort 7497
        powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Replay

    -IbkrPort defaults to 7496, which is TWS's LIVE-account port. A paper
    login listens on 7497; IB Gateway uses 4001 live and 4002 paper.
    -IbkrHost defaults to this machine. Point it at another machine's TWS only
    if that TWS lists this machine's address under Trusted IPs.
#>
[CmdletBinding()]
param(
    [switch]$Ibkr,
    [switch]$Replay,
    [string]$Symbols = "",
    [int]$Port = 0,
    [int]$IbkrPort = 0,
    [string]$IbkrHost = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Say  ($m) { Write-Host $m }
function Head ($m) { Write-Host "" ; Write-Host ("-- " + $m + " ----------------------------") -ForegroundColor DarkGray }
function Good ($m) { Write-Host "  ok   $m" -ForegroundColor Green }
function Warn ($m) { Write-Host "  warn $m" -ForegroundColor Yellow }
function Bad  ($m) { Write-Host "  xx   $m" -ForegroundColor Red }
function Note ($m) { Write-Host "       $m" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "Momentum workstation" -ForegroundColor White

# ------------------------------------------------------------------ python --
Head "python"
$py = $null
foreach ($cand in @("python", "python3", "py")) {
    $exe = Get-Command $cand -ErrorAction SilentlyContinue
    if (-not $exe) { continue }
    try {
        if ($cand -eq "py") { $v = & $cand -3 -c "import sys;print('%d.%d' % sys.version_info[:2])" }
        else                { $v = & $cand   -c "import sys;print('%d.%d' % sys.version_info[:2])" }
    } catch { continue }
    if (-not $v) { continue }
    $parts = $v.Trim().Split(".")
    if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11) {
        if ($cand -eq "py") { $py = @("py", "-3") } else { $py = @($cand) }
        Good "Python $($v.Trim()) ($cand)"
        break
    }
}
if (-not $py) {
    Bad "Python 3.11 or newer was not found."
    Note "Install it from python.org, tick 'Add python.exe to PATH', then run this again."
    exit 1
}
$pyExe = $py[0]
$pyArgs = @()
if ($py.Count -gt 1) { $pyArgs = $py[1..($py.Count - 1)] }

# -------------------------------------------------------------------- port --
Head "port"
function Test-PortFree([int]$p) {
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $p)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) { try { $listener.Stop() } catch {} }
    }
}
if ($Port -eq 0) {
    $Port = 8787
    foreach ($p in 8787, 8788, 8789, 8790) {
        if (Test-PortFree $p) { $Port = $p; break }
    }
}
if ($Port -ne 8787) { Warn "port 8787 is in use - using $Port instead" } else { Good "port 8787 is free" }

# -------------------------------------------------------------------- mode --
$serverArgs = @("--host", "127.0.0.1", "--port", "$Port")
$banner = "recorded session (no network needed)"

if ($Ibkr) {
    Head "checking TWS (Interactive Brokers)"
    if ($IbkrPort -gt 0) { $env:IBKR_PORT = "$IbkrPort" }
    if ($IbkrHost)       { $env:IBKR_HOST = $IbkrHost }
    $twsHost = $env:IBKR_HOST; if (-not $twsHost) { $twsHost = "127.0.0.1" }
    $twsPort = $env:IBKR_PORT; if (-not $twsPort) { $twsPort = "7496" }
    Note "looking for TWS at ${twsHost}:${twsPort}"
    & $pyExe @pyArgs "scripts/ibkr_preflight.py"
    $code = $LASTEXITCODE
    switch ($code) {
        0 { Good "IBKR live data confirmed - read-only" }
        1 { Bad  "ib_async is missing"
            Note "run:  $pyExe @pyArgs -m pip install -r requirements.txt" }
        2 { Bad  "nothing is listening on ${twsHost}:${twsPort}"
            Note "1. TWS must be RUNNING and logged in on that machine"
            Note "2. Edit > Global Configuration > API > Settings:"
            Note "   Enable ActiveX and Socket Clients ON, Read-Only API ON"
            Note "3. Check the port TWS actually shows in that dialog."
            Note "   7496 is the LIVE port, 7497 is PAPER; IB Gateway uses 4001 / 4002."
            Note "   Rerun with, for example:  -Ibkr -IbkrPort 7497"
            Note "To see what is listening on this machine, run:"
            Note "   netstat -ano | findstr LISTENING | findstr 749" }
        3 { Bad  "IBKR data is DELAYED"
            Note "the desk refuses delayed data; subscribe to NASDAQ real-time" }
        4 { Warn "no real-time bars arrived"
            Note "outside 04:00-20:00 ET this is normal; the desk will still connect" }
        5 { Warn "the scanner answered with nothing"
            Note "the desk starts with the symbols you gave, if any" }
        default { Bad "preflight failed (exit $code)" }
    }
    if ($code -eq 0 -or $code -ge 4) {
        $serverArgs += "--ibkr"
        $serverArgs += $Symbols
        $banner = "live IBKR feed over TWS, read-only"
        if ($Symbols) { $banner = "$banner - $Symbols" } else { $banner = "$banner - scanner picks the desk" }
    } else {
        Bad "not starting the IBKR desk; fix the point above and run this again"
        exit 1
    }
} elseif (-not $Replay) {
    Warn "no mode given - opening the recorded session"
    Note "for live data run:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr"
}

# ------------------------------------------------------------------- serve --
Head "starting"
Say  "  Open this in your browser:  http://127.0.0.1:$Port"
Note "  $banner"
Say  ""
Say  "  This window is now busy running the desk.  Ctrl-C stops it."
Say  ""

$env:PYTHONPATH = "src"
& $pyExe @pyArgs -m momentum_platform.dashboard.server @serverArgs
