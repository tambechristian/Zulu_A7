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
    # 2026-09-08 search (20 agents, Digi-Key + datasheets), NOT applied, the choice is the user's. Q1 must be
    # +-30 ppm or better all-inclusive for the FT2232H; the ASEM1 LR grade is unstocked. Verified on the shelf:
    #   ECS-3225SMV-120-FP-TR   +-10 ppm incl. aging, -40..105 C, 1,830 pcs, $2.90   (recommended)
    #   ASEMB-12.000MHZ-LY-T    +-10 ppm + 5 ppm/yr aging, -40..85 C, 6,143 pcs, $4.40 (Abracon, same lineage)
    #   ECS-3225SMVQ-120-DS-TR  +-20 ppm incl. aging, -40..125 C, 862 pcs, $1.82
    #   SIT1602BI-22-33E-12.000000  +-25 ppm incl. 1st-year aging, 440 pcs, $1.54
    # applied 2026-09-08 at the user's choice (ECS over Abracon)
    'ASEM1-12.000MHZ-LC-T': ('ECS-3225SMV-120-FP-TR', 'ECS', '12.000 MHz HCMOS XO, 1.62-3.63 V, +-10 ppm incl. initial, temp -40..105 C, supply, load, reflow and aging (ECS-3225SMV sheet p1), 3.2x2.5x1.2 mm, pin 1 tri-state (H/NC = run), 6 mA typ / 10 mA max; replaced the +-50 ppm ASEM1-12.000MHZ-LC-T on 2026-09-08', '12MHz 10ppm (FPGA + FT2232HQ)'),
    # C39/C139: no 3.3 uF 0402 >= 6.3 V exists that is not obsolete/NRND; FTDI asks for >= 3.3 uF minimum, so 4.7 uF:
    #   JMK105BBJ475MV-F (order as MSASJ105BB5475MFNA01)  4.7 uF 6.3 V X5R 0402, 0.65 mm max, ~3.7 uF at 1.8 V, 1.6 M pcs, $0.13 (recommended)
    #   GRM155R60J475ME47D  4.7 uF 6.3 V X5R 0402, 0.60 mm max, ~2.2-2.8 uF at 1.8 V, 980 k pcs, $0.10
    # applied 2026-09-08; the manufacturer's current number is used, Digi-Key stocks it mainly under the old alias
    'GRM155R60J335ME15D': ('MSASJ105BB5475MFNA01', 'Taiyo Yuden', 'X5R 6.3V +-20% 0402 4.7uF, 0.65 mm max, about 3.7 uF left at 1.8 V; Digi-Key alias JMK105BBJ475MV-F (587-2787-1-ND, 1.6 M pcs); replaced the unobtainable 3.3 uF GRM155R60J335ME15D on the FT2232H VCORE node (FTDI minimum 3.3 uF) on 2026-09-08', '4.7uF'),
    # U3, applied 2026-09-08 at the user's choice after the PCBWay sourcing check: the -6TIN (166 MHz, industrial) is
    # 0 at every distributor until Oct 2026; the -7TCN is the same B die, package and pinout in the -7 speed bin,
    # commercial 0..70 C ambient (the XC7A35T-1CPG236C beside it is itself a commercial part), 1,478 at Digi-Key.
    # L4-L7, applied 2026-09-08 at the user's choice: BLM18PG601SN1D is not a Murata catalogue number (the BLM18PG
    # series stops at 470 ohm; the sheet's own spec, 600 ohm 1.5 A, is the BLM18SP601SN1D, 567 pcs at Digi-Key).
    # The beads carry at most 60 mA (L4 FT2232H VPHY, L5 VPLL, L6 GNDADC return, L7 VCCADC 25 mA), so the 1.3 A
    # power-line BLM18KG601SN1D (913,912 at Digi-Key, LCSC C85833 791,450) on the same 0603 land is the pick.
    'BLM18PG601SN1D': ('BLM18KG601SN1D', 'Murata', 'ferrite bead 600 ohm at 100 MHz +-25%, 1.3 A at 85 C, 0.15 ohm max, 0603, 0.90 mm max; replaced BLM18PG601SN1D (a number Murata never made; the spec 600 ohm/1.5 A is BLM18SP601SN1D) on 2026-09-08; L4/L5 feed the FT2232H VPHY/VPLL (60 mA max), L6 GNDADC, L7 VCCADC (25 mA)'),
    # U3 carries no SPEC parameter, so the timing note goes onto NOTE (5th element = text appended to NOTE).
    'AS4C32M16SB-6TIN': ('AS4C32M16SB-7TCN', 'Alliance Memory', '', 'AS4C32M16SB-7TCN',
        ' 2026-09-08: AS4C32M16SB-6TIN replaced by AS4C32M16SB-7TCN (same B die, 54-TSOP II 400 mil and pinout, datasheet Rev 1.4 Table 2): -7 speed bin, 143 MHz max at CL3 (tCK 7 ns, tAC 5.4 ns), tRCD/tRP 21 ns, tRC/tRFC 63 ns, tRRD/tMRD/tWR 14 ns, tCH/tCL 2.5 ns; 100 MHz at CL2 for every grade. Commercial TA 0..70 C, matching the -1C FPGA. IDD1 max 110 mA (was 120). AS4C32M16SB-7TIN (industrial) is the timing-identical alternate; the -6TIN only if the controller is clocked above 143 MHz.'),
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
            new, manf, spec = SUBS[old][:3]
            comment = SUBS[old][3] if len(SUBS[old]) > 3 else None
            note_suffix = SUBS[old][4] if len(SUBS[old]) > 4 else None
            recs[prm['MANF#']][1] = set_field(recs[prm['MANF#']][1], 'Text', new)
            if 'MANF' in prm: recs[prm['MANF']][1] = set_field(recs[prm['MANF']][1], 'Text', manf)
            if spec and 'SPEC' in prm: recs[prm['SPEC']][1] = set_field(recs[prm['SPEC']][1], 'Text', spec)
            if note_suffix and 'NOTE' in prm and note_suffix not in field(recs[prm['NOTE']][1], 'Text'):
                recs[prm['NOTE']][1] = set_field(recs[prm['NOTE']][1], 'Text', field(recs[prm['NOTE']][1], 'Text') + note_suffix)
            if comment and 'Comment' in prm: recs[prm['Comment']][1] = set_field(recs[prm['Comment']][1], 'Text', comment)
            if comment and 'DeviceName' in prm and old.startswith('ASEM1'): recs[prm['DeviceName']][1] = set_field(recs[prm['DeviceName']][1], 'Text', 'ECS-3225SMV')
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
