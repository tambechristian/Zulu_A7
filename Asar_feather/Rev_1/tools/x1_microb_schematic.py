"""X1 USB-C -> micro-USB B (Amphenol ICC 10118193-0001LF) on sheet 1 (2026-11-17, user: "Yes, micro-B").

    python tools/x1_microb_schematic.py            # dry run on a scratch copy of the project: prints changes + netlist diff
    python tools/x1_microb_schematic.py --apply    # same checks, then backs the sheet up to backups/ and writes it

Why: the side-entry X4 (JST S2B-PH-SM4-TB) has rear legs reaching 7.6 mm behind its face; the HRO USB-C X1 sat under
the west leg. The flanged micro-B (LCSC C132562) is 4.65 mm deep and clears that leg by 2.2 mm.

Changes on asar_a7_1.SchDoc, every old value asserted first:
  - X1: description, DeviceName, MANF, MANF#, visible Comment, footprint model -> AMPHENOL-10118193-0001LF;
  - X1 pin 4 "CC1" -> "4-ID", left unconnected (wire + USB-CC1 label removed, a No-ERC marker on its hot end);
  - X1 pin MH1 "CC2" -> "GND" (name hidden like the other shell pins), the USB-CC2 label removed and the shell GND bus
    wire extended up to MH1's hot end (260, 1142);
  - R27 / R28 (the 5.1k USB-C CC pull-downs) deleted with their USB-CC1/2 and GND label stubs.
The netlist is rebuilt from the files (tools/sch_netlist.py) before and after; the run refuses unless the only
differences are: nets USB-CC1 and USB-CC2 gone, GND loses R27-1/R28-1 and gains X1-MH1, X1-4 is left alone.
Close the sheet in Altium first.
"""
import glob
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schdoc  # noqa: E402
import sch_netlist  # noqa: E402

ROOT = os.path.dirname(HERE)
PROJ = os.path.join(ROOT, 'Asar_feather.PrjPcb')
SHEET = os.path.join(PROJ, 'asar_a7_1.SchDoc')
BACKUP = os.path.join(ROOT, 'backups', 'asar_a7_1_before_x1_microb.SchDoc')

FP = 'AMPHENOL-10118193-0001LF'
X1_PARAMS = {   # record name -> (old Text, new Text)
    'DeviceName': ('105017-0001', '10118193-0001LF'),
    'MANF': ('HRO (Korean Hroparts)', 'Amphenol ICC'),
    'MANF#': ('TYPE-C-31-M-12', '10118193-0001LF'),
    'Comment': ('USB-C receptacle, USB 2.0 (LCSC C165948)', 'Micro-USB B receptacle, USB 2.0 (LCSC C132562)'),
}
DESC = ('MINI USB Connector   Source: http://www.hirose.co.jp/cataloge_hp/e24000019.pdf',
        'Micro-USB B receptacle, flanged, SMT + 2 plated slot legs (Amphenol ICC 10118193-0001LF)')


def part_index(recs, ref):
    hits = []
    for i, (h, b) in enumerate(recs):
        if schdoc.field(b, 'RECORD') == '34' and schdoc.field(b, 'Name') == 'Designator' and schdoc.field(b, 'Text') == ref:
            hits.append(schdoc.owner(b))
    assert len(hits) == 1, (ref, hits)
    assert schdoc.field(recs[hits[0]][1], 'RECORD') == '1'
    return hits[0]


def children(recs, root):
    kids = {}
    for i, (h, b) in enumerate(recs):
        o = schdoc.owner(b)
        if o is not None:
            kids.setdefault(o, []).append(i)
    out, st = set(), [root]
    while st:
        k = st.pop()
        for c in kids.get(k, []):
            if c not in out:
                out.add(c)
                st.append(c)
    return out


def one(recs, pred, what):
    hit = [i for i, (h, b) in enumerate(recs) if pred(b)]
    assert len(hit) == 1, (what, hit)
    return hit[0]


def edit(recs):
    changes = []

    def put(i, key, old, new):
        cur = schdoc.field(recs[i][1], key)
        assert cur == old, (i, key, cur, old)
        changes.append('record %d %s: %r -> %r' % (i, key, cur, new))
        recs[i][1] = schdoc.set_field(recs[i][1], key, new)

    x1 = part_index(recs, 'X1')
    kids = children(recs, x1)
    put(x1, 'ComponentDescription', DESC[0], DESC[1])
    for name, (old, new) in X1_PARAMS.items():
        hit = [i for i in kids if schdoc.field(recs[i][1], 'RECORD') == '41' and schdoc.field(recs[i][1], 'Name') == name]
        assert len(hit) == 1, (name, hit)
        put(hit[0], 'Text', old, new)
    models = [i for i in kids if schdoc.field(recs[i][1], 'RECORD') == '45' and schdoc.field(recs[i][1], 'ModelType') == 'PCBLIB']
    assert len(models) == 1, models
    put(models[0], 'ModelName', 'USB-C-HRO-TYPE-C-31-M-12', FP)
    put(models[0], 'ModelDatafileEntity0', 'MOLEX-105017-0001', FP)
    pins = {schdoc.field(recs[i][1], 'Designator'): i for i in kids if schdoc.field(recs[i][1], 'RECORD') == '2'}
    assert len(pins) == 11, sorted(pins)
    p4, mh1 = pins['4'], pins['MH1']
    assert (schdoc.field(recs[p4][1], 'Location.X'), schdoc.field(recs[p4][1], 'Location.Y')) == ('215', '1102')
    assert (schdoc.field(recs[mh1][1], 'Location.X'), schdoc.field(recs[mh1][1], 'Location.Y')) == ('250', '1142')
    put(p4, 'Name', 'CC1', '4-ID')
    put(mh1, 'Name', 'CC2', 'GND')
    put(mh1, 'PinConglomerate', '40', '32')     # bit 0x08 off: name hidden, as on the other GND shell pins

    # the shell GND bus: prepend (260, 1142) so MH1's hot end sits on the wire's first vertex
    bus = one(recs, lambda b: schdoc.field(b, 'UniqueID') == 'FJBLACUW', 'GND bus wire')
    b = recs[bus][1]
    assert schdoc.field(b, 'RECORD') == '27' and schdoc.field(b, 'LocationCount') == '9'
    pts = [(int(schdoc.field(b, 'X%d' % k)), int(schdoc.field(b, 'Y%d' % k))) for k in range(1, 10)]
    assert pts[0] == (260, 1132) and pts[-1] == (180, 1067), pts
    pts = [(260, 1142)] + pts
    loc = '|LocationCount=%d' % len(pts) + ''.join('|X%d=%d|Y%d=%d' % (k, x, k, y) for k, (x, y) in enumerate(pts, 1))
    nb, n = re.subn(rb'\|LocationCount=9(\|X\d+=\d+\|Y\d+=\d+){9}', loc.encode(), b)
    assert n == 1
    recs[bus][1] = nb
    changes.append('record %d (GND bus wire): first vertex (260, 1142) added, %d vertices' % (bus, len(pts)))

    drop = set()
    for ref in ('R27', 'R28'):
        r = part_index(recs, ref)
        drop |= {r} | children(recs, r)
        changes.append('%s: record %d and %d children deleted' % (ref, r, len(children(recs, r))))
    by_uid = {  # sheet wires / labels that only served R27, R28 and the CC pins
        'INCXGCWG': ('27', None), 'UKIQYAEJ': ('25', 'USB-CC1'), 'YSKTMWRJ': ('27', None), 'BWMKOTMW': ('25', 'USB-CC2'),
        'MYDHUWJK': ('27', None), 'XRVWZRQB': ('25', 'GND'), 'OICSHXMM': ('27', None), 'NZMJGWLX': ('25', 'GND'),
        'MAEOTMEJ': ('25', 'USB-CC1'), 'XBJHSNIY': ('25', 'USB-CC2'), 'RXBFCIXH': ('27', None),
    }
    for uid, (rec, text) in by_uid.items():
        i = one(recs, lambda bb, u=uid: schdoc.field(bb, 'UniqueID') == u, uid)
        assert schdoc.field(recs[i][1], 'RECORD') == rec and (text is None or schdoc.field(recs[i][1], 'Text') == text), uid
        drop.add(i)
        changes.append('record %d %s %s deleted' % (i, {'27': 'wire', '25': 'net label'}[rec], text or ''))
    out = schdoc.delete(recs, drop)
    noerc = next(h for h, bb in out if schdoc.field(bb, 'RECORD') == '22')
    out.append([noerc, b'|RECORD=22|OwnerPartId=-1|Location.X=185|Location.Y=1102|Color=255|Orientation=1|'
                       b'Symbol=Thin Cross|IsActive=T|SuppressAll=T|UniqueID=XMBPIN4N\x00'])
    out[0][1] = schdoc.set_field(out[0][1], 'Weight', str(len(out) - 1))
    changes.append('No-ERC marker added on X1 pin 4 (185, 1102); %d -> %d records' % (len(recs), len(out)))
    return out, changes


def netdiff(before, after):
    b = {k: set(v) for k, v in before.items()}
    a = {k: set(v) for k, v in after.items()}
    gone = sorted(set(b) - set(a))
    new = sorted(set(a) - set(b))
    changed = {k: (sorted(b[k] - a[k]), sorted(a[k] - b[k])) for k in set(a) & set(b) if a[k] != b[k]}
    return gone, new, changed


def main():
    apply = '--apply' in sys.argv
    before = sch_netlist.build(PROJ)
    tmp = tempfile.mkdtemp(prefix='x1microb_')
    for p in glob.glob(os.path.join(PROJ, '*.SchDoc')):
        shutil.copy2(p, tmp)
    work = os.path.join(tmp, os.path.basename(SHEET))
    recs = schdoc.split(schdoc.read_stream(work))
    out, changes = edit(recs)
    for c in changes:
        print(c)
    data = schdoc.join(out)
    schdoc.write_stream(work, data)
    after = sch_netlist.build(tmp)
    gone, new, changed = netdiff(before, after)
    print('netlist: gone', gone, 'new', new)
    for k, (lost, got) in sorted(changed.items()):
        print('  %s: lost %s gained %s' % (k, lost, got))
    assert gone == ['USB-CC1', 'USB-CC2'], gone
    assert new in ([], ['N$X1-4']), new
    assert changed == {'GND': ([('R27', '1'), ('R28', '1')], [('X1', 'MH1')])}, changed
    assert sorted(before['USB-CC1']) == [('R27', '2'), ('X1', '4')] and sorted(before['USB-CC2']) == [('R28', '2'), ('X1', 'MH1')]
    print('netlist diff is exactly the intended one')
    if not apply:
        print('dry run: nothing written (pass --apply)')
        return
    if not os.path.exists(BACKUP):
        shutil.copy2(SHEET, BACKUP)
    schdoc.write_stream(SHEET, data)
    again = schdoc.split(schdoc.read_stream(SHEET))
    assert len(again) == len(out) and all(x[1] == y[1] for x, y in zip(again, out)), 'read-back differs'
    assert sch_netlist.build(PROJ) == after
    print('written %s (%d records, backup %s)' % (SHEET, len(again), BACKUP))


if __name__ == '__main__':
    main()
