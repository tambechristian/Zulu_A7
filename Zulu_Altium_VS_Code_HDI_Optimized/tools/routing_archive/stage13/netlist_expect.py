# -*- coding: utf-8 -*-
"""Stage 13 judge -- Phase II schematic proof helper (read-only on its input).
From a Protel netlist exported BEFORE the 13 label renames, write
  <out>_before.json    {net: [pads]} exactly as tools/compare_netlists.py expands Altium pins
  <out>_expected.json  the same with the 13 swapped U1 pads moved to their new nets
Then, after the renames and a fresh export:
  python tools/compare_netlists.py <after.NET> <out>_expected.json   -> must print CONNECTIVITY MATCH (renamed 0)
  python tools/compare_netlists.py <after.NET> <out>_before.json     -> differences only on these 13 U1 pads
    python netlist_expect.py <before.NET> <out prefix>"""
import json, re, sys
MOVE = {'U1-E19': ('JA8', 'CHAN12'), 'U1-G17': ('JA3', 'CHAN7'), 'U1-H19': ('CHAN7', 'CHAN13'),
        'U1-K17': ('CHAN11', 'UART_FT_TXD'), 'U1-K18': ('UART_FT_TXD', 'CHAN11'), 'U1-N17': ('BTN', 'LED0_B'),
        'U1-N19': ('LED0_B', 'BTN'), 'U1-P17': ('FT-PWREN#', 'LED0_R'), 'U1-P19': ('LED0_R', 'FT-PWREN#'),
        'U1-R19': ('CHAN28', 'JA7'), 'U1-T17': ('JA7', 'CHAN28'), 'U1-W18': ('CHAN13', 'JA3'), 'U1-W19': ('CHAN12', 'JA8')}
txt = open(sys.argv[1], encoding='utf-8', errors='replace').read()
nets = {}
for block in re.findall(r'^\($(.*?)^\)$', txt, re.S | re.M):           # compare_netlists.py's own parse
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    name, pads = lines[0], lines[1:]
    exp = set()
    for pd in pads:
        part, _, des = pd.partition('-')
        ds = des.split(',')
        pre = re.match(r'[A-Za-z]+', ds[0])
        for d in ds:
            if pre and not re.match(r'[A-Za-z]', d):
                d = pre.group(0) + d
            exp.add('%s-%s' % (part, d))
    nets[name] = exp
where = {p: n for n, ps in nets.items() for p in ps}
bad = [(p, where.get(p), o) for p, (o, n) in MOVE.items() if where.get(p) != o]
if bad:
    raise SystemExit('the baseline is not the pre-rename netlist: %s' % bad)
exp = {n: set(ps) for n, ps in nets.items()}
for p, (o, n) in MOVE.items():
    exp[o].discard(p)
    if n not in exp:
        raise SystemExit('target net %s missing from the baseline' % n)
    exp[n].add(p)
json.dump({n: sorted(v) for n, v in nets.items()}, open(sys.argv[2] + '_before.json', 'w'), indent=0)
json.dump({n: sorted(v) for n, v in exp.items()}, open(sys.argv[2] + '_expected.json', 'w'), indent=0)
print('baseline: %d nets, %d pads; 13 U1 pads moved; wrote %s_before.json and %s_expected.json' % (
    len(nets), sum(len(v) for v in nets.values()), sys.argv[2], sys.argv[2]))
