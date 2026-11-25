"""OKX connector guards and the demo check, against a fake exchange (no network)."""

import importlib.util
from pathlib import Path

import pytest

from portfolio_bot.broker import okx

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "okx_demo_check.py"
spec = importlib.util.spec_from_file_location("okx_demo_check", SCRIPT)
demo_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_check)

ENV = {"OKX_API_KEY": "key-abcd1234", "OKX_API_SECRET": "s3cret", "OKX_API_PASSPHRASE": "pass", "OKX_DEMO": "1"}


class FakeExchange:
    def __init__(self, params):
        self.params, self.sandbox, self.orders = params, False, {}

    def set_sandbox_mode(self, on):
        self.sandbox = on

    def load_markets(self):
        return {"BTC/USDT": {"limits": {"amount": {"min": 0.00001}}}}

    def fetch_balance(self):
        return {"total": {"USDT": 5000.0, "BTC": 1.0}}

    def fetch_ticker(self, symbol):
        return {"bid": 60000.0, "last": 60001.0}

    def price_to_precision(self, symbol, price):
        return f"{price:.1f}"

    def create_order(self, symbol, kind, side, amount, price, params):
        assert params["postOnly"] and price < 60000.0
        self.orders["1"] = "open"
        return {"id": "1"}

    def fetch_order(self, oid, symbol):
        return {"status": self.orders[oid]}

    def cancel_order(self, oid, symbol):
        self.orders[oid] = "canceled"


def test_config_requires_all_keys_and_hides_secrets():
    cfg = okx.OkxConfig.from_env(ENV)
    assert "s3cret" not in repr(cfg) and "key-abcd1234" not in repr(cfg)
    with pytest.raises(RuntimeError, match="OKX_API_PASSPHRASE"):
        okx.OkxConfig.from_env({k: v for k, v in ENV.items() if k != "OKX_API_PASSPHRASE"})


def test_live_mode_is_refused():
    cfg = okx.OkxConfig.from_env({**ENV, "OKX_DEMO": "0"})
    with pytest.raises(RuntimeError, match="demo trading only"):
        okx.connect(cfg, exchange_factory=FakeExchange)


def test_connect_turns_on_demo_mode():
    ex = okx.connect(okx.OkxConfig.from_env(ENV), exchange_factory=FakeExchange)
    assert ex.sandbox and ex.params["password"] == "pass"


def test_symbol_falls_back_to_usdt_when_usdc_is_missing():
    assert okx.pick_symbol({"BTC/USDT": {}}) == "BTC/USDT"
    assert okx.pick_symbol({"BTC/USDC": {}, "BTC/USDT": {}}) == "BTC/USDC"
    with pytest.raises(RuntimeError):
        okx.pick_symbol({"ETH/EUR": {}})


def test_demo_check_places_unfillable_order_then_cancels_it():
    ex = okx.connect(okx.OkxConfig.from_env(ENV), exchange_factory=FakeExchange)
    report = demo_check.run(ex)
    assert ex.orders["1"] == "canceled"
    assert any("cancelled" in line for line in report)


def test_env_file_parser(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# comment\nOKX_API_KEY='abc'\nOKX_DEMO=1\nnot a line\n")
    assert okx.load_env(f) == {"OKX_API_KEY": "abc", "OKX_DEMO": "1"}
