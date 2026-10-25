"""Clear the single-pin nets the Feather removals left behind (2026-10-23, user request).

For every net in feather_map.CLEARED_NETS: delete its net label and the wires that join that label to its one
pin, then put a no-ERC mark (RECORD=22, copied from the FPGA sheet's existing ones) on the pin's hot spot. For
feather_map.NO_ERC_ONLY (AREF) only the mark is added; the label stays because it names a Feather pin.
The script follows the wires from the label and refuses if they reach anything but that one pin, and it
refuses unless every listed net is found exactly once. Check afterwards with check_feather_schematic.py.
    python tools/clear_single_pin_nets.py      (close the SchDocs in Altium first)
"""
import glob
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feather_map as M  # noqa: E402
from sch_netlist import build, num, on_segment, sheet_objects  # noqa: E402
from schdoc import delete, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Asar_feather.PrjPcb')
NOERC_TEMPLATE = b'|RECORD=22|OwnerPartId=-1|Location.X=0|Location.Y=0|Color=255|Symbol=Thin Cross|IsActive=T|SuppressAll=T|UniqueID=AAAAAAAA\x00'


def main():
    nets = build(ROOT)
    targets = set(M.CLEARED_NETS) | set(M.NO_ERC_ONLY)
    for n in targets:
        if len(nets.get(n, [])) != 1:
            sys.exit('REFUSED: net %s has %d pins (expected 1)' % (n, len(nets.get(n, []))))
    done = {}
    rng = random.Random(20261023)
    for path in sorted(glob.glob(os.path.join(ROOT, '*.SchDoc'))):
        recs = split(read_stream(path))
        pins, wires_, juncs, labels = sheet_objects(path, recs)
        hot = {(ref, des): p for ref, des, p in pins}
        wires = [(i, [(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, int(field(b, 'LocationCount')) + 1)])
                 for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '27' and owner(b) in (None, 1)]
        hdr22 = next((h for h, b in recs if field(b, 'RECORD') == '22'), None)
        hdr25 = next((h for h, b in recs if field(b, 'RECORD') == '25'), bytes(4))
        uids = {field(b, 'UniqueID') for h, b in recs}
        drop, marks = set(), []
        for i, (h, b) in enumerate(recs):
            name = field(b, 'Text')
            if field(b, 'RECORD') != '25' or name not in targets:
                continue
            (ref, des), = nets[name]
            pin = hot.get((ref, des))
            if pin is None:
                sys.exit('REFUSED: %s label is on %s but pin %s-%s is not' % (name, os.path.basename(path), ref, des))
            # walk the wires from the label point; they may reach only this pin
            start = (num(b, 'Location.X'), num(b, 'Location.Y'))
            seen, frontier, reached = set(), [start], False
            while frontier:
                p = frontier.pop()
                if p == pin:
                    reached = True
                for wi, w in wires:
                    if wi not in seen and any(on_segment(p, a, c) for a, c in zip(w, w[1:])):
                        seen.add(wi)
                        frontier += [w[0], w[-1]]
            pts = {q for wi, w in wires if wi in seen for q in w}
            others = [x for x in pins if x[2] in pts and (x[0], x[1]) != (ref, des)]
            other_labels = [t for t, q in labels if q in pts and t != name]
            if not reached or others or other_labels:
                sys.exit('REFUSED: %s label wiring reaches %s / %s' % (name, others, other_labels))
            if name in M.CLEARED_NETS:
                drop |= seen | {i}
                drop |= {j for j, (hh, bb) in enumerate(recs) if field(bb, 'RECORD') == '29'
                         and (num(bb, 'Location.X'), num(bb, 'Location.Y')) in pts}
            if not any(field(bb, 'RECORD') == '22' and (num(bb, 'Location.X'), num(bb, 'Location.Y')) == pin
                       for hh, bb in recs):
                marks.append(pin)
            done[name] = (os.path.basename(path), '%s-%s' % (ref, des), len(seen))
        if not drop and not marks:
            continue
        for p in marks:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            while u in uids:
                u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            uids.add(u)
            b = set_field(set_field(set_field(NOERC_TEMPLATE, 'Location.X', '%g' % p[0]), 'Location.Y', '%g' % p[1]),
                          'UniqueID', u)
            recs.append([hdr22 or hdr25, b])
        out = delete(recs, drop)
        write_stream(path, join(out))
        print('%s: removed %d records, added %d no-ERC marks' % (os.path.basename(path), len(drop), len(marks)))
    missing = targets - set(done)
    if missing:
        sys.exit('INCOMPLETE: no label found for %s' % sorted(missing))
    for n in sorted(done):
        print('  %-7s %-17s %-7s %d wire(s)' % (n, *done[n]))


if __name__ == '__main__':
    main()
