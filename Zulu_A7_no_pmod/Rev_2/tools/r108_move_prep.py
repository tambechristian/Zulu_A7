"""No-PMOD Rev 2 (2026-11-13): move R108 out from under L9's body.

The JTAG-column move put R108 (0402, Bottom, VU -> LD4_A, LD4's 1k) at (6.0, 13.475), between L9's two pads -- under the
2.5 x 2.0 x 1.2 mm molded inductor -- so it cannot be assembled (independent release review, 2026-11-13). Fab B has it
at (2.525, 13.475), where this board now has the JTAG column.

    python tools/r108_move_prep.py <board model.json> <out dir>

New site (scratchpad r108/sites.py: every Bottom/Top site and orientation within 8 mm, pad boxes + 0.10 mm courtyard
clear of every other part's pad extent on that side, 0.09 mm to other-net copper, 0.30 mm to the edge; the nearest
legal Bottom site, 5.0 mm away): centre (3.400, 17.800), rotation 180, pad 1 (VU) east at (4.05, 17.8) on the VU 0.40 mm
Bottom track (a direct connection), pad 2 (LD4_A) west at (2.75, 17.8). A first choice, (3.0, 18.35) vertical with pad 1
north, put pad 2 on that VU track (a short the judge caught; the site search checked each pad against the wrong net
for the flipped orientation). The legal Top sites lie just north of the microSD socket X3, where a card would sit over the part.

Writes model.json (R108 moved, its dead copper removed: router input) and rip.json {'remove', 'remove_vias',
'moves'}. The copper removed is exactly what prune_stubs.analyse() finds dead once R108's pads have left: the jumper
vias of the 2026-11-13 via-out-of-pad pass and the stubs that fed them.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

REF = 'R108'
OLD, NEW = (6.0, 13.475), (3.4, 17.8)
PAD_NEW = {'1': (4.05, 17.8), '2': (2.75, 17.8)}     # turned 180 deg: pad 1 (VU) east, on the VU 0.40 Bottom track


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    pads = [p for p in M['pads'] if p['ref'] == REF]
    assert sorted(p['pad'] for p in pads) == ['1', '2']
    for p in pads:
        assert abs(p['y'] - OLD[1]) < 1e-3 and abs(abs(p['x'] - OLD[0]) - 0.65) < 1e-3, p
        p['x'], p['y'] = PAD_NEW[p['pad']]
    # what dies with the move: prune_stubs on the board with R108 moved
    orig = {id(t) for t in M['tracks']}
    dead_t, dead_v, nt, nv = PS.analyse(M)
    trimmed = [t for t in nt if t.get('trimmed')]
    assert not trimmed, 'prune wants to trim, not just remove: %s' % trimmed
    dead_t = [t for t in dead_t if id(t) in orig]
    ids_t, ids_v = {id(t) for t in dead_t}, {id(v) for v in dead_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    # the VU feed of the old R108-1: Top 0.40 track from the U8-1 VU via, Top jumper and the jumper via. The three touch
    # each other (a closed triangle), so prune_stubs keeps them; nothing else uses them once R108 has moved.
    chain_t = [t for t in M['tracks'] if t['net'] == 'VU' and t['layer'] == 'Top Layer' and
               {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} in
               ({(5.625, 13.15), (5.9, 13.15)}, {(5.625, 13.15), (7.025, 11.175)})]
    chain_v = [v for v in M['vias'] if v['net'] == 'VU' and (round(v['x'], 3), round(v['y'], 3)) == (5.9, 13.15)]
    assert len(chain_t) == 2 and len(chain_v) == 1, (chain_t, chain_v)
    before = C.open_count(C.islands(M))
    ct, cv = {id(t) for t in chain_t}, {id(v) for v in chain_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ct]
    M['vias'] = [v for v in M['vias'] if id(v) not in cv]
    assert C.open_count(C.islands(M)) == before, 'the VU chain carried a connection'
    dead_t += chain_t
    dead_v += chain_v
    moves = [{'ref': REF, 'x': NEW[0], 'y': NEW[1], 'dx': round(NEW[0] - OLD[0], 4), 'dy': round(NEW[1] - OLD[1], 4),
              'pad1': list(PAD_NEW['1']), 'pad_xy': {k: list(v) for k, v in PAD_NEW.items()}, 'rotation': 180}]
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump({'remove': dead_t, 'remove_vias': dead_v, 'moves': moves}, open(os.path.join(out, 'rip.json'), 'w'), indent=1)
    print('removed as dead: %d tracks, %d vias on %s' % (len(dead_t), len(dead_v),
                                                         sorted({o['net'] for o in dead_t + dead_v})))
    for o in dead_t + dead_v:
        print('  ', o)
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), dict(oc)))


if __name__ == '__main__':
    main()
