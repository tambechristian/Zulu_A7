"""Lay X2's gates out like the Feather board (2026-10-23, user request).

Left column = the 16-pin strip, pads 1-16 top to bottom; right column = the 12-pin strip, pads 17-28, starting
level with pad 5 (on the board pad 17 sits across from pad 5). Rows are 10 units apart from the old top row.
Each X2 gate ("slot") is a placed part showing one pin; every placed copy carries all 28 pins at the same spot,
so a slot is re-pointed by its CurrentPartId instead of redrawing it. Per slot the script:
  - sets CurrentPartId to the part that carries the wanted pad, and moves the GATE text to that part with the
    Feather pin name (RST, 3V3, AREF, GND, A0 ...);
  - moves the slot (all its records), its wire and its net label to the new row, and sets the label to the pad's
    net (taken from the current netlist, so connectivity does not change). A no-ERC mark follows its PIN (AREF).
  (The first run on 2026-10-23 moved the AREF mark with its slot onto MOSI; it was moved back by hand-run code
  and this version fixes the logic.)
There are 15 left and 13 right slots for 16 + 12 pads, so one left slot is cloned (new UniqueIDs) and the lowest
right slot is deleted. The four outline lines are fitted to the new rows. check_feather_schematic.py and
sch_vs_board.py must still pass afterwards.
    python tools/arrange_x2.py      (close asar_a7_2.SchDoc in Altium first)
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feather_map as M  # noqa: E402
from sch_netlist import build, num  # noqa: E402
from schdoc import delete, field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Asar_feather.PrjPcb')
PATH = os.path.join(ROOT, 'asar_a7_2.SchDoc')
TOP_Y, PITCH = 1149, 10
LEFT_X, RIGHT_X = 185, 325
YKEY = re.compile(rb'(\|(?:Location\.Y|Corner\.Y|Y\d+)=)(-?\d+)')
rng = random.Random(28)


def shift_y(body, dy):
    return YKEY.sub(lambda m: m.group(1) + str(int(m.group(2)) + dy).encode(), body)


def main():
    nets = build(ROOT)
    pad_net = {d: n for n, pins in nets.items() for r, d in pins if r == 'X2'}
    recs = split(read_stream(PATH))
    uids = {field(b, 'UniqueID') for h, b in recs}
    texts = {field(b, 'Text') for h, b in recs}

    def new_uid():
        while True:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            if u not in uids and u not in texts:
                uids.add(u)
                return u

    refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
    slots = []
    for c, ref in refs.items():
        if ref != 'X2':
            continue
        cb = recs[c][1]
        cur = field(cb, 'CurrentPartId')
        pins = [(i, field(recs[i][1], 'OwnerPartId'), field(recs[i][1], 'Designator'))
                for i, (h, b) in enumerate(recs) if owner(b) == c and field(b, 'RECORD') == '2']
        if not any(p == cur for i, p, d in pins):
            continue                                            # the outline/parameter part, no pin
        loc = (num(cb, 'Location.X'), num(cb, 'Location.Y'))
        wire = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '27' and owner(b) in (None, 1)
                and loc in ((num(b, 'X1'), num(b, 'Y1')), (num(b, 'X2'), num(b, 'Y2')))]
        if len(wire) != 1:
            sys.exit('REFUSED: X2 slot at %s has %d wires' % (loc, len(wire)))
        wb = recs[wire[0]][1]
        far = [p for p in ((num(wb, 'X1'), num(wb, 'Y1')), (num(wb, 'X2'), num(wb, 'Y2'))) if p != loc][0]
        label = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '25'
                 and (num(b, 'Location.X'), num(b, 'Location.Y')) == far]
        marks = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '22'
                 and (num(b, 'Location.X'), num(b, 'Location.Y')) == loc]
        gate = [i for i, (h, b) in enumerate(recs) if owner(b) == c and field(b, 'Name') == 'GATE']
        if len(label) != 1 or len(gate) != 1:
            sys.exit('REFUSED: X2 slot at %s: %d labels, %d GATE texts' % (loc, len(label), len(gate)))
        slots.append({'comp': c, 'loc': loc, 'wire': wire[0], 'label': label[0], 'marks': marks, 'gate': gate[0],
                      'right': field(cb, 'IsMirrored') == 'T', 'pins': pins})
    left = sorted([s for s in slots if not s['right']], key=lambda s: -s['loc'][1])
    right = sorted([s for s in slots if s['right']], key=lambda s: -s['loc'][1])
    if (len(left), len(right)) != (15, 13):
        sys.exit('REFUSED: expected 15 left + 13 right slots, found %d + %d (already arranged?)' % (len(left), len(right)))
    part_of = {d: p for i, p, d in left[0]['pins']}

    # clone the first left slot (its whole record tree, wire and label) for the 16th left row
    src = left[0]
    tree = sorted(subtree(recs, [src['comp']]))
    base = len(recs)
    new_index = {old: base + k for k, old in enumerate(tree)}
    for old in tree:
        h, b = recs[old]
        o = owner(b)
        if o in new_index:
            b = set_field(b, 'OwnerIndex', str(new_index[o] - 1))
        if field(b, 'UniqueID'):
            b = set_field(b, 'UniqueID', new_uid())
        if field(b, 'Name') == 'PinUniqueId':
            b = set_field(b, 'Text', new_uid())
        recs.append([h, b])
    extra = []
    for k in ('wire', 'label'):
        h, b = recs[src[k]]
        recs.append([h, set_field(b, 'UniqueID', new_uid())])
        extra.append(len(recs) - 1)
    gate = [i for i in range(base, base + len(tree)) if field(recs[i][1], 'Name') == 'GATE'][0]
    left.append({'comp': base, 'loc': src['loc'], 'wire': extra[0], 'label': extra[1], 'marks': [], 'gate': gate,
                 'right': False, 'pins': src['pins']})

    # drop the lowest right slot
    gone = right.pop()
    drop = subtree(recs, [gone['comp']]) | {gone['wire'], gone['label']} | set(gone['marks'])

    names = {pad: name for pad, (name, old, label) in M.FEATHER.items()}
    plan = [(s, pad, TOP_Y - PITCH * (pad - 1)) for s, pad in zip(left, range(1, 17))]
    plan += [(s, pad, TOP_Y - PITCH * (4 + pad - 17)) for s, pad in zip(right, range(17, 29))]
    # a no-ERC mark belongs to the PIN it sits on (AREF), not to the slot: send it to that pad's new row
    pad_of_part = {p: d for i, p, d in left[0]['pins']}
    mark_to_pad = {m: pad_of_part[field(recs[s['comp']][1], 'CurrentPartId')] for s in left + right for m in s['marks']}
    row_y = {pad: y for s, pad, y in plan}
    for m, pad in mark_to_pad.items():
        recs[m][1] = set_field(recs[m][1], 'Location.Y', str(row_y[int(pad)]))
    for s, pad, y in plan:
        dy = int(y - s['loc'][1])
        part = part_of[str(pad)]
        for i in subtree(recs, [s['comp']]) | {s['wire'], s['label']}:
            recs[i][1] = shift_y(recs[i][1], dy)
        recs[s['comp']][1] = set_field(recs[s['comp']][1], 'CurrentPartId', part)
        g = set_field(recs[s['gate']][1], 'OwnerPartId', part)
        recs[s['gate']][1] = set_field(g, 'Text', names[pad])
        recs[s['label']][1] = set_field(recs[s['label']][1], 'Text', pad_net[str(pad)])

    # outline: x 205..305, from the top row + 10 down to the last row - 10
    bottom = TOP_Y - PITCH * 15 - PITCH
    outline = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '6' and owner(b) is None
               and {num(b, 'X1'), num(b, 'X2')} <= {205.0, 305.0} and {num(b, 'Y1'), num(b, 'Y2')} <= {909.0, 1159.0}]
    if len(outline) != 4:
        sys.exit('REFUSED: found %d outline lines' % len(outline))
    for i in outline:
        b = recs[i][1]
        for k in ('Y1', 'Y2'):
            if num(b, k) == 909.0:
                b = set_field(b, k, str(bottom))
        recs[i][1] = b

    out = delete(recs, drop)
    write_stream(PATH, join(out))
    print('X2 arranged: left pads 1-16 at y %d..%d, right pads 17-28 at y %d..%d; 1 slot cloned, 1 deleted; '
          'outline 909 -> %d' % (TOP_Y, TOP_Y - 150, TOP_Y - 40, TOP_Y - 150, bottom))


if __name__ == '__main__':
    main()
