#!/usr/bin/env python3
"""Do two desks scan and alert the same way?

Two traders each on their own IBKR connection want one screen, not two. The
rules that decide what a desk admits and what it fires live in one committed
file; this prints the fingerprint of the desk in front of you, and compares it
with a partner's when they paste theirs.

  python3 scripts/desk_parity.py                  # this checkout's rules
  python3 scripts/desk_parity.py --url http://127.0.0.1:8787   # the running desk
  python3 scripts/desk_parity.py --compare 33dfeedb3f51        # against a partner's hash
  python3 scripts/desk_parity.py --json > mine.json            # to send them

A matching hash means both desks apply the same bands, the same cadence, the
same liquidity gate, the same Confirmed pillars and the same scanner
definitions. It does NOT mean both see the same data: entitlements are printed
separately because a desk without IBKR fundamentals or without news keys
scores the float and news pillars differently, and that moves the
three-of-five liquidity gate and so the alerts.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

G, Y, R, D, B, O = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"


def from_url(url: str) -> dict:
    with urllib.request.urlopen(url.rstrip("/") + "/api/v1/health", timeout=10) as r:
        return json.loads(r.read()).get("desk") or {}


def flatten(fp: dict) -> dict:
    out = {}
    for section in ("rules", "confirmed", "scanners"):
        block = fp.get(section) or {}
        for key, value in block.items():
            if isinstance(value, dict):
                for k2, v2 in value.items():
                    out[f"{section}.{key}.{k2}"] = v2
            else:
                out[f"{section}.{key}"] = value
    for var, value in (fp.get("envOverrides") or {}).items():
        out[f"env.{var}"] = value
    return out


def show(fp: dict) -> None:
    print(f"\n{B}Desk rules{O}  {B}{fp.get('hash')}{O}")
    print(f"  build {fp.get('build') or 'unknown'} · profile v{fp.get('profileVersion')} "
          f"· {D}{fp.get('source')}{O}")
    if fp.get("note"):
        print(f"  {Y}{fp['note']}{O}")
    rules = fp.get("rules") or {}
    for section in sorted(rules):
        pairs = "  ".join(f"{k}={v}" for k, v in sorted(rules[section].items()))
        print(f"  {section:9s} {pairs}")
    if fp.get("envOverrides"):
        print(f"  {Y}env override{O} " + "  ".join(f"{k}={v}" for k, v in sorted(fp["envOverrides"].items())))
    ent = fp.get("entitlements") or {}
    if ent:
        print(f"  {D}entitlements{O} " + "  ".join(f"{k}={v}" for k, v in sorted(ent.items())))
        missing = [k for k, v in ent.items() if v is False]
        if missing:
            print(f"  {Y}note{O} {', '.join(missing)} unavailable on this desk — the float and news "
                  f"pillars score differently, which moves the 3-of-5 liquidity gate")


def compare(mine: dict, theirs: dict) -> int:
    if mine.get("hash") == theirs.get("hash"):
        print(f"\n{G}match{O}  both desks apply the same rules ({mine.get('hash')})")
        return 0
    print(f"\n{R}differ{O}  {mine.get('hash')} vs {theirs.get('hash')}")
    a, b = flatten(mine), flatten(theirs)
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            print(f"  {key:38s} {a.get(key, '—')}  vs  {b.get(key, '—')}")
    print(f"\n{D}Same rules means the same alerts from the same data. Line the differences "
          f"up — the committed profile is config/desk-profile.json.{O}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="read a running desk instead of this checkout")
    ap.add_argument("--compare", metavar="HASH_OR_FILE",
                    help="a partner's hash, or the JSON file they sent")
    ap.add_argument("--json", action="store_true", help="print the fingerprint as JSON")
    args = ap.parse_args()

    from momentum_platform import desk_profile
    mine = from_url(args.url) if args.url else desk_profile.fingerprint()
    if args.json:
        print(json.dumps(mine, indent=2, sort_keys=True))
        return 0
    show(mine)
    if not args.compare:
        print(f"\n{D}Send this hash to your partner, or --json > mine.json for the detail.{O}")
        return 0
    path = Path(args.compare)
    theirs = json.loads(path.read_text()) if path.is_file() else {"hash": args.compare}
    return compare(mine, theirs)


if __name__ == "__main__":
    raise SystemExit(main())
