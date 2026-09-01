"""Clean-room momentum scanner and alert platform.

Implements the replay-first backend described in
CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/scanner-alert-platform-spec.md.

Every scanner here is an independent, transparent approximation of publicly
described behavior. Nothing in this package reproduces Warrior Trading's
proprietary server-side formulas, and no scanner event is ever a trade order.
"""

__version__ = "0.1.0"
