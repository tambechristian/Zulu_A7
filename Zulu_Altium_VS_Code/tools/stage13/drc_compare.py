# -*- coding: utf-8 -*-
"""Stage 13 judge -- compare an Altium DRC report (.drc) with an expectation, rule by rule (read-only).
    python drc_compare.py <report.drc> [<expected.drc>]
Prints every rule's violation count; the Un-Routed connections per net ('Net X Between ...' lines) and the
'Isolated copper' plane items separately; with <expected.drc>, the per-net difference of the connection lists
(after the ECO + re-net it must be empty against judge/drc_gate.drc; after the last chunk the report must have 0
connection lines)."""
import collections, io, re, sys
def parse(p):
    rules, conn, iso, cur = collections.OrderedDict(), collections.Counter(), [], None
    for ln in io.open(p, encoding='utf-8', errors='replace'):
        m = re.match(r'Processing Rule : (.*)', ln)
        if m:
            cur = m.group(1).strip(); continue
        m = re.match(r'Rule Violations :(\d+)', ln)
        if m and cur:
            rules[cur] = int(m.group(1)); continue
        m = re.search(r'Un-Routed Net Constraint: Net (\S+) Between', ln)
        if m:
            conn[m.group(1)] += 1
        if 'Isolated copper' in ln:
            iso.append(ln.strip())
    return rules, conn, iso
r, c, iso = parse(sys.argv[1])
for k, v in r.items():
    print('%5d  %s' % (v, k[:150]))
print('Un-Routed connections: %d on %d nets; isolated plane copper items: %d' % (sum(c.values()), len(c), len(iso)))
for l in iso:
    print('   ', l[:160])
if len(sys.argv) > 2:
    r2, c2, iso2 = parse(sys.argv[2])
    d1, d2 = c - c2, c2 - c
    print('connections vs %s: %d expected, %d reported; only in the report %s; only expected %s' % (
        sys.argv[2], sum(c2.values()), sum(c.values()), dict(d1) or '{}', dict(d2) or '{}'))
    print('DRC_COMPARE %s' % ('MATCH' if not d1 and not d2 else 'DIFFERS'))
