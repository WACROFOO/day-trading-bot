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
                          + const_string_args(lines, declared_at))
        print(f'{path}  ({len(lines)} lines)')
        if not findings:
            print('  clean — no forward reference, no non-const plotshape arg')
        for n, msg in findings:
            print(f'  line {n}: {msg}')
            bad += 1
        print('  NOT CHECKED: types, runtime limits, drawing counts, repainting.'
              '\n  TradingView is the only real compiler.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
