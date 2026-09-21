#!/usr/bin/env python3
"""Print the short hash the dashboard shows for the app.js on disk.

    python3 scripts/app_build.py        ->  app 3f9a2c

The page computes the same djb2 hash of the app.js it actually loaded and
shows it in the CHARTS health line. If the two differ, the browser is running
a previous build: pull, then reload. 2026-09-21: three rounds of "no MACD yet"
were exactly this, with nothing on screen to say so.
"""
from pathlib import Path

src = (Path(__file__).resolve().parents[1] / "src" / "momentum_platform"
       / "dashboard" / "web" / "app.js").read_text(encoding="utf-8")
h = 5381
for ch in src:
    h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
print("app " + format(h, "x")[:6])
