"""Turn the copied Zulu A7 schematic into the Feather schematic, at file level (2026-10-23).

Every decision comes from feather_map.py:
  sheet 1  U5/U6/U7 EN pins leave VU and join the new net EN (the VIN-EN tie wires and their junctions go);
           X1 becomes the USB-C part: ID pin 4 -> CC1 (net USB-CC1), MH1 -> CC2 (net USB-CC2, the GND bus is
           shortened off it), MS1/MS2 deleted, footprint and parameters swapped.
  sheet 2  X2 becomes the Feather connector: 12 gates deleted, the rest renumbered 1-28, four gate labels
           renamed (AREF, VBATT, EN, USB5V0); J1 and R29-R33 deleted; R26-R28 re-used (EN pull-up, CC Rd).
  sheet 3  U3 pins renumbered TSOP -> FBGA balls; U3/U4 footprints and parameters swapped.
  sheet 4  U2/JP3/JP4/U10 footprints and parameters swapped (U10 kept, in the 2x3 TDFN).
Wires, labels, ports, junctions and no-ERC marks left dangling by a deleted part are removed with it.
The script refuses to run on an already converted project; check the result with check_feather_schematic.py.
    python tools/apply_feather_schematic.py      (close the project in Altium first)
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feather_map as M  # noqa: E402
from sch_netlist import DIRS, num, on_segment  # noqa: E402
from schdoc import del_field, delete, field, join, read_stream, set_field, split, subtree, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Zulu_feather.PrjPcb')
rng = random.Random(20261023)


def owner(b):
    v = field(b, 'OwnerIndex')
    return int(v) + 1 if v is not None else None


class Sheet:
    def __init__(self, n):
        self.path = os.path.join(ROOT, 'zulu_a7_%d.SchDoc' % n)
        self.recs = split(read_stream(self.path))
        assert join(self.recs) == read_stream(self.path)
        self.drop = set()
        self.uids = {field(b, 'UniqueID') for h, b in self.recs}
        self.log = []

    # ---- lookup -------------------------------------------------------------------------------
    def comps(self, ref):
        out = [owner(b) for h, b in self.recs if field(b, 'RECORD') == '34' and field(b, 'Text') == ref]
        if not out:
            raise SystemExit('REFUSED: %s not found on %s' % (ref, self.path))
        return out

    def children(self, c, rec=None):
        return [i for i, (h, b) in enumerate(self.recs)
                if owner(b) == c and (rec is None or field(b, 'RECORD') == rec)]

    def pins(self, c, all_parts=False):
        """[(index, designator, hot spot)] of the placed part (or of every part)."""
        cur = field(self.recs[c][1], 'CurrentPartId') or '1'
        out = []
        for i in self.children(c, '2'):
            b = self.recs[i][1]
            if not all_parts and field(b, 'OwnerPartId') not in (cur, '-1', None):
                continue
            dx, dy = DIRS[int(field(b, 'PinConglomerate') or 0) & 3]
            ln = num(b, 'PinLength')
            out.append((i, field(b, 'Designator'),
                        (round(num(b, 'Location.X') + dx * ln, 4), round(num(b, 'Location.Y') + dy * ln, 4))))
        return out

    def live(self, rec):
        return [(i, b) for i, (h, b) in enumerate(self.recs)
                if i not in self.drop and field(b, 'RECORD') == rec and (rec != '29' or field(b, 'OwnerPartId') in ('-1', None))]

    def wires(self):
        out = []
        for i, b in self.live('27'):
            if owner(b) not in (None, 0):
                continue
            n = int(field(b, 'LocationCount'))
            out.append((i, [(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, n + 1)]))
        return out

    def live_hotspots(self):
        pts = []
        for i, (h, b) in enumerate(self.recs):
            if field(b, 'RECORD') == '1' and i not in self.drop:
                pts += [p for _, _, p in self.pins(i)]
        return pts

    def at(self, rec, p):
        return [i for i, b in self.live(rec) if (num(b, 'Location.X'), num(b, 'Location.Y')) == p]

    def far_end(self, p):
        """The other end of the single two-point wire that ends at p."""
        hits = [(i, w) for i, w in self.wires() if p in (w[0], w[-1])]
        if len(hits) != 1:
            raise SystemExit('REFUSED: %d wires end at %s on %s' % (len(hits), p, self.path))
        i, w = hits[0]
        return w[-1] if w[0] == p else w[0]

    # ---- edits ----------------------------------------------------------------------------------
    def uid(self):
        while True:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            if u not in self.uids:
                self.uids.add(u)
                return u

    def set(self, i, key, value):
        self.recs[i][1] = set_field(self.recs[i][1], key, value)

    def relabel(self, p, new):
        hits = self.at('25', p)
        if len(hits) != 1:
            raise SystemExit('REFUSED: %d net labels at %s on %s' % (len(hits), p, self.path))
        old = field(self.recs[hits[0]][1], 'Text')
        self.set(hits[0], 'Text', new)
        self.log.append('label %s -> %s at %s' % (old, new, p))

    def add_label(self, p, text):
        tmpl = next(b for i, b in self.live('25') if field(b, 'Justification') in (None, '0'))
        b = del_field(del_field(tmpl, 'Location.X_Frac'), 'Location.Y_Frac')
        b = set_field(b, 'Location.X', ('%g' % p[0]))
        b = set_field(b, 'Location.Y', ('%g' % p[1]))
        b = set_field(b, 'Text', text)
        b = set_field(b, 'UniqueID', self.uid())
        top = max(int(field(bb, 'IndexInSheet') or 0) for h, bb in self.recs)
        b = set_field(b, 'IndexInSheet', str(top + 1))
        hdr = next(h for h, bb in self.recs if bb is tmpl)
        self.recs.append([hdr, b])
        self.log.append('new label %s at %s' % (text, p))

    def drop_comp(self, c):
        seeds = [p for _, _, p in self.pins(c)]
        self.drop |= subtree(self.recs, [c])
        return seeds

    def cleanup(self, seeds):
        """Remove wires/labels/ports/junctions/no-ERC marks that only served deleted pins."""
        seeds = set(seeds)
        for _ in range(4):
            hot = self.live_hotspots()
            ws = self.wires()

            def touches(p, skip):
                if p in hot:
                    return True
                for j, w in ws:
                    if j in skip:
                        continue
                    if any(on_segment(p, a, b) for a, b in zip(w, w[1:])):
                        return True
                return False

            changed = False
            for i, w in ws:
                ends = (w[0], w[-1])
                if not any(e in seeds for e in ends):
                    continue
                if not any(touches(e, {i}) for e in ends):
                    self.drop.add(i)
                    seeds |= set(w)
                    changed = True
            for rec in ('25', '17', '29', '22'):
                for i, b in self.live(rec):
                    p = (num(b, 'Location.X'), num(b, 'Location.Y'))
                    if p in seeds and not touches(p, set()):
                        self.drop.add(i)
                        changed = True
            if not changed:
                break

    def footprint(self, ref, name):
        n = 0
        for c in self.comps(ref):
            for il in self.children(c, '44'):
                for im in self.children(il, '45'):
                    self.set(im, 'ModelName', name)
                    n += 1
        self.log.append('%s footprint -> %s on %d placed parts' % (ref, name, n))

    def params(self, ref, values):
        for c in self.comps(ref):
            for i in self.children(c, '41'):
                k = field(self.recs[i][1], 'Name')
                if k in values:
                    self.set(i, 'Text', values[k])
        self.log.append('%s parameters %s' % (ref, ', '.join(sorted(values))))

    def save(self):
        out = delete(self.recs, self.drop) if self.drop else self.recs
        out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
        write_stream(self.path, join(out))
        print('%s: %d records -> %d' % (os.path.basename(self.path), len(self.recs), len(out)))
        for line in self.log:
            print('   ' + line)


def sheet1():
    s = Sheet(1)
    seeds = []
    for ref in ('U5', 'U6', 'U7'):
        c = s.comps(ref)[0]
        hs = {d: p for _, d, p in s.pins(c)}
        vin, en = hs['1'], hs['3']
        tie = [i for i, w in s.wires() if set(w) == {vin, en}]
        if len(tie) != 1:
            raise SystemExit('REFUSED: %s has no single VIN-EN tie wire' % ref)
        s.drop.add(tie[0])
        s.drop |= set(s.at('29', vin))
        s.add_label(en, 'EN')
        s.log.append('%s EN split from VIN' % ref)
    c = s.comps('X1')[0]
    pins = {d: (i, p) for i, d, p in s.pins(c)}
    i4, p4 = pins['4']
    s.set(i4, 'Name', M.X1_PINS['4'][0])
    s.drop |= set(s.at('22', p4))
    s.add_label(p4, M.X1_PINS['4'][1])
    imh, pmh = pins['MH1']
    bus = [(i, w) for i, w in s.wires() if pmh in (w[0], w[-1])]
    if len(bus) != 1 or len(bus[0][1]) != 2:
        raise SystemExit('REFUSED: MH1 is not at the end of one GND bus wire')
    i, w = bus[0]
    nxt = pins['MH2'][1]
    k = 1 if w[0] == pmh else 2
    s.set(i, 'Y%d' % k, '%g' % nxt[1])
    s.set(i, 'X%d' % k, '%g' % nxt[0])
    s.set(imh, 'Name', M.X1_PINS['MH1'][0])
    s.add_label(pmh, M.X1_PINS['MH1'][1])
    s.log.append('X1 GND bus shortened off MH1')
    for d in M.X1_DROPPED_PINS:
        s.drop |= subtree(s.recs, [pins[d][0]])
        s.log.append('X1 pin %s deleted' % d)
    s.footprint('X1', M.FOOTPRINT['X1'])
    s.params('X1', M.PARAMS['X1'])
    s.save()


def sheet2():
    s = Sheet(2)
    gates = {}
    for c in s.comps('X2'):
        ps = s.pins(c)
        if ps:
            gates[int(ps[0][1])] = (c, ps[0][2])
    if sorted(gates) != list(range(1, 41)):
        raise SystemExit('REFUSED: X2 gates are not pins 1-40 (already converted?)')
    for pad, (name, old, label) in M.FEATHER.items():
        if label:
            s.relabel(s.far_end(gates[old][1]), label)
    pin2_ends = {}
    for ref, (n1, n2, value, mpn) in M.REUSED.items():
        c = s.comps(ref)[0]
        hs = {d: p for _, d, p in s.pins(c)}
        s.relabel(s.far_end(hs['1']), n1)
        pin2_ends[ref] = s.far_end(hs['2'])
        s.params(ref, {'Comment': value, 'MANF#': mpn})
    seeds = []
    for ref in ('J1', 'R29', 'R30', 'R31', 'R32', 'R33'):
        seeds += s.drop_comp(s.comps(ref)[0])
    for old in M.X2_DROPPED:
        seeds += s.drop_comp(gates[old][0])
    s.log.append('deleted J1, R29-R33 and X2 gates %s' % M.X2_DROPPED)
    s.cleanup(seeds)
    for ref, (n1, n2, value, mpn) in M.REUSED.items():
        # the R-to-J1 wire carries the old PMOD-n label somewhere along it: rename it
        end = pin2_ends[ref]
        w = next(w for i, w in s.wires() if end in (w[0], w[-1]))
        on = [i for i, b in s.live('25')
              if any(on_segment((num(b, 'Location.X'), num(b, 'Location.Y')), a, c) for a, c in zip(w, w[1:]))]
        if len(on) == 1:
            s.relabel((num(s.recs[on[0]][1], 'Location.X'), num(s.recs[on[0]][1], 'Location.Y')), n2)
        elif not on:
            s.add_label(end, n2)
        else:
            raise SystemExit('REFUSED: %d labels on the %s pin-2 wire' % (len(on), ref))
    n = 0
    for c in s.comps('X2'):
        if c in s.drop:
            continue
        for i, d, p in s.pins(c, all_parts=True):
            old = int(d)
            s.set(i, 'Designator', str(M.X2_OLD_TO_NEW[old]) if old in M.X2_OLD_TO_NEW else 'X%d' % old)
            n += 1
    s.log.append('X2 pins renumbered on the 29 kept placed parts (%d pin records)' % n)
    s.footprint('X2', M.FOOTPRINT['X2'])
    s.params('X2', M.PARAMS['X2'])
    s.save()


def sheet3():
    s = Sheet(3)
    n = 0
    for c in s.comps('U3'):
        for i, d, p in s.pins(c, all_parts=True):
            if not d.isdigit():
                raise SystemExit('REFUSED: U3 pin %s is not a TSOP number (already converted?)' % d)
            s.set(i, 'Designator', M.SDRAM_BALL[int(d)])
            n += 1
    s.log.append('U3 pins renumbered to FBGA balls (%d pin records)' % n)
    for ref in ('U3', 'U4'):
        s.footprint(ref, M.FOOTPRINT[ref])
        s.params(ref, M.PARAMS[ref])
    s.save()


def sheet4():
    s = Sheet(4)
    for ref in ('U2', 'JP3', 'JP4', 'U10'):
        s.footprint(ref, M.FOOTPRINT[ref])
        s.params(ref, M.PARAMS[ref])
    s.save()


if __name__ == '__main__':
    only = sys.argv[sys.argv.index('--sheet') + 1] if '--sheet' in sys.argv else None
    for n, fn in (('2', sheet2), ('1', sheet1), ('3', sheet3), ('4', sheet4)):
        if only in (None, n):
            fn()
