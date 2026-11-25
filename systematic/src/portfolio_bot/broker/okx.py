"""OKX Europe connection through ccxt (class ``myokx``, host eea.okx.com).

Step 2 of the setup: **demo trading only**. The connector refuses to start
unless demo mode is on; live trading is added after the 8-week engineering
gate (crypto/PLAN.md §8).

Keys come from environment variables (normally a local ``systematic/.env``
file, which git ignores). They are never printed, logged or committed:
    OKX_API_KEY, OKX_API_SECRET, OKX_API_PASSPHRASE, OKX_DEMO=1
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
REQUIRED = ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")


def load_env(path: Path = ENV_FILE) -> dict[str, str]:
    """Read KEY=VALUE lines from a local .env file (no extra dependency)."""
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass
class OkxConfig:
    api_key: str
    secret: str
    passphrase: str
    demo: bool

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "OkxConfig":
        merged = {**load_env(), **os.environ} if env is None else env
        missing = [k for k in REQUIRED if not merged.get(k)]
        if missing:
            raise RuntimeError(f"missing in .env: {', '.join(missing)} (see systematic/.env.example)")
        return cls(merged["OKX_API_KEY"], merged["OKX_API_SECRET"], merged["OKX_API_PASSPHRASE"],
                   demo=merged.get("OKX_DEMO", "1") == "1")

    def __repr__(self) -> str:  # never show secrets, even by accident
        return f"OkxConfig(api_key=***{self.api_key[-4:]}, demo={self.demo})"


def connect(config: OkxConfig, exchange_factory=None):
    """A ccxt exchange object for OKX Europe, in demo mode."""
    if not config.demo:
        raise RuntimeError("live trading is disabled in this version: set OKX_DEMO=1 (demo trading only)")
    if exchange_factory is None:
        import ccxt  # imported here so the rest of the package works without ccxt
        exchange_factory = ccxt.myokx
    exchange = exchange_factory({
        "apiKey": config.api_key,
        "secret": config.secret,
        "password": config.passphrase,
        "enableRateLimit": True,
    })
    exchange.set_sandbox_mode(True)  # sends x-simulated-trading: 1
    return exchange


def pick_symbol(markets: dict, preferred=("BTC/USDC", "BTC/USDT")) -> str:
    """BTC/USDC if the demo environment lists it, else BTC/USDT."""
    for symbol in preferred:
        if symbol in markets:
            return symbol
    raise RuntimeError(f"none of {preferred} available in this environment")
