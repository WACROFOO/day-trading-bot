#!/usr/bin/env bash
# PreToolUse hook: refuse a blind grep of the knowledge base.
#
# CLAUDE.md says descend the index, never grep blind. I wrote that rule and
# then grepped the corpus in the same session, which is the whole argument for
# not leaving it as prose. This denies grep/rg/find aimed at knowledge-base/
# or research/ and points at kb.py instead.
#
# It does NOT block searching code (scripts/, *.py, *.pine) — only the corpus,
# which is the part that has a maintained index to descend.
#
# ESCAPE HATCH, deliberately a declaration rather than a flag: append
#     # INDEX-FAILED: <what you looked for and which index should have had it>
# to the command and it runs. Saying that out loud is the point — per CLAUDE.md
# it obliges fixing the index that missed, in the same commit as the answer.
# Every use is appended to research/index-failures.log so the excuse leaves a
# trace and a pattern of them becomes visible.
set -uo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

CMD=$(python3 -c '
import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: print("")
' 2>/dev/null) || exit 0
[ -z "$CMD" ] && exit 0

# Is this a search tool at all?
echo "$CMD" | grep -Eq '(^|[|;&[:space:]])(grep|egrep|fgrep|rg|ag|ack|find)([[:space:]]|$)' || exit 0

# Aimed at the corpus? Either names it, or sweeps the repo root recursively.
TARGETS_KB=0
echo "$CMD" | grep -Eq 'knowledge-base|research/' && TARGETS_KB=1
echo "$CMD" | grep -Eq '(grep|rg)[^|]*-[a-zA-Z]*r[a-zA-Z]*[[:space:]]+[^|]*[[:space:]]\.([[:space:]]|$)' && TARGETS_KB=1
[ "$TARGETS_KB" -eq 0 ] && exit 0

# Declared index failure — allow, but record it.
if echo "$CMD" | grep -q 'INDEX-FAILED:'; then
  REASON=$(echo "$CMD" | sed -n 's/.*INDEX-FAILED:[[:space:]]*//p')
  mkdir -p "$ROOT/research"
  printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${REASON:-(no reason given)}" \
    "$(echo "$CMD" | cut -c1-160)" >> "$ROOT/research/index-failures.log"
  exit 0
fi

python3 - "$CMD" <<'PY'
import json, sys
cmd = sys.argv[1][:300]
reason = (
 "Blocked: blind search of the knowledge base.\n\n"
 f"  {cmd}\n\n"
 "CLAUDE.md search protocol — descend the index, never grep blind. Grep\n"
 "returns line-hits with no register attached, and the register is usually\n"
 "the finding (185 ABCD mentions in teaching vs 3 in recaps IS the answer).\n\n"
 "Do this instead:\n"
 "  1. python3 scripts/kb.py where \"term\"     which folder (indexes only)\n"
 "  2. python3 scripts/kb.py open DIR          that folder's index\n"
 "  3. python3 scripts/corpus.py \"term\"        register split\n\n"
 "If steps 1-3 genuinely cannot find it, an index has failed. Re-run with\n"
 "  # INDEX-FAILED: <what you sought, which index should have had it>\n"
 "appended. That is allowed and logged — and it obliges running\n"
 "`python3 scripts/kb.py doctor` and fixing the index in this same commit.")
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": reason}}))
PY
