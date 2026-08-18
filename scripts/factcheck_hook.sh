#!/usr/bin/env bash
# PreToolUse hook: refuse a git commit whose staged .md cites something unreal.
#
# CLAUDE.md rule 1 says nothing is asserted that was not read this turn. A rule
# in a prompt is a wish; this is the part that can actually say no. It resolves
# video ids, timestamps and repo paths in the staged files and denies the commit
# when one points nowhere.
#
# It cannot check that a quote is accurate or a claim fair — only that the
# reference EXISTS. That is the mechanical half; the rest stays judgement.
#
# Path is resolved through git, not hardcoded, so it works on any clone.
set -uo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$ROOT/scripts/factcheck.py" ] || exit 0

OUT=$(cd "$ROOT" && python3 scripts/factcheck.py --staged 2>&1)
STATUS=$?

# Exit 0 = every citation resolved. Stay silent and let the commit through.
[ $STATUS -eq 0 ] && exit 0

# Anything else = at least one reference points nowhere. Deny, and hand the
# model the actual failing lines so it can fix them rather than guess.
python3 - "$OUT" <<'PY'
import json, sys
reason = ("factcheck blocked this commit — a citation in the staged files does "
          "not resolve.\n\n" + sys.argv[1] + "\n\n"
          "Fix or remove the reference. Do not commit around this by "
          "rephrasing the claim while keeping the number.")
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": reason}}))
PY
