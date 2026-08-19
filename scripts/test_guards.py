#!/usr/bin/env python3
"""Test the guardrails — including trying to get around them.

Four tools now stand between a plausible-sounding claim and a commit:
pine_check, factcheck, kb doctor, and the two PreToolUse hooks. None of them
had a test, which for tools whose entire job is catching MY errors is the
wrong way round.

FACTCHECK-FIXTURES — this file deliberately contains fabricated video ids,
invented timestamps and paths to nothing. They are the test data. factcheck.py
honours that declaration and skips this file; without it, the suite that
proves factcheck works would be blocked by factcheck.

Each guard is tested three ways:
  POSITIVE  it passes something that should pass  (no false alarms)
  NEGATIVE  it catches something that should fail (it actually works)
  BYPASS    it is asked to catch the same thing dressed differently

The BYPASS block is the point. A guard that only stops the obvious form of a
mistake stops nobody, because the next attempt is never the obvious form.
Failures there are reported, not hidden — a known hole beats a false sense of
coverage.

    python3 scripts/test_guards.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS, FAIL, HOLE = [], [], []


def sh(cmd, stdin=None):
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True,
                       text=True, input=stdin)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def check(name, cond, detail='', hole=False):
    if cond:
        PASS.append(name)
        print(f'  PASS  {name}')
    elif hole:
        HOLE.append((name, detail))
        print(f'  HOLE  {name}  — {detail}')
    else:
        FAIL.append((name, detail))
        print(f'  FAIL  {name}  — {detail}')


def hook(script, command):
    """Run a PreToolUse hook with a synthetic payload; return (denied, reason)."""
    payload = json.dumps({'tool_name': 'Bash',
                          'tool_input': {'command': command}})
    _, out = sh(f'./scripts/{script}', stdin=payload)
    out = out.strip()
    if not out:
        return False, ''
    try:
        d = json.loads(out)
        hs = d.get('hookSpecificOutput', {})
        return hs.get('permissionDecision') == 'deny', hs.get(
            'permissionDecisionReason', '')
    except json.JSONDecodeError:
        return False, out


def tmp(content, suffix='.md'):
    fd, p = tempfile.mkstemp(suffix=suffix, dir=os.path.join(ROOT, '.testtmp'))
    with os.fdopen(fd, 'w') as fh:
        fh.write(content)
    return p


# ───────────────────────────── pine_check ─────────────────────────────
def test_pine():
    print('\npine_check — Pine compile errors we have actually shipped')
    rc, out = sh('python3 scripts/pine_check.py '
                 'knowledge-base/tradingview/ross-fp-v4.pine')
    check('clean file passes', rc == 0 and 'clean' in out, out[:100])

    # the two real historical bugs, reconstructed
    fwd = tmp('//@version=6\nindicator("t")\nx = thinRoom ? 1 : 0\n'
              'thinRoom = close > open\n', '.pine')
    rc, out = sh(f'python3 scripts/pine_check.py {fwd}')
    check('catches forward reference (CE10272)', rc == 1 and 'CE10272' in out,
          out[:120])

    cst = tmp('//@version=6\nindicator("t")\n'
              'MSZ = input.string("tiny","s") == "tiny" ? size.tiny : size.normal\n'
              'plotshape(true, size=MSZ, text="X")\n', '.pine')
    rc, out = sh(f'python3 scripts/pine_check.py {cst}')
    check('catches non-const plotshape size (CE10123)',
          rc == 1 and 'CE10123' in out, out[:120])

    # BYPASS: same defect, different spelling
    var = tmp('//@version=6\nindicator("t")\nmySz = size.tiny\n'
              'plotshape(true, size=mySz, text="X")\n', '.pine')
    rc, out = sh(f'python3 scripts/pine_check.py {var}')
    check('BYPASS: const-valued variable in size= still flagged',
          rc == 1, 'a variable holding size.tiny is still not a const string '
                   'to Pine; checker let it through', hole=True)


# ───────────────────────────── factcheck ─────────────────────────────
def test_factcheck():
    print('\nfactcheck — citations that point nowhere')
    real = tmp('He says it in `js25lIZMUSY` @00:22:49 and see `scripts/tape.py`.\n')
    rc, out = sh(f'python3 scripts/factcheck.py {real}')
    check('real video id + timestamp + path passes', rc == 0, out[:120])

    # Shaped like a real id (has caps/digits) — a pure-lowercase token is now
    # correctly read as prose, so the fixture has to look like what it imitates.
    fake = tmp('Ross states it in `zZ9qQ7xKm2p` @00:11:22.\n')
    rc, out = sh(f'python3 scripts/factcheck.py {fake}')
    check('catches fabricated video id', rc == 1 and 'no such transcript' in out,
          out[:120])

    # ...and the id-shape heuristic must not become a bypass: a lowercase
    # token is skipped, which is a MISS, never a false pass of a real id.
    lower = tmp('Ross states it in `abcdefghijk` @00:11:22.\n')
    rc, out = sh(f'python3 scripts/factcheck.py {lower}')
    check('HOLE: pure-lowercase fake id is skipped as prose', rc == 1,
          'no corpus id is pure lowercase (0 of 611 measured), so this can '
          'only miss a fabricated id that looks like an English word - '
          'accepted cost of not accusing prose', hole=True)

    badts = tmp('He says it in `js25lIZMUSY` @23:59:58.\n')
    rc, out = sh(f'python3 scripts/factcheck.py {badts}')
    check('catches real video, invented timestamp',
          rc == 1 and 'timestamp does not' in out, out[:120])

    nopath = tmp('See `research/nowhere/absent.md` for the proof.\n')
    rc, out = sh(f'python3 scripts/factcheck.py {nopath}')
    check('catches path that exists nowhere',
          rc == 1 and 'NOT FOUND ANYWHERE' in out, out[:120])

    # FALSE POSITIVE found live: the 11-char tail of a longer word followed by
    # "at HH:MM" was read as a video id. Prose must not trip a citation checker.
    prose = tmp('Volume has been accumulating at 04:00 and stabilising at 09:30.\n')
    rc, out = sh(f'python3 scripts/factcheck.py {prose}')
    check('ordinary prose with "word at HH:MM" is not a citation', rc == 0,
          out[:140])

    # BYPASS: the same invented claim with the citation simply omitted
    naked = tmp('Ross requires float under 3.7M and RVOL over 8.2x.\n')
    rc, out = sh(f'python3 scripts/factcheck.py {naked}')
    check('BYPASS: uncited invented numbers pass untouched', rc == 1,
          'factcheck only validates citations that EXIST; a fabricated number '
          'with no citation is invisible to it — this is by design and is the '
          'residual risk', hole=True)


# ─────────────────────────────── kb doctor ───────────────────────────────
def test_kb():
    print('\nkb.py — index navigation and staleness')
    rc, out = sh('python3 scripts/kb.py doctor')
    check('repo indexes currently clean', rc == 0 and '0 stale' in out, out[:120])

    rc, out = sh('python3 scripts/kb.py where "reverse split"')
    check('where() routes a known term to indexes',
          rc == 0 and 'SCANNERS.md' in out, out[:120])

    rc, out = sh('python3 scripts/kb.py where "zqxjvwk-nonsense"')
    check('where() reports honestly when a term is absent',
          rc == 1 and 'NO index' in out, out[:120])

    # NEGATIVE: create a directory invisible to its parent index
    d = os.path.join(ROOT, 'testtmp_orphan')
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'x.md'), 'w').write('content\n')
    rc, out = sh('python3 scripts/kb.py doctor')
    sh('rm -rf testtmp_orphan')
    check('doctor catches a directory with no index',
          rc == 1 and 'testtmp_orphan' in out, out[:200])


# ─────────────────────────────── the hooks ───────────────────────────────
def test_hooks():
    print('\nindex_first_hook — blind corpus search')
    for cmd in ['grep -rin "flame" knowledge-base/',
                'rg "abcd" research/momentum-replication/reports/',
                'find knowledge-base/ -name "*.txt"']:
        d, _ = hook('index_first_hook.py', cmd)
        check(f'denies: {cmd[:44]}', d, 'not denied')

    for cmd in ['python3 scripts/kb.py where "flame"',
                'grep -n "def compute" scripts/tape.py',
                'git log --oneline -5']:
        d, _ = hook('index_first_hook.py', cmd)
        check(f'allows: {cmd[:44]}', not d, 'wrongly denied')

    d, _ = hook('index_first_hook.py',
                'grep -rin "x" knowledge-base/ # INDEX-FAILED: testing')
    check('escape hatch runs', not d, 'declared failure still denied')

    print('\nindex_first_hook — BYPASS attempts')
    bypasses = [
        ('cd + relative dot', 'cd knowledge-base && grep -rn "flame" .'),
        ('cat piped to grep', 'cat knowledge-base/transcripts/*.txt | grep flame'),
        ('awk instead of grep', 'awk "/flame/" knowledge-base/transcripts/*.txt'),
        ('sed instead of grep', 'sed -n "/flame/p" knowledge-base/transcripts/*.txt'),
        ('python one-liner', 'python3 -c "import glob;[print(l) for f in '
                             'glob.glob(\'knowledge-base/**/*.txt\') for l in open(f)]"'),
    ]
    for label, cmd in bypasses:
        d, _ = hook('index_first_hook.py', cmd)
        check(f'BYPASS blocked: {label}', d,
              'reaches the corpus without tripping the hook', hole=True)

    print('\nindex_first_hook — FALSE POSITIVES (found live, not by this suite)')
    # The hook blocked the commit that documented the hook: the heredoc BODY
    # contained "grep" and "research/". Writing about the rule is not breaking it.
    doc_edit = ("python3 - <<'PY'\n"
                "s = open('CLAUDE.md').read()\n"
                "s = s.replace('old', 'A grep of research/ is denied by the hook')\n"
                "open('CLAUDE.md','w').write(s)\n"
                "PY")
    d, _ = hook('index_first_hook.py', doc_edit)
    check('heredoc writing ABOUT grep is not blocked', not d,
          'hook matched prose inside a heredoc body')

    commit_msg = ("git commit -m \"denies grep of knowledge-base/ and "
                  "research/ paths\"")
    d, _ = hook('index_first_hook.py', commit_msg)
    check('commit message mentioning grep is not blocked', not d,
          'hook matched a commit message')

    # Reading ONE named file is the documented allowance and was blocked live,
    # on the exact lookup this rule is meant to speed up. Fan-out is the
    # failure mode; a line-range read of a known file is step 2 of the protocol.
    for label, cmd in [
        ('sed line-range on one file',
         "sed -n '10,20p' knowledge-base/strategies/SCANNERS.md"),
        ('head on one file', 'head -30 knowledge-base/daytrade-dash/README.md'),
        ('cat one named file', 'cat knowledge-base/strategies/FILTERS.md'),
        ('awk on one file', "awk 'NR<20' knowledge-base/strategies/SCANNERS.md"),
    ]:
        d, _ = hook('index_first_hook.py', cmd)
        check(f'allows: {label}', not d, 'single-file read wrongly denied')

    # ...but the same tools fanning out must still trip.
    for label, cmd in [
        ('sed over a glob', "sed -n '/flame/p' knowledge-base/transcripts/*.txt"),
        ('head over a directory', 'grep -r flame knowledge-base'),
    ]:
        d, _ = hook('index_first_hook.py', cmd)
        check(f'denies: {label}', d, 'fan-out slipped through')

    print('\nindex_first_hook — non-Bash tool surfaces')
    for tool, ti, want, label in [
        ('Grep', {'pattern': 'flame', 'path': 'knowledge-base'}, True, 'Grep tool at corpus'),
        ('Grep', {'pattern': 'flame'}, True, 'Grep tool with no path (whole repo)'),
        ('Grep', {'pattern': 'def compute', 'path': 'scripts/tape.py'}, False, 'Grep tool at code'),
        ('Glob', {'pattern': '**/*.txt', 'path': 'knowledge-base'}, True, 'Glob tool at corpus'),
        ('Read', {'file_path': 'knowledge-base/transcripts/js25lIZMUSY.txt'}, True, 'Read raw transcript'),
        ('Read', {'file_path': 'knowledge-base/strategies/FILTERS.md'}, False, 'Read a strategy doc'),
    ]:
        out = sh('./scripts/index_first_hook.py',
                 stdin=json.dumps({'tool_name': tool, 'tool_input': ti}))[1].strip()
        denied = 'permissionDecision\": \"deny' in out or '"permissionDecision": "deny"' in out
        check(f'{"denies" if want else "allows"}: {label}', denied == want,
              f'got denied={denied}')

    print('\nfactcheck_hook — commit gating')
    d, reason = hook('factcheck_hook.sh', 'git commit -m "x"')
    check('clean staging area commits', not d, reason[:120])


def main():
    os.makedirs(os.path.join(ROOT, '.testtmp'), exist_ok=True)
    print('GUARD TEST SUITE')
    print('POSITIVE = no false alarm · NEGATIVE = actually catches it · '
          'BYPASS = catches it disguised')
    try:
        test_pine()
        test_factcheck()
        test_kb()
        test_hooks()
    finally:
        sh('rm -rf .testtmp')

    n = len(PASS) + len(FAIL) + len(HOLE)
    print(f'\n{"=" * 70}')
    print(f'{len(PASS)}/{n} pass · {len(FAIL)} broken · {len(HOLE)} known holes')
    if FAIL:
        print('\nBROKEN — the guard does not do what it claims:')
        for k, d in FAIL:
            print(f'  {k}\n      {d}')
    if HOLE:
        print('\nKNOWN HOLES — the guard is real but does not cover this:')
        for k, d in HOLE:
            print(f'  {k}\n      {d}')
    print('\nNo guard here checks whether a quote is ACCURATE or a claim FAIR.')
    print('Those stay judgement, and no test in this file changes that.')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
