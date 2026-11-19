"""finish_e.py <router_out.json> <tag> [rip.json]   (one python process: everything runs in-process)

  1. merge: hand USB pair (usb_plan.json) + router copper; router copper identical to a ripped item cancels the rip
     (it is simply kept on the board, no delete + re-create)
  2. augment (B/augment.py logic): connector tracks inside existing copper for off-centreline T-joins
  3. compose_plan.py on prep/base_moved.json -> plan_<tag>.json (emit-ready)
  4. gates: route_check (base_moved), widthcheck (PcbDoc rules), prune_stubs on base - remove + plan, through vias in
     SMD pads, microvias in SMD pads, USB pair metrics, counts."""
import io
import math
import os
import runpy
import sys
from collections import Counter
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E  # noqa: E402
import compose_plan as CP  # noqa: E402
import prune_stubs as PS  # noqa: E402

PCBDOC = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc'
WIDTHCHECK = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/widthcheck.py'
BASE = os.path.join(E.PREP, 'base_moved.json')


def merge(rout, rip, usb):
    rk, rvk = {E.tkey(t) for t in rip['remove']}, {E.vkey(v) for v in rip['remove_vias']}
    kt = [t for t in rout['tracks'] if E.tkey(t) in rk]
    kv = [v for v in rout['vias'] if E.vkey(v) in rvk]
    ktk, kvk = {E.tkey(t) for t in kt}, {E.vkey(v) for v in kv}
    rip2 = {'remove': [t for t in rip['remove'] if E.tkey(t) not in ktk],
            'remove_vias': [v for v in rip['remove_vias'] if E.vkey(v) not in kvk]}
    route = {'tracks': usb['tracks'] + [t for t in rout['tracks'] if E.tkey(t) not in ktk],
             'vias': usb['vias'] + [v for v in rout['vias'] if E.vkey(v) not in kvk], 'remove': [], 'remove_vias': []}
    print('merge: %d tracks / %d vias of router copper are unripped board copper (kept)' % (len(kt), len(kv)))
    return rip2, route


def augment(B, R, P):
    EPS, JOIN = 1e-4, 0.01

    def proj(px, py, t, tol=0.0):
        x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return None
        k = ((px - x1) * dx + (py - y1) * dy) / L2
        L = math.sqrt(L2)
        if not (JOIN / L < k < 1 - JOIN / L):
            return None
        qx, qy = x1 + k * dx, y1 + k * dy
        d = math.hypot(px - qx, py - qy)
        if d <= EPS or d > t['w'] / 2 + tol + EPS:
            return None
        return round(qx, 4), round(qy, 4)
    rk = {E.tkey(t) for t in R['remove']}
    tracks = [t for t in B['tracks'] if E.tkey(t) not in rk] + P['tracks']
    by = {}
    for t in tracks:
        by.setdefault((t['net'], t['layer']), []).append(t)
    add, pts, seen = [], [], set()
    for t in P['tracks']:
        for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            pts.append((t['net'], t['layer'], x, y, t['w'], 0.0))
    for v in P['vias']:
        for L in E.span(v):
            if L in ('L2-GND', 'L5-VCC3V3'):
                continue
            pts.append((v['net'], L, v['x'], v['y'], 9.0, v['size'] / 2))
    for net, L, x, y, w, tol in pts:
        for o in by.get((net, L), []):
            if any(math.hypot(x - a, y - b) <= JOIN * 0.5 for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2']))):
                continue
            near = [(a, b) for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2'])) if tol == 0 and math.hypot(x - a, y - b) <= 0.02]
            if near:
                a, b = near[0]
                key = (net, L, round(x, 4), round(y, 4), (round(a, 4), round(b, 4)))
                if key not in seen:
                    seen.add(key)
                    add.append({'net': net, 'layer': L, 'w': min(w, o['w']), 'x1': round(x, 4), 'y1': round(y, 4),
                                'x2': round(a, 4), 'y2': round(b, 4)})
                continue
            q = proj(x, y, o, tol)
            if q and (net, L, round(x, 4), round(y, 4), q) not in seen:
                seen.add((net, L, round(x, 4), round(y, 4), q))
                add.append({'net': net, 'layer': L, 'w': min(w, o['w']), 'x1': round(x, 4), 'y1': round(y, 4),
                            'x2': q[0], 'y2': q[1]})
    print('augment: %d connectors' % len(add))
    return dict(P, tracks=P['tracks'] + add)


def compose(base, rip, rp):
    plan = {'moves': rip.get('moves', []), 'remove': list(rip['remove']), 'remove_vias': list(rip['remove_vias']),
            'tracks': list(rp['tracks']), 'vias': list(rp['vias'])}
    for it in range(8):
        M = CP.apply(base, plan)
        dt, dv, nt, nv = PS.analyse(M)
        if not dt and not dv:
            break
        ptk, pvk = {CP.tkey(t) for t in plan['tracks']}, {CP.vkey(v) for v in plan['vias']}
        trims = [t for t in nt if t.get('trimmed')]
        dtk, dvk = {CP.tkey(t) for t in dt}, {CP.vkey(v) for v in dv}
        plan['tracks'] = [t for t in plan['tracks'] if CP.tkey(t) not in dtk]
        plan['vias'] = [v for v in plan['vias'] if CP.vkey(v) not in dvk]
        plan['remove'] += [t for t in dt if CP.tkey(t) not in ptk]
        plan['remove_vias'] += [v for v in dv if CP.vkey(v) not in pvk]
        plan['tracks'] += [{k: v for k, v in t.items() if k != 'trimmed'} for t in trims]
        print('compose pass %d: %d dead tracks (%d trimmed), %d dead vias' % (it + 1, len(dt), len(trims), len(dv)))
    # a removed board item that the plan re-adds identically cancels out
    ptk, pvk = {CP.tkey(t) for t in plan['tracks']}, {CP.vkey(v) for v in plan['vias']}
    both_t = {CP.tkey(t) for t in plan['remove']} & ptk
    both_v = {CP.vkey(v) for v in plan['remove_vias']} & pvk
    plan['remove'] = [t for t in plan['remove'] if CP.tkey(t) not in both_t]
    plan['tracks'] = [t for t in plan['tracks'] if CP.tkey(t) not in both_t]
    plan['remove_vias'] = [v for v in plan['remove_vias'] if CP.vkey(v) not in both_v]
    plan['vias'] = [v for v in plan['vias'] if CP.vkey(v) not in both_v]
    # strip helper keys, vias as from/to objects
    plan['vias'] = [{'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'],
                     'from': E.span(v)[0], 'to': E.span(v)[-1]} for v in plan['vias']]
    return plan


def usb_metrics(plan):
    P = [t for t in plan['tracks'] if t['net'] == 'USB_D_P']
    N = [t for t in plan['tracks'] if t['net'] == 'USB_D_N']
    L = lambda ts: sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts)  # noqa: E731
    coupled = 0.0
    for a in P:
        ax, ay = a['x2'] - a['x1'], a['y2'] - a['y1']
        la = math.hypot(ax, ay)
        if la < 1e-6:
            continue
        ux, uy = ax / la, ay / la
        best = 0.0
        for b in N:
            bx, by = b['x2'] - b['x1'], b['y2'] - b['y1']
            lb = math.hypot(bx, by)
            if lb < 1e-6 or abs(ux * by - uy * bx) / lb > 1e-3:
                continue
            d = abs((b['x1'] - a['x1']) * uy - (b['y1'] - a['y1']) * ux)
            if abs(d - 0.30) > 0.02:
                continue
            s1 = (b['x1'] - a['x1']) * ux + (b['y1'] - a['y1']) * uy
            s2 = (b['x2'] - a['x1']) * ux + (b['y2'] - a['y1']) * uy
            lo, hi = max(0, min(s1, s2)), min(la, max(s1, s2))
            if hi > lo:
                best += hi - lo
        coupled += min(best, la)
    vias = [v for v in plan['vias'] if v['net'] in ('USB_D_P', 'USB_D_N')]
    layers = Counter(t['layer'] for t in P + N)
    ws = Counter(t['w'] for t in P + N)
    return {'P': round(L(P), 4), 'N': round(L(N), 4), 'mismatch': round(abs(L(P) - L(N)), 4),
            'coupled_0.30pitch': round(coupled, 3), 'vias': len(vias), 'layers': dict(layers), 'widths': dict(ws)}


def vkind(v):
    sp = E.span(v)
    return '%s>%s %.2f/%.2f' % (sp[0], sp[-1], v['size'], v['hole'])


def gates(plan, base, tag):
    out = {}
    import route_check as RC
    buf = io.StringIO()
    argv = sys.argv[:]
    sys.argv[:] = ['route_check.py', os.path.join(E.EDIR, 'plan_%s.json' % tag), BASE]
    with redirect_stdout(buf):
        RC.main()
    sys.argv[:] = argv
    rc = buf.getvalue()
    out['route_check'] = [l for l in rc.splitlines() if l.startswith(('violations', 'open connections', 'PASS', 'FAIL'))]
    out['route_check_detail'] = [l.strip() for l in rc.splitlines() if l.startswith('  ')][:30]
    buf = io.StringIO()
    sys.argv[:] = ['widthcheck.py', PCBDOC, os.path.join(E.EDIR, 'plan_%s.json' % tag)]
    with redirect_stdout(buf):
        runpy.run_path(WIDTHCHECK, run_name='__main__')
    sys.argv[:] = argv
    out['widthcheck'] = [l for l in buf.getvalue().splitlines()][-6:]
    M = CP.apply(base, plan)
    dt, dv, _, _ = PS.analyse(M)
    out['dead_copper'] = {'tracks': len(dt), 'vias': len(dv),
                          'items': ['%s %s' % (t['net'], t.get('layer')) for t in dt][:10] + ['via %s %.3f,%.3f' % (v['net'], v['x'], v['y']) for v in dv][:10]}
    oc = E.C.open_count(E.C.islands(M))
    out['open'] = {k: v for k, v in oc.items() if v}
    th_in, uv_in = [], []
    for v in plan['vias']:
        hits = E.via_in_pads(M, v)
        if not hits:
            continue
        desc = ['%s-%s(%s,%s)' % (p['ref'], p['pad'], p['net'], l[:3]) for l, p in hits]
        if v['size'] >= 0.349:
            th_in.append('%s %.3f,%.3f %s' % (v['net'], v['x'], v['y'], desc))
        else:
            uv_in.append('%s %.3f,%.3f %s %s' % (v['net'], v['x'], v['y'], vkind(v), desc))
    out['through_vias_in_smd_pads'] = th_in
    out['microvias_in_smd_pads'] = uv_in
    out['usb'] = usb_metrics(M)
    out['counts'] = {'tracks_added': len(plan['tracks']), 'tracks_removed': len(plan['remove']),
                     'vias_added': dict(Counter(vkind(v) for v in plan['vias'])),
                     'vias_removed': dict(Counter(vkind(v) for v in plan['remove_vias'])),
                     'via_objects_added': len(plan['vias']), 'via_objects_removed': len(plan['remove_vias'])}
    Ls = lambda ts: round(sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts), 2)  # noqa: E731
    out['track_length_mm'] = {'added': Ls(plan['tracks']), 'removed': Ls(plan['remove'])}
    return out


def main():
    rout = E.load(sys.argv[1])
    tag = sys.argv[2]
    rip = E.load(sys.argv[3] if len(sys.argv) > 3 else os.path.join(E.EDIR, 'rip_E1.json'))
    usb = E.load(os.path.join(E.EDIR, 'usb_plan.json'))
    base = E.load(BASE)
    rip2, route = merge(rout, rip, usb)
    M0 = CP.apply(base, {'remove': rip2['remove'], 'remove_vias': rip2['remove_vias'], 'tracks': route['tracks'],
                         'vias': route['vias']})
    oc0 = E.C.open_count(E.C.islands(M0))
    print('before compose: open %d %s' % (sum(oc0.values()), {k: v for k, v in oc0.items() if v}))
    route = augment(base, rip2, route)
    E.dump(route, os.path.join(E.EDIR, 'route_%s.json' % tag), 0)
    E.dump(rip2, os.path.join(E.EDIR, 'rip_%s.json' % tag), 0)
    plan = compose(base, rip2, route)
    E.dump(plan, os.path.join(E.EDIR, 'plan_%s.json' % tag), 1)
    g = gates(plan, base, tag)
    import json
    print(json.dumps(g, indent=1))


if __name__ == '__main__':
    main()
