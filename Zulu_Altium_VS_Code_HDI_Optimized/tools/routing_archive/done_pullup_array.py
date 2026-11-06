# -*- coding: utf-8 -*-
"""Sheet 4, 2026-09-10: the DONE pull-up moves off R100 and onto R4's two spare elements.

WHAT AND WHY. R4 is a CTS 742C163101JP, eight isolated 100 R elements, of which six were used (A
PROG#, B DONE, C TDI, D TDO, E TMS, F TCK) and pads 7-10 were spare. The DONE pull-up was R100, a
330 R discrete sitting in the pull-up row at (812,1042) and reaching FPGA-DONE through a labelled
stub. It becomes elements G and H of R4 IN SERIES, drawn on the FPGA-DONE row itself, and R100 is
deleted.

WHY IN SERIES, AND NOT ONE ELEMENT. A single 100 R element across 3.3 V dissipates 3.3^2/100 =
109 mW, and the 742C163101JP is rated 63 mW per element -- 173 % of rating, held for as long as the
FPGA holds DONE low, which is indefinitely if configuration never completes. Two in series see half
the voltage each: 27 mW apiece, comfortably inside the rating. The pull-up becomes 200 R, so DONE
sinks 16.5 mA when low against 10 mA for the 330 R that UG470 draws. Both spare elements are used up.

WHERE IT IS DRAWN. Every vertical route from the FPGA-DONE row at y 422 crosses another row -- the
six rows run x 632..777 at y 342..442 -- so the chain goes to the right of the label column, into a
region that holds nothing at all between y 300 and y 600 past x 777:

    FPGA-DONE row extended (632,422) -> (837,422)
      wire (837,422)-(837,452)
        R4G at (837,452), pads 7 and 10, hots at x 837 and 877
      wire (877,452)-(877,492)                    the series link, labelled DONE-PU
        R4H at (837,492), pads 8 and 9, hots at x 837 and 877
      wire (837,492)-(837,522)
        VCC3V3 port at (837,522)

R1's PROGRAM_B pull-up one row above is drawn the same way -- a tap off the row up to a VCC3V3 port
-- so this is the sheet's own idiom, just two elements tall instead of one.

HOW A NEW ELEMENT IS MADE. A multi-part component is one RECORD=1 per placed part, and each one
already carries the WHOLE package: all 16 pins, all 32 body lines and every per-part parameter, with
CurrentPartId choosing which of them Altium draws. So parts 7 and 8 are made by cloning the part-1
subtree (94 records: the placement and 93 children), translating it, and setting CurrentPartId. The
translation is chosen so the clone lands where it should without any rotation: part 1 draws pads 1
and 16 at Location (602,442) and (622,442), and part 7 draws pads 7 and 10 at exactly the same two
Locations, so (+245,+10) puts G's hots on 837 and 877 at y 452 and (+245,+50) does the same for H at
y 492. Only the designator and comment are placed by hand afterwards, moved left so they clear the
two vertical wires.

Every cloned record gets a fresh UniqueID -- the six existing R4 placements each have their own, and
a duplicate is the trap tools/sc189_pin_ids.py had to clean up after. Child OwnerIndex values are
remapped into the clone.

R100 AND ITS WIRES ARE DELETED: the placement and everything it owns, its tap to the VCC3V3 rail at
(812,1052)-(812,1072), the stub (760,932)-(812,932)-(812,1032) and the FPGA-DONE label on it that
tools/done_pullup_xadc_gnd.py added. Deleting shifts every later index, so every surviving OwnerIndex
is remapped through an old->new table and the header count is rewritten -- skipping exactly that is
what once left a sheet unopenable.

U2-22 keeps its own DONE stub at (607,932)-(662,932), so the FT2232H still watches DONE through
R4B's 100 R and nothing else changes on that net.

    python tools/done_pullup_array.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import num, oi, rectype, points, fonts_of, drawn_boxes, roots, signature

SRC_PART = 1                                   # the subtree cloned, found by CurrentPartId
NEW = [dict(part='7', dx=245, dy=10, desig=(827, 441), comment=(843, 441)),
       dict(part='8', dx=245, dy=50, desig=(827, 481), comment=(843, 481))]

ROW_OLD = ((632, 422), (777, 422))
ROW_NEW = ((632, 422), (837, 422))
WIRES = [((837, 422), (837, 452)), ((877, 452), (877, 492)), ((837, 492), (837, 522))]
PORT = (837, 522)
# The node between the two elements, named so it is not an auto-name in the netlist and the BOM
# audit can state what pads 9 and 10 are on. It has to fit BETWEEN their two pad numbers: measured
# on the PDF, pad 10's digits end at y 460.5 and pad 9's begin at 493.5, so the label has 33 units
# and a character of FontID 4 is 4.23 of them -- seven characters, anchored at 462.
LINK = (877, 462, 'DONE-PU')

R100_RAIL = ((812, 1052), (812, 1072))
R100_STUB = ((760, 932), (812, 932), (812, 1032))
R100_LABEL = (760, 932, 'FPGA-DONE')

XK = ['Location.X', 'Corner.X'] + [f'X{k}' for k in range(1, 12)]
YK = ['Location.Y', 'Corner.Y'] + [f'Y{k}' for k in range(1, 12)]


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def fresh(b):
    return re.sub(rb'\|UniqueID=[A-Za-z0-9]{6,}', lambda m: b'|UniqueID=' + uid().encode(), b)


def shift(b, dx, dy):
    for k in XK:
        v = num(b, k)
        if v is not None:
            b = set_field(b, k, str(v + dx))
    for k in YK:
        v = num(b, k)
        if v is not None:
            b = set_field(b, k, str(v + dy))
    return b


def set_pts(b, pts):
    b = re.sub(rb'\|(X|Y)\d+(_Frac)?=[^|\x00]*', b'', b)
    tail = ''.join(f'|X{k}={x}|Y{k}={y}' for k, (x, y) in enumerate(pts, 1))
    b = set_field(b, 'LocationCount', str(len(pts)))
    return b[:-1] + tail.encode() + b'\x00'


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    root, place = roots(recs)
    des = {oi(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    r4 = [i for i in place if des.get(i) == 'R4']
    if any(field(recs[i][1], 'CurrentPartId') in ('7', '8') for i in r4):
        raise SystemExit('R4 already has parts 7 and 8 placed; nothing done')
    src = [i for i in r4 if field(recs[i][1], 'CurrentPartId') == str(SRC_PART)]
    assert len(src) == 1, f'R4 part {SRC_PART}: found {len(src)} placements'
    src = src[0]
    kids = sorted(j for j in range(len(recs)) if root[j] == src)
    sub = [src] + kids
    assert sub == list(range(src, src + len(sub))), 'the R4 part-1 subtree is not contiguous'
    print(f'  cloning R4 part {SRC_PART}: records {sub[0]}..{sub[-1]} ({len(sub)} records)')

    # ---- what goes -------------------------------------------------------------------------
    r100 = [i for i in place if des.get(i) == 'R100']
    assert len(r100) == 1, f'R100: found {len(r100)} placements'
    kill = {r100[0]} | {j for j in range(len(recs)) if root[j] == r100[0]}
    for pts, what in ((R100_RAIL, 'the R100 rail tap'), (R100_STUB, 'the R100 stub')):
        hit = [i for i, (h, b) in enumerate(recs) if rectype(b) == 27 and tuple(points(b)) == pts]
        assert len(hit) == 1, f'{what}: found {len(hit)}'
        kill |= set(hit)
    hit = [i for i, (h, b) in enumerate(recs)
           if rectype(b) == 25 and field(b, 'Text') == R100_LABEL[2]
           and (num(b, 'Location.X'), num(b, 'Location.Y')) == R100_LABEL[:2]]
    assert len(hit) == 1, f'the stub FPGA-DONE label: found {len(hit)}'
    kill |= set(hit)
    print(f'  deleting R100 and its wires: {len(kill)} records')
    assert not (kill & set(sub)), 'the delete set overlaps the clone source'

    # ---- the row wire grows ------------------------------------------------------------------
    row = [i for i, (h, b) in enumerate(recs) if rectype(b) == 27 and tuple(points(b)) == ROW_OLD]
    assert len(row) == 1, f'the FPGA-DONE row wire: found {len(row)}'
    recs[row[0]][1] = set_pts(recs[row[0]][1], ROW_NEW)

    # ---- rebuild without the dead records, remapping every OwnerIndex ------------------------
    keep = [i for i in range(len(recs)) if i not in kill]
    newpos = {old: new for new, old in enumerate(keep)}
    out = []
    for old in keep:
        b = recs[old][1]
        o = oi(b)
        if o is not None:
            assert o in newpos, f'record {old} is owned by a deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[o] - 1))
        out.append([recs[old][0], b])

    # ---- append the two clones ----------------------------------------------------------------
    tmpl = {i: recs[i][1] for i in sub}
    for spec in NEW:
        base = len(out)                                   # the clone's placement lands here
        for k, old in enumerate(sub):
            b = fresh(tmpl[old])
            b = shift(b, spec['dx'], spec['dy'])
            o = oi(tmpl[old])
            if o is not None:
                assert sub[0] <= o <= sub[-1], f'child {old} owned from outside the subtree'
                b = set_field(b, 'OwnerIndex', str(base + (o - sub[0]) - 1))
            if k == 0:
                b = set_field(b, 'CurrentPartId', spec['part'])
            out.append([recs[old][0], b])
        pl = out[base][1]
        assert rectype(pl) == 1 and field(pl, 'CurrentPartId') == spec['part']
        for j in range(base, base + len(sub)):
            b = out[j][1]
            if rectype(b) == 34:
                out[j][1] = set_field(set_field(b, 'Location.X', str(spec['desig'][0])),
                                      'Location.Y', str(spec['desig'][1]))
            elif rectype(b) == 41 and field(b, 'Name') == 'Comment':
                out[j][1] = set_field(set_field(b, 'Location.X', str(spec['comment'][0])),
                                      'Location.Y', str(spec['comment'][1]))
        print(f"  R4 part {spec['part']} placed at "
              f"({num(pl, 'Location.X')},{num(pl, 'Location.Y')})")

    # ---- the wires and the port ---------------------------------------------------------------
    wire_tmpl = next(b for h, b in recs if rectype(b) == 27 and len(points(b)) == 2)
    port_tmpl = next(b for h, b in recs if rectype(b) == 17 and field(b, 'Text') == 'VCC3V3'
                     and field(b, 'Orientation') == '1')
    for pts in WIRES:
        out.append([bytes(4), set_pts(fresh(wire_tmpl), pts)])
    p = fresh(port_tmpl)
    p = set_field(set_field(p, 'Location.X', str(PORT[0])), 'Location.Y', str(PORT[1]))
    out.append([bytes(4), p])
    lab_tmpl = next(b for h, b in recs if rectype(b) == 25 and field(b, 'Orientation') == '1'
                    and field(b, 'Justification') is None)
    lb = fresh(lab_tmpl)
    lb = set_field(set_field(lb, 'Location.X', str(LINK[0])), 'Location.Y', str(LINK[1]))
    out.append([bytes(4), set_field(lb, 'Text', LINK[2])])
    print(f'  {len(WIRES)} wires, a VCC3V3 port at {PORT} and the {LINK[2]} label added')

    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 4: {N} -> {len(out)} records')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    for i, (h, b) in enumerate(recs):
        o = oi(b)
        if o is not None:
            assert 0 <= o < len(recs), f'record {i} owns nothing'
            assert rectype(recs[o][1]) in (1, 2, 44, 45, 46), (i, o, rectype(recs[o][1]))
    root, place = roots(recs)
    des = {oi(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    parts = sorted(field(recs[i][1], 'CurrentPartId') for i in place if des.get(i) == 'R4')
    assert parts == ['1', '2', '3', '4', '5', '6', '7', '8'], parts
    assert not [i for i in place if des.get(i) == 'R100'], 'R100 survived'
    sig = signature(recs)
    node = [n for n in sig if any(p.startswith('R4-7') or p.startswith('R4-10') for p in n)]
    fonts = fonts_of(recs)
    boxes = drawn_boxes(recs, fonts)
    right = max(e[2][2] for e in boxes if e[1] != 6)
    print(f'verify: {len(recs)} records, R4 parts {"".join(parts)}, R100 gone, '
          f'{len(boxes)} drawn objects, rightmost non-frame x={right:.1f}')
    for n in sorted(sig):
        if any(p.split('-')[0] in ('R4',) and p.split('-')[1] in
               ('7', '8', '9', '10') for p in n if '-' in p):
            print(f'    node {n}')


if __name__ == '__main__':
    main(sys.argv[2])
