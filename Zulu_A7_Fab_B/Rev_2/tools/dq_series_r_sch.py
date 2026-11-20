"""Fab B Rev 2 sync (2026-11-20), sheet 3: the 16 SDRAM DQ series resistors R119-R134, copied from Zulu_A7_no_pmod Rev 2.

    python tools/dq_series_r_sch.py            dry run
    python tools/dq_series_r_sch.py apply      writes Imported zulu_a7.PrjPcb/zulu_a7_3.SchDoc

WHY: Zulu_A7_no_pmod/Rev_2/docs/dq_series_resistors.md and docs/si_analysis.md there -- on reads, U3's full-drive DQ
edges undershoot past DS181 Table 4 at U1's ball; a 22 ohm 0201 on every data bit fixes it.  The SDRAM, U1 and the
whole DQ fan-out are the same copper on both boards, so the fix and its placement carry over.

HOW (record copy; was the inventory prototype proto_dq_r_fabb.py).  This sheet 3 is the no-PMOD sheet 3 minus the
resistors: same U3 box, pins, caps and rails (both were re-laid out by sheet3_u3_layout.py).  So:
- delete this sheet's 18 ten-unit stubs on U3's right edge (895,y)-(905,y), their 18 labels D0..D15 / LDQM / UDQM at
  (905,y) and the 2-line C3-C9 caption at (555, 540/530);
- append from the no-PMOD sheet: the 16 resistor subtrees R119-R134 (R-US_SMALLR0201, footprint R0201, 22 ohm,
  RC0201FR-0722RL), the 34 wires (16 x (895,y)-(965,y) to pin 1, 16 x (985,y)-(995,y) from pin 2, LDQM and UDQM
  (895,y)-(995,y)), the 34 net labels (SDRAM-Dn at x 901, Dn / LDQM / UDQM at x 995) and the 5-line caption at x 555.
  Pin 1 = SDRAM-Dn (U3 side), pin 2 = Dn (U1 side, the XDC / HDL name).  Sheet 5 keeps Dn.
- One text differs from the no-PMOD sheet: the resistors' hidden NOTE and caption line 3 point at
  Zulu_A7_no_pmod/Rev_2/docs/dq_series_resistors.md (this board has no docs/dq_series_resistors.md of its own).
- This sheet's own deviations stay: U3's Comment/PART text centred, X3 caption "PCB footprint DM3D-SF".
Copied UniqueIDs are checked free here; OwnerIndex is remapped; component IndexInSheet continues this sheet's numbering;
Weight is rewritten.  Netlist effect: each Dn splits into SDRAM-Dn = {U3 DQ pin, Rn-1} and Dn = {Rn-2, U1 ball}.
Needs backups/zulu_a7_3.SchDoc.pre-sync.
"""
import re
import sys

from sync_sch_common import field, load, num, owner, require_backup, save, set_field, sheet, subtree, designators

YS = {'D0': 990, 'D1': 970, 'D2': 950, 'D3': 930, 'D4': 910, 'D5': 890, 'D6': 870, 'D7': 850, 'LDQM': 830,
      'D8': 790, 'D9': 770, 'D10': 750, 'D11': 730, 'D12': 710, 'D13': 690, 'D14': 670, 'D15': 650, 'UDQM': 630}
OLD_CAPTION = ('C3-C9: 0.1 uF, one on each supply pin above; the ground pin below',
               'is the one it faces in the TSOP (pin 55-n).')
NEW_CAPTION_Y = {540, 530, 520, 505, 495}
DOC_OLD = b'docs/dq_series_resistors.md'
DOC_NEW = b'Zulu_A7_no_pmod/Rev_2/docs/dq_series_resistors.md'


def pts(b):
    return {(num(b, 'X%d' % j), num(b, 'Y%d' % j)) for j in range(1, (num(b, 'LocationCount') or 0) + 1)}


def build(R, S):
    """R: this sheet's records, S: the no-PMOD sheet 3 records.  Returns (new records, report dict)."""
    # ---- this sheet's right-edge stubs, their labels and the old caption ----
    drop = set()
    for i, (h, b) in enumerate(R):
        if owner(b) is not None:
            continue
        r = field(b, 'RECORD')
        if r == '27' and num(b, 'LocationCount') == 2 and any(pts(b) == {(895, y), (905, y)} for y in YS.values()):
            drop.add(i)
        elif r == '25' and field(b, 'Text') in YS and \
                (num(b, 'Location.X'), num(b, 'Location.Y')) == (905, YS[field(b, 'Text')]):
            drop.add(i)
        elif r == '4' and field(b, 'Text') in OLD_CAPTION and num(b, 'Location.X') == 555:
            drop.add(i)
    assert len(drop) == 18 + 18 + 2, len(drop)
    keep = [i for i in range(len(R)) if i not in drop]
    # nothing may hang off a dropped record
    assert not any(owner(R[i][1]) in drop for i in keep)
    # ---- what to copy from the no-PMOD sheet ----
    des = designators(S)
    roots = [i for i, (h, b) in enumerate(S) if field(b, 'RECORD') == '1' and
             re.fullmatch(r'R1(19|2\d|3[0-4])', des.get(i) or '')]
    assert len(roots) == 16, roots
    take = []
    for rt in sorted(roots, key=lambda i: int(des[i][1:])):
        take += subtree(S, rt)
    free = []
    for i, (h, b) in enumerate(S):
        if owner(b) is not None:
            continue
        r = field(b, 'RECORD')
        if r == '27' and num(b, 'LocationCount') == 2:
            p = pts(b)
            if any(p in ({(895, y), (965, y)}, {(985, y), (995, y)}, {(895, y), (995, y)}) for y in YS.values()):
                free.append(i)
        elif r == '25' and (num(b, 'Location.X'), num(b, 'Location.Y')) in {(x, y) for y in YS.values() for x in (901, 995)}:
            free.append(i)
        elif r == '4' and num(b, 'Location.X') == 555 and num(b, 'Location.Y') in NEW_CAPTION_Y:
            free.append(i)
    assert len(free) == 34 + 34 + 5, len(free)
    # fonts used by the copied records must mean the same on both sheets
    fonts = {field(S[i][1], k) for i in take + free for k in ('FontID', 'Name_CustomFontID', 'Designator_CustomFontID')
             if field(S[i][1], k)}
    hr = [b for h, b in R if field(b, 'RECORD') == '31'][0]
    hs = [b for h, b in S if field(b, 'RECORD') == '31'][0]
    for k in sorted(fonts):
        for f in ('FontName', 'Size', 'Rotation', 'Bold', 'Italic', 'Underline'):
            assert field(hr, f + k) == field(hs, f + k), (k, f)
    used = {field(b, 'UniqueID') for h, b in R if field(b, 'UniqueID')}
    # ---- assemble: kept records, then the copies (component subtrees first, then the free records) ----
    out = []
    new_of_old = {}
    for i in keep:
        new_of_old[i] = len(out)
        out.append([R[i][0], R[i][1]])
    for i in keep:
        b = out[new_of_old[i]][1]
        o = owner(b)
        if o is not None and o > 0:
            out[new_of_old[i]][1] = set_field(b, 'OwnerIndex', str(new_of_old[o] - 1))
    new_of_src = {}
    for n, i in enumerate(take + free):
        new_of_src[i] = len(out) + n
    nxt = max(num(b, 'IndexInSheet') or 0 for h, b in R if field(b, 'RECORD') == '1') + 1
    doc_edits = 0
    for i in take + free:
        b = S[i][1]
        u = field(b, 'UniqueID')
        assert u is None or u not in used, u
        o = owner(b)
        if o is not None and o > 0:
            b = set_field(b, 'OwnerIndex', str(new_of_src[o] - 1))
        if field(b, 'RECORD') == '1':
            b = set_field(b, 'IndexInSheet', str(nxt))
            nxt += 1
        if DOC_OLD in b:
            assert (field(b, 'RECORD') == '41' and field(b, 'Name') == 'NOTE') or field(b, 'RECORD') == '4', b[:80]
            assert b.count(DOC_OLD) == 1
            b = b.replace(DOC_OLD, DOC_NEW)
            doc_edits += 1
        out.append([S[i][0], b])
    assert doc_edits == 16 + 1, doc_edits
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    return out, dict(dropped=sorted(drop), copied_component_records=len(take), copied_free_records=len(free),
                     records_before=len(R), records_after=len(out))


def main():
    apply = 'apply' in sys.argv[1:]
    path = sheet(3)
    R = load(path)
    if any(field(b, 'Text') == 'R119' and field(b, 'RECORD') == '34' for h, b in R):
        raise SystemExit('Refusing: R119 is already on this sheet')
    out, rep = build(R, load(sheet(3, src=True)))
    print('dropped %(dropped)s\ncopied %(copied_component_records)d component records + %(copied_free_records)d free '
          'records; records %(records_before)d -> %(records_after)d' % dict(rep, dropped=len(rep['dropped'])))
    if not apply:
        print('dry run (add "apply" to write)')
        return
    require_backup(path)
    print('written zulu_a7_3.SchDoc md5 %s' % save(path, out))


if __name__ == '__main__':
    main()
