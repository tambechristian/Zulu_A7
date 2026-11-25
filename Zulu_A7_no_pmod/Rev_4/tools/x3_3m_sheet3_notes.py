"""No-PMOD Rev 4 (2026-11-24), after review: correct X3's sheet-3 text (close the sheet in Altium first).

    python tools/x3_3m_sheet3_notes.py

* The 4-line note at (70, 590..560): lines 2-4 were the Hirose note's continuation (HRS code, card-detect switch
  'left open', 'needs its own footprint'). Rewritten for the 3M part.
* X3's SPEC claimed 'detect via DAT3'. DAT3 has R34's 4.7 k pull-up to VCC3V3, so it reads high with or without a
  card: card presence is found in firmware (CMD0/ACMD41 time-out). SPEC says so now.
* AllPinCount 14 -> 12 (pins A/B left with the Hirose part).
Refuses unless every record is found as expected.
"""
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

PATH = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/Imported zulu_a7.PrjPcb/zulu_a7_3.SchDoc'
NOTE = {
    '(HRS 609-0025-8), DM3 catalog p9. Same 8-contact pinout;':
        '(3M TS-2197-02). Same 8-contact pinout; G1/G2 lock pins and',
    'shell pads G1-G4 to GND; card-detect switch A/B (closed with':
        'G3/G4 shell tabs to GND. No card-detect switch: DAT3 has a 4.7k',
    'card) left open. Needs its own footprint on the PCB.':
        'pull-up (R34), so card presence is found in firmware (CMD0).',
}
SPEC = ('microSD push-push (spring eject), top mount, 1.85 mm high, 0.5 A; 8 contacts + G1/G2 lock pins and G3/G4 '
        'shell tabs (GND); no card-detect switch (DAT3 is pulled up by R34, so detect in firmware); 3M TS-2197-02')


def main():
    R = split(read_stream(PATH))
    hit = 0
    for i, (h, b) in enumerate(R):
        t = field(b, 'Text')
        if field(b, 'RECORD') == '4' and t in NOTE:
            R[i] = [h, set_field(b, 'Text', NOTE[t])]
            hit += 1
    if hit != 3:
        sys.exit('REFUSED: found %d of the 3 note lines' % hit)
    comp = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '1' and field(b, 'LibReference') == 'MICROSD_CONDM3D-SF']
    if len(comp) != 1 or field(R[comp[0]][1], 'AllPinCount') != '14':
        sys.exit('REFUSED: X3 component not found as expected')
    h, b = R[comp[0]]
    R[comp[0]] = [h, set_field(b, 'AllPinCount', '12')]
    own = str(comp[0] - 1)
    spec = [i for i, (h, b) in enumerate(R) if field(b, 'OwnerIndex') == own and field(b, 'Name') == 'SPEC']
    if len(spec) != 1:
        sys.exit('REFUSED: X3 SPEC not found once')
    h, b = R[spec[0]]
    R[spec[0]] = [h, set_field(b, 'Text', SPEC)]
    blob = join(R)
    write_stream(PATH, blob)
    assert read_stream(PATH) == blob
    print('note lines 3, SPEC, AllPinCount 12 written; %d records' % len(R))


if __name__ == '__main__':
    main()
