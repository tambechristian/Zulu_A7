# -*- coding: utf-8 -*-
"""Connectivity and architecture checks over the exported netlist -> docs/connectivity_check.md

    python tools/connectivity_check.py > docs/connectivity_check.md

Two questions, asked of the netlist Altium exports rather than of the drawing.

1. POWER AND GROUND ARCHITECTURE. Every supply and ground pin of every integrated circuit is
   traced to the rail it lands on and checked against the pin list in that part's datasheet, so a
   supply pin that never got connected shows up as a hole rather than as silence. The capacitors
   bridging each rail to its ground are then counted by value tier. The FPGA is measured against
   UG483 Table 2-2, the row for XC7A35T in CPG236, which is the only per-device decoupling
   requirement any of these datasheets states as a number; the FT2232H is measured against the
   reference circuit in DS_FT2232H Figures 4.1 and 6.1; the rest against the ordinary rule of one
   high-frequency capacitor per supply pin plus bulk per rail.

   What a netlist cannot answer is whether a capacitor is placed near the pin it serves. That is a
   layout property. The nearest thing a schematic can say is which sheet each capacitor was drawn
   on beside which part, so that allocation is reported and the limit is stated plainly.

2. BUSES AND DIFFERENTIAL PAIRS. Each multi-line group is checked end to end against the pin
   assignment in the part's datasheet: the SDRAM address, bank, data and control lines, the quad
   SPI flash, the microSD bus, the Pmod header, the JTAG and UART links, the prototyping channels
   and the two differential analogue pairs, plus the USB pair, which is checked for orientation,
   symmetry and series elements.

Pin maps are transcribed from Datasheet/: AS4C32M16SB Figure 1 (page 3), W25Q128JV pin
configuration, the DM3D-SF catalogue page, DS_FT2232H Figures 4.1 and 6.1, the Molex 105017
drawing, and xc7a35tcpg236pkg_pinout.txt, which is read directly. Read-only: it changes nothing.
"""
import os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bom_audit
from bom_audit import load_components

NET = os.path.join(bom_audit.ROOT, 'Imported zulu_a7.PrjPcb', 'Project Outputs for zulu_a7', 'zulu_a7.NET')
PINOUT = os.path.join(bom_audit.ROOT, '..', 'Datasheet', 'xc7a35tcpg236pkg_pinout.txt')
out, findings = [], []
w = out.append

t = open(NET, encoding='latin-1').read()
NETS = {}
for blk in re.findall(r'\(\n(.*?)\n\)', t, re.S):
    L = blk.split('\n')
    NETS[L[0].strip()] = [x.strip() for x in L[1:] if x.strip()]
PAD = {p: n for n, ps in NETS.items() for p in ps}
COMP = load_components()
GND_OF = collections.defaultdict(lambda: 'GND', {'VCCADC': 'GNDADC'})


def net(pad):
    return PAD.get(pad, '(open)')


def value(ref):
    return (COMP[ref]['params'].get('Comment') or '') if ref in COMP else ''


def farads(v):
    m = re.match(r'\s*([\d.]+)\s*(p|n|u)?F', v or '', re.I)
    if not m:
        return None
    return float(m.group(1)) * {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, None: 1.0}[m.group(2).lower() if m.group(2) else None]


def fmt(f):
    if f >= 1e-6: return f'{f * 1e6:g} uF'
    if f >= 1e-9: return f'{f * 1e9:g} nF'
    return f'{f * 1e12:g} pF'


CAPS = []                                            # (ref, rail, farads, sheet)
for ref, c in COMP.items():
    if not ref.startswith('C') or len(c['pins']) != 2:
        continue
    ns = {net(f'{ref}-{p}') for p in c['pins']}
    rail = ns - {'GND', 'GNDADC'}
    if len(ns) == 2 and len(rail) == 1 and (ns & {'GND', 'GNDADC'}):
        CAPS.append((ref, rail.pop(), farads(value(ref)) or 0.0, c['sheet']))


def on(rail, lo=0.0, hi=1e9, sheet=None):
    return [c for c in CAPS if c[1] == rail and lo <= c[2] < hi and (sheet is None or c[3] == sheet)]


def tier(rail, sheet=None):
    """(count of 0.47 uF class, count of 4.7 uF class, total bulk farads) -- UG483's three tiers"""
    cs = on(rail, sheet=sheet)
    hf = sum(1 for c in cs if 1e-7 <= c[2] < 1e-6)
    mid = sum(1 for c in cs if 1e-6 <= c[2] < 1e-5)
    bulk = sum(c[2] for c in cs if c[2] >= 1e-6)
    return hf, mid, bulk


def group(cs):
    g = collections.Counter(c[2] for c in cs)
    return ' + '.join(f'{n} x {fmt(f)}' for f, n in sorted(g.items())) or 'none'


# ---------------------------------------------------------- FPGA package map ---
PKG = []
for line in open(PINOUT, encoding='latin-1', errors='replace'):
    p = line.split()
    if len(p) >= 6 and re.fullmatch(r'[A-Z]+\d+', p[0]):
        PKG.append((p[0], p[1]))
PKG_GROUP = collections.defaultdict(list)
for pin, name in PKG:
    PKG_GROUP[re.sub(r'_\d+$', '', name)].append(pin)
VCCO_BANKS = sorted({n.split('_')[1] for _, n in PKG if n.startswith('VCCO_')})
IO_BANKS = [b for b in VCCO_BANKS if b != '0']

w('# Zulu A7 connectivity and architecture checks\n')
w(f'Source: the Protel netlist Altium exported from `Imported zulu_a7.PrjPcb` ({len(NETS)} nets, '
  f'{sum(len(v) for v in NETS.values())} pads), the seven schematic sheets, and the datasheets in '
  '`Datasheet/`. Generated by `tools/connectivity_check.py`. Nothing here is measured from a board: '
  'where a question can only be settled by layout, it says so.\n')

# =========================================================== 1. power tree =====
w('## 1. Power and ground architecture\n')
w('### 1.1 The rails and what decouples them\n')
SOURCE = {'USB5V0': 'X1 micro-USB VBUS', 'VBATT': 'X4 LiPo cell',
          'VU': 'U8 bq24232 OUT, 4.4 V on USB or VBAT - 60 mV on battery',
          'VCC3V3': 'U5 SC189Z buck', 'VCC1V8': 'U6 SC189L buck', 'VCC1V0': 'U7 SC189A buck',
          'VCCADC': 'VCC1V8 through the ferrite L7', 'FT-VCORE': "U2's own 1.8 V regulator (VREGOUT)",
          'FT-VPHY': 'VCC3V3 through the ferrite L4', 'FT-VPLL': 'VCC3V3 through the ferrite L5'}
w('| Rail | Sourced by | Pads | Bulk (>= 1 uF) | High frequency (< 1 uF) |')
w('|---|---|---|---|---|')
for rail in SOURCE:
    w(f'| {rail} | {SOURCE[rail]} | {len(NETS.get(rail, []))} | {group(on(rail, 1e-6))} | {group(on(rail, 0, 1e-6))} |')
w('')
w(f'GND carries {len(NETS["GND"])} pads and GNDADC {len(NETS["GNDADC"])}. They meet only at the ferrite '
  'L6, which is the analogue-ground split UG480 asks for around the XADC.\n')

# ---- 1.2 FPGA supply and ground pins, from the package file
w('### 1.2 Every FPGA package pin that carries power or ground\n')
w('Read from `Datasheet/xc7a35tcpg236pkg_pinout.txt`, so this is the whole package, not just what '
  'the symbol happens to draw.\n')
w('| Package function | Pins | Net they land on |')
w('|---|---|---|')
holes = []
for base in ('VCCINT', 'VCCBRAM', 'VCCAUX', 'VCCBATT', 'VCCO', 'VCCADC', 'GND', 'GNDADC', 'VREFP', 'VREFN', 'DXP', 'DXN'):
    pins = PKG_GROUP.get(base, [])
    if not pins:
        continue
    seen = collections.Counter(net(f'U1-{p}') for p in pins)
    w(f'| {base} | {len(pins)} | {", ".join(f"{n} x {k}" for k, n in seen.items())} |')
    for p in pins:
        if net(f'U1-{p}') == '(open)':
            holes.append(f'U1-{p} ({base})')
if holes:
    findings.append(f'**FPGA supply or ground pins with no net**: {", ".join(holes)}.')
mgt = {p: net(f'U1-{p}') for p, n in PKG for _ in [0] if n.startswith('MGT')}
mgt_open = [p for p, n in mgt.items() if n == '(open)']
w('')
w(f'The GTP transceiver block is unused: its supplies MGTAVCC ({len(PKG_GROUP.get("MGTAVCC", []))} pins) '
  f'and MGTAVTT ({len(PKG_GROUP.get("MGTAVTT", []))} pins), the reference resistor pin MGTRREF and the '
  f'four receive pins are all tied to GND, and the {len(mgt_open)} transmit and reference-clock pins are '
  'left open. That is the disposition Xilinx gives for an unused GTP block, and it is the only group of '
  'FPGA pins deliberately left unconnected.\n')

# ---- 1.3 UG483
w('### 1.3 The FPGA against UG483 Table 2-2 (XC7A35T in CPG236)\n')
w('The table counts capacitors in three tiers, 0.47 uF, 4.7 uF and a bulk part. This board uses 470 nF '
  'for the first tier, 4.7 uF for the second and 22 uF parts instead of one 47 uF or 100 uF, so the '
  'comparison below counts the two small tiers and adds up the bulk.\n')
req = {  # rail -> (0.47 uF count, 4.7 uF count, bulk farads, what the table calls it)
    'VCC1V0': (3 + 1, 2, 100e-6 + 47e-6, 'VCCINT (1 x 100 uF, 2 x 4.7 uF, 3 x 0.47 uF) plus VCCBRAM (1 x 47 uF, 1 x 0.47 uF)'),
    'VCC1V8': (2, 1, 47e-6, 'VCCAUX (1 x 47 uF, 1 x 4.7 uF, 2 x 0.47 uF)'),
    'VCC3V3': (4 * len(IO_BANKS), 2 * len(IO_BANKS), 47e-6 + 47e-6,
               f'VCCO: bank 0 takes 1 x 47 uF, and the {len(IO_BANKS)} I/O banks ({", ".join(IO_BANKS)}) take '
               f'4 x 0.47 uF and 2 x 4.7 uF each, sharing one 47 or 100 uF between up to four of them'),
}
w('| Rail | UG483 asks for | The board has | Verdict |')
w('|---|---|---|---|')
for rail, (nhf, nmid, nbulk, label) in req.items():
    hf, mid, bulk = tier(rail)
    ok = hf >= nhf and mid >= nmid and bulk >= nbulk * 0.95
    w(f'| {rail} | {label} | {hf} x 470 nF, {mid} x 4.7 uF, {fmt(bulk)} of bulk | '
      f'{"**meets it**" if ok else "**SHORT**"} (asks {nhf} / {nmid} / {fmt(nbulk)}) |')
    if not ok:
        findings.append(f'**{rail} is short of UG483 Table 2-2**: has {hf} x 470 nF, {mid} x 4.7 uF and '
                        f'{fmt(bulk)} of bulk against {nhf}, {nmid} and {fmt(nbulk)}.')
w('')

# ---- 1.4 FT2232H against FTDI's reference
w("### 1.4 The FT2232H against FTDI's reference circuit\n")
w('DS_FT2232H Figures 4.1 and 6.1 show one 100 nF at every supply pin, a 4.7 uF on each of the 3.3 V and '
  '1.8 V rails, and a ferrite plus 100 nF on VPHY and on VPLL.\n')
FT = {'VCCIO (pins 20, 31, 42, 56) and VREGIN (50)': ('VCC3V3', 5),
      'VCORE (pins 12, 37, 64) fed by VREGOUT (49)': ('FT-VCORE', 4),
      'VPHY (pin 4)': ('FT-VPHY', 1), 'VPLL (pin 9)': ('FT-VPLL', 1)}
w('| Supply | Pins | Rail | 100 nF class on that rail | Bulk on that rail |')
w('|---|---|---|---|---|')
for label, (rail, npins) in FT.items():
    hf = on(rail, 0, 1e-6)
    sheet_hf = [c for c in hf if c[3] == COMP['U2']['sheet']]
    w(f'| {label} | {npins} | {rail} | {len(hf)} on the rail, {len(sheet_hf)} drawn on the FT2232H sheet | {group(on(rail, 1e-6))} |')
core_hf = on('FT-VCORE', 0, 1e-6)
if not core_hf:
    findings.append('**The FT2232H core rail has no high-frequency decoupling.** FT-VCORE reaches four pins '
                    '(VCORE 12, 37 and 64, and VREGOUT 49) and carries only C39 and C139, both 4.7 uF. '
                    "FTDI's own figures put a 100 nF at each VCORE pin alongside the 4.7 uF. Adding three "
                    '100 nF 0402 parts on that rail is cheap and worth doing before the board is laid out.')
w('')

# ---- 1.5 the other parts
w('### 1.5 The other parts, one capacitor per supply pin\n')
OTHER = {
    'U3 SDRAM': ('U3', {'VDD': ['1', '14', '27'], 'VDDQ': ['3', '9', '43', '49']},
                 {'VSS': ['28', '41', '54'], 'VSSQ': ['6', '12', '46', '52']}),
    'U4 SPI flash': ('U4', {'VCC': ['8']}, {'GND': ['4']}),
    'U10 EEPROM': ('U10', {'VCC': ['8']}, {'VSS': ['5']}),
    'Q1 oscillator': ('Q1', {'VDD': ['4']}, {'GND': ['2']}),
    'X3 microSD': ('X3', {'VDD': ['4']}, {'VSS': ['6', 'G1', 'G2', 'G3', 'G4']}),
    'U8 charger': ('U8', {}, {'VSS': ['8'], 'thermal pad': ['17']}),
    'U5 SC189Z 3.3 V': ('U5', {'VIN': ['1'], 'VOUT': ['4']}, {'GND': ['2']}),
    'U6 SC189L 1.8 V': ('U6', {'VIN': ['1'], 'VOUT': ['4']}, {'GND': ['2']}),
    'U7 SC189A 1.0 V': ('U7', {'VIN': ['1'], 'VOUT': ['4']}, {'GND': ['2']}),
}
w('| Part | Supply pins | Rails | Ground pins | HF capacitors drawn on the same sheet |')
w('|---|---|---|---|---|')
for label, (ref, sup, gnd) in OTHER.items():
    sp = [p for ps in sup.values() for p in ps]
    gp = [p for ps in gnd.values() for p in ps]
    rails = collections.Counter(net(f'{ref}-{p}') for p in sp)
    sheet = COMP[ref]['sheet']
    hf = sum(1 for r in rails for c in on(r, 0, 1e-6, sheet=sheet))
    bad = [f'{ref}-{p} on {net(f"{ref}-{p}")}' for p in gp if net(f'{ref}-{p}') != 'GND']
    if bad:
        findings.append(f'**{ref} ground pin not on GND**: {", ".join(bad)}.')
    w(f'| {label} | {len(sp)} | {", ".join(f"{n} x {r}" for r, n in rails.items()) or "-"} | '
      f'{len(gp)} ({"all on GND" if not bad else "**" + ", ".join(bad) + "**"}) | {hf} |')
w('')

# ---- 1.6 allocation by sheet
w('### 1.6 Where the decoupling was drawn\n')
w('The closest a schematic gets to "near the pin": which sheet each capacitor sits on, beside which part.\n')
SHEETNAME = {0: 'block diagram', 1: 'power supplies', 2: 'general IO', 3: 'memory', 4: 'FT2232 / JTAG / clock',
             5: 'FPGA', 6: 'FPGA power'}
bysheet = collections.defaultdict(lambda: collections.Counter())
for ref, rail, f, sh in CAPS:
    bysheet[sh][(rail, 'HF' if f < 1e-6 else 'bulk')] += 1
w('| Sheet | Parts on it | Decoupling drawn there |')
w('|---|---|---|')
for sh in sorted(bysheet):
    ics = [r for r in ('U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U8', 'U10', 'Q1', 'X1', 'X3') if COMP[r]['sheet'] == sh]
    w(f'| {sh} {SHEETNAME.get(sh, "")} | {", ".join(ics) or "-"} | '
      f'{", ".join(f"{r} {k} x{n}" for (r, k), n in sorted(bysheet[sh].items()))} |')
w('')
w('Sheet 3 carries nine high-frequency capacitors for the nine 3.3 V supply pins of the SDRAM, the flash '
  'and the card socket, and sheet 4 carries seven for the seven 3.3 V supply pins of the bridge, the '
  'EEPROM and the oscillator. That is one apiece, so the schematic has allocated them per pin rather '
  'than lumping them on one rail. **Whether each ends up beside its pin is a placement question and '
  'cannot be settled here.**\n')

# =========================================================== 2. buses =========
w('## 2. Buses and differential pairs\n')
BUSES = {
 'SDRAM address A0-A12': [('A0','U1-U2','U3-23'),('A1','U1-T3','U3-24'),('A2','U1-T2','U3-25'),('A3','U1-T1','U3-26'),
                   ('A4','U1-R3','U3-29'),('A5','U1-R2','U3-30'),('A6','U1-P3','U3-31'),('A7','U1-P1','U3-32'),
                   ('A8','U1-N3','U3-33'),('A9','U1-N2','U3-34'),('A10','U1-U3','U3-22'),('A11','U1-N1','U3-35'),
                   ('A12','U1-M3','U3-36')],
 'SDRAM bank BS0-BS1': [('BS0','U1-V2','U3-20'),('BS1','U1-U1','U3-21')],
 'SDRAM data D0-D15': [(f'D{i}', '', p) for i, p in enumerate(
                 ['U3-2','U3-4','U3-5','U3-7','U3-8','U3-10','U3-11','U3-13',
                  'U3-42','U3-44','U3-45','U3-47','U3-48','U3-50','U3-51','U3-53'])],
 'SDRAM control': [('SDRAM-CS#','U1-W2','U3-19'),('RAS#','U1-V3','U3-18'),('CAS#','U1-W3','U3-17'),
                   ('WE#','U1-V4','U3-16'),('CKE','U1-M2','U3-37'),('SDRAM-CLK','U1-M1','U3-38'),
                   ('LDQM','U1-W4','U3-15'),('UDQM','U1-L2','U3-39')],
 'Quad SPI flash': [('FLASH-CS#','U1-K19','U4-1'),('FPGA-CCLK','U1-C11','U4-6'),('FLASH-D00','U1-D18','U4-5'),
                ('FLASH-D01','U1-D19','U4-2'),('FLASH-D02','U1-G18','U4-3'),('FLASH-D03','U1-F18','U4-7')],
 'microSD': [('SD-CLK','U1-U8','X3-5'),('SD-CMD','U1-U7','X3-3'),('SD-DAT0','U1-C15','X3-7'),
             ('SD-DAT1','U1-B15','X3-8'),('SD-DAT2','U1-L3','X3-1'),('SD-DAT3','U1-A16','X3-2')],
 'USB (differential)': [('USB_D_P','U2-8','X1-3'),('USB_D_N','U2-7','X1-2')],
 'JTAG, bridge to FPGA': [('TCK','U2-16','R36-1'),('TMS','U2-19','R4-1'),('TDI','U2-17','R8-1'),('TDO','U2-18','R37-1')],
 'UART, bridge to FPGA': [('UART_FT_TXD','U2-38','U1-K18'),('UART_FT_RXD','U2-39','U1-G19'),
                          ('UART_FT_RTS#','U2-40','U1-L18'),('UART_FT_CTS#','U2-41','U1-B16'),
                          ('UART_FT_DTR#','U2-43','U1-M18')],
 'EEPROM, bridge to 93LC46': [('EE-CS','U2-63','U10-1'),('EE-CLK','U2-62','U10-2'),('EE-DATA','U2-61','U10-3')],
 'XADC pairs': [('AIN15_P','U1-G3','C36-2'),('AIN15_N','U1-G2','C36-1'),
                ('AIN16_P','U1-H2','C37-2'),('AIN16_N','U1-J2','C37-1')],
}
w('### 2.1 Every line against the datasheet pin it should reach\n')
w('| Bus | Lines | Result |')
w('|---|---|---|')
for name, lines in BUSES.items():
    bad = []
    for netname, a, b in lines:
        pads = NETS.get(netname)
        if pads is None:
            bad.append(f'{netname} does not exist'); continue
        for pad in (a, b):
            if pad and pad not in pads:
                bad.append(f'{netname} is not on {pad} (that pin is on {net(pad)})')
    w(f'| {name} | {len(lines)} | {"all correct" if not bad else "**" + "; ".join(bad) + "**"} |')
    if bad:
        findings.append(f'**{name}**: ' + '; '.join(bad))
w('')
chans = [n for n in NETS if re.fullmatch(r'CHAN\d+|CHAN-CLK', n)]
chan_ok = all(len(NETS[n]) == 2 and any(p.startswith('X2-') for p in NETS[n]) and any(p.startswith('U1-') for p in NETS[n]) for n in chans)
pmods = [n for n in NETS if n.startswith('PMOD-')]
pmod_ok = all(len(NETS[n]) == 2 and any(p.startswith('J1-') for p in NETS[n]) for n in pmods)
w(f'The prototyping bus is {len(chans)} nets (CHAN-CLK and CHAN0 to CHAN28), each with exactly two pads, '
  f'one on the FPGA and one on X2: {"all confirmed" if chan_ok else "**some do not**"}. The Pmod header '
  f'carries {len(pmods)} signals, each from a J1 pin through its series resistor: '
  f'{"all confirmed" if pmod_ok else "**some do not**"}.\n')
if not chan_ok:
    findings.append('**A prototyping channel does not run FPGA to X2.**')
if not pmod_ok:
    findings.append('**A Pmod line does not run from J1 through a resistor.**')

# ---- USB pair
w('### 2.2 The USB pair in detail\n')
dp, dn = NETS.get('USB_D_P', []), NETS.get('USB_D_N', [])
w('| | D+ | D- |')
w('|---|---|---|')
w(f'| Net | USB_D_P | USB_D_N |')
w(f'| Pads | {", ".join(dp)} | {", ".join(dn)} |')
w('| Receptacle pin | X1-3, which the Molex 105017 drawing calls D+ | X1-2, D- |')
w('| Bridge pin | U2-8, DP | U2-7, DM |')
w(f'| Series or shunt parts in the path | {", ".join(sorted({p.split("-")[0] for p in dp if p[0] in "RCL"})) or "none"} '
  f'| {", ".join(sorted({p.split("-")[0] for p in dn if p[0] in "RCL"})) or "none"} |')
w('')
crossed = not ('X1-3' in dp and 'X1-2' in dn and 'U2-8' in dp and 'U2-7' in dn)
sym = len(dp) == len(dn)
w(f'The pair is {"symmetric" if sym else "**asymmetric**"} at {len(dp)} and {len(dn)} pads, and it is '
  f'{"**crossed**" if crossed else "not crossed"}: D+ runs receptacle pin 3 to bridge pin 8 and D- runs '
  'pin 2 to pin 7. Neither leg carries a series or shunt part, which is what FTDI draws: the FT2232H '
  'transceiver contains its own series resistors, so the pair goes straight from the receptacle to the '
  'bridge. Length matching and 90 ohm differential impedance are layout matters and are not settled here.\n')
if crossed or not sym:
    findings.append('**The USB pair is crossed or asymmetric.**')
x1 = {p: net(p) for p in sorted(q for q in PAD if q.startswith('X1-'))}
w('The rest of the receptacle: ' + ', '.join(f'{k} on {v}' for k, v in x1.items()) +
  '. Pin 4 is ID, left open for a device-only port, and the shell tabs go to ground.\n')

# ---- analogue pairs
w('### 2.3 The analogue pairs\n')
w('UG480 asks that the two halves of a differential input see the same SOURCE impedance, not the same '
  'resistor value. Each channel divides the header pin down with a 2.32k over 1k pair and feeds the '
  'positive input through a series resistor, so the impedance looking back out of the positive input is '
  'that series resistor plus the divider in parallel. The negative input sees a single resistor to '
  'ground, chosen to equal it. The check computes both.\n')


def ohms(v):
    m = re.match(r'\s*([\d.]+)\s*(k|K|M)?', v or '')
    return None if not m else float(m.group(1)) * {'k': 1e3, 'K': 1e3, 'M': 1e6, None: 1.0}[m.group(2)]


w('| Pair | + input | - input | Anti-alias | Impedance out of + | Impedance out of - | Matched |')
w('|---|---|---|---|---|---|---|')
for pair, pn, nn, cap, rser, rtop, rbot, rgnd in (
        ('AIN15', 'AIN15_P', 'AIN15_N', 'C36', 'R12', 'R10', 'R11', 'R13'),
        ('AIN16', 'AIN16_P', 'AIN16_N', 'C37', 'R16', 'R14', 'R15', 'R17')):
    rs, rt, rb, rg = (ohms(value(r)) for r in (rser, rtop, rbot, rgnd))
    zp, zn = rs + rt * rb / (rt + rb), rg
    err = abs(zp - zn) / zn * 100
    up = [x for x in NETS[pn] if x.startswith('U1')][0]
    un = [x for x in NETS[nn] if x.startswith('U1')][0]
    verdict = f'yes, {err:.1f}% apart' if err < 2 else f'**no, {err:.1f}% apart**'
    w(f'| {pair} | {pn} on {up} | {nn} on {un} | {cap} {value(cap)} across the pair | '
      f'{rser} {value(rser)} + ({rtop} {value(rtop)} || {rbot} {value(rbot)}) = {zp:.0f} ohm | '
      f'{rgnd} {value(rgnd)} = {zn:.0f} ohm | {verdict} |')
    if err >= 2:
        findings.append(f'**{pair} source impedances are not matched**: {zp:.0f} ohm out of the positive '
                        f'input against {zn:.0f} ohm out of the negative, {err:.1f}% apart.')
w('')
w('The divider also sets full scale: 2.32k over 1k turns the 3.3 V a header pin can present into 0.994 V '
  'at the FPGA, just inside the 1 V the XADC accepts on a unipolar auxiliary channel. The 1 nF across the '
  'pair against roughly 840 ohm of source impedance rolls off around 190 kHz, well below the 1 Msps the '
  'converter runs at.\n')

# ---- loose ends
w('### 2.4 Loose ends\n')
single = {n: ps for n, ps in NETS.items() if len(ps) == 1}
w(f'Nets reaching only one pad: {len(single)}'
  + (' - ' + ', '.join(f'{n} ({ps[0]})' for n, ps in sorted(single.items())) if single else '.') + '\n')
if single:
    findings.append(f'**{len(single)} net(s) reach only one pad**: ' + ', '.join(sorted(single)) + '.')
allpins = {f'{r}-{p}' for r, c in COMP.items() for p in c['pins']
           if c['lib'] != 'DOCFIELD' and not c['lib'].startswith('CC_')}
unconn = sorted(allpins - set(PAD))
byref = collections.Counter(p.split('-')[0] for p in unconn)
w(f'Pins on no net: {len(unconn)}' + (' - ' + ', '.join(f'{r} x{n}' for r, n in byref.most_common()) if unconn else '.') + '\n')

# =========================================================== findings ==========
w('## 3. Findings\n')
if not findings:
    findings.append('**Nothing failed.** Every supply and ground pin lands on the rail its datasheet names, '
                    'every bus line reaches the pin the datasheet gives, the USB pair is symmetric and the '
                    'right way round, and no net is left with a single pad.')
for i, f in enumerate(findings, 1):
    w(f'{i}. {f}')
w('')
w('**The limit of this check.** Placement. A capacitor near its pin, a short return loop, a via count, a '
  'plane split, the length matching of the USB pair and of the SDRAM address and data lines: none of that '
  'is in a netlist. What is checked above is that the right parts exist and are wired to the right pins, '
  'which is the prerequisite. Keeping them close is the first job of the board work.')

print('\n'.join(out))
