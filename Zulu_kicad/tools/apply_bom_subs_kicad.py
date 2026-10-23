# KiCad copy: the 2026-10-23 BOM substitutions, as on the Altium copies (Zulu_Altium_VS_Code/tools/
# apply_bom_substitutions.py): U1 XC7A35T-1CPG236C -> XC7A35T-2CPG236I, LD0 EAST1616RGBA8 -> 19-337/R6GHBHC-A01/2T.
# The new LD0 SPEC and NOTE texts are read from the updated Altium General IO sheet, so both copies carry identical
# strings. Fields only: no symbol, footprint, pin or net changes. Refuses to run twice.
#   python tools/apply_bom_subs_kicad.py kicad_project <Altium project folder with the updated SchDocs>
# After a later SPEC/NOTE correction on the Altium side, copy LD0's two texts again (repeatable):
#   python tools/apply_bom_subs_kicad.py kicad_project <Altium project folder> --resync-ld0
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Zulu_Altium_VS_Code', 'tools'))
from fix_text_orientation import read_stream, split, field  # noqa: E402

KP, ALT = sys.argv[1], sys.argv[2]
LD0_SPEC_START = 'RGB LED, three independent diodes, 1.6 x 1.6 x 0.35 mm, water-clear lens'


def ld0_params():
    recs = split(read_stream(os.path.join(ALT, 'zulu_a7_2.SchDoc'), 'FileHeader'))
    owners = {}
    for h, b in recs:
        if b.startswith(b'|RECORD=41|') and field(b, 'OwnerIndex') is not None:
            owners.setdefault(field(b, 'OwnerIndex'), {})[field(b, 'Name')] = field(b, 'Text')
    hit = [p for p in owners.values() if p.get('MANF#') == '19-337/R6GHBHC-A01/2T']
    assert len(hit) == 1, 'run the Altium substitution first'
    return hit[0]


def main():
    ld0 = ld0_params()
    old_spec = ('RGB LED, three independent diodes, 1.6 x 1.6 x 0.35 mm, diffused lens, 624 / 525 / 468 nm, VF typ '
                '2.05 / 3.2 / 3.2 V (max 2.4 / 3.7 / 3.7), IF 25 mA max per colour')
    suffix_at = ld0['NOTE'].index(' 2026-10-23: replaced by 19-337/R6GHBHC-A01/2T')
    old_note = ld0['NOTE'][:suffix_at]
    reps = [
        ('(property "MANF#" "XC7A35T-1CPG236C"', '(property "MANF#" "XC7A35T-2CPG236I"'),
        ('(property "Value" "XC7A35T-1CPG236C"', '(property "Value" "XC7A35T-2CPG236I"'),
        ('(property "DEVICENAME" "-1CPG236C"', '(property "DEVICENAME" "-2CPG236I"'),
        ('"Xilinx Artix-7 XC7A35T-1CPG236C ', '"Xilinx Artix-7 XC7A35T-2CPG236I '),
        ('(property "MANF#" "EAST1616RGBA8"', '(property "MANF#" "19-337/R6GHBHC-A01/2T"'),
        ('(property "Value" "EAST1616RGBA8"', '(property "Value" "19-337/R6GHBHC-A01/2T"'),
        ('(property "NOTE" "%s"' % old_note, '(property "NOTE" "%s"' % ld0['NOTE']),
    ]
    files = ['zulu_a7_2.kicad_sch', 'zulu_a7_5.kicad_sch', 'zulu_a7_6.kicad_sch', 'zulu_a7.kicad_pcb', 'ctambe.kicad_sym']
    total = 0
    for f in files:
        path = os.path.join(KP, f)
        t = open(path, encoding='utf-8', newline='').read()
        if 'XC7A35T-2CPG236I' in t or '19-337/R6GHBHC-A01/2T"' in t:
            raise SystemExit('REFUSED: %s already carries the new part numbers' % f)
        counts = []
        for a, b in reps:
            n = t.count(a)
            t = t.replace(a, b)
            counts.append(n)
        # SPEC: the old text may be the whole property value or its start
        spec_key = '(property "SPEC" "%s' % old_spec
        n_spec = t.count(spec_key)
        if n_spec:
            i = t.index(spec_key) + len('(property "SPEC" "')
            j = t.index('"', i)
            t = t[:i] + ld0['SPEC'] + t[j:]
        open(path, 'w', encoding='utf-8', newline='').write(t)
        print('%-22s %s spec %d' % (f, counts, n_spec))
        total += sum(counts) + n_spec
    print('replacements:', total)


def resync_ld0():
    """Set every LD0 SPEC/NOTE property value that starts like the substituted part's to the Altium texts."""
    ld0 = ld0_params()
    note_start = ld0['NOTE'][:ld0['NOTE'].index(' 2026-10-23: replaced by 19-337/R6GHBHC-A01/2T')]
    for f in ['zulu_a7_2.kicad_sch', 'zulu_a7.kicad_pcb']:
        path = os.path.join(KP, f)
        t = open(path, encoding='utf-8', newline='').read()
        counts = []
        for name, start, value in [('SPEC', LD0_SPEC_START, ld0['SPEC']), ('NOTE', note_start, ld0['NOTE'])]:
            key = '(property "%s" "%s' % (name, start)
            n = t.count(key)
            assert n == 1, (f, name, n)
            i = t.index(key) + len('(property "%s" "' % name)
            j = t.index('"', i)
            t = t[:i] + value + t[j:]
            counts.append(n)
        open(path, 'w', encoding='utf-8', newline='').write(t)
        print('%-22s SPEC/NOTE resynced %s' % (f, counts))


if __name__ == '__main__':
    resync_ld0() if sys.argv[3:] == ['--resync-ld0'] else main()
