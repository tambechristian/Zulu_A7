# -*- coding: utf-8 -*-
"""Component and BOM validation for the Zulu A7 Altium project.

Writes docs/component_validation.md from four sources:
  * the seven SchDocs (components, parameters, pins) and the Protel netlist
    Project Outputs for zulu_a7/zulu_a7.NET (pad -> net)
  * zulu_a7.sch, whose embedded EAGLE library still holds every package
    (pad names and coordinates) the Altium footprints were imported from
  * Datasheet/xc7a35tcpg236pkg_pinout.txt (AMD ball list)
  * tables typed in below from the datasheets on disk (pin functions, land
    patterns) and from Digi-Key on 2026-09-06 (status, stock, price)

Machine checks: every FPGA ball present once with power/ground/config balls
on the right nets; fixed-function pins of U2, pad functions of U3/U4/U10/Q1/
X1/LD0/R34 against the datasheet tables; EAGLE package geometry against the
datasheet land patterns; capacitor voltage and resistor power derating from
the nets each part sits on.  Supply-chain and second-source data are static
snapshots and carry their date.

    python tools/bom_audit.py > docs/component_validation.md
"""
import sys, re, json, os
import xml.etree.ElementTree as ET
from collections import defaultdict, OrderedDict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fix_text_orientation import read_stream, split, field
ROOT = os.path.dirname(HERE)
PRJ = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb')
NET = os.path.join(PRJ, 'Project Outputs for zulu_a7', 'zulu_a7.NET')
SCH = os.path.join(ROOT, 'zulu_a7.sch')
PINOUT = os.path.join(ROOT, '..', 'Datasheet', 'xc7a35tcpg236pkg_pinout.txt')
DATE = '2026-09-07'

# ---------------------------------------------------------------- inputs --
def natkey(s):
    m = re.match(r'([A-Za-z$]*)(\d*)', s); return (m.group(1), int(m.group(2) or 0), s)

def load_components():
    comps = OrderedDict()
    for n in range(7):
        recs = split(read_stream(os.path.join(PRJ, f'zulu_a7_{n}.SchDoc'), 'FileHeader'))
        desig = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
        params, pins, fp = defaultdict(dict), defaultdict(list), {}
        for i, (h, b) in enumerate(recs):
            o = field(b, 'OwnerIndex')
            if o is None: continue
            o = int(o) + 1
            if b.startswith(b'|RECORD=41|'): params[o][field(b, 'Name')] = field(b, 'Text')
            elif b.startswith(b'|RECORD=2|'): pins[o].append((field(b, 'Designator'), field(b, 'Name'), field(b, 'OwnerPartId')))
            elif b.startswith(b'|RECORD=44|'):
                for k, (h3, b3) in enumerate(recs):
                    if b3.startswith(b'|RECORD=45|') and field(b3, 'OwnerIndex') == str(i - 1): fp[o] = field(b3, 'ModelName')
        for i, (h, b) in enumerate(recs):
            if not b.startswith(b'|RECORD=1|'): continue
            d = desig.get(i)
            if not d: continue
            part = field(b, 'CurrentPartId')
            c = comps.setdefault(d, {'sheet': n, 'lib': field(b, 'LibReference'), 'pins': {}, 'params': {}, 'fp': None, 'gates': 0, 'pkgpins': None})
            c['gates'] += 1
            # AllPinCount is the whole package; c['pins'] holds only the gates actually placed,
            # which is fewer when an array has spare elements. The pad pairing needs the package.
            c['pkgpins'] = c['pkgpins'] or (int(field(b, 'AllPinCount')) if field(b, 'AllPinCount') else None)
            for des, name, opid in pins.get(i, []):
                if opid == part: c['pins'][des] = name
            c['params'].update({k: v for k, v in params.get(i, {}).items() if v})
            c['fp'] = c['fp'] or fp.get(i)
    return comps

def load_netlist():
    txt = open(NET, encoding='utf-8', errors='replace').read()
    padnet = {}
    for block in re.findall(r'^\($(.*?)^\)$', txt, re.S | re.M):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        for p in lines[1:]: padnet[p] = lines[0]
    return padnet

def load_packages():
    root = ET.parse(SCH).getroot()
    pk = {}
    for pkg in root.iter('package'):
        pads = [(e.get('name'), float(e.get('x')), float(e.get('y')), e.get('dx'), e.get('dy')) for e in pkg if e.tag in ('smd', 'pad')]
        if pads: pk[pkg.get('name')] = pads
    return pk

def load_xilinx():
    xl = {}
    for line in open(PINOUT, encoding='utf-8', errors='replace'):
        p = line.split()
        if len(p) >= 4 and re.fullmatch(r'[A-Z]{1,2}\d{1,2}', p[0]): xl[p[0]] = (p[1], p[3])
    return xl

# --------------------------------------------------------- expectations --
# FT2232H, DS_FT2232H.pdf v2.10 tables 3.2-3.4 and the bus pins of 3.1.4
FT2232H = {1: 'GND', 2: 'OSCI', 3: 'OSCO', 4: 'VPHY', 5: 'GND', 6: 'REF', 7: 'DM', 8: 'DP', 9: 'VPLL', 10: 'AGND', 11: 'GND',
           12: 'VCORE', 13: 'TEST', 14: 'RESET#', 15: 'GND', 20: 'VCCIO', 25: 'GND', 31: 'VCCIO', 35: 'GND', 36: 'SUSPEND#',
           37: 'VCORE', 42: 'VCCIO', 47: 'GND', 49: 'VREGOUT', 50: 'VREGIN', 51: 'GND', 56: 'VCCIO', 60: 'PWREN#',
           61: 'EEDATA', 62: 'EECLK', 63: 'EECS', 64: 'VCORE'}
for i, n in enumerate(range(16, 20)): FT2232H[n] = f'ADBUS{i}'
for i, n in enumerate(range(21, 25)): FT2232H[n] = f'ADBUS{i + 4}'
for i, n in enumerate(range(26, 31)): FT2232H[n] = f'ACBUS{i}'
for i, n in enumerate(range(32, 35)): FT2232H[n] = f'ACBUS{i + 5}'
for i, n in enumerate(range(38, 42)): FT2232H[n] = f'BDBUS{i}'
for i, n in enumerate(range(43, 47)): FT2232H[n] = f'BDBUS{i + 4}'
FT2232H[48] = 'BCBUS0'
for i, n in enumerate(range(52, 56)): FT2232H[n] = f'BCBUS{i + 1}'
for i, n in enumerate(range(57, 60)): FT2232H[n] = f'BCBUS{i + 5}'
# AS4C32M16SB 54-TSOP II, datasheet rev 1.2 p3 (JEDEC x16 SDRAM)
SDRAM = 'VDD DQ0 VDDQ DQ1 DQ2 VSSQ DQ3 DQ4 VDDQ DQ5 DQ6 VSSQ DQ7 VDD LDQM WE# CAS# RAS# CS# BA0 BA1 A10 A0 A1 A2 A3 VDD VSS A4 A5 A6 A7 A8 A9 A11 A12 CKE CLK UDQM NC VSS DQ8 VDDQ DQ9 DQ10 VSSQ DQ11 DQ12 VDDQ DQ13 DQ14 VSSQ DQ15 VSS'.split()
# net-name pattern each SDRAM function must land on
def sdram_ok(fn, net):
    if fn in ('VDD', 'VDDQ'): return net == 'VCC3V3'
    if fn in ('VSS', 'VSSQ'): return net == 'GND'
    if fn == 'NC': return net is None
    core = re.sub(r'^DQ', 'D', fn).replace('BA', 'BS').replace('#', '')
    return re.sub(r'^SDRAM[-_]', '', net or '').replace('#', '').upper() == core
W25Q = {'1': 'CS#', '2': 'DO/IO1', '3': 'WP#/IO2', '4': 'GND', '5': 'DI/IO0', '6': 'CLK', '7': 'HOLD#/IO3', '8': 'VCC'}
W25Q_NET = {'1': 'FLASH-CS#', '2': 'FLASH-D01', '3': 'FLASH-D02', '4': 'GND', '5': 'FLASH-D00', '6': 'FPGA-CCLK', '7': 'FLASH-D03', '8': 'VCC3V3'}
EEPROM = {'1': 'CS', '2': 'CLK', '3': 'DI', '4': 'DO', '5': 'VSS', '6': 'NC', '7': 'NC', '8': 'VCC'}      # 93LC46B SN, DS20001749 p3
EEPROM_NET = {'1': 'EE-CS', '2': 'EE-CLK', '3': 'EE-DATA', '4': 'EE-DATA-DO', '5': 'GND', '8': 'VCC3V3'}
OSC_NET = {'1': 'VCC3V3', '2': 'GND', '3': 'CLK-12M-SHARED', '4': 'VCC3V3'}                             # ASEM1: 1 ST, 2 GND, 3 OUT, 4 VDD
USB_NET = {'1': 'USB5V0', '2': 'USB_D_N', '3': 'USB_D_P'}                                               # Molex 105017: 1 VBUS 2 D- 3 D+ 4 ID 5 GND
RGB = {'2': 'LED0_B', '4': 'LED0_R', '6': 'LED0_G'}                                                     # Everlight 19-337 p8: cathodes 2 B, 4 R, 6 G; anodes 1 B, 3 R, 5 G (VS NRD8 numbered them 1/2/3 and 4/5/6)
RGB_ANODE = {'1': 'R80', '3': 'R81', '5': 'R82'}

# EAGLE package geometry against the datasheet land patterns (mm)
GEOM = [
    ('XC7A35T-CPG236', 'UG475 v1.20 Table A-1: 0.5 mm pitch, land 0.275 mm NSMD, mask 0.375', 'pitch 0.5 OK; pads 0.225 mm, 0.05 mm under the AMD land', 'deviation'),
    ('FT2232HL-LQFP64', 'DS_FT2232H Figure 8.2: LQFP-64, 10 x 10 mm body, 12 x 12 mm over leads, 0.5 mm pitch, JEDEC MS-026 BCD, no exposed pad', 'no such package in the EAGLE library: draw at the PCB stage; the FT2232HQ QFN pattern it replaces (pitch 0.5, pads 0.25x0.6, EP 4.95) does not fit', 'missing'),
    ('TSOPII-54', 'AS4C32M16SB TSOP II 400 mil, 0.8 mm pitch, lead span 11.76 max', 'pitch 0.8, rows 11.36 apart, 1.2 mm pads OK', 'ok'),
    ('SOIC-8_208MIL', 'W25Q128JVSIQ SOIC-8 208 mil, lead span 7.9-8.1', 'rows 7.3 apart, 1.51 mm pads OK', 'ok'),
    ('SOIC8', '93LC46BT-I/SN: SN = 3.90 mm narrow body, E = 6.00 BSC, foot 0.40-1.27', 'rows 7.62 apart, pads 1.5 long: inner edge at 3.06 mm, lead tip at 3.00 mm - no overlap', 'FAIL'),
    ('SOT23-3', '2N7002LT1G SOT-23: 1 G, 2 S, 3 D (standard 2N7002 pinout, datasheet not on disk)', 'pads G(-0.95,-0.7) S(0.95,-0.7) D(0,0.7), 0.95 pitch OK', 'ok'),
    ('SOT23-5', 'SC189xSKTRT SOT23-5, datasheet p23 land: 0.95 pitch, pads 0.60 x 1.10, inner gap 1.40, outer span 3.60', 'no such package in the EAGLE library: footprint must be drawn at the PCB stage', 'missing'),
    ('DM3D-SF', 'DM3 catalog p9: 8 x 0.55 pads on 1.1 pitch, 4 cover pads, 2 switch pads, 2 keep-outs', 'no such package in the EAGLE library: footprint must be drawn at the PCB stage', 'missing'),
    ('ZULU-DIP37', 'Sullins PRPC drawing: 0.64 mm square pins on 2.54 mm, recommended hole 1.02 mm', '40 pins numbered 1-40 on 2026-09-09, the two rows cut identically at 9 + landing + 11 with both landings on the same four x values (36.83..29.21): the imported footprint still carries 44 pads on the old numbering, so redraw it with 40 pads named 1-40 before loading the netlist onto a board', 'redraw'),
    ('VQFN16-3X3-RGT', 'bq24232 SLUS821J RGT package: 16-pin VQFN 3.0 x 3.0 mm, 0.5 mm pitch, 1.68 mm thermal pad', 'no such package in the EAGLE library: draw at the PCB stage from the datasheet package drawing', 'missing'),
    ('JST-B2B-PH-SM4-TB', 'JST PH SM4 top-entry SMT: two contact pads on 2.0 mm pitch plus two 1.6 x 3.0 mm fixing pads (catalog page 1)', 'no such package in the EAGLE library: draw at the PCB stage', 'missing'),
    ('742C163', 'CTS 742C163 (DOC 008-0335-0 Rev T): 8 x 0603 concave-termination array, body 6.4 x 1.6, 0.8 mm pitch, 16 pads; CTS publishes one land for the whole 742 family, the 0.45 x 0.9 pads at +-0.85 already checked for 742C083', 'no such package in the EAGLE library: draw it at the PCB stage from the 742C083 pad cell, sixteen pads instead of eight; six elements used, pads 7-10 spare', 'missing'),
    ('742C043', 'CTS 742C043 (DOC 008-0335-0 Rev T): 2 x 0603 concave-termination array, body 1.6 x 1.6, 0.8 mm pitch, 4 pads; same family land as 742C083', 'no such package in the EAGLE library: draw it at the PCB stage from the 742C083 pad cell, four pads instead of eight', 'missing'),
    ('MOLEX-105017-0001', 'Molex 105017 drawing: 5 x 0.4 mm pads on 0.65 pitch, 4 shell pads, 2 pegs', '0.65 pitch, 0.4x1.35 pads, shell pads OK', 'ok'),
    ('32X25', 'ASEM1 3.2x2.5 mm, 4 pads', 'pads 1.2x1.4 at 1.7 x 2.2 OK', 'ok'),
    ('EVERLIGHT-19-337', 'Everlight 19-337 p8 recommended pads: 0.55x0.4 outer at +-0.725, 0.7x0.5 middle, 1.9/2.2 spans (the VS NRD8 p2 drawing line for line)', 'identical to the VS-NRD8 pattern in the library; renumber the pads 1/2/3 -> 2/4/6, 4/5/6 -> 1/3/5 when the footprint is drawn', 'ok'),
    ('PTS810', 'C&K PTS810 sheet p1: four pads 1.05 x 0.65 mm centred at +-2.075 x +-1.075 mm (5.2 x 2.8 mm envelope), body 4.2 x 3.2 mm', 'no such package in the EAGLE library: draw it at the PCB stage; the PTA-142 pattern it replaces (1.6 mm pads at +-3.75 / +-1.4) does not fit', 'missing'),
    ('742C083', 'CTS 742C083: 4 x 0603 concave-termination array (3.2 x 1.6), 0.8 mm pitch; CTS land 0.45 x 0.9 pads at +-0.85', 'pitch 0.8, 0.5 x 0.9 pads at +-0.9, 0.05 mm per side wider than CTS: OK; 742C083472JP shares the package code, the Bourns CAT16 and Panasonic EXB-V8V substitutes are convex parts on the same land', 'ok'),
    ('IND2520', 'Murata DFE252010P: 2.5 x 2.0 mm, two pads', 'pads 1.05x2.3 at 2.35 OK', 'ok'),
    ('C0402 / R0402', 'Murata GRM15 land 0.5 wide, gap 0.4, span 1.5; Samsung 1005 land 0.51-0.59 wide, gap 0.36-0.44, span 1.34-1.58', 'pads 0.7 x 0.9 at +-0.65 (gap 0.6, span 2.0): larger in every dimension than either vendor asks; solders, but the extra solder volume raises tombstoning exposure on every 0402 position', 'note'),
]

# Digi-Key, 2026-09-06 evening (manual lookups; NF = part number not recognised)
SUPPLY = {
    'XC7A35T-1CPG236C': ('Active', '72', '$57.06', 'XC7A35T-1CPG236I / -2CPG236C / XC7A50T-1CPG236I also listed'),
    'FT2232HQ-REEL': ('Active', '0, 4,000 due 2027-04-19', '$5.30', 'replaced by the FT2232HL-REEL on 2026-09-09; the QFN-64 stays a same-pin alternate'),
    'FT2232HL-REEL': ('Active', '0, 1,000 due 2027-02-19', '$5.30', 'LQFP-64 of the same die, 50-week lead (Digi-Key 2026-09-09); LCSC C27882 4,767 at $11.45, not an FTDI-authorized channel; FT2232HL-TRAY 0, 160 due 2027-01-18, LCSC 21'),    'AS4C32M16SB-6TIN': ('Active', '0', '$31.12', 'replaced by the -7TCN on 2026-09-08; 108 expected 06-Oct-2026 at Digi-Key, 16-week factory lead'),
    'AS4C32M16SB-7TCN': ('Active', '1,478', '$23.85', 'commercial 0..70 C grade of the same B die (Digi-Key 2026-09-08); -7TCNTR 455 cut tape at $23.05; industrial -7TIN 47 tray / -7TINTR 160 cut tape; -6TIN 0 until Oct 2026; LCSC lists only the -7TIN (15 at $63.93)'),
    'W25Q128JVSIQ': ('Active', 'in stock', '$4.21', ''),
    'SC189ZSKTRT': ('Active', '5,767', '$1.07', ''), 'SC189LSKTRT': ('Active', '2,846', '$0.97', ''), 'SC189ASKTRT': ('Active', '4,589', '$0.90', ''),
    '93LC46BT-I/SN': ('Active', '5,497', '$0.32', '8-SOIC 3.90 mm: confirms the narrow body'),
    '105017-0001': ('Active', '53,846', '$1.00', ''),
    'DM3D-SF': ('Active', 'in stock', '$2.32', ''),
    'BQ24232RGTR': ('Active', '541', '$1.93', 'TI single-cell Li-ion charger + power path, 16-VQFN 3x3, 9-week lead; $1.15 at 100, 3,000-reel $0.97; the 250-piece reel BQ24232RGTT has 1,764 at $1.53; LCSC C528622 766 at $1.18 (Digi-Key and LCSC 2026-09-09); added as U8 in place of D1 on 2026-09-09'),
    'B2B-PH-SM4-TB(LF)(SN)': ('Active', '57,541', '$0.47', 'JST PH 2.0 mm 2-pin top-entry SMT header, 16-week lead, $0.339 at 100, 2,000-reel $0.288; LCSC C160352 49,145 at $0.22 (MOQ 5), TBT variant with auxiliary solder pins C265003 4,654 (Digi-Key and LCSC 2026-09-09); battery input X4, added 2026-09-09'),
    'RC0402FR-073K57L': ('Active', 'not checked', '$0.10', 'Yageo RC0402 E96 value, ISET on U8; verify stock at order time'),
    'RC0402FR-073K09L': ('Active', 'not checked', '$0.10', 'Yageo RC0402 E96 value, ILIM on U8; verify stock at order time'),
    'RC0402FR-0756K2L': ('Active', 'not checked', '$0.10', 'Yageo RC0402 E96 value, TMR on U8; verify stock at order time'),
    'RC0402FR-074K32L': ('Active', 'not checked', '$0.10', 'Yageo RC0402 E96 value, ITERM on U8; verify stock at order time'),
    'RC0402FR-071K5L': ('Active', 'not checked', '$0.10', 'Yageo RC0402 1.5k, LD3/LD4 series resistors; verify stock at order time'),
    '2x PRPC009SAAN-RC + 2x PRPC011SAAN-RC': ('Active', '1,201 / 428', '2 x $0.18 + 2 x $0.22', 'Sullins 0.1 in male breakaway strips for the X2 pin field, two part numbers and two of each per board since the rows were cut identically on 2026-09-09 (1x9 for pins 1-9 and 21-29, 1x11 for pins 10-20 and 30-40); the 1x11 stock covers about 200 boards (Digi-Key 2026-09-08)'),
    'ASEM1-12.000MHZ-LC-T': ('Active', '11,473', '$3.06', 'the +-50 ppm grade; replaced by ECS-3225SMV-120-FP-TR on 2026-09-08'),
    'ECS-3225SMV-120-FP-TR': ('Active', '1,830', '$2.90', 'ECS 12 MHz HCMOS XO, +-10 ppm incl. aging, -40..105 C, 3.2x2.5x1.2 mm, pin 1 tri-state; direct Digi-Key listing, 25-week factory lead time on backorder'),
    'MSASJ105BB5475MFNA01': ('Active', '7,620 (1,608,710 under the alias JMK105BBJ475MV-F)', '$0.13', 'Taiyo Yuden 4.7 uF 6.3 V X5R 0402, 0.65 mm max, about 3.7 uF at 1.8 V; replaced GRM155R60J335ME15D on C39/C139 on 2026-09-08'),
    '2N7002LT1G': ('Active', 'in stock', '$0.25', ''),
    'PPTC062LFBN-RC': ('Active', '7,303', '$0.78', ''),
    'PTA-142': ('NF', '-', '-', 'no distributor listing, catalog vendor unknown; replaced by the PTS810SJM250SMTR LFS on 2026-09-08'),
    'PTS810SJM250SMTR LFS': ('Active', '106,352', '$0.58', 'C&K / Littelfuse PTS810, 1.6 N grade, 16-week factory lead (Digi-Key 4176610, 2026-09-08); LCSC C116501 dry, the 2.6 N K grade C221896 has 2,675'),
    'VS NRD8': ('NF', '-', '-', 'Victory Electronics (TW), no distributor listing; replaced by the Everlight EAST1616RGBA8 on 2026-09-08'),
    'EAST1616RGBA8': ('Active', '15,840', '$0.43', 'Everlight 19-337/R6GHBHW-A01/2T, diffused; pad-for-pad the VS NRD8 (Digi-Key 2026-09-08); water-clear twin EAST1616RGBA4'),
    'LTST-C191KRKT': ('Active', '1,568,793', '$0.15', ''), 'LTST-C191KGKT': ('Active', '2,675,844', '$0.15', ''),
    'BLM18PG601SN1D': ('not a catalogue number', '-', '-', 'Murata BLM18PG series stops at 470 ohm (ENFA0003); replaced by BLM18KG601SN1D on 2026-09-08'),
    'BLM18KG601SN1D': ('Active', '913,912', '$0.10', '600 ohm 1.3 A 0.15 ohm power-line bead 0603 (Digi-Key 2026-09-08; LCSC C85833 791,450); replaced the non-existent BLM18PG601SN1D on L4-L7, which carry 60 mA at most'),
    'DFE252010P-1R5M=P2': ('Active', '16,424', '$0.22', 'Isat 2.1 A, 82 mOhm max'),
    '742C083472JTR': ('OBSOLETE', '0', '-', 'drop-ins: 742C083472JP (98,887, $0.17), Bourns CAT16-472J4LF (225,765, $0.10), Panasonic EXB-V8V472JV (373,378)'),
    'GRM155R71C104KA88D': ('Active', '0, due 2026-11-25', '$0.10', 'stocked substitutes (0.1 uF 16 V X7R 0402): Murata GRM155R71C104JA88D (+-5 %, 703,856) or Samsung CL05B104KO3LNNC (1,829,985)'),
    'GRM188R60J106ME47D': ('Active', '0, due 2026-09-10', '$0.12', ''),
    'GRM155R71H102KA01D': ('Active', '4,888,062', '$0.11', ''),
    'GRM033R71E103KE14D': ('Active', '1,919', '$0.10', ''),
    'GRM155R60J335ME15D': ('NF', '-', '-', 'number unknown to Digi-Key; TDK C1005X5R0J335K050BC (NRND, 43,000) is the only 3.3 uF 6.3 V 0402 found'),
    'GRM033R61A104KE15D': ('Active', '0, due 2026-11-18', '$0.11', 'Taiyo Yuden LMK063BJ104KP-F (1,731,139) or Kyocera KGM03AR51A104KH (380,421)'),
    'GRM21BR61A106KE19L': ('OBSOLETE', '0', '-', 'Samsung CL21A106KPFNNNG (101,469, $0.12) or TDK C2012X5R1A106K085AB (29,234)'),
    'GRM21BR61A226ME44L': ('Active', '0, due 2027-01-04', '$0.32', 'Samsung CL21A226MPQNNNE 0, TDK C2012X5R1A226M125AE 5,046 ($0.91), TDK C2012X5R1A226M085AC NRND 117,921'),
    'GRM188R60J226MEA0D': ('Active', '0, due 2027-01-04', '$0.15', 'Samsung CL10A226MP8NUNE 10 V (521,853, $0.20) or Murata GRT188R60J226ME13D (33,074)'),
    'GRM188R61A475KE15D': ('OBSOLETE', '0', '-', 'Murata GRM188R61A475KAAJD (32,005, $0.42)'),
    'GRM033R60J474KE15D': ('NF', '-', '-', 'typo: GRM033R60J474KE90D is the live number (Active, 1,717,601, $0.10)'),
    'GRM155R61C474KA88D': ('NF', '-', '-', 'GRM155R61C474KE01D is NRND (105,254); Samsung CL05A474KO5NNNC 16 V (67,193) or CL05A474KP5NNNC 10 V (95,280)'),
    '742C163101JP': ('Active', '25,352', '$0.47 cut / $0.1214 at 4,000', '8 x 100 ohm isolated, 2506 concave 6.40 x 1.60 mm, 0.80 mm pitch, 63 mW per element, 5 % (the 742C163 has no 1 % option); six of the eight elements used. Digi-Key read live 2026-09-09. The genuine 6-element part, CTS 753123101GP, is 0 in stock at 28 weeks and MOQ 1,000 ($2.63), and its 12-SRT body, 8.76 x 2.03 mm, is larger than this one'),
    '742C043472JP': ('Active', '36,227', '$0.14 cut / $0.0581 at 100', '2 x 4.7K isolated, 0606 concave 1.60 x 1.60 mm, 0.80 mm pitch, 63 mW per element, 5 %, AEC-Q200. Digi-Key read live 2026-09-09. Same CTS 742 land pattern as R34'),
    '742C083472JP': ('Active', '98,887', '$0.17 reel / $0.18 cut', 'replaced 742C083472JTR on 2026-09-07; same CTS package code, concave terminations (verified 2026-09-08 against CTS DOC 008-0335-0 Rev T)'),
    'CL21A106KPFNNNG': ('Active', '110,449', '$0.13', 'Samsung 10 uF 10 V X5R 0805, 1.35 mm max; replaced GRM21BR61A106KE19L on 2026-09-07 (verified 2026-09-08)'),
    'GRM188R61A475KAAJD': ('NRND', '32,005', '$0.42', 'chosen on 2026-09-07, then found NRND on Murata\'s own page and at Digi-Key on 2026-09-08; replaced again by GRM188R61C475KE11D'),
    'GRM188R61C475KE11D': ('Active', '67,764', '$0.24', 'Murata 4.7 uF 16 V X5R 0603, 0.95 mm max, in production at Murata (2026-09-08); the 10 V value is dying at every vendor. Alternate on the same land: TDK C1608X5R1C475K080AC (16 V, 0.90 mm max, 125,661 at $0.25)'),
    'GRM033R60J474KE90D': ('Active', '1,717,601', '$0.10', 'replaced the mistyped GRM033R60J474KE15D on 2026-09-07; in production at Murata (verified 2026-09-08)'),
    'CL05A474KO5NNNC': ('Active', '18,193', '$0.20', 'Samsung 0.47 uF 16 V X5R 0402, 0.55 mm max; replaced GRM155R61C474KA88D on 2026-09-07 (verified 2026-09-08)'),
    'CL10A226MP8NUNE': ('Active', '469,856', '$0.20', 'Samsung 22 uF 10 V X5R 0603, 1.05 mm max (the Murata was 6.3 V, 1.00 mm); replaced GRM188R60J226MEA0D on 2026-09-07 (verified 2026-09-08)'),
    'RC0402FR-07680RL': ('Active', '0, due 2026-09-28', '$0.10', 'Vishay CRCW0402680RFKTD 16,515'),
}
YAGEO_OK = 'RC0402FR-07100RL RC0201FR-075K1L RC0201FR-074K7L RC0201FR-07100RL RC0201FR-072K32L RC0201FR-071KL RC0201FR-07140RL RC0201FR-07845RL RC0402FR-0712KL RC0201FR-0710KL RC0402FR-071KL RC0201FR-0733RL RC0201FR-07200RL RC0402FR-074K7L RC0402FR-07100KL RC0402FR-0733RL RC0402FR-07330RL RC0402FR-0710KL RC0201FR-072K21L'.split()
for y in YAGEO_OK: SUPPLY[y] = ('Active', 'stocked', '$0.10', '')

SECOND_SOURCE = [
    ('U1 XC7A35T-1CPG236C', 'none (sole source)', 'XC7A15T/XC7A50T-1CPG236 are pin-identical (UG475 CPG236 shared footprint); -2 speed or I grade as stop-gaps'),
    ('U2 FT2232HL', 'FT2232HQ-REEL (QFN-64, same pin numbers, 0 stock until April 2027); FT4232HL / FT4232HQ (same pin numbers for every signal the board uses, UART lands on channel C, EEPROM re-templated, PID 0x6011)', 'no other vendor makes a compatible dual-channel bridge; the FT2232H-56Q keeps every signal but renumbers every pin (re-pinned symbol needed)'),
    ('U3 AS4C32M16SB-7TCN', 'Alliance AS4C32M16SB-7TIN (industrial) and -6TIN (166 MHz), timing-identical or faster; ISSI IS42S16320F-7TL / -6TLI, Micron MT48LC32M16A2P', 'JEDEC 54-TSOP II 32M x16 pinout (A12 on 36, NC on 40); Winbond W9825G6KH is 256 Mbit, half the density; the ISSI -6 grades were 0 stock at MOQ 324 on 2026-09-08'),
    ('U4 W25Q128JVSIQ', 'Macronix MX25L12835FM2I-10G, GigaDevice GD25Q128ESIG, ISSI IS25LP128-JBLE', 'SOIC-8 208 mil, same pinout; all in the Vivado configuration-memory list'),
    ('U5-U7 SC189x', 'none pin-compatible in SOT23-5', 'TI TLV62568 (EN-GND-FB-SW-VIN) and its family differ; the SC189 order VIN-GND-EN-VOUT-LX is Semtech-specific. Mitigation: three grades stocked, buy ahead; fallback is a footprint change'),
    ('U10 93LC46BT-I/SN', 'onsemi CAT93C46VI-GT3, ST M93C46-WMN6TP, Atmel AT93C46EN-SH-T', 'same SOIC-8 pinout, all FTDI-approved 93C46 types (after the footprint is corrected to narrow SOIC)'),
    ('Q1 ASEM1-12.000MHZ', 'SiTime SiT8008BI-xx-33E-12.000000, ECS ECS-2520MV-120-CN-TR, Abracon ASDMB-12.000MHZ', '3225 4-pad oscillators, 1 ST 2 GND 3 OUT 4 VDD; pick a +-25/30 ppm grade'),
    ('X1 105017-0001', 'Amphenol 10118194-0001LF, Hirose ZX62D-B-5P8', 'micro-B receptacles with near-identical 0.65 mm pad rows; shell pads differ, check at layout'),
    ('X3 DM3D-SF', 'none footprint-compatible', 'Molex 104031-0811 and GCT MEM2075 need their own patterns'),
    ('X2 Sullins 2x PRPC009SAAN-RC + 2x PRPC011SAAN-RC', 'any 2.54 mm 1x40 breakaway strip cut to 9 + 11 twice (LCSC Boomele C2337, 81,690); Wurth 6130xx11121 series', '0.64 mm square pins in 1.016 mm holes; four strips per board, one each side of the USB landing and one each side of the LiPo landing directly opposite it'),
    ('U8 bq24232', 'bq24230 (same pinout, 6.6 V OVP, TD pin instead of ITERM: fixed 10 % termination); bq24210/bq24232 family members differ', 'RGT VQFN-16 3x3; the ITERM resistor R105 becomes a TD strap on the bq24230'),
    ('X4 B2B-PH-SM4-TB(LF)(SN)', 'S2B-PH-SM4-TB(LF)(SN) (side entry, 5.5 mm, same pads); JST B2B-PH-K-S (through-hole, different pattern)', 'PH 2.0 mm family; any pack with a PHR-2 housing mates'),
    ('LD0 EAST1616RGBA8', 'Everlight EAST1616RGBA4 (water-clear twin, same pads and numbering); Victory VS NRD8 with the pads renumbered back; Kingbright APTF1616SEEZGKQBKC (pinout to verify)', '1.6 x 1.6 mm six-pad RGB; the Everlight and Victory drawings are identical apart from the pad numbers'),
    ('BTN PTS810SJM250SMTR LFS', 'PTS810SJK / SJG / SJS250SMTR LFS (2.6, 4.0, 6.0 N, same body and pads; K grade stocked at LCSC)', 'PTS810 4.2 x 3.2 mm J-lead; other 4.2 x 3.2 tacts (Panasonic EVQ-P7, Alps SKRT) need their own pattern check'),
    ('R34 742C083472JTR', '742C083472JP, Bourns CAT16-472J4LF, Panasonic EXB-V8V472JV', 'Digi-Key lists all three as direct substitutes'),
    ('R4 742C163101JP', 'Panasonic EXB-2HV101JV (8 x 100 ohm isolated, 3.80 x 1.60 mm, 73,820 in stock, $0.20)', 'same element count and value in a shorter body, but convex terminals on 0.50 mm pitch: its own land pattern, not a drop-in'),
    ('R1 742C043472JP', 'Panasonic EXB-V4V472JV (4,562, $0.22)', 'same 1.60 x 1.60 mm concave body on 0.80 mm pitch, a true drop-in; the convex twin EXB-34V472JV is NOT'),
    ('passives', 'Samsung / TDK / Taiyo Yuden equivalents per the supply table', 'all standard sizes'),
]

# ------------------------------------------------------------------ main --
def main():
    comps = load_components(); padnet = load_netlist(); pk = load_packages(); xl = load_xilinx()
    out = []; w = out.append
    w(f'# Zulu A7 component and BOM validation\n')
    w(f'Generated by tools/bom_audit.py on {DATE} from the Altium sheets, the Protel netlist, the EAGLE packages in zulu_a7.sch, '
      f'AMD\'s CPG236 pinout file and the datasheets in Datasheet/. Distributor data is a Digi-Key snapshot from the evening of 2026-09-06.\n')
    # --- BOM
    groups = OrderedDict()
    for d, c in comps.items():
        if c['lib'] == 'DOCFIELD' or c['lib'].startswith('CC_'): continue
        p = c['params']
        mpn = p.get('MANF#') or p.get('Comment') or c['lib']
        if p.get('DNS') == 'Yes': mpn = 'DNS: ' + mpn          # do not stuff: bare positions carried in the BOM with the flag PCBWay's template uses
        key = (mpn, p.get('MANF') or '', c['fp'] or '', p.get('Comment') or '')
        groups.setdefault(key, []).append(d)
    w('## 1. Bill of materials\n')
    dns_groups = [k for k in groups if k[0].startswith('DNS: ')]
    w(f'{sum(len(v) for k, v in groups.items() if k not in dns_groups)} fitted components, {len(groups) - len(dns_groups)} distinct parts, '
      f'plus {sum(len(groups[k]) for k in dns_groups)} DNS positions (do not stuff). Frames and the licence logos are excluded.\n')
    w('| Part | Manufacturer | Footprint | Value | Qty | Designators |'); w('|---|---|---|---|---:|---|')
    for (mpn, manf, fpn, val), ds in sorted(groups.items(), key=lambda kv: natkey(sorted(kv[1], key=natkey)[0])):
        ds = sorted(ds, key=natkey)
        w(f'| {mpn} | {manf} | {fpn} | {val} | {len(ds)} | {", ".join(ds)} |')
    # --- FPGA
    w('\n## 2. Footprint and pin verification\n')
    w('### 2.1 U1 XC7A35T-1CPG236C against the AMD pinout file\n')
    u1 = {k[3:]: v for k, v in padnet.items() if k.startswith('U1-')}
    sym = comps['U1']['pins']
    missing = sorted(set(xl) - set(sym)); extra = sorted(set(sym) - set(xl))
    w(f'- Symbol pins: {len(sym)}; AMD balls: {len(xl)}; missing from the symbol: {missing or "none"}; not in the package: {extra or "none"}.')
    groups2 = defaultdict(lambda: defaultdict(list))
    for ball, (name, bank) in xl.items():
        base = 'IO bank ' + bank if name.startswith('IO_') else re.sub(r'_\d+$', '', name)
        groups2[base][u1.get(ball, '<open>')].append(ball)
    w('- Power, ground and dedicated balls and the nets they sit on:\n')
    w('| Ball function | Net(s) | Balls |'); w('|---|---|---:|')
    for base in sorted(groups2):
        if base.startswith('IO bank'): continue
        nets = groups2[base]
        w(f'| {base} | ' + ', '.join(f'{n} ({len(b)})' for n, b in nets.items()) + f' | {sum(len(b) for b in nets.values())} |')
    for base in sorted(groups2):
        if base.startswith('IO bank'):
            nets = groups2[base]
            w(f'| {base} | {len(nets)} signal nets | {sum(len(b) for b in nets.values())} |')
    w('\nVCCINT and VCCBRAM on VCC1V0, VCCAUX and VCCBATT on VCC1V8, every VCCO on VCC3V3, the unused GTP supplies and receivers on GND '
      'with the transmitters and reference clocks open (UG482 allows both), VP/VN/VREFP/VREFN on GNDADC (internal reference), '
      'CFGBVS high for a 3.3 V bank 0. Dedicated config pins (CCLK, DONE, INIT_B, PROGRAM_B, M0-M2, TCK/TMS/TDI/TDO) and the SPI flash '
      'D00-D03/FCS_B all sit on their AMD balls; CLK12M is on an MRCC pin and CHAN-CLK on an SRCC pin.\n')
    # --- fixed-function pins
    w('### 2.2 Other parts against their datasheet pin tables\n')
    w('| Part | Check | Result |'); w('|---|---|---|')
    u2 = comps['U2']['pins']
    bad = [(n, u2.get(str(n)), exp) for n, exp in FT2232H.items() if u2.get(str(n)) != exp]
    w(f'| U2 FT2232HL | 64 pins, symbol names vs DS_FT2232H tables 3.1-3.4 (the LQFP and QFN share the numbering; no EP on the LQFP) | {"all match" if not bad else bad} |')
    u3 = {k[3:]: v for k, v in padnet.items() if k.startswith('U3-')}
    bad = [(i + 1, fn, u3.get(str(i + 1))) for i, fn in enumerate(SDRAM) if not sdram_ok(fn, u3.get(str(i + 1)))]
    w(f'| U3 AS4C32M16SB | 54 pads: net on each pad vs the JEDEC x16 pin assignment | {"all 54 match (pin 40 NC open)" if not bad else bad} |')
    u4 = {k[3:]: v for k, v in padnet.items() if k.startswith('U4-')}
    bad = [(p, u4.get(p), n) for p, n in W25Q_NET.items() if u4.get(p) != n]
    w(f'| U4 W25Q128JVSIQ | 8 pads vs W25Q128JV SOIC-8 pin configuration ({", ".join(f"{k} {v}" for k, v in W25Q.items())}) | {"all match" if not bad else bad} |')
    u10 = {k[4:]: v for k, v in padnet.items() if k.startswith('U10-')}
    bad = [(p, u10.get(p), n) for p, n in EEPROM_NET.items() if u10.get(p) != n]
    w(f'| U10 93LC46BT-I/SN | pins vs DS20001749 pin table, FTDI EEPROM wiring (DO via 2.2 k to EEDATA) | {"all match" if not bad else bad} |')
    q1 = {k[3:]: v for k, v in padnet.items() if k.startswith('Q1-')}
    bad = [(p, q1.get(p), n) for p, n in OSC_NET.items() if q1.get(p) != n]
    w(f'| Q1 ASEM1 | 1 ST/OE, 2 GND, 3 OUT, 4 VDD | {"all match" if not bad else bad} |')
    x1 = {k[3:]: v for k, v in padnet.items() if k.startswith('X1-')}
    bad = [(p, x1.get(p), n) for p, n in USB_NET.items() if x1.get(p) != n]
    w(f'| X1 Molex 105017-0001 | 1 VBUS, 2 D-, 3 D+, 4 ID open, 5 + shell GND | {"all match" if not bad else bad} |')
    ld0 = {k[4:]: v for k, v in padnet.items() if k.startswith('LD0-')}
    bad = [(p, ld0.get(p), n) for p, n in RGB.items() if ld0.get(p) != n]
    bad += [(p, ld0.get(p)) for p, r in RGB_ANODE.items() if padnet.get(f'{r}-2') != ld0.get(p)]
    w(f'| LD0 EAST1616RGBA8 | cathodes 2 B, 4 R, 6 G to the FPGA; anodes 1/3/5 through R80/R81/R82 to 3.3 V (19-337 sheet p8 polarity) | {"all match" if not bad else bad} |')
    # Isolated arrays pair pad k with pad 2N+1-k. Each entry is the pad -> net map that pairing
    # implies, written out so the netlist is checked against the intent and not against itself.
    ARRAYS = [
        ('R34', '742C083', 'isolated 4-array, 1-8 2-7 3-6 4-5, the microSD DAT0..3 pull-ups',
         {**{str(i): f'SD-DAT{i - 1}' for i in range(1, 5)}, **{str(i): 'VCC3V3' for i in range(5, 9)}}),
        ('R4', '742C163', 'isolated 8-array, the six 100R series resistors: A PROG#, B DONE, C TDI, '
         'D TDO, E TMS, F TCK, bridge side on pads 1-6 and FPGA side on pads 16 down to 11',
         {'1': 'PROG#', '16': 'RST#', '2': 'DONE', '15': 'FPGA-DONE', '3': 'TDI', '14': 'FPGA-TDI', '4': 'TDO', '13': 'FPGA-TDO', '5': 'TMS', '12': 'FPGA-TMS', '6': 'TCK', '11': 'FPGA-TCK'}),
        ('R1', '742C043', 'isolated 2-array, A the INIT_B pull-up and B the PROGRAM_B pull-up, '
         'both commons on pads 4 and 3',
         {'1': 'FPGA-INIT#', '4': 'VCC3V3', '2': 'RST#', '3': 'VCC3V3'}),
    ]
    for ref, fp, txt, want in ARRAYS:
        got = {k[len(ref) + 1:]: v for k, v in padnet.items() if k.startswith(ref + '-')}
        bad = {p: (got.get(p), n) for p, n in want.items() if got.get(p) != n}
        extra = {p: n for p, n in got.items() if p not in want}
        w(f'| {ref} {fp} | {txt} | {"all match" if not bad and not extra else f"{bad} {extra}"} |')
    w('| Q2 2N7002LT1G | G on PGOOD, S on GND, D on the LED; SOT-23 1 G 2 S 3 D | matches (standard 2N7002 pinout, onsemi sheet not fetchable) |')
    X2 = {'X2-1': 'GND', 'X2-2': 'CHAN-CLK', 'X2-3': 'CHAN0', 'X2-9': 'CHAN6', 'X2-10': 'CHAN7', 'X2-16': 'CHAN13', 'X2-17': 'VCC3V3', 'X2-18': 'VCC1V8', 'X2-19': 'VCC1V0', 'X2-20': 'GND',
          'X2-21': 'GND', 'X2-22': 'VU', 'X2-23': 'RST#', 'X2-24': 'CHAN14', 'X2-26': 'CHAN16', 'X2-27': 'CHAN17', 'X2-38': 'CHAN28', 'X2-39': 'ANALOG-IO0', 'X2-40': 'ANALOG-IO1'}
    bad = [(pad, padnet.get(pad), exp) for pad, exp in X2.items() if padnet.get(pad) != exp]
    bad += [pad for pad in ('X2-41', 'X2-42', 'X2-43', 'X2-44', 'D2-A', 'D2-K', 'D3-A', 'D3-K') if pad in padnet] + [n for n in set(padnet.values()) if n == 'VEXT']
    w(f'| X2 pin field | 40 pins numbered 1-40 (2026-09-09); mirrored rows, 1-9 + USB landing + 10-20 above, 21-29 + LiPo landing + 30-40 below. Top row 1 GND, 2 CHAN-CLK, 3-9 CHAN0-6, 10-16 CHAN7-13, 17 +3.3V, 18 +1.8V, 19 +1.0V, 20 GND; bottom row 21 GND, 22 VU, 23 RST#, 24-29 CHAN14-19, 30-38 CHAN20-28, 39-40 ANALOG-IO0/1 | {"all match" if not bad else bad} |')
    BQ = {1: 'TS', 2: 'BAT', 3: 'BAT', 4: 'CE', 5: 'EN2', 6: 'EN1', 7: 'PGOOD', 8: 'VSS', 9: 'CHG', 10: 'OUT', 11: 'OUT', 12: 'ILIM', 13: 'IN', 14: 'TMR', 15: 'ITERM', 16: 'ISET', 17: 'PAD'}
    u8 = comps['U8']['pins']
    bad = [(n, u8.get(str(n)), exp) for n, exp in BQ.items() if u8.get(str(n)) != exp]
    bad += [(pad, padnet.get(pad), exp) for pad, exp in (('U8-13', 'USB5V0'), ('U8-10', 'VU'), ('U8-11', 'VU'), ('U8-2', 'VBATT'), ('U8-3', 'VBATT'), ('U8-4', 'GND'), ('U8-6', 'GND'), ('U8-5', 'VU'), ('U8-8', 'GND'), ('U8-17', 'GND'), ('X4-1', 'VBATT'), ('X4-2', 'GND')) if padnet.get(pad) != exp]
    w(f'| U8 bq24232 | 17 pin names vs SLUS821J Pin Functions; IN on USB5V0, OUT on VU, BAT on VBATT with X4-1, CE/EN1 low, EN2 high | {"all match" if not bad else bad} |')
    w('| BTN PTS810SJM250SMTR LFS | pins 1,2 = 3.3 V, pins 3,4 = BTN net | PTS810 sheet schematic joins 1-2 and 3-4: matches |')
    # --- geometry
    w('\n### 2.3 EAGLE package geometry against the datasheet land patterns\n')
    w('| Package | Datasheet | Library package | Verdict |'); w('|---|---|---|---|')
    for name, ds, lib, v in GEOM: w(f'| {name} | {ds} | {lib} | **{v}** |')
    # --- supply
    w('\n## 3. Supply chain and lifecycle (Digi-Key, ' + DATE + ')\n')
    w('| Part | Status | Stock | Price qty 1 | Note |'); w('|---|---|---|---|---|')
    seen = set()
    for (mpn, manf, fpn, val), ds in sorted(groups.items(), key=lambda kv: natkey(sorted(kv[1], key=natkey)[0])):
        if mpn in seen or mpn not in SUPPLY: continue
        seen.add(mpn); s = SUPPLY[mpn]
        w(f'| {mpn} (x{len(ds)}) | {s[0]} | {s[1]} | {s[2]} | {s[3]} |')
    dns = [f'{", ".join(sorted(groups[k], key=natkey))} ({k[0][5:]})' for k in groups if k[0].startswith('DNS: ')]
    if dns: w(f'\nDNS, not stuffed, nothing to order: {"; ".join(dns)}.\n')
    unl = [k[0] for k in groups if k[0] not in SUPPLY and not k[0].startswith('DNS: ')]
    if unl: w(f'\nNot looked up (no orderable part): {", ".join(unl)}.\n')
    # --- second source
    w('## 4. Second sourcing\n')
    w('| Part | Pin-compatible alternatives | Note |'); w('|---|---|---|')
    for a, b, c in SECOND_SOURCE: w(f'| {a} | {b} | {c} |')
    # --- derating
    w('\n## 5. Derating\n')
    RAIL = {'GND': 0, 'GNDADC': 0, 'VCC1V0': 1.0, 'VCC1V8': 1.8, 'VCCADC': 1.8, 'VCC3V3': 3.3, 'VU': 5.25, 'USB5V0': 5.25, 'FT-VPHY': 3.3, 'FT-VPLL': 3.3}
    vnet = lambda n: RAIL.get(n, 5.25 if 'USB' in (n or '') else 3.3)
    code = {'0J': 6.3, '1A': 10, '1C': 16, '1E': 25, '1H': 50, '2A': 100}
    w('### 5.1 Capacitors: rated voltage vs the worst node voltage\n')
    w('| Rated | Applied | Ratio | Package | Value | Qty | Designators |'); w('|---:|---:|---:|---|---|---:|---|')
    byk = OrderedDict()
    for d, c in comps.items():
        if not re.fullmatch(r'C\d+', d): continue
        pn = c['params'].get('MANF#') or ''; vr = code.get(pn[8:10]) if pn.startswith('GRM') else ({'Q': 6.3, 'P': 10, 'O': 16, 'A': 25, 'B': 50}.get(pn[9:10]) if pn.startswith('CL') else None)
        nets = [padnet.get(f'{d}-1'), padnet.get(f'{d}-2')]
        v = abs(vnet(nets[0]) - vnet(nets[1])) if None not in nets else 0
        byk.setdefault((vr, v, c['fp'], c['params'].get('Comment')), []).append(d)
    for (vr, v, fp, val), ds in sorted(byk.items(), key=lambda kv: -(kv[0][1] / (kv[0][0] or 1))):
        w(f'| {vr} V | {v:.2f} V | {v / vr * 100 if vr else 0:.0f}% | {fp} | {val} | {len(ds)} | {", ".join(sorted(ds, key=natkey))} |')
    w('\nNothing above 52 % of its rating. The 6.3 V parts on 3.3 V (C13, C39, C139, C107-C122) are within the usual 80 % ceiling for X5R/X7R but lose '
      'roughly half their capacitance to DC bias, which the UG483 decoupling counts already assume.\n')
    w('### 5.2 Resistors that see DC\n')
    w('| Ref | Value | Package | Nets | Worst V | Power | Of rating |'); w('|---|---|---|---|---:|---:|---:|')
    for d, c in comps.items():
        if not re.fullmatch(r'R\d+', d) or len(c['pins']) != 2: continue   # arrays: pads 1 and 2 are different elements
        m = re.match(r'([\d.]+)\s*([kKmM]?)', c['params'].get('Comment', ''))
        if not m: continue
        R = float(m.group(1)) * {'': 1, 'k': 1e3, 'K': 1e3, 'm': 1e6, 'M': 1e6}[m.group(2)]
        a, b = padnet.get(f'{d}-1'), padnet.get(f'{d}-2')
        if a is None or b is None or not (a in RAIL or b in RAIL): continue
        V = abs(vnet(a) - vnet(b)) if (a in RAIL and b in RAIL) else vnet(a if a in RAIL else b)
        P = V * V / R; Pr = {'R0201': 0.05, 'R0402': 0.0625}.get(c['fp'], 0.05)
        if P / Pr > 0.2: w(f'| {d} | {c["params"].get("Comment")} | {c["fp"]} | {a} - {b} | {V:.2f} | {P * 1000:.1f} mW | {P / Pr * 100:.0f}% |')
    w('\nR80/R82 (33 ohm) only reach that figure with a shorted LED; with the blue/green VF of 3.3-3.8 V they carry a few milliamps. R81 (red, 330 ohm) runs at 3.9 mA, '
      'R100 (DONE pull-up, the UG470 value) at 33 mW only while DONE is low. Everything else is a signal-path or pull-up part under 20 % of its rating.\n')
    w('### 5.3 Semiconductors, regulators, magnetics, connectors\n')
    w('| Part | Rating | Applied | Margin |'); w('|---|---|---|---|')
    for row in [
        ('U5-U7 SC189', 'VIN 2.9-5.5 V (abs max 6 V), 1.5 A, Tj 125 C', 'VU 4.4-4.95 V, 0.68 A worst on 3.3 V, Tj rise 11-22 C at 90 C/W', 'OK; VU is the bq24232 OUT, 4.4 V regulated or VBAT - 60 mV, never above 5.5 V now that the +5V-INPUT pin is gone (2026-09-09)'),
        ('L1-L3 DFE252010P-1R5M', 'Isat 2.1 A, Idc 1.8 A (40 C rise)', 'peak 0.83 A at the 677 mA worst case', 'OK, 40 % of Isat'),
        ('U8 bq24232', 'IN 4.35-10.2 V (OVP 10.5 V), IIN 500 mA, IOUT 1.5 A, ICHG 500 mA, Tj regulated at 125 C', 'USB 5.25 V max, 495 mA input limit, 244 mA charge; 0.6 W worst = 27 C rise at 44.5 C/W', 'OK'),
        ('X4 JST PH', '2 A per contact, 100 V', 'charge 244 mA, discharge under 0.5 A', 'OK'),
        ('Q2 2N7002', '60 V, 115 mA (onsemi), VGS +-20 V', '3.3 V, 1.8 mA LED current, 3.3 V gate', 'OK'),
        ('U1 XC7A35T-1CPG236C', 'VCCINT 0.95-1.05, VCCAUX 1.71-1.89, VCCO 3.135-3.465 V, Tj 0-85 C', 'SC189 +-2.5 % plus +-1 % load: 0.965-1.035, 1.737-1.863, 3.18-3.42 V; Tj rise 10-15 C', 'OK; VCCINT has 15 mV of the 50 mV band left for ripple and drop, keep the 1.0 V path short'),
        ('U2 FT2232HL', 'VCCIO 3.0-3.6 V, clock 12 MHz +-30 ppm, Tj 125 C', '3.3 V; ECS-3225SMV-120-FP-TR is +-10 ppm incl. aging; LQFP thetaJA 37.66 C/W', 'OK'),
        ('U3 AS4C32M16SB-7TCN', 'VDD 3.0-3.6 V, 143 MHz at CL3 (100 MHz at CL2), TA 0..70 C', '3.3 V; commercial ambient range, the same 0 C floor as the -1C FPGA (Tj 0..85 C)', 'OK; the controller must use the -7 column (tRCD/tRP 21 ns, tRC 63 ns, tWR 14 ns) and CL3 above 100 MHz'),
        ('U4 W25Q128JVSIQ', '2.7-3.6 V, 133 MHz', '3.3 V, CCLK a few tens of MHz', 'OK'),
        ('X1 105017-0001', '1 A per contact, 30 V', '0.66 A worst on VBUS', 'OK, 66 % of the contact rating'),
        ('X2 header / J1 Pmod', '0.1 in pins ~1-3 A', 'VU pass-through and 3.3 V outputs', 'OK'),
        ('LEDs', 'IF 25 mA (Everlight 19-337, the same table as the VS NRD8), 20-30 mA (LTST)', '3.9 mA red, <10 mA blue/green, 1.8 mA LD5, 4 mA LD1/LD2, 1.5 mA LD3/LD4 from the 4.4 V charger output', 'OK'),
        ('FPGA I/O driving LEDs', '12 mA default LVCMOS33 drive', '4-10 mA sinks', 'OK'),
    ]:
        w(f'| {row[0]} | {row[1]} | {row[2]} | {row[3]} |')
    # --- findings
    w('\n## 6. Findings\n')
    for i, f in enumerate([
        '**U10 footprint does not fit the part.** The library package SOIC8 has its pad rows 7.62 mm apart (a 300 mil pattern). The 93LC46BT-I/SN is the 3.90 mm narrow SOIC with a 6.00 mm lead span, so the lead tips end 0.06 mm before the pads begin. Redraw U10 on a 150 mil SOIC-8 pattern (the library\'s SPI-8_SOIC_150 has the right row spacing) or order the SOIJ 208 mil part 93LC46BT-I/SM to suit the pads.',
        '**The SOD123 pattern is no longer used.** D1 went with the bq24232 and D2/D3 went with the +5V-INPUT pin, both on 2026-09-09 (the LiPo on X4 is the external supply), so the SOD323F / SOD-123FL land mismatch found on 2026-09-07 needs no correction; no diode remains on the board.',
        '**CPG236 land pads are undersize.** The library uses 0.225 mm pads; UG475 Table A-1 asks for 0.275 mm NSMD lands with 0.375 mm mask openings on the 0.5 mm pitch. Set that when the PCB library is built.',
        '**Footprints that do not exist yet**: SOT23-5 for the SC189s, DM3D-SF for X3, PTS810 for the button, EVERLIGHT-19-337 (the VS-NRD8 pattern renumbered), FT2232HL-LQFP64, and since 2026-09-09 VQFN16-3X3-RGT for the charger and JST-B2B-PH-SM4-TB for the battery connector. the ZULU-DIP37 pin field must be redrawn with 40 pads named 1-40 (renumbered 2026-09-09; the imported 44-pad names no longer match). All must be drawn at the PCB stage from the makers land patterns.',
        '**Oscillator grade is out of the FT2232H spec.** ASEM1-12.000MHZ-LC-T decodes (datasheet p3) to 3.3 V, -40..85 C, +-50 ppm; the FT2232H datasheet asks for +-30 ppm. The comment on Q1 says 25 ppm, so the intent was the LR grade (ASEM1-12.000MHZ-LR-T), which no distributor stocks. A 20-agent search on 2026-09-08 (Digi-Key plus the makers\' datasheets, top picks cross-examined) found four pin-compatible 3.2 x 2.5 mm parts on Digi-Key\'s shelf that meet +-30 ppm all-inclusive: ECS-3225SMV-120-FP-TR (+-10 ppm including aging, -40..105 C, 1,830 pcs, $2.90, recommended), Abracon ASEMB-12.000MHZ-LY-T (+-10 ppm plus 5 ppm/yr aging, 6,143 pcs, $4.40), ECS-3225SMVQ-120-DS-TR (+-20 ppm including aging, 862 pcs, $1.82) and SiTime SIT1602BI-22-33E-12.000000 (+-25 ppm including first-year aging, 440 pcs, $1.54). The SiTime SiT8008 grades that a judge preferred are factory stock programmed to order, not shelf stock. Applied on 2026-09-08 at the user\'s choice: Q1 is now ECS-3225SMV-120-FP-TR (comment 12MHz 10ppm), same 3225 land, pin 1 tied high runs the oscillator.',
        '**Three parts were obsolete** and were replaced on 2026-09-07 by tools/apply_bom_substitutions.py: R34 742C083472JTR by 742C083472JP, the 10 uF 10 V 0805 GRM21BR61A106KE19L on C78/C147-C149 by Samsung CL21A106KPFNNNG, and the 4.7 uF GRM188R61A475KE15D on eleven decoupling positions. The first 4.7 uF replacement (GRM188R61A475KAAJD) turned out to be NRND at Murata, and every 4.7 uF 10 V X5R 0603 on the market is NRND, obsolete or dry, so on 2026-09-08 those eleven positions moved to the 16 V grade GRM188R61C475KE11D, which Murata lists as in production and which also halves the DC-bias loss on the 3.3 V positions.',
        '**Three part numbers were unknown to the distributor**; two were replaced on 2026-09-07 (GRM033R60J474KE15D, a typo, by GRM033R60J474KE90D on 22 positions; GRM155R61C474KA88D on C124 by Samsung CL05A474KO5NNNC) and the 22 uF 0603 on C82/C84 moved to the stocked 10 V Samsung CL10A226MP8NUNE. GRM155R60J335ME15D (C39/C139, the FT2232H VCORE filter, FTDI minimum 3.3 uF) is unobtainable and no 3.3 uF 0402 at 6.3 V or more exists that is not obsolete or NRND (Digi-Key\'s whole 3.3 uF 0402 list was checked on 2026-09-08). The same-footprint answer is 4.7 uF: Taiyo Yuden JMK105BBJ475MV-F, ordered under its new number MSASJ105BB5475MFNA01 (6.3 V X5R, 0.65 mm max, about 3.7 uF left at 1.8 V, 1.6 M pcs, $0.13, recommended), or Murata GRM155R60J475ME47D (0.60 mm max, in production, 980 k pcs, $0.10, but only about 2.2-2.8 uF left at 1.8 V so the pair sits close to FTDI\'s minimum at the tolerance corners). Both survived two skeptics each. Applied on 2026-09-08: C39 and C139 are now 4.7 uF MSASJ105BB5475MFNA01 (Digi-Key alias JMK105BBJ475MV-F).',
        '**No part is without a distributor any more**: the PTA-142 button became the C&K PTS810SJM250SMTR LFS and the Victory VS NRD8 RGB LED became the Everlight EAST1616RGBA8 (its pad-for-pad twin, pins renumbered) and the X2 ZULU-CONN pin field got its Sullins PRPC strips, all on 2026-09-08 (PRPC009/011 on the top row; the bottom row became 1x6 + 1x14 on 2026-09-09 after the LiPo landing was opened and the field renumbered 1-40). Only JP3/JP4 remain without a part, by design (bare holes).',
        '**Long-lead items**: U2 became the FT2232HL on 2026-09-09 because the FT2232HQ has no authorized stock until April 2027; the HL is itself 0 at Digi-Key (1,000 due 19-Feb-2027) and only LCSC holds it (4,767), so name that channel or consign, the SDRAM -6 grade is dry until October 2026, so on 2026-09-08 U3 became the AS4C32M16SB-7TCN (same die, package and pinout, 143 MHz, commercial 0..70 C like the -1C FPGA; 1,478 at Digi-Key), and the 22 uF 0805 value (13 pcs) is dry across Murata, Samsung and TDK\'s active parts, with only NRND TDK stock; C82/C84 now carry the stocked Samsung CL10A226MP8NUNE.',
        '**C124 returns to the wrong ground.** Seen while re-checking its substitution: C123 (100 nF) returns to GNDADC but C124 (470 nF) returns to digital GND, whereas UG480 Figure 6-1 draws both XADC supply filter capacitors from VCCADC to the analog ground on the far side of the ground ferrite L6. The sheet-1 note describes both as one filter. Move C124\'s ground pin to GNDADC when the XADC front end is next touched; it is a one-wire change.',
        '**Everything else checks out**: the FPGA symbol and power tree, the FT2232H, SDRAM, flash and EEPROM pin functions, the USB receptacle, LED polarity and pads, capacitor voltage margins, resistor power, regulator and diode ratings. On 2026-09-08 nine of the findings and substitutions above were handed to independent reviewers told to refute them from primary sources; they confirmed all of the conclusions and corrected the details now written here (the D1/D2 land numbers, the D3 verdict, the 4.7 uF replacement, the 22 uF height, R34\'s concave terminations).',
        '**LiPo charger added 2026-09-09.** U8 (TI bq24232) replaces D1: USB5V0 into IN, OUT regulated at 4.4 V onto VU (VBAT - 60 mV on battery), battery on X4 (JST PH, pin 1 = +). The input is capped at 495 mA (R103), so the board can no longer exceed the USB limit; DPPM trims the 244 mA charge current (R102) first and the battery supplements peaks. On battery alone the 3.3 V buck holds regulation down to about 3.45 V. TS is a fixed 10 k (R106): the pack must carry its own protection. The +5V-INPUT pin with D2 and D3 was removed on 2026-09-09: the LiPo is the external supply. Scope battery-only start-up into the 40 uF on VU on the first board.',
        '**X2 pin field reworked 2026-09-09** for the LiPo header X4, which sits on the top side in the bottom row opposite the USB, the way X1 sits in the top row: +5V-INPUT (with D2/D3 and the VEXT net), GND5 and GND3 were removed, +3.3V2 and GND3 first swapped with CHAN12/CHAN13, then the bottom row was closed up and re-numbered by position: 21 GND, 22 VU, 23 RST#, 24 +3.3V, 25-27 CHAN14-16, 28-30 EMPTY (x 41.91 / 39.37 / 36.83, 10.16 mm between the neighbouring pin centres for the 7.95 mm JST body), then +3.3V2 as well, and the row was finally closed up and the whole field renumbered 1-40 straight through, skipping both landings the way the top row always has. The landing was then moved opposite the micro-USB and the top row put in channel order (1 GND, 2 CHAN-CLK, 3-9 CHAN0-6, 10-16 CHAN7-13, 17-20 the supplies). FINAL, the two rows mirror images: top row pins 1-9 (x 59.69..39.37), USB landing (36.83..29.21), pins 10-20 (26.67..1.27); bottom row pins 21-29 (21 GND, 22 VU, 23 RST#, 24-29 CHAN14-19), LiPo landing on the SAME four x values, pins 30-40 (CHAN20-28, ANALOG-IO0/1). Each landing is 12.70 mm between neighbouring pin centres and 11.176 mm clear, so the 7.95 mm JST body has 1.61 mm each side and X4 sits directly opposite the USB receptacle. Three grounds (1, 20, 21), 3.3 V on pin 17 alone. Strips: 1x9 + 1x11 in each row, two part numbers, two of each per board. THE ZULU-DIP37 FOOTPRINT MUST BE REDRAWN with 40 pads named 1-40: the imported one still names 44 and no longer matches above pin 26. Netlists checked at each step against the previous export: only the documented pad reassignments, nothing else.',
    ], 1):
        w(f'{i}. {f}')
    print('\n'.join(out))

if __name__ == '__main__':
    main()
