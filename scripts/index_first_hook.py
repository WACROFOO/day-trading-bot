#!/usr/bin/env python3
"""PreToolUse hook: refuse a blind search of the knowledge base.

CLAUDE.md says descend the index, never grep blind. I wrote that rule and then
grepped the corpus in the same session, which is why it is a hook.

The first version only matched `grep|rg|find` inside Bash. Its own test suite
found three ways past it in one run — `awk`, `sed`, and a python one-liner —
plus a fourth that needed no cleverness at all: the **Grep tool is not Bash**,
so it never reached the hook. A guard that only stops the obvious spelling
stops nobody, because the next attempt is never the obvious spelling.

So this covers three surfaces:
  Bash        search tools, and bulk readers pointed at a glob of the corpus
  Grep/Glob   the tools, which bypassed the Bash matcher entirely
  Read        only when pointed at a raw transcript, which is never step 1

Reading ONE named file stays allowed everywhere — that is what `kb.py open`
does, and it is not the failure mode. Globbing the corpus is.

ESCAPE HATCH, a declaration rather than a flag: append
    # INDEX-FAILED: <what you sought, which index should have had it>
Every use is logged to research/index-failures.log so the excuse leaves a
trace and a pattern of them becomes visible.
"""
import datetime
import json
import os
import re
import subprocess
import sys

CORPUS = re.compile(r'knowledge-base|research/')
# Anything that reads MANY files at once, or scans for a pattern.
SEARCH = re.compile(
    r'(^|[|;&`(\s])(grep|egrep|fgrep|rg|ag|ack|find|awk|sed|perl)(\s|$)')
BULK = re.compile(r'(^|[|;&`(\s])(cat|head|tail|less|more|wc|sort|uniq|xargs)(\s|$)')
# a python/node one-liner is a search engine wearing a disguise
INLINE = re.compile(r'(python3?|node|ruby)\s+-(c|e)\b')
RECURSIVE_DOT = re.compile(r'(grep|rg|ag|ack)\b[^|]*-[a-zA-Z]*r[a-zA-Z]*\s+[^|]*\s\.(\s|$)')
RAW_CORPUS_FILE = re.compile(
    r'knowledge-base/(transcripts|streams|recaps|summaries)/[\w-]+\.(txt|md)')

ADVICE = """Do this instead:
  1. python3 scripts/kb.py where "term"     which folder (indexes only)
  2. python3 scripts/kb.py open DIR          that folder's index
  3. python3 scripts/corpus.py "term"        register split

If steps 1-3 genuinely cannot find it, an index has failed. Re-run with
  # INDEX-FAILED: <what you sought, which index should have had it>
appended. That is allowed and logged — and it obliges running
`python3 scripts/kb.py doctor` and fixing the index in this same commit."""


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason}}))
    sys.exit(0)


def log_escape(root, cmd):
    try:
        m = re.search(r'INDEX-FAILED:\s*(.*)', cmd)
        reason = (m.group(1).strip() if m else '') or '(no reason given)'
        with open(os.path.join(root, 'research', 'index-failures.log'), 'a') as fh:
            ts = datetime.datetime.now(datetime.timezone.utc).strftime(
                '%Y-%m-%dT%H:%M:%SZ')
            fh.write(f'{ts}\t{reason}\t{cmd[:160]}\n')
    except OSError:
        pass


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool = payload.get('tool_name', '')
    ti = payload.get('tool_input', {}) or {}

    try:
        root = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return 0
    if not root:
        return 0

    # ---- the Grep / Glob tools: the hole the Bash matcher never saw ----
    if tool in ('Grep', 'Glob'):
        target = f"{ti.get('path', '')} {ti.get('glob', '')} {ti.get('pattern', '')}"
        # No path given means it searches the cwd — the whole repo, corpus included.
        if CORPUS.search(target) or not ti.get('path'):
            deny(f'Blocked: {tool} tool aimed at the knowledge base '
                 f'(path="{ti.get("path", "") or "<repo root>"}").\n\n'
                 'The index-first rule is not about which tool you use — it is\n'
                 'about not discarding the index layer. This tool bypassed the\n'
                 f'Bash hook, which is exactly why it is covered here.\n\n{ADVICE}')
        return 0

    # ---- Read of a raw transcript without descending first ----
    if tool == 'Read':
        fp = str(ti.get('file_path', ''))
        if RAW_CORPUS_FILE.search(fp):
            deny(f'Blocked: reading a raw corpus file directly.\n\n  {fp}\n\n'
                 'A transcript is step 3+, never step 1 — reading one you have\n'
                 'not located through the index means you already believe you\n'
                 'know what it says, which is the failure rule 1 exists for.\n\n'
                 'Locate it first (`kb.py where`, `corpus.py "term" --files`),\n'
                 'then read the hit. Append `# INDEX-FAILED: ...` is not\n'
                 'available here — use corpus.py --show to read in context.')
        return 0

    if tool != 'Bash':
        return 0

    cmd = str(ti.get('command', ''))
    if not cmd:
        return 0

    if 'INDEX-FAILED:' in cmd:
        log_escape(root, cmd)
        return 0

    # Strip heredoc BODIES before matching. A heredoc is data, not a command,
    # and this hook blocked the very commit that documented it: the CLAUDE.md
    # text being written contained the words "grep" and "research/", which is
    # indistinguishable from a search if you match the whole command string.
    # Writing prose about the rule must not trip the rule.
    cmd = re.sub(r"<<-?\s*'?\"?(\w+)'?\"?.*?^\1\s*$", '<<HEREDOC',
                 cmd, flags=re.S | re.M)

    # Same class: a git command is never a corpus search, but a commit message
    # describing this hook necessarily contains the words it matches on.
    # `git grep` is the one exception and stays checked.
    if re.match(r'\s*git\s', cmd) and not re.search(r'\bgit\s+grep\b', cmd):
        return 0

    hits_corpus = bool(CORPUS.search(cmd)) or bool(RECURSIVE_DOT.search(cmd))
    if not hits_corpus:
        return 0

    # FAN-OUT is the failure mode, not reading. `sed -n '10,20p' FILE.md` is a
    # single-file read and blocking it was a false positive on the very lookup
    # this rule exists to make fast. So a search tool only trips when it
    # actually sweeps: a glob, a recursive flag, or a bare directory target.
    fans_out = (
        '*' in cmd
        or re.search(r'\s-[a-zA-Z]*[rR][a-zA-Z]*(\s|$)', cmd)
        or re.search(r'(knowledge-base|research)[\w/.-]*/(\s|$|["\')])', cmd)
        or re.search(r'\b(knowledge-base|research)\b(?![\w/.-]*\.\w+)', cmd)
    )
    is_search = (bool(SEARCH.search(cmd)) or bool(INLINE.search(cmd))) and fans_out
    is_bulk_glob = bool(BULK.search(cmd)) and '*' in cmd

    if is_search or is_bulk_glob:
        deny('Blocked: blind search of the knowledge base.\n\n'
             f'  {cmd[:300]}\n\n'
             'Grep returns line-hits with no register attached, and the\n'
             'register is usually the finding (185 ABCD mentions in teaching\n'
             f'vs 3 in recaps IS the answer).\n\n{ADVICE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
