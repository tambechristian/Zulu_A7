# -*- coding: utf-8 -*-
"""Concatenate routing plans into one: python tools/stage3/merge.py out.json a.json b.json ...

Exact duplicates (same net, layer, end points and width; same net and centre for vias) are kept once
and reported.  'remove' keys are carried through as their union (stage 4b allows the removals the user
approved; route_emit checks each one matches exactly one existing primitive)."""
import io, json, sys


def key_t(t):
    e = sorted(((round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))))
    return (t['net'], t['layer'], round(t['width'], 4)) + tuple(e)


def key_v(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4))


def merge(paths):
    vias, tracks, sv, st, dup = [], [], set(), set(), 0
    rvias, rtracks, rvs, rts = [], [], set(), set()
    for p in paths:
        d = json.load(io.open(p, encoding='utf-8'))
        rem = d.get('remove') or {}
        for v in rem.get('vias', []):
            k = key_v(v)
            if k not in rvs:
                rvs.add(k); rvias.append(dict(net=v['net'], x=v['x'], y=v['y']))
        for t in rem.get('tracks', []):
            k = key_t(t)
            if k not in rts:
                rts.add(k); rtracks.append(dict(t))
        for v in d.get('vias', []):
            k = key_v(v)
            if k in sv:
                dup += 1
                continue
            sv.add(k); vias.append(dict(net=v['net'], x=v['x'], y=v['y']))
        for t in d.get('tracks', []):
            k = key_t(t)
            if k in st:
                dup += 1
                continue
            st.add(k); tracks.append(dict(t))
    out = dict(vias=vias, tracks=tracks)
    if rvias or rtracks:
        out['remove'] = dict(vias=rvias, tracks=rtracks)   # stage 4b: named removals travel with the plan
    return out, dup


def main():
    out, paths = sys.argv[1], sys.argv[2:]
    plan, dup = merge(paths)
    io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(plan, indent=1))
    rem = plan.get('remove', {})
    print('wrote %s: %d vias, %d tracks from %d plan(s), %d exact duplicate(s) dropped%s' % (out, len(plan['vias']), len(plan['tracks']), len(paths), dup,
          ', removes %d via(s) / %d track(s)' % (len(rem.get('vias', [])), len(rem.get('tracks', []))) if rem else ''))


if __name__ == '__main__':
    main()
