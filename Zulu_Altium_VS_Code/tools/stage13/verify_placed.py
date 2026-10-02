# -*- coding: utf-8 -*-
"""Stage 13 judge -- Phase II acceptance from the SAVED FILE (read-only; run it on a route_inputs.json regenerated
from the PcbDoc with `python tools/route_inputs.py` after Ctrl+S).

    python verify_placed.py <regenerated route_inputs.json> <judge/inputs_gate.json>              # after ECO + re-net
    python verify_placed.py <regenerated route_inputs.json> <judge/inputs_gate.json> <plan.json> [<chunk_k.json> ...]

Without a plan: the board must equal the gate inputs (the 13 U1 pad nets and the 12 re-netted placed objects of the
swaps included).  With the plan: expected = gate inputs minus the plan's 'remove' plus the plan's copper, each via
record expanded into the Altium via objects route_emit emits (hdi.altium_objects); with chunk files after the plan,
only those chunks' copper is expected (placement in progress: chunk 1 carries the removals).  Objects compare as
multisets of (kind, net, layer/span, coordinates to 1e-4 mm, width/size/hole).  Rule semantics are checked by
verify_widths.py because Altium can serialize equivalent per-layer Width tables differently after a layer conversion.
Exit 0 = identical geometry, pad nets, classes, outline, land field, and keepouts."""
import collections, io, json, os, sys
C = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(C))
import hdi  # noqa: E402

got = json.load(io.open(sys.argv[1], encoding='utf-8'))
gate = json.load(io.open(sys.argv[2], encoding='utf-8'))
H = hdi.load(gate)
R = lambda v: round(v + 0.0, 4)


def tkey(t):
    a, b = (R(t['x1']), R(t['y1'])), (R(t['x2']), R(t['y2']))
    return ('T', t['net'], t['layer'], min(a, b), max(a, b), R(t['width']))


def vkey(v):
    sp = tuple(v.get('span') or gate['hdi']['stack'])
    return ('V', v['net'], sp[0], sp[-1], R(v['x']), R(v['y']), R(v['size']), R(v['hole']))


exp_t = collections.Counter(tkey(t) for t in gate['tracks'])
exp_v = collections.Counter(vkey(v) for v in gate['vias'])
if len(sys.argv) > 3:
    plan = json.load(io.open(sys.argv[3], encoding='utf-8'))
    parts = [json.load(io.open(p, encoding='utf-8')) for p in sys.argv[4:]] or [plan]
    rem = (plan.get('remove') or {}) if (len(sys.argv) == 4 or any(p.get('remove') for p in parts)) else {}
    # removals: matched on layer + end points (either direction) and net, as route_emit's Kill list does
    for t in rem.get('tracks', []):
        k = [k for k in exp_t if k[1] == t['net'] and k[2] == t['layer'] and
             {k[3], k[4]} == {(R(t['x1']), R(t['y1'])), (R(t['x2']), R(t['y2']))}]
        assert len(k) == 1 and exp_t[k[0]] > 0, ('removal not on the gate board', t)
        exp_t[k[0]] -= 1
    for v in rem.get('vias', []):
        k = [k for k in exp_v if k[1] == v['net'] and (k[4], k[5]) == (R(v['x']), R(v['y']))]
        assert len(k) == 1 and exp_v[k[0]] > 0, ('removal not on the gate board', v)
        exp_v[k[0]] -= 1
    for p in parts:
        for t in p['tracks']:
            exp_t[tkey(t)] += 1
        for v in p['vias']:
            sp = hdi.span_of(v)
            for (s2, land, hole) in H.altium_objects(sp):
                exp_v[('V', v['net'], s2[0], s2[-1], R(v['x']), R(v['y']), R(land), R(hole))] += 1
got_t = collections.Counter(tkey(t) for t in got['tracks'])
got_v = collections.Counter(vkey(v) for v in got['vias'])
fail = []
for name, e, g in (('tracks', +exp_t, got_t), ('vias', +exp_v, got_v)):
    miss, extra = e - g, g - e
    print('%-6s expected %5d, in the file %5d, missing %d, extra %d' % (name, sum(e.values()), sum(g.values()), sum(miss.values()), sum(extra.values())))
    for k in list(miss)[:15]:
        print('     MISSING', k)
    for k in list(extra)[:15]:
        print('     EXTRA  ', k)
    if miss or extra:
        fail.append(name)
for key in ('top_pads', 'bottom_pads', 'th_pads'):
    a = collections.Counter((p['ref'], p['pad'], p.get('net')) for p in gate[key])
    b = collections.Counter((p['ref'], p['pad'], p.get('net')) for p in got[key])
    d1, d2 = a - b, b - a
    print('%-11s pad nets: %d differ%s' % (key, sum(d1.values()), (': expected ' + str(sorted(d1)[:13]) + ' / file ' + str(sorted(d2)[:13])) if d1 else ''))
    if d1 or d2:
        fail.append(key)
for key in ('classes', 'outline', 'land_field', 'keepouts'):
    if key in gate and gate.get(key) != got.get(key):
        print('%s differs from the gate inputs' % key)
        fail.append(key)
def rules_without_priority(rules):
    return {name: {k: v for k, v in rule.items() if k != 'PRIORITY'}
            for name, rule in (rules or {}).items()}
if rules_without_priority(gate.get('rules')) != rules_without_priority(got.get('rules')):
    print('note: rule records differ from the gate inputs; rule semantics are checked by verify_widths.py')
if gate.get('nets') != got.get('nets'):          # derived per-net escape data: reported, judged by eye, not fatal
    print('note: the per-net table (nets) differs from the gate inputs in %d net(s)' % sum(
        1 for n in set(gate['nets']) | set(got.get('nets', {})) if gate['nets'].get(n) != got.get('nets', {}).get(n)))
print('VERIFY_PLACED %s' % ('PASS' if not fail else 'FAIL: ' + ', '.join(fail)))
sys.exit(1 if fail else 0)
