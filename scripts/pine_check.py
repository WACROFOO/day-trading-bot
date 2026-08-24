#!/usr/bin/env python3
"""Static pre-push check for Pine v6 files — the two errors we actually shipped.

TradingView is the only real compiler; this does not replace it. It catches
the two classes that cost a round-trip through the user's editor this week:

  CE10272  Undeclared identifier — a top-level name used above the line that
           assigns it. Pine has no hoisting. (V4.8 shipped `thinRoom` used
           two blocks above its own declaration.)
  CE10123  plotshape(size=) / plotshape(text=) given a non-const value. Pine
           demands a *const string* there; anything derived from input.* or
           from a ternary over inputs is rejected. (V4.9 shipped `size=MSZ`.)

    python3 scripts/pine_check.py knowledge-base/tradingview/ross-fp-v4.pine

Exit 0 = clean, 1 = findings. Findings are line-numbered so they paste
straight into an editor jump.
"""
import re
import sys

# `name = expr` / `name := expr` / `var bool name = expr` at column 0
# (top-level only — indented ones are inside a block and scope differently).
# The optional type keyword matters: `var bool eventArmed = false` declares on
# THAT line, and missing it made the checker report its own first four hits.
TYPE = (r'(?:int|float|bool|string|color|line|label|box|table|linefill|'
        r'polyline|array<[^>]*>|matrix<[^>]*>|map<[^>]*>|[A-Z]\w*)')
ASSIGN = re.compile(rf'^(?:var\s+|varip\s+)?(?:{TYPE}\s+)?([A-Za-z_]\w*)\s*(?::=|=)(?!=)')
# `f(a, b) =>` — user function; its params are local, not forward refs.
FUNCDEF = re.compile(r'^([A-Za-z_]\w*)\s*\(([^)]*)\)\s*=>')
IDENT = re.compile(r'\b([A-Za-z_]\w*)\b')

# Pine builtins and namespaces we must not report. Not exhaustive — it does
# not need to be: an unknown builtin produces a false positive we read and
# dismiss, which is the safe direction for a pre-push gate.
NAMESPACES = {
    'ta', 'math', 'str', 'array', 'matrix', 'map', 'request', 'input', 'color',
    'shape', 'location', 'size', 'plot', 'display', 'scale', 'format', 'xloc',
    'yloc', 'extend', 'line', 'label', 'box', 'table', 'position', 'text',
    'font', 'alert', 'strategy', 'syminfo', 'timeframe', 'session', 'barmerge',
    'dayofweek', 'currency', 'order', 'hline', 'chart', 'runtime', 'log',
    'linefill', 'polyline', 'timeframe', 'adjustment', 'earnings', 'dividends',
    'splits', 'backadjustment', 'settlement_as_close',
}
BUILTINS = {
    'open', 'high', 'low', 'close', 'volume', 'time', 'time_close', 'bar_index',
    'barstate', 'na', 'true', 'false', 'int', 'float', 'bool', 'string',
    'if', 'else', 'for', 'to', 'by', 'while', 'switch', 'and', 'or', 'not',
    'var', 'varip', 'type', 'enum', 'method', 'export', 'import', 'series',
    'simple', 'const', 'indicator', 'library', 'plotshape', 'plotchar',
    'plotarrow', 'plotcandle', 'plotbar', 'bgcolor', 'fill', 'nz', 'max_bars_back',
    'timenow', 'year', 'month', 'weekofyear', 'dayofmonth', 'hour', 'minute',
    'second', 'na', 'hl2', 'hlc3', 'ohlc4', 'hlcc4', 'break', 'continue',
}
SKIP = NAMESPACES | BUILTINS

# plotshape/plotchar arguments that Pine types as `const string`.
CONST_STR_ARGS = ('size', 'text', 'char', 'title', 'editable', 'display')


def strip_comment(line):
    """Drop a trailing // comment without eating one inside a string."""
    out, instr, quote, i = [], False, '', 0
    while i < len(line):
        c = line[i]
        if instr:
            if c == quote:
                instr = False
            out.append(c)
        elif c in '"\'':
            instr, quote = True, c
            out.append(c)
        elif c == '/' and i + 1 < len(line) and line[i + 1] == '/':
            break
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def blank_strings(s):
    """Replace string literal contents so identifiers inside them are ignored."""
    return re.sub(r'"[^"]*"', '""', re.sub(r"'[^']*'", "''", s))


def forward_refs(lines):
    """Top-level identifiers read on a line above the line that assigns them."""
    declared = {}   # name -> first line it is assigned at column 0
    for n, raw in enumerate(lines, 1):
        code = strip_comment(raw)
        m = FUNCDEF.match(code) or ASSIGN.match(code)
        if m and m.group(1) not in declared:
            declared[m.group(1)] = n

    # function parameters are local — collect them so they are not flagged
    params = set()
    for raw in lines:
        m = FUNCDEF.match(strip_comment(raw))
        if m:
            for p in m.group(2).split(','):
                p = p.strip().split('=')[0].strip().split()[-1:] or ['']
                if p[0]:
                    params.add(p[0])

    findings = []
    for n, raw in enumerate(lines, 1):
        code = blank_strings(strip_comment(raw))
        if not code.strip():
            continue
        lhs = ASSIGN.match(code)
        rhs = code[lhs.end():] if lhs else code
        for name in IDENT.findall(rhs):
            if name in SKIP or name in params or name not in declared:
                continue
            if declared[name] > n:
                findings.append(
                    (n, f'CE10272 risk: "{name}" used here, assigned at line '
                        f'{declared[name]} — Pine does not hoist'))
    return findings


# `[a, b, c] = f(...)` — tuple destructuring declares every name in the bracket.
TUPLE = re.compile(r'^\s*\[([^\]]+)\]\s*=(?!=)')
# `for i = 0 to n` and `for [k, v] in m` declare their loop variables.
FOR1 = re.compile(r'\bfor\s+([A-Za-z_]\w*)\s*=')
FOR2 = re.compile(r'\bfor\s+\[?([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\]?\s+in\b')
# `strategy.closedtrades.entry_price(...)` — a dotted path of ANY depth is a
# builtin reference, not a bare identifier. Two-part stripping alone left the
# three-part ones looking undeclared.
DOTTED = re.compile(r'\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+')
# `title=` / `color=` — a named-argument key is syntax, not a name being read.
NAMEDARG = re.compile(r'\b[A-Za-z_]\w*\s*=(?!=)')


def _all_declared(lines):
    """Every name this file binds, at any indent — assignment, tuple, function,
    parameter or loop variable. Indent is irrelevant here: we are asking
    whether a name exists at all, not whether it is in scope."""
    names = set()
    for raw in lines:
        code = strip_comment(raw)
        stripped = code.strip()
        m = FUNCDEF.match(stripped)
        if m:
            names.add(m.group(1))
            for prm in m.group(2).split(','):
                prm = prm.strip().split('=')[0].strip().split()
                if prm:
                    names.add(prm[-1])
            continue
        m = TUPLE.match(code)
        if m:
            for nm in m.group(1).split(','):
                nm = nm.strip().split()[-1:] or ['']
                if nm[0]:
                    names.add(nm[0])
            continue
        m = ASSIGN.match(stripped)
        if m:
            names.add(m.group(1))
        m = FOR1.search(code)
        if m:
            names.add(m.group(1))
        m = FOR2.search(code)
        if m:
            names.add(m.group(1))
            names.add(m.group(2))
    return names


def undeclared(lines):
    """Identifiers read but never bound anywhere in the file.

    forward_refs() only compares line numbers for names it already found a
    declaration for, so `if name not in declared: continue` made a name with
    NO declaration the one case it could not see. That is the gap V12.6
    shipped through: a block replacement whose range happened to end on the
    two lines declaring `sm` and `lg` deleted them, left twelve uses behind,
    and the checker called the file clean. TradingView answered CE10272."""
    declared = _all_declared(lines)
    findings = []
    seen = set()
    for n, raw in enumerate(lines, 1):
        code = blank_strings(strip_comment(raw))
        if not code.strip():
            continue
        code = DOTTED.sub(' ', code)
        code = NAMEDARG.sub(' ', code)
        for name in IDENT.findall(code):
            if name in SKIP or name in declared or name in seen:
                continue
            seen.add(name)
            findings.append(
                (n, f'CE10272: "{name}" is used but never declared anywhere '
                    f'in this file'))
    return findings


def const_string_args(lines, declared_at):
    """plotshape/plotchar const-string args fed a variable or an input."""
    findings = []
    for n, raw in enumerate(lines, 1):
        code = strip_comment(raw)
        if not re.search(r'\b(plotshape|plotchar)\s*\(', code):
            continue
        for arg in CONST_STR_ARGS:
            m = re.search(rf'\b{arg}\s*=\s*([^,)]+)', code)
            if not m:
                continue
            val = m.group(1).strip()
            # literal, or a const namespace member — both fine
            if val.startswith(('"', "'")) or re.match(r'^(size|shape|location|'
                                                      r'display|color)\.', val):
                continue
            head = IDENT.match(val)
            if head and head.group(1) in declared_at:
                findings.append(
                    (n, f'CE10123 risk: {arg}={val} is not a const string — '
                        f'"{head.group(1)}" is assigned at line '
                        f'{declared_at[head.group(1)]}'))
    return findings


# Named args that do NOT exist on these calls — each pair shipped once.
# label.new sizes text with `size=`; table.cell with `text_size=`. Mixing
# them compiles nowhere (CE10120) and the V9.6 trend-line labels shipped
# with exactly that mix.
WRONG_ARGS = (
    ('label.new', re.compile(r'\btext_size\s*='), 'label.new has no text_size — the argument is size='),
    ('line.new', re.compile(r'\btext_size\s*=|(?<![\w.])size\s*='), 'line.new has no size/text_size argument'),
    ('table.cell', re.compile(r'(?<![\w.])(?<!text_)size\s*='), 'table.cell has no size — the argument is text_size='),
)


def wrong_named_args(lines):
    """Scan multi-line drawing calls for named args the function lacks."""
    findings = []
    for fn, pat, msg in WRONG_ARGS:
        depth = 0
        start = 0
        buf = []
        for n, raw in enumerate(lines, 1):
            code = strip_comment(raw)
            if depth == 0:
                idx = code.find(fn + '(')
                if idx < 0:
                    continue
                start = n
                buf = [code[idx:]]
                depth = buf[0].count('(') - buf[0].count(')')
            else:
                buf.append(code)
                depth += code.count('(') - code.count(')')
            if depth <= 0 and buf:
                stmt = ' '.join(buf)
                if pat.search(blank_strings(stmt)):
                    findings.append((start, f'CE10120 risk: {msg} (call starting here)'))
                buf = []
                depth = 0
    return findings


# ── continuation indent ──────────────────────────────────────────────────────
# Pine splits a statement across lines only when the continuation is indented
# by a number of spaces that is NOT a multiple of four; four, eight, twelve...
# read as the start of a local block instead, and the compiler answers
#   CE10156: Syntax error at input "end of line without line continuation"
# which points at the NEXT line and never says why. Cost one round trip in
# TradingView to find, so the linter learns it.
#
# Only applies when the brackets are already balanced: inside an unclosed
# ( or [ any indent is legal, which is why the file's deep argument lists are
# fine.
CONT_OPS = ("or", "and", "not", "+", "-", "*", "/", "%", "?", ":", ",",
            "==", "!=", ">=", "<=", ">", "<", ":=", "=")


def _ends_with_operator(line):
    """True when the line ends on a binary operator, so the statement is
    unfinished. Word operators need a boundary — stopExceedsHaltBand ends with
    the letters 'and' and is not a continuation."""
    stripped = line.rstrip()
    if stripped.endswith("=>"):          # a function body, not a continuation
        return False
    for op in CONT_OPS:
        if not stripped.endswith(op):
            continue
        if op[0].isalpha():
            head = stripped[: -len(op)]
            if head and (head[-1].isalnum() or head[-1] == "_"):
                continue                 # part of an identifier
        return True
    return False


def continuation_indent(lines):
    out, depth = [], 0
    for i, raw in enumerate(lines):
        code = strip_comment(blank_strings(raw)).rstrip()
        if code.strip() and depth == 0 and i > 0:
            prev = ""
            for j in range(i - 1, -1, -1):
                pc = strip_comment(blank_strings(lines[j])).rstrip()
                if pc.strip():
                    prev = pc
                    break
            if prev and _ends_with_operator(prev):
                indent = len(raw) - len(raw.lstrip(" "))
                if indent > 0 and indent % 4 == 0:
                    out.append((
                        i + 1,
                        "continuation indented %d spaces (a multiple of 4) — "
                        "Pine reads this as a new block, not a continuation, "
                        "and answers CE10156 on the NEXT line. Use 5." % indent))
        depth += code.count("(") - code.count(")")
        depth += code.count("[") - code.count("]")
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    bad = 0
    for path in sys.argv[1:]:
        with open(path) as fh:
            lines = fh.read().splitlines()
        declared_at = {}
        for n, raw in enumerate(lines, 1):
            m = ASSIGN.match(strip_comment(raw))
            if m and m.group(1) not in declared_at:
                declared_at[m.group(1)] = n

        findings = sorted(forward_refs(lines)
                          + const_string_args(lines, declared_at)
                          + wrong_named_args(lines)
                          + continuation_indent(lines)
                          + undeclared(lines))
        print(f'{path}  ({len(lines)} lines)')
        if not findings:
            print('  clean — no bad continuation indent, no forward reference, no non-const plotshape arg, no wrong-named drawing arg, no undeclared name')
        for n, msg in findings:
            print(f'  line {n}: {msg}')
            bad += 1
        print('  NOT CHECKED: types, runtime limits, drawing counts, repainting.'
              '\n  TradingView is the only real compiler.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
