# -*- coding: utf-8 -*-
"""Power ports and junctions are snapped onto the exact wire they are meant to sit on.

WHY THIS EXISTS. `tools/rail_ports.py` rewrote each rail net label in place as a power port, keeping
the label's Location. That is right for a label and wrong for a port. A net label does not have to
touch its wire -- Altium associates it with the wire it is nearest -- but a port has one electrical
hot point and it has to land ON the conductor. Some of these wires do not sit on whole units:

    |RECORD=27|...|X1=86|Y1=682|Y1_Frac=86600|X2=126|Y2=682|Y2_Frac=86600

that wire is at y 682.866, and a port written at y 682 misses it by 0.866 of a unit. The exported
netlist caught exactly two of them -- the VCC1V0 bulk bank (C141, C142, C143) and the VCC3V3 bulk
bank (C145, C146) on sheet 6, both of which are islands whose only tie to their rail was that one
name, so losing it turned them into NetC141_1 and NetC145_1. The same fault anywhere else would have
been invisible in the netlist, because the net would still have been named by something at the other
end -- which is the reason to fix every port, not just the two that showed.

This is the _Frac trap that the C40 cluster on sheet 4 already taught once: the sub-unit offsets are
real geometry, not rounding noise, and integer arithmetic silently walks past them.

WHAT IT DOES. Every RECORD=17 port and RECORD=29 junction on the five sheets is tested against every
wire using exact coordinates (unit + _Frac/100000). One already lying on a wire is left alone. One
lying within 1.5 units of a wire is projected onto the nearest point of it and rewritten with the
matching _Frac fields. One further away than that is reported and not touched, because at that
distance the intent is no longer obvious.

    python tools/snap_ports.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import rectype
from rail_ports import SHEETS

TOL = 1.5
EPS = 1e-6


def ex(b, k):
    """the exact value of a coordinate field: unit + _Frac/100000."""
    v = field(b, k)
    if v is None:
        return None
    f = field(b, k + '_Frac')
    return int(v) + (int(f) / 100000.0 if f else 0.0)


def put(b, k, value):
    """write an exact coordinate back as unit + _Frac, dropping a zero _Frac."""
    unit = int(value // 1)
    frac = int(round((value - unit) * 100000))
    if frac >= 100000:
        unit, frac = unit + 1, 0
    b = set_field(b, k, str(unit))
    if frac:
        b = set_field(b, k + '_Frac', str(frac)) if field(b, k + '_Frac') is not None else \
            b.replace(f'|{k}={unit}|'.encode(), f'|{k}={unit}|{k}_Frac={frac}|'.encode(), 1)
    elif field(b, k + '_Frac') is not None:
        b = re.sub(rb'\|' + k.encode().replace(b'.', rb'\.') + rb'_Frac=[^|\x00]*', b'', b)
    return b


def segments(recs):
    out = []
    for h, b in recs:
        if rectype(b) != 27:
            continue
        n = int(field(b, 'LocationCount') or 0)
        P = [(ex(b, f'X{k}'), ex(b, f'Y{k}')) for k in range(1, n + 1)]
        out += [(a, c) for a, c in zip(P, P[1:]) if None not in a and None not in c]
    return out


def nearest(segs, x, y):
    """(distance, point) of the closest point on any wire."""
    best = (float('inf'), None)
    for (ax, ay), (cx, cy) in segs:
        dx, dy = cx - ax, cy - ay
        L2 = dx * dx + dy * dy
        if L2 < EPS:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
        px, py = ax + t * dx, ay + t * dy
        d = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
        if d < best[0]:
            best = (d, (px, py))
    return best


def main(prj):
    total = snapped = far = 0
    for name in SHEETS:
        path = os.path.join(prj, name + '.SchDoc')
        recs = split(read_stream(path, 'FileHeader'))
        N = len(recs)
        segs = segments(recs)
        moved, away = [], []
        for i, (h, b) in enumerate(recs):
            if rectype(b) not in (17, 29):
                continue
            total += 1
            x, y = ex(b, 'Location.X'), ex(b, 'Location.Y')
            if x is None:
                continue
            d, p = nearest(segs, x, y)
            if d <= EPS:
                continue
            if d > TOL:
                away.append((rectype(b), field(b, 'Text'), x, y, d))
                continue
            b = put(put(b, 'Location.X', p[0]), 'Location.Y', p[1])
            recs[i][1] = b
            moved.append((rectype(b), field(b, 'Text'), x, y, p, d))
        snapped += len(moved)
        far += len(away)
        print(f'{name}: {len(moved)} snapped onto their wire, {len(away)} too far to guess')
        for r, t, x, y, p, d in moved:
            print(f'    R{r} {t or "junction":10} ({x:g},{y:g}) -> ({p[0]:g},{p[1]:g})  off by {d:.3f}')
        for r, t, x, y, d in away:
            print(f'    R{r} {t or "junction":10} ({x:g},{y:g}) left alone, nearest wire {d:.2f} away')
        if not moved:
            continue
        assert len(recs) == N
        blob = join(recs)
        write_stream(path, 'FileHeader', blob)
        assert read_stream(path, 'FileHeader') == blob
        back = split(read_stream(path, 'FileHeader'))
        assert int(field(back[0][1], 'Weight')) == len(back) - 1, 'header count'
        assert all(bb.endswith(b'\x00') for hh, bb in back), 'a record lost its terminator'
        segs2 = segments(back)
        left = [i for i, (hh, bb) in enumerate(back) if rectype(bb) in (17, 29)
                and ex(bb, 'Location.X') is not None
                and nearest(segs2, ex(bb, 'Location.X'), ex(bb, 'Location.Y'))[0] > EPS]
        print(f'    verify: {len(left)} ports/junctions still off a wire')
    if not snapped:
        raise SystemExit('every port and junction already lies on its wire; nothing done')
    print(f'\n{snapped} of {total} ports and junctions snapped, {far} left alone')


if __name__ == '__main__':
    main(sys.argv[2])
