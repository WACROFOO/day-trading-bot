#!/usr/bin/env python3
"""Inline the workstation into a single self-contained HTML page.

Same markup, same stylesheet, same application code as the served dashboard —
only the session is embedded instead of fetched, so the page runs anywhere
with no server, no network and no credentials.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

WEB = Path("src/momentum_platform/dashboard/web")
FIXTURE = Path("fixtures/market_replay/workstation_open_2026-09-01.jsonl")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/workstation.html")
    out.parent.mkdir(parents=True, exist_ok=True)

    html = (WEB / "index.html").read_text()
    css = (WEB / "styles.css").read_text()
    js = (WEB / "app.js").read_text()
    session = json.dumps(build_session(FIXTURE), default=str, separators=(",", ":"))

    # The artifact host supplies <!doctype>, <head> and <body>; keep only the
    # page content and fold the assets inline.
    body = html.split("<body>", 1)[1].rsplit("</body>", 1)[0]
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    body = body.replace('<script src="session.js"></script>', "").replace('<script src="app.js"></script>', "")

    page = (f"<title>{title}</title>\n<style>\n{css}\n</style>\n{body}\n"
            f"<script>window.__SESSION__={session};</script>\n<script>\n{js}\n</script>\n")
    out.write_text(page)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
