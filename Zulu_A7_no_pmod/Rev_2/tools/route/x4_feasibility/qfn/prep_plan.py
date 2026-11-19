"""Create the exact pad-moved baseline and copper prep plan for a QFN build.

    python prep_plan.py base.json model.json newpads.json out_dir
"""
import collections
import copy
import json
import os
import sys


STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def tkey(track):
    ends = sorted((
        (round(track['x1'], 4), round(track['y1'], 4)),
        (round(track['x2'], 4), round(track['y2'], 4)),
    ))
    return track['net'], track['layer'], round(track['w'], 4), tuple(ends)


def span(via):
    if 'span' in via:
        return tuple(via['span'])
    a, b = STACK.index(via['from']), STACK.index(via['to'])
    return tuple(STACK[min(a, b):max(a, b) + 1])


def vkey(via):
    return (
        via['net'],
        round(via['x'], 4),
        round(via['y'], 4),
        round(via['size'], 4),
        round(via['hole'], 4),
        span(via),
    )


def difference(left, right, key):
    remaining = collections.Counter(key(item) for item in right)
    result = []
    for item in left:
        k = key(item)
        if remaining[k]:
            remaining[k] -= 1
        else:
            result.append(item)
    return result


def apply(base, plan):
    remove_t = collections.Counter(tkey(t) for t in plan['remove'])
    remove_v = collections.Counter(vkey(v) for v in plan['remove_vias'])
    tracks = []
    for item in base['tracks']:
        k = tkey(item)
        if remove_t[k]:
            remove_t[k] -= 1
        else:
            tracks.append(item)
    vias = []
    for item in base['vias']:
        k = vkey(item)
        if remove_v[k]:
            remove_v[k] -= 1
        else:
            vias.append(item)
    out = copy.deepcopy(base)
    out['tracks'] = tracks + copy.deepcopy(plan['tracks'])
    out['vias'] = vias + [dict(v, span=list(span(v))) for v in plan['vias']]
    return out


def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: prep_plan.py base.json model.json newpads.json out_dir')
    base_path, model_path, pads_path, out_dir = sys.argv[1:]
    base = json.load(open(base_path))
    model = json.load(open(model_path))
    newpads = json.load(open(pads_path))
    os.makedirs(out_dir, exist_ok=True)

    moved = copy.deepcopy(base)
    moved['pads'] = [
        p for p in moved['pads'] if p['ref'] not in ('U2', 'X4', 'U10')
    ] + newpads['u2'] + newpads['x4'] + newpads['u10']

    remove = difference(moved['tracks'], model['tracks'], tkey)
    remove_vias = difference(moved['vias'], model['vias'], vkey)
    add = difference(model['tracks'], moved['tracks'], tkey)
    add_vias = difference(model['vias'], moved['vias'], vkey)
    plan = {
        'moves': [],
        'remove': remove,
        'remove_vias': remove_vias,
        'tracks': add,
        'vias': add_vias,
    }

    rebuilt = apply(moved, plan)
    if collections.Counter(map(tkey, rebuilt['tracks'])) != collections.Counter(map(tkey, model['tracks'])):
        raise RuntimeError('prep track reconstruction failed')
    if collections.Counter(map(vkey, rebuilt['vias'])) != collections.Counter(map(vkey, model['vias'])):
        raise RuntimeError('prep via reconstruction failed')
    if moved['pads'] != model['pads']:
        raise RuntimeError('moved pad model does not match router model')

    json.dump(moved, open(os.path.join(out_dir, 'base_moved.json'), 'w'), indent=1)
    json.dump(plan, open(os.path.join(out_dir, 'prep_plan.json'), 'w'), indent=1)
    json.dump(
        {'moves': [], 'remove': remove, 'remove_vias': remove_vias},
        open(os.path.join(out_dir, 'rip.json'), 'w'),
        indent=1,
    )
    json.dump(
        {'tracks': add, 'vias': add_vias, 'remove': []},
        open(os.path.join(out_dir, 'prep_route.json'), 'w'),
        indent=1,
    )
    print(
        'prep: remove %d tracks + %d vias; add %d trimmed tracks + %d vias'
        % (len(remove), len(remove_vias), len(add), len(add_vias))
    )


if __name__ == '__main__':
    main()
