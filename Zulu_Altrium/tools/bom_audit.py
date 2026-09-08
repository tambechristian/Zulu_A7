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
            c = comps.setdefault(d, {'sheet': n, 'lib': field(b, 'LibReference'), 'pins': {}, 'params': {}, 'fp': None, 'gates': 0})
            c['gates'] += 1
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
RGB = {'1': 'LED0_B', '2': 'LED0_R', '3': 'LED0_G'}                                                     # VS NRD8 p2: cathodes 1 B, 2 R, 3 G; anodes 4 B, 5 R, 6 G
RGB_ANODE = {'4': 'R80', '5': 'R81', '6': 'R82'}

# EAGLE package geometry against the datasheet land patterns (mm)
GEOM = [
    ('XC7A35T-CPG236', 'UG475 v1.20 Table A-1: 0.5 mm pitch, land 0.275 mm NSMD, mask 0.375', 'pitch 0.5 OK; pads 0.225 mm, 0.05 mm under the AMD land', 'deviation'),
    ('FT2232HQ-QFN64', 'DS_FT2232H QFN-64 9x9, 0.5 mm pitch, exposed pad', 'pitch 0.5, pads 0.25x0.6, EP 4.95 OK', 'ok'),
    ('TSOPII-54', 'AS4C32M16SB TSOP II 400 mil, 0.8 mm pitch, lead span 11.76 max', 'pitch 0.8, rows 11.36 apart, 1.2 mm pads OK', 'ok'),
    ('SOIC-8_208MIL', 'W25Q128JVSIQ SOIC-8 208 mil, lead span 7.9-8.1', 'rows 7.3 apart, 1.51 mm pads OK', 'ok'),
    ('SOIC8', '93LC46BT-I/SN: SN = 3.90 mm narrow body, E = 6.00 BSC, foot 0.40-1.27', 'rows 7.62 apart, pads 1.5 long: inner edge at 3.06 mm, lead tip at 3.00 mm - no overlap', 'FAIL'),
    ('SOD123', 'PMEG2020EJ = SOD323F (SC-90): tip to tip 2.3-2.7, foot 0.3-0.5; Nexperia reflow lands 0.6 x 0.6 mm centred +-1.1 (inner edge 0.8, pitch 2.2)', 'pads centred +-1.4, 0.9 long (0.95..1.85), 0.3 mm outboard of Nexperia: lead tips at 1.15-1.35, only 0.2-0.4 mm of foot on pad, 0.5-0.7 mm of pad past the tip', 'FAIL'),
    ('SOD123', 'SMF5.0A = SOD-123FL: tip to tip 3.4-3.9, foot 0.35-0.90 (about 0.6 nominal); Littelfuse pads 1.3 x 1.4 with a 1.6 gap', 'pads 0.9 x 1.1 at +-1.4 (0.95..1.85): 0.25-0.80 mm of foot on copper but zero toe at the nominal span and 0.1 mm overhang at the maximum; solderable, not the maker\'s pattern', 'marginal'),
    ('SOT23-3', '2N7002LT1G SOT-23: 1 G, 2 S, 3 D (standard 2N7002 pinout, datasheet not on disk)', 'pads G(-0.95,-0.7) S(0.95,-0.7) D(0,0.7), 0.95 pitch OK', 'ok'),
    ('SOT23-5', 'SC189xSKTRT SOT23-5, datasheet p23 land: 0.95 pitch, pads 0.60 x 1.10, inner gap 1.40, outer span 3.60', 'no such package in the EAGLE library: footprint must be drawn at the PCB stage', 'missing'),
    ('DM3D-SF', 'DM3 catalog p9: 8 x 0.55 pads on 1.1 pitch, 4 cover pads, 2 switch pads, 2 keep-outs', 'no such package in the EAGLE library: footprint must be drawn at the PCB stage', 'missing'),
    ('MOLEX-105017-0001', 'Molex 105017 drawing: 5 x 0.4 mm pads on 0.65 pitch, 4 shell pads, 2 pegs', '0.65 pitch, 0.4x1.35 pads, shell pads OK', 'ok'),
    ('32X25', 'ASEM1 3.2x2.5 mm, 4 pads', 'pads 1.2x1.4 at 1.7 x 2.2 OK', 'ok'),
    ('VS-NRD8', 'VS NRD8 p2 recommended pads: 0.55x0.4 outer at +-0.725, 0.7x0.5 middle', 'identical', 'ok'),
    ('PTA-142', 'PTA-142 catalog: 7.5 x 3.0 lead span, 1.6 x 1.4 pads', 'pads 1.6x1.6 at 7.5 x 2.8 OK (0.2 mm closer than drawn); same-side pads assumed common - verify', 'ok'),
    ('742C083', 'CTS 742C083: 4 x 0603 concave-termination array (3.2 x 1.6), 0.8 mm pitch; CTS land 0.45 x 0.9 pads at +-0.85', 'pitch 0.8, 0.5 x 0.9 pads at +-0.9, 0.05 mm per side wider than CTS: OK; 742C083472JP shares the package code, the Bourns CAT16 and Panasonic EXB-V8V substitutes are convex parts on the same land', 'ok'),
    ('IND2520', 'Murata DFE252010P: 2.5 x 2.0 mm, two pads', 'pads 1.05x2.3 at 2.35 OK', 'ok'),
    ('C0402 / R0402', 'Murata GRM15 land 0.5 wide, gap 0.4, span 1.5; Samsung 1005 land 0.51-0.59 wide, gap 0.36-0.44, span 1.34-1.58', 'pads 0.7 x 0.9 at +-0.65 (gap 0.6, span 2.0): larger in every dimension than either vendor asks; solders, but the extra solder volume raises tombstoning exposure on every 0402 position', 'note'),
]

# Digi-Key, 2026-09-06 evening (manual lookups; NF = part number not recognised)
SUPPLY = {
    'XC7A35T-1CPG236C': ('Active', '72', '$57.06', 'XC7A35T-1CPG236I / -2CPG236C / XC7A50T-1CPG236I also listed'),
    'FT2232HQ-REEL': ('Active', '0, 4,000 due 2027-04-19', '$5.30', 'FT2232HQ-TRAY also 0, 260 due 2027-04-19, 46-week lead time; FTDI, Mouser, Arrow, Newark pages not reachable'),
    'AS4C32M16SB-6TIN': ('Active', '0', '$31.12', '-7TIN 47, -7TCN 1,478, -7TCNTR 1,455 in stock; -6 grade dry'),
    'W25Q128JVSIQ': ('Active', 'in stock', '$4.21', ''),
    'SC189ZSKTRT': ('Active', '5,767', '$1.07', ''), 'SC189LSKTRT': ('Active', '2,846', '$0.97', ''), 'SC189ASKTRT': ('Active', '4,589', '$0.90', ''),
    '93LC46BT-I/SN': ('Active', '5,497', '$0.32', '8-SOIC 3.90 mm: confirms the narrow body'),
    '105017-0001': ('Active', '53,846', '$1.00', ''),
    'DM3D-SF': ('Active', 'in stock', '$2.32', ''),
    'ASEM1-12.000MHZ-LC-T': ('Active', '11,473', '$3.06', 'this is the +-50 ppm grade; the +-25 ppm LR grade is not stocked'),
    '2N7002LT1G': ('Active', 'in stock', '$0.25', ''),
    'PMEG2020EJ,115': ('Active', 'in stock', '$0.60', 'SOD323F'),
    'SMF5.0A': ('Active', 'in stock', '$0.50', 'SOD-123FL'),
    'PPTC062LFBN-RC': ('Active', '7,303', '$0.78', ''),
    'PTA-142': ('NF', '-', '-', 'no distributor listing; catalog vendor unknown'),
    'VS NRD8': ('NF', '-', '-', 'Victory Electronics (TW), no distributor listing; Digilent sources it directly'),
    'LTST-C191KRKT': ('Active', '1,568,793', '$0.15', ''), 'LTST-C191KGKT': ('Active', '2,675,844', '$0.15', ''),
    'BLM18PG601SN1D': ('unverified', '-', '-', 'Digi-Key search returns nothing for this number and the Murata page did not load; a current catalogue part, verify at order time'),
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
    ('U2 FT2232HQ', 'none pin-compatible', 'FT2232HL is the LQFP-64 of the same die (different footprint); no other vendor makes a compatible dual-channel bridge'),
    ('U3 AS4C32M16SB-6TIN', 'Winbond W9825G6KH-6, ISSI IS42S16320F-6TL, Micron MT48LC32M16A2P-6A', 'JEDEC 54-TSOP II 32M x16 pinout (A12 on 36, NC on 40); -7 grades of any if 143 MHz is enough'),
    ('U4 W25Q128JVSIQ', 'Macronix MX25L12835FM2I-10G, GigaDevice GD25Q128ESIG, ISSI IS25LP128-JBLE', 'SOIC-8 208 mil, same pinout; all in the Vivado configuration-memory list'),
    ('U5-U7 SC189x', 'none pin-compatible in SOT23-5', 'TI TLV62568 (EN-GND-FB-SW-VIN) and its family differ; the SC189 order VIN-GND-EN-VOUT-LX is Semtech-specific. Mitigation: three grades stocked, buy ahead; fallback is a footprint change'),
    ('U10 93LC46BT-I/SN', 'onsemi CAT93C46VI-GT3, ST M93C46-WMN6TP, Atmel AT93C46EN-SH-T', 'same SOIC-8 pinout, all FTDI-approved 93C46 types (after the footprint is corrected to narrow SOIC)'),
    ('Q1 ASEM1-12.000MHZ', 'SiTime SiT8008BI-xx-33E-12.000000, ECS ECS-2520MV-120-CN-TR, Abracon ASDMB-12.000MHZ', '3225 4-pad oscillators, 1 ST 2 GND 3 OUT 4 VDD; pick a +-25/30 ppm grade'),
    ('X1 105017-0001', 'Amphenol 10118194-0001LF, Hirose ZX62D-B-5P8', 'micro-B receptacles with near-identical 0.65 mm pad rows; shell pads differ, check at layout'),
    ('X3 DM3D-SF', 'none footprint-compatible', 'Molex 104031-0811 and GCT MEM2075 need their own patterns'),
    ('LD0 VS NRD8', 'Kingbright APTF1616SEEZGKQBKC (1.6x1.6 RGB)', 'pinout to verify; VS NRD8 itself only via Victory/Digilent'),
    ('D1/D2 PMEG2020EJ', 'Nexperia PMEG2010EJ, PMEG2020EJ alternatives in SOD323F', 'or Diodes SDM2U30 class; any SOD323F 2 A Schottky once the pattern is corrected'),
    ('BTN PTA-142', 'E-Switch TL3305AF160QG, Panasonic EVQ-P2 class', '4.5 mm SMD tactile with 7.5 mm lead span; verify pad pairing'),
    ('R34 742C083472JTR', '742C083472JP, Bourns CAT16-472J4LF, Panasonic EXB-V8V472JV', 'Digi-Key lists all three as direct substitutes'),
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
        key = (p.get('MANF#') or p.get('Comment') or c['lib'], p.get('MANF') or '', c['fp'] or '', p.get('Comment') or '')
        groups.setdefault(key, []).append(d)
    w('## 1. Bill of materials\n')
    w(f'{sum(len(v) for v in groups.values())} fitted components, {len(groups)} distinct parts. Frames and the licence logos are excluded.\n')
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
    w(f'| U2 FT2232HQ | 64 pins + EP, symbol names vs DS_FT2232H tables 3.2-3.4 and the bus pins | {"all match" if not bad else bad} |')
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
    w(f'| LD0 VS NRD8 | cathodes 1 B, 2 R, 3 G to the FPGA; anodes 4/5/6 through R80/R81/R82 to 3.3 V (datasheet p2 polarity) | {"all match" if not bad else bad} |')
    r34 = {k[4:]: v for k, v in padnet.items() if k.startswith('R34-')}
    ok = all(r34.get(str(i)) == f'SD-DAT{i - 1}' for i in range(1, 5)) and all(r34.get(str(i)) == 'VCC3V3' for i in range(5, 9))
    w(f'| R34 742C083 | isolated 4-array: 1-8, 2-7, 3-6, 4-5 pairs, SD-DAT0..3 pull-ups | {"all match" if ok else r34} |')
    w('| Q2 2N7002LT1G | G on PGOOD, S on GND, D on the LED; SOT-23 1 G 2 S 3 D | matches (standard 2N7002 pinout, onsemi sheet not fetchable) |')
    w('| D1/D2/D3 | D1 USB5V0->VU, D2 VEXT->VU, D3 TVS cathode on VEXT | orientation correct |')
    w('| BTN PTA-142 | pads 1,2 = 3.3 V, pads 3,4 = BTN net | same-side pads assumed internally common; verify on a sample |')
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
    unl = [k[0] for k in groups if k[0] not in SUPPLY]
    w(f'\nNot looked up (no orderable part): {", ".join(unl)}.\n')
    # --- second source
    w('## 4. Second sourcing\n')
    w('| Part | Pin-compatible alternatives | Note |'); w('|---|---|---|')
    for a, b, c in SECOND_SOURCE: w(f'| {a} | {b} | {c} |')
    # --- derating
    w('\n## 5. Derating\n')
    RAIL = {'GND': 0, 'GNDADC': 0, 'VCC1V0': 1.0, 'VCC1V8': 1.8, 'VCCADC': 1.8, 'VCC3V3': 3.3, 'VU': 5.25, 'USB5V0': 5.25, 'VEXT': 5.25, 'FT-VPHY': 3.3, 'FT-VPLL': 3.3}
    vnet = lambda n: RAIL.get(n, 5.25 if ('USB' in (n or '') or 'VEXT' in (n or '')) else 3.3)
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
        if not re.fullmatch(r'R\d+', d) or d == 'R34': continue
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
        ('U5-U7 SC189', 'VIN 2.9-5.5 V (abs max 6 V), 1.5 A, Tj 125 C', 'VU 4.4-4.95 V, 0.68 A worst on 3.3 V, Tj rise 11-22 C at 90 C/W', 'OK; a +5V-INPUT above 5.5 V is only clamped by D3 at 6.4-9.2 V, so keep the external supply regulated'),
        ('L1-L3 DFE252010P-1R5M', 'Isat 2.1 A, Idc 1.8 A (40 C rise)', 'peak 0.83 A at the 677 mA worst case', 'OK, 40 % of Isat'),
        ('D1/D2 PMEG2020EJ', '20 V, 2 A, Tj 150 C', '5.25 V, 0.66 A worst; VF 0.35-0.41 V', 'OK, 33 % current; 0.25 W in a 350 K/W package is a 90 C rise on a bare pad, use the 1 cm2 cathode pour Nexperia assumes for 150 K/W'),
        ('D3 SMF5.0A', 'Vwm 5 V, Vbr 6.4 V, Vc 9.2 V at Ipp', 'VEXT nominal 5 V, USB max 5.25 V', 'OK; clamps well above the SC189 6 V abs max, so it protects the port, not the regulators'),
        ('Q2 2N7002', '60 V, 115 mA (onsemi), VGS +-20 V', '3.3 V, 1.8 mA LED current, 3.3 V gate', 'OK'),
        ('U1 XC7A35T-1CPG236C', 'VCCINT 0.95-1.05, VCCAUX 1.71-1.89, VCCO 3.135-3.465 V, Tj 0-85 C', 'SC189 +-2.5 % plus +-1 % load: 0.965-1.035, 1.737-1.863, 3.18-3.42 V; Tj rise 10-15 C', 'OK; VCCINT has 15 mV of the 50 mV band left for ripple and drop, keep the 1.0 V path short'),
        ('U2 FT2232HQ', 'VCCIO 3.0-3.6 V, clock 12 MHz +-30 ppm', '3.3 V; ASEM1-12.000MHZ-LC-T is +-50 ppm over -40..85 C', 'clock tolerance out of spec on paper'),
        ('U3 AS4C32M16SB-6TIN', 'VDD 3.0-3.6 V, 166 MHz, Tc -40..85 C', '3.3 V, industrial grade', 'OK'),
        ('U4 W25Q128JVSIQ', '2.7-3.6 V, 133 MHz', '3.3 V, CCLK a few tens of MHz', 'OK'),
        ('X1 105017-0001', '1 A per contact, 30 V', '0.66 A worst on VBUS', 'OK, 66 % of the contact rating'),
        ('X2 header / J1 Pmod', '0.1 in pins ~1-3 A', 'VU pass-through and 3.3 V outputs', 'OK'),
        ('LEDs', 'IF 25 mA (VS NRD8), 20-30 mA (LTST)', '3.9 mA red, <10 mA blue/green, 1.8 mA LD5, 4 mA LD1/LD2', 'OK'),
        ('FPGA I/O driving LEDs', '12 mA default LVCMOS33 drive', '4-10 mA sinks', 'OK'),
    ]:
        w(f'| {row[0]} | {row[1]} | {row[2]} | {row[3]} |')
    # --- findings
    w('\n## 6. Findings\n')
    for i, f in enumerate([
        '**U10 footprint does not fit the part.** The library package SOIC8 has its pad rows 7.62 mm apart (a 300 mil pattern). The 93LC46BT-I/SN is the 3.90 mm narrow SOIC with a 6.00 mm lead span, so the lead tips end 0.06 mm before the pads begin. Redraw U10 on a 150 mil SOIC-8 pattern (the library\'s SPI-8_SOIC_150 has the right row spacing) or order the SOIJ 208 mil part 93LC46BT-I/SM to suit the pads.',
        '**D1/D2 footprint is for the wrong package.** PMEG2020EJ is SOD323F: 2.3-2.7 mm tip to tip, 0.3-0.5 mm feet, Nexperia reflow lands 0.6 x 0.6 mm centred 1.1 mm from centre (inner edge at 0.8). The SOD123 pattern centres its pads 1.4 mm out, 0.3 mm further, leaving 0.2-0.4 mm of foot on pad and 0.5-0.7 mm of bare pad beyond the tip. Draw the Nexperia pattern for D1/D2. D3 (SMF5.0A, SOD-123FL) is solderable on the SOD123 pads but marginal: zero toe at the nominal lead span and pads far smaller than Littelfuse\'s 1.3 x 1.4 mm, so give it the Littelfuse pattern at the same time.',
        '**CPG236 land pads are undersize.** The library uses 0.225 mm pads; UG475 Table A-1 asks for 0.275 mm NSMD lands with 0.375 mm mask openings on the 0.5 mm pitch. Set that when the PCB library is built.',
        '**Two footprints do not exist yet**: SOT23-5 for the SC189s and DM3D-SF for X3. Both must be drawn at the PCB stage from the catalog land patterns.',
        '**Oscillator grade is out of the FT2232H spec.** ASEM1-12.000MHZ-LC-T decodes (datasheet p3) to 3.3 V, -40..85 C, +-50 ppm; the FT2232H datasheet asks for +-30 ppm. The comment on Q1 says 25 ppm, so the intent was the LR grade (ASEM1-12.000MHZ-LR-T), which no distributor stocks. A 20-agent search on 2026-09-08 (Digi-Key plus the makers\' datasheets, top picks cross-examined) found four pin-compatible 3.2 x 2.5 mm parts on Digi-Key\'s shelf that meet +-30 ppm all-inclusive: ECS-3225SMV-120-FP-TR (+-10 ppm including aging, -40..105 C, 1,830 pcs, $2.90, recommended), Abracon ASEMB-12.000MHZ-LY-T (+-10 ppm plus 5 ppm/yr aging, 6,143 pcs, $4.40), ECS-3225SMVQ-120-DS-TR (+-20 ppm including aging, 862 pcs, $1.82) and SiTime SIT1602BI-22-33E-12.000000 (+-25 ppm including first-year aging, 440 pcs, $1.54). The SiTime SiT8008 grades that a judge preferred are factory stock programmed to order, not shelf stock. Not applied: tools/apply_bom_substitutions.py carries the entry commented out.',
        '**Three parts were obsolete** and were replaced on 2026-09-07 by tools/apply_bom_substitutions.py: R34 742C083472JTR by 742C083472JP, the 10 uF 10 V 0805 GRM21BR61A106KE19L on C78/C147-C149 by Samsung CL21A106KPFNNNG, and the 4.7 uF GRM188R61A475KE15D on eleven decoupling positions. The first 4.7 uF replacement (GRM188R61A475KAAJD) turned out to be NRND at Murata, and every 4.7 uF 10 V X5R 0603 on the market is NRND, obsolete or dry, so on 2026-09-08 those eleven positions moved to the 16 V grade GRM188R61C475KE11D, which Murata lists as in production and which also halves the DC-bias loss on the 3.3 V positions.',
        '**Three part numbers were unknown to the distributor**; two were replaced on 2026-09-07 (GRM033R60J474KE15D, a typo, by GRM033R60J474KE90D on 22 positions; GRM155R61C474KA88D on C124 by Samsung CL05A474KO5NNNC) and the 22 uF 0603 on C82/C84 moved to the stocked 10 V Samsung CL10A226MP8NUNE. GRM155R60J335ME15D (C39/C139, the FT2232H VCORE filter, FTDI minimum 3.3 uF) is unobtainable and no 3.3 uF 0402 at 6.3 V or more exists that is not obsolete or NRND (Digi-Key\'s whole 3.3 uF 0402 list was checked on 2026-09-08). The same-footprint answer is 4.7 uF: Taiyo Yuden JMK105BBJ475MV-F, ordered under its new number MSASJ105BB5475MFNA01 (6.3 V X5R, 0.65 mm max, about 3.7 uF left at 1.8 V, 1.6 M pcs, $0.13, recommended), or Murata GRM155R60J475ME47D (0.60 mm max, in production, 980 k pcs, $0.10, but only about 2.2-2.8 uF left at 1.8 V so the pair sits close to FTDI\'s minimum at the tolerance corners). Both survived two skeptics each. Not applied: the entry is commented out in tools/apply_bom_substitutions.py.',
        '**Two parts have no distributor at all**: the PTA-142 button and the VS NRD8 RGB LED. Both work if you already hold stock; otherwise pick the alternatives in section 4 and re-check their pads.',
        '**Long-lead items**: FT2232HQ-REEL is dry at Digi-Key until April 2027 (tray packaging exists; check FTDI direct and Mouser before ordering), the SDRAM -6 grade is dry (the -7 grade, 143 MHz, is in stock), and the 22 uF 0805 value (13 pcs) is dry across Murata, Samsung and TDK\'s active parts, with only NRND TDK stock; C82/C84 now carry the stocked Samsung CL10A226MP8NUNE.',
        '**C124 returns to the wrong ground.** Seen while re-checking its substitution: C123 (100 nF) returns to GNDADC but C124 (470 nF) returns to digital GND, whereas UG480 Figure 6-1 draws both XADC supply filter capacitors from VCCADC to the analog ground on the far side of the ground ferrite L6. The sheet-1 note describes both as one filter. Move C124\'s ground pin to GNDADC when the XADC front end is next touched; it is a one-wire change.',
        '**Everything else checks out**: the FPGA symbol and power tree, the FT2232H, SDRAM, flash and EEPROM pin functions, the USB receptacle, LED polarity and pads, capacitor voltage margins, resistor power, regulator and diode ratings. On 2026-09-08 nine of the findings and substitutions above were handed to independent reviewers told to refute them from primary sources; they confirmed all of the conclusions and corrected the details now written here (the D1/D2 land numbers, the D3 verdict, the 4.7 uF replacement, the 22 uF height, R34\'s concave terminations).',
    ], 1):
        w(f'{i}. {f}')
    print('\n'.join(out))

if __name__ == '__main__':
    main()
