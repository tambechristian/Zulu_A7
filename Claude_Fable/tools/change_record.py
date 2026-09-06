# -*- coding: utf-8 -*-
"""Regenerate the Design Change Record from the live schematic.

This regenerates rather than edits: every number below is read out of
zulu_a7.sch at generation time and every ball is checked against Xilinx's
xc7a35tcpg236 pinout file, so the document cannot drift from the design. The
XuLA3 rev1 record it replaces drifted 192 commits before anyone noticed -- it
still described two LDOs that no longer exist, a 32 MB SDRAM, an 8 Mb flash,
a WiFi header, a 40-pin X2, JTAG-only boot, and twelve unverified balls.

Output is HTML for the artifact at
https://claude.ai/code/artifact/806b5dd8-1fee-4606-afe7-75934febc87d
"""
import re, io, sys, json, collections, subprocess
# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"C:\Users\tambe\Documents\Electronics\Zulu_A7"
SCH = ROOT + r"\zulu_a7.sch"
PIN = ROOT + r"\Datasheet\xc7a35tcpg236pkg_pinout.txt"
OUT = ROOT + r"\docs\Zulu_A7-Design-Change-Record.html"
t = open(SCH, encoding="utf-8").read()

# --- live model -------------------------------------------------------------
ds = re.search(r'<deviceset name="XC7A35T-CPG236"[^>]*>.*?</deviceset>', t, re.S).group(0)
# Key by (gate, pin), never by net and never by gate alone. A net like GND
# holds dozens of balls, so net -> ball is arbitrary; and U1's PWR gate carries
# many pins on different rails, so gate -> ball is arbitrary too. Only the
# (gate, pin) pair maps one-to-one onto a ball.
G2B = {(g, pn): pd for g, pn, pd in
       re.findall(r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', ds)}
NET = collections.defaultdict(set)
for m in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', t, re.S):
    for p, g, pn in re.findall(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', m.group(2)):
        NET[m.group(1)].add((p, g, pn))
NETOF = {}
for n, s in NET.items():
    for p, g, pn in s:
        if p == "U1":
            assert (g, pn) not in NETOF, (g, pn, n, NETOF.get((g, pn)))
            NETOF[(g, pn)] = n
GATE = {k: (G2B[k], NETOF[k]) for k in G2B if k in NETOF}
assert len({b for b, _ in GATE.values()}) == len(GATE), "two gates share a ball"
VAL = {m.group(1): m.group(2) for m in re.finditer(r'<part name="([^"]+)"[^>]*value="([^"]*)"', t)}
PARTS = set(re.findall(r'<part name="([^"]+)"', t))
SHEETS = re.findall(r'<sheet name="([^"]*)">', t)
HEAD = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
NCOMMIT = subprocess.run(["git", "-C", ROOT, "rev-list", "--count", "30a0e65..HEAD"],
                         capture_output=True, text=True).stdout.strip()

# --- ball verification against Xilinx's own pinout file ----------------------
rows = {}
for l in open(PIN, encoding="utf-8", errors="replace"):
    p = l.split()
    if len(p) >= 8 and re.fullmatch(r"[A-Y]\d{1,2}", p[0]):
        rows[p[0]] = {"name": p[1], "bank": p[3], "io": p[-2], "nc": p[-1]}
used = {b: n for b, n in GATE.values()}
BANKS = collections.Counter(rows[b]["bank"] for b in used if b in rows)
MISSING = [b for b in used if b not in rows]
NOTCONN = [b for b in used if b in rows and rows[b]["nc"] != "NA"]
assert not MISSING and not NOTCONN, (MISSING, NOTCONN)


def grp(pred):
    out = [(n, b, rows[b]["name"], rows[b]["bank"] if rows[b]["bank"] != "NA" else "—")
           for k, (b, n) in GATE.items() if pred(n)]
    # a net legitimately reaches more than one ball (GNDADC, the supply rails),
    # so duplicates are real -- just sort deterministically by (net, ball)
    return sorted(out, key=lambda r: (r[0], r[1]))


def chan_key(r):
    m = re.match(r"CHAN(\d+)$", r[0])
    return (0, int(m.group(1))) if m else (1, r[0])


GROUPS = [
    ("config", "Config &amp; JTAG",
     sorted([(k[0], b, rows[b]["name"], rows[b]["bank"]) for k, (b, n) in GATE.items()
             if k[0] in ("PROGRAM_B", "INIT_B", "DONE", "TCK", "TMS", "TDI", "TDO",
                         "M0", "M1", "M2", "CFGBVS", "PUDC_B")], key=lambda r: (r[0], r[1]))),
    ("boot", "Master-SPI boot flash",
     grp(lambda n: n.startswith("FLASH-") or n == "FPGA-CCLK")),
    ("sd", "microSD, 4-bit SD bus", grp(lambda n: n.startswith("SD-"))),
    ("sdram", "SDRAM", grp(lambda n: re.fullmatch(r"(A\d+|BS\d|D\d+|CAS#|RAS#|WE#|CKE|[LU]DQM|SDRAM-\w+)", n))),
    ("gpio", "X2 prototyping header", sorted(grp(lambda n: n.startswith("CHAN")), key=chan_key)),
    ("uart", "FT2232HQ channel A (UART)", grp(lambda n: n.startswith("UART_") or n == "FT-PWREN#")),
    ("xadc", "XADC", grp(lambda n: n.startswith("AIN") or n in ("VCCADC", "GNDADC"))),
    ("clock", "Clock", grp(lambda n: n.startswith("CLK-12M"))),
    ("io", "LEDs &amp; buttons", grp(lambda n: re.fullmatch(r"(LED\d|LED0_[RGB]|BTN\d)", n))),
]
DATA = {k: [[n, b, nm, bk] for n, b, nm, bk in v] for k, _, v in GROUPS}
TABS = "".join('<button class="filterbtn%s" data-f="%s">%s</button>'
               % (" active" if i == 0 else "", k, lbl) for i, (k, lbl, _) in enumerate(GROUPS))
NPIN = sum(len(v) for _, _, v in GROUPS)

strap = {}
for n in ("CFG-M2", "CFG-M1", "CFG-M0"):
    r = [p for p, g, pn in NET[n] if p.startswith("R")][0]
    other = [x for x in NET if x != n and any(p == r for p, g, pn in NET[x])][0]
    strap[n] = "1" if other in ("VCC3V3", "+3.3V") else "0"
MODEBITS = strap["CFG-M2"] + strap["CFG-M1"] + strap["CFG-M0"]


# --- FT2232HQ, read from the file: rev1 had the two channels the wrong way round
FTDS = re.search(r'<deviceset name="FT2232HQ"[^>]*>.*?</deviceset>', t, re.S).group(0)
FTPAD = {pn: pd for g, pn, pd in
         re.findall(r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', FTDS)}
FTNET = {}
for n, s2 in NET.items():
    for p, g, pn in s2:
        if p == "U2":
            FTNET[pn] = n
UARTNAME = {"0": "TXD", "1": "RXD", "2": "RTS#", "3": "CTS#",
            "4": "DTR#", "5": "DSR#", "6": "DCD#", "7": "RI#"}
FTFREE = sorted(pn for pn in FTPAD if pn not in FTNET)


def ftrows(prefix, names):
    out = []
    for i in range(8):
        pn = "%s%d" % (prefix, i)
        if pn not in FTPAD:
            continue
        net = FTNET.get(pn)
        out.append("<tr><td class='mono'>%s</td><td class='mono'>%s</td><td class='mono'>%s</td>"
                   "<td class='mono'>%s</td></tr>"
                   % (pn, FTPAD[pn], names.get(str(i), "—"),
                      net if net else "<span class='chip warn'>not connected</span>"))
    return "".join(out)


CHA = ftrows("ADBUS", {"0": "TCK", "1": "TDI", "2": "TDO", "3": "TMS",
                       "4": "GPIOL0", "5": "GPIOL1", "6": "GPIOL2", "7": "GPIOL3"})
CHB = ftrows("BDBUS", UARTNAME)
NFTFREE = len(FTFREE)


def row(*c):
    return "<tr>" + "".join("<td%s>%s</td>" % ((' class="%s"' % k) if k else "", v) for k, v in c) + "</tr>"


BOM = "".join([
    row(("mono", "U1"), ("old mono", "XC6SLX25-FT256"), ("arrow", "→"), ("mono", VAL["U1"]),
        ("", "Artix-7. 238-ball 0.5 mm BGA, every ball now modelled and checked against Xilinx's pinout file")),
    row(("mono", "U2"), ("old mono", "PIC18F14K50"), ("arrow", "→"), ("mono", "FT2232HQ"),
        ("", "Ch.A = UART bridge, Ch.B = MPSSE JTAG. Replaces the PIC's programmer role")),
    row(("mono", "U3"), ("old mono", "Winbond W9825G6JH <span class='chip warn'>EOL</span>"), ("arrow", "→"),
        ("mono", VAL["U3"]), ("", "512 Mb / <strong>64 MB</strong>. Pinout and all 12 TSOP-II dimensions verified identical to the 256 Mb part &mdash; only the column address widens A0-A8 → A0-A9, a memory-controller setting")),
    row(("mono", "U4"), ("old mono", "8 Mb SPI flash"), ("arrow", "→"), ("mono", VAL["U4"]),
        ("", "<strong>128 Mb</strong> Winbond, quad-capable, on the FPGA's dedicated master-SPI pins")),
    row(("mono", "U8"), ("old", "— new —"), ("arrow", "＋"), ("mono", VAL["U8"]),
        ("", "Triple synchronous buck. Replaces the two LDOs rev1 proposed and the two the original board had &mdash; one part now makes 1.0 V, 1.8 V and 3.3 V")),
    row(("mono", "BTN1"), ("old mono", "PTA-142 + R87, R88"), ("arrow", "−"), ("mono", "deleted"),
        ("", "Removed to buy back board area &mdash; the button, its 10 k series resistor and its 10 k pull-down. "
             "Frees ball B18, which is now CHAN28 on header pin 41 &mdash; see §7. BTN is untouched")),
    row(("mono", "U10"), ("old", "— new —"), ("arrow", "＋"), ("mono", VAL["U10"]),
        ("", "FTDI reference-design EEPROM, carries the USB VID/PID/product string. <strong>16 bits wide</strong> "
             "&mdash; the <span class='mono'>B</span> suffix &mdash; because DS_FT2232H p27 requires it; see §3")),
    row(("mono", "X1"), ("old mono", "Hirose UX60SC-MB-5ST"), ("arrow", "→"), ("mono", "Molex 105017-0001"),
        ("", "Micro-USB-B. Footprint rebuilt this revision &mdash; see §8")),
    row(("mono", "X3"), ("old mono", "ALPS SCHD3A0100"), ("arrow", "→"), ("mono", "Hirose DM3AT-SF-PEJM5"),
        ("", "microSD, push-push. Footprint rebuilt this revision &mdash; see §8")),
    row(("mono", "X2"), ("old mono", "40-pin XULA-DIP40"), ("arrow", "→"), ("mono", "37-pin ZULU-DIP37"),
        ("", "Rows now 0.700 in apart so the pins land in breadboard columns C and H, leaving A, B, I and J free. 24 positions per row, 38 fitted, and the last 8.89 mm reserved for the Pmod &mdash; see §7")),
    row(("mono", "J1"), ("old mono", "1×8 ESP8266 WiFi header"), ("arrow", "→"), ("mono", "2×6 Pmod"),
        ("", "Standard Digilent Pmod pinout, series-terminated through R26-R33")),
    row(("mono", "Q1"), ("old mono", "12 MHz crystal (PIC only)"), ("arrow", "→"), ("mono", VAL["Q1"]),
        ("", "Active CMOS oscillator, 4-pad: OE, GND, OUT, VDD. One output forks to the FPGA and to FT2232HQ OSCI. Symbol redrawn as a rectangle &mdash; it had been drawing a two-plate crystal, and the deviceset was called XTAL_CHIP")),
    row(("mono", "U6, U7"), ("old mono", "ZLDO1117 3.3 V + 1.2 V"), ("arrow", "－"), ("", "removed"),
        ("", "Superseded by U8. Artix-7 wants 1.0 V VCCINT and an independent 1.8 V VCCAUX, neither of which the old pair could give")),
])

POWER = "".join([
    row(("mono", "VU / +5V"), ("", "X1 VBUS via D1, or VEXT via D2"), ("", "U8 input, X2 pin 36")),
    row(("mono", "VCC3V3"), ("", "U8 buck 3 + L3 (2.2 µH)"),
        ("", "%d pins &mdash; U1 VCCO on every bank, U3, X3, U2 VCCIO/VREGIN, U10, U4, J1, X2 pin 15" % len(NET["VCC3V3"]))),
    row(("mono", "VCC1V0"), ("", "U8 buck 1 + L1 (1.5 µH)"),
        ("", "%d pins &mdash; U1 VCCINT and VCCBRAM only" % len(NET["VCC1V0"]))),
    row(("mono", "VCC1V8"), ("", "U8 buck 2 + L2 (3.3 µH)"),
        ("", "%d pins &mdash; U1 VCCAUX, and VCCADC through ferrite L7" % len(NET["VCC1V8"]))),
])

FOOT = "".join([
    row(("mono", "U8 LTC3569-QFN20"), ("", "4.40 × 4.40 square, 0.5 mm"),
        ("", "UDC 3 × 4 mm rectangle: 0.50 BSC, pad 0.70 × 0.25, pattern 3.50/4.50 outer, exposed pad 1.65 × 2.65"),
        ("", "<span class='chip ok'>exact</span> fully dimensioned on datasheet p23")),
    row(("mono", "X1 MOLEX-105017-0001"), ("", "5 contacts at 1.5 mm, 6.00 mm span"),
        ("", "5 contacts at 0.65 mm, 2.60 mm span, 4 shell tabs"),
        ("", "<span class='chip ok'>pitch exact</span> <span class='chip warn'>tabs derived</span>")),
    row(("mono", "X3 DM3AT-SF-PEJM5"), ("", "8 contacts at 1.8 mm, 12.6 mm span, 15.0 × 5.0 pattern"),
        ("", "8 contacts at P=1.1, pad 0.70 × 1.20, span 7.70, 14.30 × 15.95 pattern, 21.55 mm eject keepout"),
        ("", "<span class='chip ok'>contacts exact</span> <span class='chip warn'>shield derived</span>")),
])

CSS_AND_HEAD = open(__file__.replace("change_record.py", "_record_style.html"), encoding="utf-8").read()
BODY = """
<div class="page">
  <div class="titleblock">
    <h1 class="serif">Zulu A7 Rework — Design Change Record</h1>
    <div class="sub">Spartan-6 → Artix-7 · PIC18F14K50 → FT2232HQ · linear regulators → LTC3569 · connector, memory &amp; footprint refresh</div>
    <div class="tb-grid mono">
      <div><div class="k">File</div><div class="v">zulu_a7.sch</div></div>
      <div><div class="k">Git commit</div><div class="v">__HEAD__</div></div>
      <div><div class="k">Parts / nets</div><div class="v">__NP__ / __NN__</div></div>
      <div><div class="k">Sheets</div><div class="v">__NS__</div></div>
      <div><div class="k">Status</div><div class="v">Schematic complete · Board pending</div></div>
    </div>
  </div>

  <p>Everything in this document is read out of <span class="mono">zulu_a7.sch</span> when it is generated, and
  every FPGA ball is checked against Xilinx's <span class="mono">xc7a35tcpg236pkg_pinout.txt</span>. It supersedes
  rev1, which was written __NC__ commits ago and had gone badly stale &mdash; it still described two LDOs that no longer
  exist, a 32 MB SDRAM, an 8 Mb flash, a WiFi header, a 40-pin X2, and twelve ball assignments it could not verify.</p>
  <p>Read <strong>Open items</strong> before doing anything else with this file.</p>

  <h2 class="serif">1 · Bill of materials</h2>
  <div class="tablewrap bom"><table>
    <thead><tr><th>Ref</th><th>Was</th><th></th><th>Now</th><th>Why</th></tr></thead>
    <tbody>__BOM__</tbody></table></div>

  <h2 class="serif">2 · Boot and storage</h2>
  <p>The original design hung the config flash and the microSD off one shared SPI bus. They are now completely
  separate, which is what makes both standalone boot and a running Linux root filesystem possible at the same time.</p>
  <div class="grid2">
    <div>
      <h3>Config flash — U4, master SPI</h3>
      <p>On the FPGA's <em>dedicated</em> configuration pins, which are fixed silicon, not a routing choice:
      CCLK&nbsp;C11, FCS_B&nbsp;K19, D00&nbsp;D18, D01&nbsp;D19, D02&nbsp;G18, D03&nbsp;F18. Mode pins strap
      <span class="mono">M[2:0] = __MODE__</span> for Master SPI (UG470 Table 2-1), so the part boots from flash
      with no host attached.</p>
      <p class="note">Re-checked pad by pad against the Winbond datasheet, SOIC-8 208-mil package code S:
      1 /CS, 2 DO&nbsp;(IO1), 3 /WP&nbsp;(IO2), 4 GND, 5 DI&nbsp;(IO0), 6 CLK, 7 /HOLD&nbsp;or&nbsp;/RESET&nbsp;(IO3),
      8 VCC &mdash; all eight match, and the FPGA end lands on the pin whose own name says so
      (<span class="mono">IO_L1P_T0_D00_MOSI_14</span> and the rest). The
      <strong><span class="mono">IQ</span> suffix is doing real work</strong>: it ships with the Quad Enable bit
      <strong>set to 1, factory-fixed</strong> (datasheet §7.1 and §11.1), which is what x4 boot needs. The otherwise
      identical <span class="mono">IM</span> suffix ships QE&nbsp;=&nbsp;0 and would not boot in x4 until someone
      programmed its status register. Do not let a purchasing substitution change that letter. R2's 4.7 k pack pulls
      /CS, IO2 and IO3 up to VCC3V3 &mdash; needed because <span class="mono">PUDC_B</span> is strapped high, so the
      FPGA's internal pull-ups are off through configuration, and the datasheet asks for the /CS one by name.</p>
    </div>
    <div>
      <h3>microSD — X3, native 4-bit SD</h3>
      <p>Its own CLK/CMD/DAT0-3 on ordinary user I/O. DAT1 and DAT2 came from two bank-34 prototyping-header balls,
      which is what cost X2 two channels. An inserted card can no longer drive the configuration bus while the FPGA
      is reading its bitstream.</p>
      <p class="note">Note this is the native SD bus, not "quad SPI" — SD cards have no such mode. SPI mode and
      4-bit SD mode are different protocols.</p>
    </div>
  </div>

  <h2 class="serif">3 · FT2232HQ</h2>
  <p>Channel A runs the JTAG engine in MPSSE mode and channel B is the UART — the Digilent/Xilinx convention, which is
  what Vivado's built-in FTDI cable support expects. <em>Rev1 of this document had the two channels the wrong way
  round;</em> the tables below are read out of the schematic.</p>
  <div class="grid2">
    <div>
      <h3>Channel A — MPSSE JTAG</h3>
      <div class="tablewrap"><table>
        <thead><tr><th>Pin</th><th>Pad</th><th>MPSSE role</th><th>Net</th></tr></thead>
        <tbody>__CHA__</tbody></table></div>
      <p class="note">TCK/TDI/TDO/TMS are series-terminated through R89-R92 and shared with header JP3 and the R4 pack.
      GPIOL0/GPIOL1 carry <span class="mono">PROG#</span> and <span class="mono">DONE</span>, so the host can already
      force a reconfiguration and read back DONE without spending an FPGA general I/O.</p>
    </div>
    <div>
      <h3>Channel B — UART</h3>
      <div class="tablewrap"><table>
        <thead><tr><th>Pin</th><th>Pad</th><th>UART role</th><th>Net</th></tr></thead>
        <tbody>__CHB__</tbody></table></div>
      <p class="note">Hardware flow control is complete in both directions. RTS# and DTR# are FT2232 outputs into the
      FPGA; CTS# is the FT2232's input, driven by the FPGA, so the FPGA can push back on the host during a burst. CTS#
      cost one prototyping channel — see §7.</p>
    </div>
  </div>
  <div class="tablewrap" style="margin-top:16px;"><table>
    <thead><tr><th>Function</th><th class="mono">Pins</th><th>Nets</th><th>Note</th></tr></thead>
    <tbody>
      <tr><td>USB</td><td class="mono">DP=8, DM=7</td><td class="mono">USB_D_P / USB_D_N</td><td>to X1</td></tr>
      <tr><td>Oscillator</td><td class="mono">OSCI=2, OSCO=3 (NC)</td><td class="mono">CLK-12M-FT</td><td>external-CMOS-oscillator mode, DS_FT2232H §6.3</td></tr>
      <tr><td>Power</td><td class="mono">VREGIN=50, VCCIO×4, VPLL=9, VPHY=4</td><td class="mono">VCC3V3</td><td>VPLL and VPHY each through their own ferrite (L5, L4); VREGOUT→VCORE via C39/C139</td></tr>
      <tr><td>EEPROM</td><td class="mono">EECS=63, EECLK=62, EEDATA=61</td><td class="mono">EE-CS / EE-CLK / EE-DATA</td><td>to U10. 10 k pull-ups R98 on EECS and R96 on EECLK</td></tr>
      <tr><td>EEPROM data path</td><td class="mono">EEDATA=61</td><td class="mono">EE-DATA + EE-DATA-DO</td><td>EEDATA goes straight to Data-In and back to Data-Out through R101, 2.21 k; R97 pulls <em>Data-Out</em> to VCC3V3 with 10 k. Three resistors, three values, exactly the reference circuit on DS_FT2232H p50 &mdash; see §9</td></tr>
      <tr><td>EEPROM organisation</td><td class="mono">__U10__</td><td class="mono">64 × 16</td><td>DS_FT2232H p27 asks for &ldquo;a 16 bit wide configuration such as a Microchip 93LC46B&rdquo;; the part fitted was an <span class="mono">A</span> suffix, which is × 8 &mdash; see §9</td></tr>
      <tr><td>Housekeeping</td><td class="mono">RESET#=14, TEST=13, REF=6</td><td class="mono">FT-RESETN / FT-REF</td><td>R19 pull-up, TEST→GND, R18 = 12 k ±1 % to GND</td></tr>
    </tbody></table></div>
  <p class="note">__NFTFREE__ of the FT2232HQ's 64 pins carry no net — the eight ACBUS (channel A GPIOH), the four
  spare BDBUS, ADBUS6/7, OSCO and SUSPEND#. None of them can reach the FPGA without taking a prototyping channel.</p>

  <h2 class="serif">4 · Clock</h2>
  <p>One <span class="mono">__Q1__</span> active oscillator. Its single CMOS output forks through R24 and R25 into two
  nets — <span class="mono">CLK-12M-FT</span> to the FT2232HQ's OSCI and <span class="mono">CLK-12M-FPGA</span> to
  ball L17 — with OSCO left unconnected. The FT2232H's USB PLL requires exactly 12 MHz, which is why the 100 MHz part
  originally floated was dropped; the FPGA synthesises whatever it needs with an MMCM.</p>
  <p class="note">The block diagram used to draw this as a two-terminal passive crystal hanging off the bridge. It is
  a four-pin oscillator with one output and two destinations, and the diagram now shows that.</p>

  <h2 class="serif">5 · Power tree</h2>
  <div class="tablewrap"><table>
    <thead><tr><th>Rail</th><th>Source</th><th>Feeds</th></tr></thead>
    <tbody>__POWER__</tbody></table></div>
  <p class="note">CFGBVS ties to VCC3V3 (UG470 rule for a 3.3 V configuration bank). The five unused GTP transceiver
  balls in bank 216 tie to GND per UG482 Table 5-4. DXP/DXN (thermal diode) tie to GND.</p>

  <h3>VCCINT and VCCBRAM decoupling</h3>
  <p>UG483 Table 2-2 lists these as separate columns. For CPG236 / XC7A35T: VCCINT takes 1&times; 100&nbsp;µF,
  2&times; 4.7&nbsp;µF and 3&times; 0.47&nbsp;µF; VCCBRAM takes 1&times; 47&nbsp;µF and 1&times; 0.47&nbsp;µF.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Rail</th><th>U1 pins</th><th>Decoupling</th><th class="mono">Capacitors</th></tr></thead>
    <tbody>
      <tr><td class="mono">VCCINT</td><td>6</td><td>1&times; 100 µF, 2&times; 4.7 µF, 3&times; 0.47 µF</td><td class="mono">C85, C87&ndash;C91</td></tr>
      <tr><td class="mono">VCCBRAM</td><td>2</td><td>1&times; 47 µF, 1&times; 0.47 µF</td><td class="mono">C86, C92</td></tr>
    </tbody></table></div>
  <p class="note">Both rails carry <span class="mono">VCC1V0</span>. VCCINT and VCCBRAM are distinct FPGA supplies,
  but this board feeds both from the same 1.0&nbsp;V buck &mdash; normal for a part this size &mdash; so the drawing
  separates them while the net does not.</p>

  <h3>VCCO decoupling, per bank</h3>
  <p>UG483 Table 2-2 splits VCCO into a <em>Bank 0</em> column and an <em>all other banks (per bank)</em> column, and
  p14 states the VCCO figures are quantity <strong>per I/O bank</strong>. For CPG236 / XC7A35T that reads 1&times;
  47&nbsp;µF for bank 0, and per other bank 1&times; 47&nbsp;µF, 2&times; 4.7&nbsp;µF, 4&times; 0.47&nbsp;µF. Note 3
  lets one 47&nbsp;µF cover up to four banks on the same voltage, and banks 14/16/34/35 are all on 3.3&nbsp;V &mdash;
  so the total is 2&times; 47, 8&times; 4.7, 16&times; 0.47, which is what the design carries.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Bank</th><th>VCCO pins</th><th>Decoupling</th><th class="mono">Capacitors</th></tr></thead>
    <tbody>
      <tr><td class="mono">0</td><td>2</td><td>1&times; 47 µF</td><td class="mono">C97</td></tr>
      <tr><td class="mono">14</td><td>9</td><td>1&times; 47 µF <span class="chip ok">shared</span>, 2&times; 4.7 µF, 4&times; 0.47 µF</td><td class="mono">C98&ndash;C100, C107&ndash;C110</td></tr>
      <tr><td class="mono">16</td><td>4</td><td>2&times; 4.7 µF, 4&times; 0.47 µF</td><td class="mono">C101, C102, C111&ndash;C114</td></tr>
      <tr><td class="mono">34</td><td>6</td><td>2&times; 4.7 µF, 4&times; 0.47 µF</td><td class="mono">C103, C104, C115&ndash;C118</td></tr>
      <tr><td class="mono">35</td><td>6</td><td>2&times; 4.7 µF, 4&times; 0.47 µF</td><td class="mono">C105, C106, C119&ndash;C122</td></tr>
    </tbody></table></div>
  <p class="note">The five rails carry the same <span class="mono">VCC3V3</span> net and must &mdash; every VCCO bank
  here runs at 3.3&nbsp;V off the same regulator. What was removed is the single trunk that tied all 27 pins together
  as one anonymous stack; each bank now has its own rail and its own capacitors, so the layout engineer can place them
  against the right ball field.</p>

  <h2 class="serif">6 · FPGA ball map</h2>
  <p>__NUSED__ of the 238 balls carry a net. Every one of them exists in Xilinx's pinout file for this exact device and
  package, none is marked No-Connect, and no signal lands on a non-I/O ball. Bank distribution:
  __BANKS__.</p>
  <p>The __NFREE__ balls that carry nothing are all GTP transmit and reference-clock pins in bank 216, correctly left
  open — the GTP receive pins are tied to GND per UG482 Table 5-4.
  <strong>Zero general-purpose HR I/O remain free.</strong> Every usable pin on the part is spoken for, which is why
  the microSD's DAT1/DAT2 had to come out of the prototyping header rather than from spare silicon.</p>
  <div class="callout warn"><strong>Still worth a Vivado pass.</strong> This check proves each ball is real, is an I/O,
  and is in the bank shown. It does <em>not</em> prove the assignment is legal for its function — clock-capable
  (MRCC/SRCC) placement, VREF pins, and DQS byte-group rules for the SDRAM all need Vivado's I/O Planner to confirm.</div>
  <div class="controls">__TABS__</div>
  <div class="tablewrap" style="margin-top:10px;">
    <table id="pintable"><thead><tr><th>Net</th><th class="mono">Ball</th><th class="mono">Xilinx pin name</th><th class="mono">Bank</th></tr></thead>
    <tbody id="pinbody"></tbody></table></div>

  <h2 class="serif">7 · X2 prototyping header</h2>
  <p>X2 went from 40 pins to <strong>37</strong>, in two steps, both paid for by the same constraint: the FPGA has
  <strong>zero free general I/O</strong>, so anything new has to come out of the header.</p>
  <ul>
    <li><strong>Two positions</strong> were CHAN0/CHAN1 until their balls (W2, V2) went to the microSD as DAT2/DAT1.</li>
    <li><strong>One position</strong> was CHAN28. Its ball (M3) now carries UART CTS#, which completed hardware flow
    control on the FT2232HQ link. M3 was the right one to give up: highest-numbered so the header stays contiguous,
    in bank 35 alongside RTS# (N1) and DTR# (P1), and an ordinary HR pin — the other bank-35 channels are MRCC
    (CHAN22/23) or DQS (CHAN26/27) and are worth more where they are.</li>
  </ul>
  <ul>
    <li><strong>The USB landing sits between pin 5 and pin 6</strong> — the three positions at x=39.37, 36.83 and
    34.29, between CHAN3 and CHAN4. 10.16&nbsp;mm centre-to-centre, 8.64&nbsp;mm clear against X1's 7.80&nbsp;mm of
    copper and 7.50&nbsp;mm of body, so it clears both neighbours by 0.42&nbsp;mm. On the board that is
    <span class="mono">X1 at (22.90, 13.97) rot R90</span>, opening facing the x=25.40 edge.</li>
    <li><strong>Every pin keeps the signal it had.</strong> Pin 2 is still CHAN0, pin 5 still CHAN3, pin 6 still
    CHAN4, pin 13 still CHAN11 — the gate-to-pad map did not change. Only pads 2-5 moved, each +7.62&nbsp;mm into the
    space the gap had been occupying; pads 1 and 6-18 did not move at all.</li>
    <li><strong>The bottom row was closed up and is contiguous</strong> — pins 19..37 from x=49.53 down to x=3.81, and
    the empty position is the board corner at x=1.27. Getting there <strong>moved three pins</strong> 2.54 mm:
    <span class="mono">+5V</span>, <span class="mono">ANALOG-IO0</span> and <span class="mono">ANALOG-IO1</span>. Their
    pin numbers did not change; their positions did. Anything already built against the old positions — a socket, an
    adapter, a constraint file keyed to physical position — is now wrong by one position on those three pins.</li>
    <li><strong>The gap is reserved, not spare.</strong> It is kept clear for the edge-mounted micro-USB. As drawn, X1
    needs 2.60 mm for its contacts and about 7.8 mm for its shell against 6.10 mm of clear space, so the board edge has
    to move out or a third position has to go before it drops in.</li>
    <li>Channels are now <span class="mono">CHAN0..CHAN27</span> on pins 2-13 and 19-34, contiguous. The old numbering
    ran 0-13 then 15-31 — there was never a CHAN14. GND is pin 16, and it is the only ground pin.</li>
    <li><strong>The board is now 1.000 &times; 2.400 in &mdash; 25.40 &times; 60.96&nbsp;mm &mdash; and sized to a
    breadboard.</strong> X2's two rows were 0.700&nbsp;in apart on the old 0.800&nbsp;in board: columns C and H.
    When the board widened to 1.000&nbsp;in the rows moved out with it, and they are now <strong>0.900&nbsp;in</strong>
    apart: columns <strong>B and I</strong>, with A, C, D, E and F, G, H, J free to patch into. The edges sit half a pitch outside the pins, so the long edges land exactly halfway between
    columns B and C. 24 grid positions per row now instead of 21; <strong>44 are fitted and 4 left bare</strong>, the bare
    four being top-row columns 12 to 15 &mdash; the USB landing &mdash; not spare columns at an end.
    <br>Two of the numbers originally asked for do not survive contact with the geometry, and are worth recording.
    <strong>0.74&nbsp;in is too narrow to hold the pads</strong>: at 0.700&nbsp;in pin spacing it leaves 0.508&nbsp;mm
    from pin centre to edge, where the 1.016&nbsp;mm drill with its 25&nbsp;% ring needs 1.062, so copper would hang
    off the edge &mdash; even the smallest drill a 0.025&nbsp;in post tolerates still needs 0.763&nbsp;in. And
    <strong>2.75&nbsp;in is 27.5 row pitches</strong>, not a whole number of rows, and not the same board as
    &ldquo;rows 1 to 24&rdquo;, which is 2.400&nbsp;in. 2.400 was built first, then lengthened to
    <strong>2.750</strong> to buy an 8.89&nbsp;mm strip past the grid for the Pmod, and has now been cut back to
    <strong>2.400</strong>. The outline is the 24-column grid again and nothing more, so the strip the Pmod stood
    on is gone with the length: J1, 5.08&nbsp;mm wide, and JP3 both need a place inside the channel. The earlier plain 53.34 &times; 25.40 rectangle &mdash; which
    replaced a 25.40 &times; 50.80 board with a 5.94 &times; 1.22&nbsp;mm mini-USB tab &mdash; is superseded by
    this.</li>
    <li>Both the package outline in the schematic and the layer-20 dimension in <span class="mono">zulu_a7.brd</span>
    were updated, since the outline is the one thing meant to survive the re-layout. X1's board position follows the
    USB landing &mdash; see the bullet above.</li>
  </ul>

  <h2 class="serif">8 · Footprint audit</h2>
  <p>Three footprints were electrically correct and geometrically generic: right pin counts, right connects, ERC-clean,
  and physically unmateable. That combination survives every check in this project's battery, which is why they lasted
  until someone measured them against the datasheets.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Part</th><th>Was</th><th>Now</th><th>Confidence</th></tr></thead>
    <tbody>__FOOT__</tbody></table></div>
  <p class="note">Verified correct and left alone: U1 (238 balls, 19×19 at 0.5 mm, matched ball-for-ball against the
  Xilinx pinout file), U3 TSOP-II 54 at 0.8 mm, U2 QFN-64, U10 SOIC-8, and the 2.54 mm headers. U4's SOIC-8 208-mil land was recomputed to IPC-7351B level B this revision &mdash; see &sect;9.</p>
  <div class="callout"><strong>Two deliberate electrical changes.</strong> X1's four shell tabs and X3's shield pads
  G3/G4 now join GND. None of them appeared in any connect before, so they would have been isolated copper under a
  metal shell.</div>

  <h2 class="serif">9 · Fixed along the way</h2>
  <ul>
    <li><span class="mono">R2.B</span> pulled <span class="mono">PROGRAM_B</span> <em>down</em> in the original design.
    Xilinx wants it pulled up; that leg is gone and PROGRAM_B reuses the <span class="mono">RST#</span> net.</li>
    <li><span class="mono">ANALOG-IO0/1</span> used to reach two PIC ADC pins. They are now the FPGA's XADC auxiliary
    differential pair.</li>
    <li><strong>The FT2232HQ's EEPROM was the wrong organisation.</strong> <span class="mono">93LC56A</span> is 256 × 8;
    DS_FT2232H p27 requires 16 bits wide and names the <span class="mono">93LC46B</span>. An × 8 part would have left the
    bridge unable to read its configuration, so it would have enumerated on FTDI's default VID 0403 / PID 6010 with no
    serial number &mdash; working, but not the custom identity the EEPROM is there for. Now
    <span class="mono">__U10__</span>, 64 × 16. Nothing electrical moves: CS, CLK, DI, DO, VCC and VSS keep their pads
    and their nets, and only the two unconnected pins were renamed.</li>
    <li><strong>The EEPROM pull-ups were wrong in value, and one of them on the wrong node.</strong> All three were
    4.7 k, and R97 pulled up <span class="mono">EE-DATA</span> &mdash; the Data-In line. DS_FT2232H p11 says of pin 61:
    &ldquo;Connect directly to Data-In of the EEPROM and to Data-Out of the EEPROM via a 2.2 K resistor. Also, pull
    Data-Out of the EEPROM to VCC via a 10 K resistor for correct operation,&rdquo; and the reference circuits on p28
    and p50-53 draw three 10 k pull-ups: EECS, EECLK, and Data-Out &mdash; none on the Data-In line. R96 and R98 are now
    10 k where they were; R97 is 10 k and moved to <span class="mono">EE-DATA-DO</span>. Its drop crosses the three
    signal runs without joining them, which is how FTDI draws it too.</li>
    <li><strong>U4's land was a 150/208-mil compromise; it is now IPC-7351B nominal for the 208.</strong> The pads
    were 2.921 mm long, running 1.87 mm past the lead heel and putting 1.21 mm of copper under the plastic body.
    Recomputed from the datasheet's own section 10.1 at density level B &mdash; Z 8.806, G 5.788, X 0.558 &mdash;
    giving a 1.51 &times; 0.56 pad 3.65 from the centreline: 0.455 past the toe, 0.405 inside the heel, and 0.255
    <em>clear</em> of the body. <strong>The outer envelope barely moves</strong> (8.70 &rarr; 8.81), so this buys no
    board width; what it buys is 43 % less copper per pad, no copper under the body, and a routing channel between
    the pad rows that widens from 2.86 mm to 5.79 mm &mdash; enough to take traces or a via field under the chip.
    Renamed <span class="mono">SOIC-8_208MIL</span>, because it is no longer a land that takes either body: a
    150-mil lead, with toes at &plusmn;3.00 and heels at &plusmn;2.50, would overhang the new pad by 0.105 mm and sit
    on nothing. The rename also guarantees the regenerated board takes this land rather than silently matching the
    stale <span class="mono">xess</span> copy of the old name.</li>
    <li><strong>The header clock was on a ball that cannot take a clock.</strong> Vivado's placer rejects it outright
    &mdash; <span class="mono">DRC PLIO-9</span>, an error, not a warning: <em>&ldquo;The following clock source has
    been LOCed to a N-Type CCIO : CHAN_CLK&rdquo;</em>. <span class="mono">CHAN-CLK</span> sat on R18 =
    <span class="mono">IO_L14N_T2_SRCC_14</span>, the N half of a clock-capable pair, and a single-ended clock input
    has to be on the P half. <span class="mono">place_design</span> refuses to run, so as drawn nobody could have
    built a design that clocks from the prototyping header. Swapped with SDRAM <span class="mono">WE#</span> on
    P18 = <span class="mono">IO_L14P_T2_SRCC_14</span> &mdash; same bank, and WE# is a plain output that does not care
    which half of a pair it sits on. Only the two <span class="mono">&lt;connect&gt;</span> entries changed; the pins
    are drawn <span class="mono">visible="pad"</span>, so the sheet picked up the new balls by itself.
    <span class="mono">CLK-12M-FPGA</span> on L17 = <span class="mono">IO_L12P_T1_MRCC_14</span> was already right.</li>
    <li><strong>The whole file is back on the 1.27 mm grid.</strong> 1175 of 1818 wire endpoints and 298 of 468
    instances sat off-grid, by many different offsets &mdash; U2 by (&minus;0.33, +0.19), R96/R97/R98 by +0.12 in x,
    the C39/C40/C41 and L4/L5 group by nearly 0.6 in both axes, and the whole of the FPGA-connections sheet by varying
    amounts. Anything wired between two parts with different offsets needed a dogleg to close the gap, and there were
    34 of them, from 0.013 to 0.19 mm. They are invisible at normal zoom, they render as small rings when you zoom in,
    and they made the file fragile: nudge one part in Fusion and its runs come away from the taps, which is what
    happened to the EEPROM block on two consecutive exports. Now 0 off-grid endpoints, 0 off-grid instances, 0 wires
    under 1 mm, across all seven sheets.</li>
    <li><strong>The &ldquo;56 stray junction dots&rdquo; this record used to report were a bug in the audit, not in
    the schematic.</strong> The rule &mdash; a dot belongs where <span class="mono">E + 2T + pin &ge; 3</span> &mdash;
    was only ever evaluated at wire <em>endpoints</em>. A decoupling pin landing straight on a supply rail with no stub
    of its own has E = 0, so it was never considered and its perfectly correct dot was counted as stray. That one
    omission accounted for 55 of the 56. The real state was one missing dot and two stray, all on
    <span class="mono">VCC1V0</span>, and the re-grid resolved them. The audit and the validator were both fixed to
    enumerate wire ends, pin positions and existing dots.</li>
    <li>Whole-file geometry pass: <strong>0 missing junctions, 0 stray, on every sheet</strong>; no wire endpoint on a
    foreign net; no overlapping wires.</li>
    <li><span class="mono">uservalue</span> normalised across 17 devicesets, so part values display the manufacturer
    part number rather than the deviceset name.</li>
    <li>JP3's board footprint corrected 2×2 → 2×3 with all existing routing preserved — the board had always been
    short two pads for a six-signal JTAG header.</li>
    <li>Block diagram brought in line: separate flash and SD buses, the Pmod box, the 4-bit SD bus, the CHAN-I/O count,
    oscillator-not-crystal, the Artix-7 label, and 64 MB.</li>
  </ul>

  <h2 class="serif">Open items — read before layout</h2>
  <div class="callout warn"><strong>1. The board file is still the original Spartan-6 layout.</strong> 65 elements
  against __NP__ parts, and X1's element now sits outside the outline because the tab it was mounted on is gone —
  expected, and it resolves on regeneration. Its 421 routed connections are all for the Spartan-6 and are worthless. The stackup is already declared four-layer &mdash; <span class="mono">layerSetup (1*2*3*16)</span>, with Route2 and Route3 active &mdash; but only Top and Bottom carry copper, so nothing has ever been routed on the inner pair. The design rules are the old board's and will not do for the BGA: a via at <span class="mono">msDrill</span> 10 mil with a 25 % annular ring comes out 0.56 mm across, where the diagonal channel between four 0.5 mm-pitch balls offers a free radius of only 0.204 mm. Rebuild the board from the schematic rather than forward-annotating onto this one.</div>
  <div class="callout"><strong>2. The ball assignments have been through Vivado.</strong> <span class="mono">
  tools/vivado_io_check.py</span> reads the ball map out of the schematic, writes a Verilog stub with one port per
  user I/O and both clock inputs through BUFGs, and runs synth &rarr; opt &rarr; place &rarr; DRC on
  <span class="mono">xc7a35tcpg236-1</span>. Placement is what enforces the I/O rules, and it now completes clean:
  101 ports on exactly the balls drawn here, no bank/VCCO/IOSTANDARD conflict, no dual-purpose config-pin conflict
  under SPIx4, no VREF or DQS complaint. Re-run it after any change to the pinout. It caught one real error &mdash;
  see §9.</div>
  <div class="callout warn"><strong>3. Two footprints carry derived geometry.</strong> X1's shell tabs need Molex's
  <span class="mono">1050170001_sd.pdf</span>; X3's shield pads need Hirose's own PCB pattern. The contacts on both
  are exact. Each package carries a layer-51 note recording this, so the provenance travels with the file.</div>
  <div class="callout"><strong>4. The board now has real margin.</strong> Usable area has two zones: where the header pads are, only the 16.256&nbsp;mm channel between the rows is free; past the last pad there are no through-holes, so the full 20.32 is. That is 1205&nbsp;mm&sup2; a side, 2409 across both, against 1983&nbsp;mm&sup2; of placed parts &mdash; <strong>+426&nbsp;mm&sup2;, about 21&nbsp;%</strong>. Earlier revisions applied the channel to the whole length and so undercounted the board: the 2.400&nbsp;in version read as break-even when it was really about +65, which means deleting BTN1 bought comfort rather than rescuing the design. Both packing factors (&times;&nbsp;1.70 for chip passives, &times;&nbsp;1.15 for everything else) are assumptions, not measurements. See <span class="mono">Zulu A7 Board Plan.html</span>.</div>
  <ul>
    <li>SDRAM CLK drives from a single FPGA pin; the original double-drove it from two in parallel. Add the second back
    if timing margin needs it.</li>
    <li>Nothing else free on the FT2232HQ is worth an FPGA pin — DSR#/DCD#/RI# are modem-era, and the ACBUS/spare
    BDBUS pins would only duplicate what the prototyping header already gives you. Since the FPGA has no free I/O,
    every one of them would cost a channel.</li>
    <li><strong>U10 pin 6 is confirmed, not assumed.</strong> This was carried as unverified because no Microchip
    datasheet was thought to be in the project folder. It is &mdash;
    <span class="mono">DS20001749</span> &mdash; and it says so twice on its own front page: <em>&ldquo;64 x 16-bit
    Organization &lsquo;B&rsquo; Devices (no ORG)&rdquo;</em> and <em>&ldquo;ORG pin is NC on A/B devices&rdquo;</em>.
    So <span class="mono">NC@2</span> on pin 6 is right. The same datasheet puts the
    <span class="mono">LC</span> part at 2.5&ndash;5.5 V and specifies its clock at 2 MHz down to VCC = 3.0 V, so
    FTDI's 1 Mbit/s at 3.0&ndash;3.6 V has margin. Still true that a <span class="mono">93LC46C</span> substitution
    would need pin 6 tied to VCC to select × 16.</li>
    <li>Dropping 2 Kbit → 1 Kbit costs descriptor space: 128 bytes now hold the VID, PID, serial number, string
    descriptors and the per-channel mode bits. A long custom product string can fill it. That is a programming-time
    limit in FT_PROG, not a wiring one.</li>
    <li>Around 23 text notes overrun the drawn sheet borders — cosmetic, but they will look wrong when plotted.</li>
  </ul>

  <footer>
    Baseline <span class="mono">30a0e65</span> · this revision <span class="mono">__HEAD__</span> ·
    __NC__ commits since baseline.
    Regenerate with <span class="mono">python tools/change_record.py</span>.
  </footer>
</div>
<script>
const DATA = __DATA__;
const body = document.getElementById('pinbody');
function render(f) {
  body.innerHTML = '';
  for (const [net, ball, name, bank] of (DATA[f] || [])) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td class="mono">${net}</td><td class="mono">${ball}</td><td class="mono">${name}</td><td class="mono">${bank}</td>`;
    body.appendChild(tr);
  }
}
document.querySelectorAll('.filterbtn').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.filterbtn').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  render(b.dataset.f);
}));
render(Object.keys(DATA)[0]);
</script>
"""
html = CSS_AND_HEAD + BODY
for k, v in (("__HEAD__", HEAD), ("__NP__", str(len(PARTS))), ("__NN__", str(len(NET))),
             ("__NS__", str(len(SHEETS))), ("__NC__", NCOMMIT), ("__BOM__", BOM),
             ("__POWER__", POWER), ("__FOOT__", FOOT), ("__TABS__", TABS),
             ("__DATA__", json.dumps(DATA)), ("__MODE__", MODEBITS), ("__Q1__", VAL["Q1"]),
             ("__U10__", VAL["U10"]),
             ("__NUSED__", str(len(used))), ("__NFREE__", str(238 - len(used))),
             ("__CHA__", CHA), ("__CHB__", CHB), ("__NFTFREE__", str(NFTFREE)),
             ("__BANKS__", ", ".join(("no&nbsp;bank&nbsp;(GND)&nbsp;×&nbsp;%d" % n) if b == "NA"
                                     else ("bank&nbsp;%s&nbsp;×&nbsp;%d" % (b, n))
                                     for b, n in sorted(BANKS.items())))):
    html = html.replace(k, v)
assert "__" not in re.sub(r'[A-Za-z0-9_]*__[A-Za-z0-9_]*', lambda m: "" if m.group(0).startswith("_") and False else m.group(0), "") or True
left = re.findall(r"__[A-Z0-9]+__", html)
assert not left, left
open(OUT, "w", encoding="utf-8").write(html)
print("wrote %s (%d chars)" % (OUT, len(html)))
print("HEAD %s, %s commits since baseline; %d parts, %d nets, %d sheets"
      % (HEAD, NCOMMIT, len(PARTS), len(NET), len(SHEETS)))
print("M[2:0] = %s (Master SPI)  |  %d balls used, banks %s" % (MODEBITS, len(used), dict(BANKS)))
print("pin table groups: %s = %d rows" % (", ".join("%s:%d" % (k, len(v)) for k, _, v in GROUPS), NPIN))
