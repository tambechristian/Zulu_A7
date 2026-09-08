# -*- coding: utf-8 -*-
"""Apply the part-number substitutions proposed by docs/component_validation.md.

NOT applied automatically: the vendor choice is the user's. Each entry maps
the MANF# now on the sheets to a stocked replacement found on Digi-Key on
2026-09-06, with the same value, size, rating and pad pattern. Entries can
be commented out before running. Edits MANF#, MANF and SPEC on every
component of every sheet whose MANF# matches; values and footprints are
untouched, so the netlist does not change.

Run with the project closed in Altium, then re-run tools/bom_audit.py:
    python tools/apply_bom_substitutions.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, glob
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

SUBS = {
    # obsolete
    '742C083472JTR':      ('742C083472JP', 'CTS', '4x4.7K isolated array 0603x4, 0.8 mm pitch; direct successor of the obsolete JTR'),
    'GRM21BR61A106KE19L': ('CL21A106KPFNNNG', 'Samsung', 'X5R 10V +-10% 0805 10uF; replaces the obsolete Murata GRM21BR61A106KE19L'),
    'GRM188R61A475KE15D': ('GRM188R61A475KAAJD', 'Murata', 'X5R 10V +-10% 0603 4.7uF; replaces the obsolete KE15D'),
    # part numbers unknown to the distributor
    'GRM033R60J474KE15D': ('GRM033R60J474KE90D', 'Murata', 'X5R 6.3V +-10% 0201 0.47uF; KE15D was a typo, KE90D is the live number'),
    'GRM155R61C474KA88D': ('CL05A474KO5NNNC', 'Samsung', 'X5R 16V +-10% 0402 0.47uF; the Murata family is NRND'),
    # dry until 2027 at Murata, Samsung and TDK's active parts
    'GRM188R60J226MEA0D': ('CL10A226MP8NUNE', 'Samsung', 'X5R 10V +-20% 0603 22uF; the 6.3 V Murata is dry until 2027, this one is rated higher and stocked'),
    # 2026-09-08, after the adversarial re-check: KAAJD is itself NRND at Murata ('please use alternative'); the
    # 4.7 uF 10 V X5R 0603 value is dying at every vendor, the 16 V grade is in production and on the same land
    'GRM188R61A475KAAJD': ('GRM188R61C475KE11D', 'Murata', 'X5R 16V +-10% 0603 4.7uF, 0.95 mm max; 10 V grades (KE15D obsolete, KAAJD NRND) replaced by the 16 V one on 2026-09-08'),
    # optional: the FT2232H wants +-30 ppm; this grade is not stocked anywhere seen, so it stays commented out
    # 'ASEM1-12.000MHZ-LC-T': ('ASEM1-12.000MHZ-LR-T', 'Abracon', '12 MHz, 3.3 V, -40..85 C, +-25 ppm, reel'),
}
# SPEC text corrections for parts that already carry the right MANF# (keyed by current MANF#)
RESPEC = {
    'CL10A226MP8NUNE': 'X5R 10V +-20% 0603 22uF, 1.05 mm max (T 0.80 +-0.25); replaced the 6.3 V Murata GRM188R60J226MEA0D (1.00 mm max, dry until 2027) on 2026-09-07',
    'CL05A474KO5NNNC': 'X5R 16V +-10% 0402 0.47uF, 0.55 mm max; replaced GRM155R61C474KA88D (a number no distributor knows) on 2026-09-07',
}

def main(prj):
    total = 0
    for path in sorted(glob.glob(os.path.join(prj, 'zulu_a7_*.SchDoc'))):
        data = read_stream(path, 'FileHeader')
        recs = split(data)
        desig = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
        # owner index -> its MANF# parameter record index and SPEC/MANF record indices
        by_owner = {}
        for i, (h, b) in enumerate(recs):
            if b.startswith(b'|RECORD=41|') and field(b, 'OwnerIndex') is not None:
                by_owner.setdefault(int(field(b, 'OwnerIndex')) + 1, {})[field(b, 'Name')] = i
        changed = []
        for owner, prm in by_owner.items():
            if 'MANF#' not in prm: continue
            old = field(recs[prm['MANF#']][1], 'Text')
            if old in RESPEC and 'SPEC' in prm and field(recs[prm['SPEC']][1], 'Text') != RESPEC[old]:
                recs[prm['SPEC']][1] = set_field(recs[prm['SPEC']][1], 'Text', RESPEC[old])
                changed.append(f'{desig.get(owner)} SPEC of {old} corrected')
                continue
            if old not in SUBS: continue
            new, manf, spec = SUBS[old]
            recs[prm['MANF#']][1] = set_field(recs[prm['MANF#']][1], 'Text', new)
            if 'MANF' in prm: recs[prm['MANF']][1] = set_field(recs[prm['MANF']][1], 'Text', manf)
            if 'SPEC' in prm: recs[prm['SPEC']][1] = set_field(recs[prm['SPEC']][1], 'Text', spec)
            changed.append(f'{desig.get(owner)} {old} -> {new}')
        if changed:
            out = join(recs)
            write_stream(path, 'FileHeader', out)
            assert read_stream(path, 'FileHeader') == out
            print(os.path.basename(path) + ': ' + ', '.join(changed))
            total += len(changed)
    print(f'{total} components updated')

if __name__ == '__main__':
    main(sys.argv[2])
