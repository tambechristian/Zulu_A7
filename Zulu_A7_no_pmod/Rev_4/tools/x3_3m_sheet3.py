"""No-PMOD Rev 4 (2026-11-24): X3 becomes the 3M 2908-05WB-MG push-push microSD socket on zulu_a7_3.SchDoc.

    python tools/x3_3m_sheet3.py      (close the project in Altium first)

The symbol keeps its 8 contact pins and the four shell pins G1-G4 (all GND). The 3M part has no card-detect
switch (card detect is via DAT3, datasheet TS-2197-02 sheet 2), so the Hirose switch pins A (SW_A) and B (SW_B),
which were unconnected, go together with their two No-ERC marks at (345, 787) / (355, 787). Parameters, the
footprint model (DM3D-SF -> 3M-2908-05WB-MG), the description and the 2026-09-06 sheet note are updated.
Refuses unless every record is found exactly where expected.
"""
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import delete, field, join, read_stream, set_field, split, subtree, write_stream  # noqa: E402

PATH = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/Imported zulu_a7.PrjPcb/zulu_a7_3.SchDoc'
FP = '3M-2908-05WB-MG'
PARAMS = {
    'DeviceName': '2908-05WB-MG',
    'MANF': '3M',
    'MANF#': '2908-05WB-MG',
    'MOUSER#': '517-2908-05WB-MG',
    'Comment': '2908-05WB-MG',
    'SPEC': 'microSD push-push (spring eject), top mount, 1.85 mm high, 0.5 A; 8 contacts + 4 shell/lock pads '
            'G1-G4 (GND); no card-detect switch (detect via DAT3); 3M TS-2197-02',
}


def text(b, k):
    v = field(b, k)
    return v.decode('latin-1') if isinstance(v, bytes) else v


def main():
    R = split(read_stream(PATH))
    comp = [i for i, (h, b) in enumerate(R) if text(b, 'RECORD') == '1' and text(b, 'LibReference') == 'MICROSD_CONDM3D-SF']
    if len(comp) != 1:
        sys.exit('REFUSED: X3 component not found once (%d)' % len(comp))
    ci = comp[0]
    own = str(ci - 1)                                   # OwnerIndex is the record index minus the header
    kids = [i for i, (h, b) in enumerate(R) if text(b, 'OwnerIndex') == own]
    des = [i for i in kids if text(R[i][1], 'RECORD') == '34' and text(R[i][1], 'Text') == 'X3']
    if len(des) != 1:
        sys.exit('REFUSED: designator X3 not owned by record %d' % ci)
    pins = {text(R[i][1], 'Designator'): i for i in kids if text(R[i][1], 'RECORD') == '2'}
    if sorted(pins) != sorted(['1', '2', '3', '4', '5', '6', '7', '8', 'G1', 'G2', 'G3', 'G4', 'A', 'B']):
        sys.exit('REFUSED: unexpected X3 pins %s' % sorted(pins))
    noerc = [i for i, (h, b) in enumerate(R) if text(b, 'RECORD') == '22' and text(b, 'Location.Y') == '787'
             and text(b, 'Location.X') in ('345', '355') and not text(b, 'OwnerIndex')]
    if len(noerc) != 2:
        sys.exit('REFUSED: the two No-ERC marks under pins A/B not found (%d)' % len(noerc))
    note = [i for i, (h, b) in enumerate(R) if text(b, 'RECORD') == '4'
            and text(b, 'Text') == '2026-09-06: X3 is now the Hirose DM3D-SF push-pull socket']
    if len(note) != 1:
        sys.exit('REFUSED: sheet note not found once')
    # edits in place first (indices stay valid), deletions last
    h, b = R[ci]
    b = set_field(b, 'ComponentDescription', 'microSD socket, push-push, 3M 2908-05WB-MG')
    R[ci] = [h, b]
    seen, hrs = set(), None
    for i in kids:
        h, b = R[i]
        if text(b, 'RECORD') == '41' and text(b, 'Name') in PARAMS:
            R[i] = [h, set_field(b, 'Text', PARAMS[text(b, 'Name')])]
            seen.add(text(b, 'Name'))
        if text(b, 'RECORD') == '41' and text(b, 'Name') == 'HRS#':
            hrs = i                                   # Hirose order code: dropped below
    if seen != set(PARAMS):
        sys.exit('REFUSED: parameters missing %s' % sorted(set(PARAMS) - seen))
    impl = [i for i, (h, b) in enumerate(R) if text(b, 'RECORD') == '45' and text(b, 'ModelName') == 'DM3D-SF']
    if len(impl) != 1 or text(R[int(text(R[impl[0]][1], 'OwnerIndex')) + 1][1], 'OwnerIndex') != own:
        sys.exit('REFUSED: the DM3D-SF footprint model is not X3\'s (%d)' % len(impl))
    h, b = R[impl[0]]
    for k in ('ModelName', 'ModelDatafileEntity0'):
        b = set_field(b, k, FP)
    R[impl[0]] = [h, b]
    h, b = R[note[0]]
    R[note[0]] = [h, set_field(b, 'Text', '2026-11-24: X3 is now the 3M 2908-05WB-MG push-push socket (was Hirose DM3D-SF)')]
    drop = subtree(R, [pins["A"], pins["B"]]) | set(noerc) | {hrs}
    R = delete(R, drop)
    blob = join(R)
    write_stream(PATH, blob)
    assert read_stream(PATH) == blob
    print('X3: %d records dropped (pins A, B + their PinUniqueId + 2 No-ERC), %d parameters set, model -> %s, %d records'
          % (len(drop), len(seen), FP, len(R)))


if __name__ == '__main__':
    main()
