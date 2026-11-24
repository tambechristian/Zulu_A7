"""Through-via-in-pad acceptance check for the Asar Feather (the owner's request: PCBWay must not have to
resin-plug and plate over any through via).  Read-only; deterministic; ~0.1 s.

    python vip_check.py <model.json> [--plan plan.json] [--truth pad_truth.json] [--json out.json] [--quiet]

<model.json>  route_model.py format (pads/tracks/vias, board mm, y up).  When parts were moved, pass the
              MOVED model (pads at their new places, e.g. model_moved.json or model_final.json).
--plan        apply a plan.json first ({remove, remove_vias, tracks, vias}: vias by from/to or span, as
              emit_copper.py consumes it).  'moves' are NOT applied: give the moved model instead.
--truth       pad shape class + mask expansion per pad (vip_truth.py output, proven against the released
              Gerbers).  Default: pad_truth.json beside this tool.  Without it the model's shape and the
              board's SolderMaskExpansion rules (built in below) are used and a warning is printed.

Checked: EVERY through via (span Top Layer .. Bottom Layer) against EVERY SMD pad on Top or Bottom
(through-hole pads excluded; both outer sides count, a through via exists on both).
  (a) the via land (its own size, 0.35) overlaps or touches the pad copper (real shape: rect / round,
      w x h already rotated in the model).  Touch = land-to-copper gap < 1e-4 mm.  Any net.
  (b) the via HOLE edge is closer than 0.05 mm (mask registration) to the pad's solder-mask opening
      (copper grown by that pad's expansion: rect -> rect + e, round -> radius + e).  Any net.
      Pass needs hole-edge-to-opening >= 0.05 (1e-6 tolerance).
  (c) the via land lies partly inside the mask opening of a pad of ANOTHER net.
Each (via, pad) contact gets a kind:
  in_pad / on_pad_edge / land_only   (a), with tools/fab_facts.py's position rule (hole fully inside the
                                     copper / hole edge crosses the copper edge / only the land overlaps)
  touch                              (a) land within 1e-4 of the copper but not overlapping by fab_facts' rule
  mask_near                          (b) only: land clear of copper, hole edge < 0.05 from the opening
  land_in_mask_other_net             (c) only
Distances per contact: d_cu (via centre to pad copper, signed, < 0 inside), land_gap (= d_cu - land/2),
hole_mask_gap (hole edge to the mask opening, signed), land_mask (= opening distance - land/2).
For a via to pass against a pad: d_cu >= land/2 + 1e-4 and d_mask >= hole/2 + 0.05 (and, other net,
d_mask >= land/2).  With the default 0.05 expansion that is a via centre >= 0.20 mm from the pad copper
(U2 0.185, X3 0.19, C3 0.17, U1 0.175 from (a)).

Exit code: 0 no violation, 1 violations, 2 bad input.
"""
import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
OUTER = {'Top Layer': 'T', 'Bottom Layer': 'B'}
SIDE_NAME = {'T': 'Top', 'B': 'Bottom'}
MASK_REG = 0.05        # mm, hole edge to any mask opening
TOUCH = 1e-4           # mm, land-to-copper gap below which the land "touches" the pad
POS_EPS = 1e-4         # fab_facts.py's tolerance for the in/edge/land position rule
EPS = 1e-6
# the board's enabled SolderMaskExpansion rules (Rules6): InComponent(...) first, then All; vias tented
RULE_MASK = {'C3': 0.02, 'U2': 0.035, 'U1': 0.0, 'X3': 0.04}
DEFAULT_MASK = 0.05
DEFAULT_TRUTH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pad_truth.json')


# ---- model ------------------------------------------------------------------
def span_of(v):
    if 'span' in v and v['span']:
        return list(v['span'])
    return STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def is_through(v):
    sp = span_of(v)
    return sp[0] == 'Top Layer' and sp[-1] == 'Bottom Layer'


def tkey(t):
    a, b = (round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))
    return (t['net'], t['layer'], round(t['w'], 4)) + tuple(sorted([a, b]))


def vkey(v):
    sp = span_of(v)
    return (v['net'], round(v['x'], 4), round(v['y'], 4), round(v['hole'], 4), sp[0], sp[-1])


def apply_plan(M, plan):
    """remove / remove_vias / tracks / vias of a plan.json, keyed as tools/route/jtag6/east/build.py."""
    M = dict(M)
    rt = Counter(tkey(t) for t in plan.get('remove', []))
    rv = Counter(vkey(v) for v in plan.get('remove_vias', []))
    have_t = Counter(tkey(t) for t in M['tracks'])
    have_v = Counter(vkey(v) for v in M['vias'])
    miss_t = [k for k in rt if have_t[k] < rt[k]]
    miss_v = [k for k in rv if have_v[k] < rv[k]]
    if miss_t or miss_v:
        raise ValueError('plan removes copper that is not in the model: %d tracks %s, %d vias %s'
                         % (len(miss_t), miss_t[:3], len(miss_v), miss_v[:3]))
    M['tracks'] = [t for t in M['tracks'] if tkey(t) not in rt] + [dict(t) for t in plan.get('tracks', [])]
    M['vias'] = [v for v in M['vias'] if vkey(v) not in rv] + [
        dict({q: v[q] for q in v if q not in ('from', 'to')}, span=span_of(v)) for v in plan.get('vias', [])]
    return M


# ---- pad geometry -----------------------------------------------------------
class Pad(object):
    __slots__ = ('ref', 'pad', 'net', 'x', 'y', 'side', 'hx', 'hy', 'cx', 'cy', 'r', 'e', 'shape', 'name', 'src')

    def __init__(self, p, side, shape, e, src):
        self.ref, self.pad, self.net, self.x, self.y, self.side = p['ref'], p['pad'], p['net'], p['x'], p['y'], side
        self.hx, self.hy = p['w'] / 2.0, p['h'] / 2.0
        self.shape, self.e, self.src = shape, e, src
        if shape == 'round':
            self.r = min(self.hx, self.hy)
        else:                                   # rect (an octagon would be inside its rect: conservative)
            self.r = 0.0
        self.cx, self.cy = self.hx - self.r, self.hy - self.r
        self.name = '%s-%s' % (self.ref, self.pad)

    def sd_copper(self, px, py):
        """signed distance from (px, py) to the pad copper (< 0 inside)."""
        qx, qy = abs(px - self.x) - self.cx, abs(py - self.y) - self.cy
        return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - self.r

    def sd_mask(self, px, py):
        """signed distance to the mask opening: rect grows to a sharp rect, round grows its radius."""
        if self.shape == 'round':
            qx, qy, r = abs(px - self.x) - self.cx, abs(py - self.y) - self.cy, self.r + self.e
        else:
            qx, qy, r = abs(px - self.x) - self.hx - self.e, abs(py - self.y) - self.hy - self.e, 0.0
        return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r

    def depth_ff(self, px, py):
        """tools/fab_facts.py pad_inner_depth (for its in_pad / on_pad_edge rule)."""
        dx, dy = abs(px - self.x), abs(py - self.y)
        if self.r == 0:
            return min(self.hx - dx, self.hy - dy)
        return self.r - math.hypot(max(dx - self.cx, 0.0), max(dy - self.cy, 0.0))

    def reach(self):
        return max(self.hx, self.hy) + self.e


def load_truth(path):
    if not path or not os.path.exists(path):
        return None
    T = json.load(open(path))
    out = defaultdict(list)
    for e in T['pads']:
        if e['smd']:
            for L, s in e['sides'].items():
                out[(e['ref'], e['pad'], L[0])].append((e['x'], e['y'], s['shape'], s['mask']))
    return out


def smd_pads(M, truth):
    pads, unmatched = [], []
    for p in M['pads']:
        if (p.get('drill') or 0) > 0 or len(p['layers']) != 1 or p['layers'][0] not in OUTER:
            continue
        side = OUTER[p['layers'][0]]
        cand = truth.get((p['ref'], p['pad'], side)) if truth is not None else None
        if cand:
            x, y, shape, e = min(cand, key=lambda c: math.hypot(c[0] - p['x'], c[1] - p['y']))
            pads.append(Pad(p, side, shape, e, 'truth'))
        else:
            shape = 'round' if p['shape'] in ('circle', 'round') else 'rect'
            e = RULE_MASK.get(p['ref'], DEFAULT_MASK)
            pads.append(Pad(p, side, shape, e, 'model'))
            if truth is not None:
                unmatched.append('%s-%s' % (p['ref'], p['pad']))
    return pads, unmatched


# ---- check ------------------------------------------------------------------
def check(M, truth=None):
    pads, unmatched = smd_pads(M, truth)
    grid = defaultdict(list)
    G = 1.0
    for i, p in enumerate(pads):
        rr = p.reach() + 0.5
        for gx in range(int(math.floor((p.x - rr) / G)), int(math.floor((p.x + rr) / G)) + 1):
            for gy in range(int(math.floor((p.y - rr) / G)), int(math.floor((p.y + rr) / G)) + 1):
                grid[(gx, gy)].append(i)
    thru = [v for v in M['vias'] if is_through(v)]
    out = []
    for v in sorted(thru, key=lambda v: (round(v['x'], 4), round(v['y'], 4), v['net'] or '')):
        R, H = v['size'] / 2.0, v['hole'] / 2.0
        contacts = []
        for i in sorted(set(grid.get((int(math.floor(v['x'] / G)), int(math.floor(v['y'] / G))), []))):
            p = pads[i]
            if abs(p.x - v['x']) > p.reach() + R + 0.1 or abs(p.y - v['y']) > p.reach() + R + 0.1:
                continue
            dc = p.sd_copper(v['x'], v['y'])
            dm = p.sd_mask(v['x'], v['y'])
            other = p.net != v['net']
            ra = dc - R < TOUCH
            rb = dm - H < MASK_REG - EPS
            rc = other and dm < R - EPS
            if not (ra or rb or rc):
                continue
            d_ff = max(dc, 0.0)
            if ra and d_ff < R - POS_EPS:
                kind = ('in_pad' if p.depth_ff(v['x'], v['y']) >= H - POS_EPS
                        else 'on_pad_edge' if d_ff < H - POS_EPS else 'land_only')
            elif ra:
                kind = 'touch'
            elif rb:
                kind = 'mask_near'
            else:
                kind = 'land_in_mask_other_net'
            contacts.append(dict(pad=p.name, ref=p.ref, pad_no=p.pad, side=p.side, pad_net=p.net,
                                 rules=''.join(k for k, f in (('a', ra), ('b', rb), ('c', rc)) if f), kind=kind,
                                 d_cu=round(dc, 4), land_gap=round(dc - R, 4), hole_mask_gap=round(dm - H, 4),
                                 land_mask=round(dm - R, 4), mask_exp=p.e, shape=p.shape, other_net=other,
                                 ff_overlap=round(R - d_ff, 4)))
        if contacts:
            contacts.sort(key=lambda c: (c['side'], c['pad']))
            out.append(dict(net=v['net'], x=round(v['x'], 4), y=round(v['y'], 4), size=v['size'], hole=v['hole'],
                            rules=''.join(sorted(set(''.join(c['rules'] for c in contacts)))), contacts=contacts))
    S = summarize(out, thru, pads)
    S['pads_from_truth'] = sum(1 for p in pads if p.src == 'truth')
    S['pads_unmatched_in_truth'] = unmatched
    return S, out


def summarize(out, thru, pads):
    cs = [c for v in out for c in v['contacts']]
    a = [c for c in cs if 'a' in c['rules']]
    return dict(
        through_vias=len(thru), smd_pads=len(pads),
        smd_pads_by_side=dict(sorted(Counter(SIDE_NAME[p.side] for p in pads).items())),
        violating_vias=len(out), contacts=len(cs),
        rule_a=dict(vias=sum(1 for v in out if 'a' in v['rules']), contacts=len(a),
                    by_kind=dict(sorted(Counter(c['kind'] for c in a).items())),
                    by_side=dict(sorted(Counter(SIDE_NAME[c['side']] for c in a).items()))),
        rule_b=dict(vias=sum(1 for v in out if 'b' in v['rules']), contacts=sum(1 for c in cs if 'b' in c['rules']),
                    vias_only_b=sum(1 for v in out if v['rules'] == 'b'),
                    contacts_only_b=sum(1 for c in cs if c['rules'] == 'b')),
        rule_c=dict(vias=sum(1 for v in out if 'c' in v['rules']), contacts=sum(1 for c in cs if 'c' in c['rules'])),
        by_kind=dict(sorted(Counter(c['kind'] for c in cs).items())),
        by_net=dict(sorted(Counter(v['net'] for v in out).items(), key=lambda kv: (-kv[1], str(kv[0])))))


def report(S, out, src, quiet=False):
    print('vip_check %s' % src)
    print('  %d through vias, %d SMD pads (%s); pad shape/mask from truth: %d, unmatched %d%s' % (
        S['through_vias'], S['smd_pads'], ', '.join('%s %d' % kv for kv in S['smd_pads_by_side'].items()),
        S['pads_from_truth'], len(S['pads_unmatched_in_truth']),
        (' (' + ' '.join(S['pads_unmatched_in_truth'][:8]) + ')') if S['pads_unmatched_in_truth'] else ''))
    ra, rb, rc = S['rule_a'], S['rule_b'], S['rule_c']
    print('  (a) land touches pad copper:        %3d vias, %3d contacts %s %s' % (
        ra['vias'], ra['contacts'], ra['by_kind'], ra['by_side']))
    print('  (b) hole edge < %.2f from mask:     %3d vias, %3d contacts (%d vias / %d contacts beyond (a))' % (
        MASK_REG, rb['vias'], rb['contacts'], rb['vias_only_b'], rb['contacts_only_b']))
    print('  (c) land in other-net mask opening: %3d vias, %3d contacts' % (rc['vias'], rc['contacts']))
    print('  by net: %s' % ' '.join('%s %d' % kv for kv in S['by_net'].items()))
    for v in ([] if quiet else out):
        print('  %-14s (%7.3f, %7.3f) %-3s %s' % (v['net'], v['x'], v['y'], v['rules'], '; '.join(
            '%s/%s %s%s d_cu %.3f land_gap %.3f hole_mask %.3f' % (
                c['pad'], c['side'], c['kind'], ' [%s]' % c['pad_net'] if c['other_net'] else '',
                c['d_cu'], c['land_gap'], c['hole_mask_gap']) for c in v['contacts'])))
    print('VIP_CHECK: %d violating through vias, %d contacts -> %s' % (
        S['violating_vias'], S['contacts'], 'PASS' if not out else 'FAIL'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('model')
    ap.add_argument('--plan')
    ap.add_argument('--truth', default=DEFAULT_TRUTH)
    ap.add_argument('--json')
    ap.add_argument('--quiet', action='store_true', help='summary lines only')
    a = ap.parse_args(argv)
    try:
        M = json.load(open(a.model))
        if a.plan:
            P = json.load(open(a.plan))
            if P.get('moves'):
                print('note: plan has %d moves; they are NOT applied (pass the moved model)' % len(P['moves']))
            M = apply_plan(M, P)
    except (OSError, ValueError, KeyError) as ex:
        print('vip_check: bad input: %s' % ex)
        return 2
    truth = load_truth(a.truth)
    if truth is None:
        print('WARNING: no pad truth file (%s): model shapes + rule mask expansions used' % a.truth)
    S, out = check(M, truth)
    report(S, out, a.model + (' + ' + a.plan if a.plan else ''), a.quiet)
    if a.quiet and out:
        print('  (per-via list suppressed: --quiet)')
    if a.json:
        json.dump(dict(model=os.path.abspath(a.model), plan=a.plan and os.path.abspath(a.plan),
                       truth=a.truth if truth is not None else None,
                       rules=dict(mask_registration=MASK_REG, touch=TOUCH, pos_eps=POS_EPS),
                       summary=S, vias=out), open(a.json, 'w'), indent=1)
    return 1 if out else 0


if __name__ == '__main__':
    sys.exit(main())
