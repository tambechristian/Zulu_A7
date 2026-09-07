# -*- coding: utf-8 -*-
"""Zulu A7 power budget, rail by rail, from the schematic and the datasheets.

    python tools/power_budget.py                 prints the report (markdown)
    python tools/power_budget.py --fpga-int 500  heavier FPGA core current, mA
    python tools/power_budget.py --header 150    external load on the header's +3.3V pins, mA

Every current below names its source. "typ" is what the board draws in
ordinary use, "max" is the datasheet maximum or the largest simultaneous case
that can actually happen. The FPGA's dynamic currents are the only inputs the
datasheets cannot give: replace them with Vivado's report_power for the real
bitstream (--fpga-int / --fpga-aux / --fpga-io).
"""
import argparse

# ---- supply topology, from the schematic ----------------------------------
USB_VBUS = 5.0      # V, USB 2.0 port; 4.75 V minimum at the connector
D1_DROP = 0.30      # V, PMEG2020EJ Schottky in the USB5V0 -> VU path at ~0.5 A
VU = USB_VBUS - D1_DROP
USB_LIMIT = 500     # mA, USB 2.0 configured high-power device
USB_UNCONF = 100    # mA, allowed before enumeration
LTC3569_THJA = 43   # C/W, UDC (QFN-20 4x4) package, datasheet p2
FPGA_THJA = 24.8    # C/W, XC7A35T CPG236 still air, UG475 thermal table
FT2232_THJA = 28    # C/W, ASSUMED for a 64-QFN 9x9 with exposed pad (datasheet gives none)
SDRAM_THJA = 45     # C/W, ASSUMED for TSOP-II 54 (datasheet gives none)

# channel -> (rail, V, limit mA, efficiency at VIN~4.7 V read from datasheet p4/p5)
CHANNELS = {
    "SW1 (buck 1, 1.2 A)": ("VCC1V0", 1.0, 1200, 0.78),   # 1.2 V curve ~80 % at 5 V; 1.0 V a little lower
    "SW2 (buck 2, 600 mA)": ("VCC1V8", 1.8, 600, 0.85),   # 1.8 V curve ~85-88 % at 5 V
    "SW3 (buck 3, 600 mA)": ("VCC3V3", 3.3, 600, 0.90),   # high duty cycle; 1.5 V curve ~83 %, 3.3 V better
}


def consumers(a):
    """rail -> [(who, typ mA, max mA, source)]"""
    return {
        "VCC1V0": [
            ("U1 VCCINT quiescent (6 balls)", 95, 95,
             "DS181 Table 7, XC7A35T ICCINTQ 95 mA typ at 85 C junction"),
            ("U1 VCCINT dynamic", a.fpga_int, a.fpga_int,
             "ASSUMED design load; replace with Vivado report_power"),
            ("U1 VCCBRAM (2 balls) quiescent + dynamic", 2 + a.fpga_bram, 2 + a.fpga_bram,
             "DS181 ICCBRAMQ 2 mA; dynamic assumed"),
            ("X2 pin 19 +1.0V to header", a.header_1v0, a.header_1v0, "external, user allowance"),
        ],
        "VCC1V8": [
            ("U1 VCCAUX quiescent (H13, J13)", 22, 22, "DS181 Table 7, ICCAUXQ 22 mA"),
            ("U1 VCCAUX dynamic (MMCM, config, I/O aux)", a.fpga_aux, 2 * a.fpga_aux,
             "ASSUMED; Vivado report_power"),
            ("U1 VCCADC via L7 (XADC on, AIN15/AIN16 used)", 12, 25, "DS181 ICCADC 25 mA max"),
            ("U1 VCCBATT (C9)", 0, 0, "tied to VCC1V8, no battery: negligible"),
            ("X2 pin 18 +1.8V to header", a.header_1v8, a.header_1v8, "external, user allowance"),
        ],
        "VCC3V3": [
            ("U2 FT2232HQ core via VREGIN (Icc1)", 70, 70, "FT2232H DS Table 5.2, 70 mA"),
            ("U2 FT2232HQ USB PHY (Iccphy, high speed)", 30, 60, "FT2232H DS Table 5.4, 30 typ / 60 max"),
            ("U2 FT2232HQ VCCIO switching", 10, 20, "ASSUMED, 3.3 V I/O cells at JTAG/UART rates"),
            ("U3 SDRAM AS4C32M16SB-6", 100, 160,
             "IDD1 120, IDD4 124, IDD5 160 (refresh), IDD2N 50 standby"),
            ("U4 W25Q128JV flash (quad read 104 MHz / program)", 12, 25,
             "ICC3 12 typ 20 max; ICC5 program 25 max"),
            ("X3 microSD card", a.sd_typ, a.sd_max,
             "SD spec: ~60 typ, 200 max at 3.3 V for a high-speed card"),
            ("U10 93LC46B EEPROM", 1, 2, "read 1 mA, write 2 mA max"),
            ("Q1 ASEM1 12 MHz oscillator", 7, 15, "1-40 MHz row: 7 typ / 15 max, no load"),
            ("U1 VCCO banks 0/14/16/34/35 (28 balls) static", 5, 5, "DS181 ICCOQ, about 1 mA per bank"),
            ("U1 VCCO dynamic (SDRAM bus, header, LED sink path)", a.fpga_io, 3 * a.fpga_io,
             "ASSUMED; about 1.6 mA per toggling pin at 100 MHz, 10 pF"),
            ("LD0 RGB (R80 33, R81 330, R82 33) + LD1/LD2 (330) + LD5 (680)", 8, 22,
             "VF from VS NRD8 sheet: red 2.0-2.4, green/blue 3.3-3.8 V"),
            ("pull-ups when driven low (6 x 4.7k, 12 x 10k)", 2, 8,
             "R1, R2, R6, R7, R34, R35, R89-R99, R19, R20, R23"),
            ("J1 Pmod pins 6/12 and X2 pins 2/17 +3.3V to header", a.header, a.header,
             "external, user allowance"),
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fpga-int", type=int, default=250, help="VCCINT dynamic, mA (default 250: a moderate design)")
    p.add_argument("--fpga-bram", type=int, default=20)
    p.add_argument("--fpga-aux", type=int, default=15)
    p.add_argument("--fpga-io", type=int, default=30)
    p.add_argument("--sd-typ", type=int, default=60)
    p.add_argument("--sd-max", type=int, default=200)
    p.add_argument("--header", type=int, default=0, help="+3.3V drawn by the header/Pmod, mA")
    p.add_argument("--header-1v8", type=int, default=0)
    p.add_argument("--header-1v0", type=int, default=0)
    a = p.parse_args()
    C = consumers(a)
    out = []
    w = out.append
    w("# Zulu A7 power budget\n")
    w(f"Source: zulu_a7.sch as imported (Imported zulu_a7.PrjPcb), datasheets in Datasheet/. "
      f"Generated by tools/power_budget.py with --fpga-int {a.fpga_int} --fpga-aux {a.fpga_aux} "
      f"--fpga-io {a.fpga_io} --header {a.header}.\n")
    w("Power comes in as USB VBUS through D1 (PMEG2020EJ) onto VU, or as +5V-INPUT on X2 pin 44 through D2 "
      "with D3 (SMF5.0A) clamping it; the two are diode-ORed. VU feeds the LTC3569 (U8), whose three bucks "
      "make the rails. EN1 is tied to VU so VCC1V0 rises first; EN2 and EN3 sit on EN_BIAS, gated by Q3 "
      "whose base is driven from VCC1V0 through R79, so VCC1V8 and VCC3V3 follow. That is the order UG483 "
      "recommends (VCCINT, VCCBRAM, VCCAUX, VCCO).\n")
    totals = {}
    for ch, (rail, V, limit, eff) in CHANNELS.items():
        rows = C[rail]
        t = sum(r[1] for r in rows)
        m = sum(r[2] for r in rows)
        totals[rail] = (V, limit, eff, t, m)
        w(f"\n## {rail} = {V} V on {ch}\n")
        w("| Consumer | typ mA | max mA | Source |")
        w("|---|---:|---:|---|")
        for who, ty, mx, src in rows:
            w(f"| {who} | {ty} | {mx} | {src} |")
        w(f"| **Total** | **{t}** | **{m}** | channel limit {limit} mA |")
        w(f"| Headroom | {limit - t} | {limit - m} | {'**over the channel limit**' if m > limit else 'ok'} |")
    w("\n## Power-on requirement (DS181 Table 9, XC7A35T)\n")
    w("The supplies must deliver the quiescent current plus an inrush allowance while the FPGA powers up, "
      "before anything is configured:\n")
    w("| Rail | Requirement | This board | ok |")
    w("|---|---|---:|---|")
    po = {"VCC1V0": ("ICCINTQ + 120 + ICCBRAMQ + 60", 95 + 120 + 2 + 60),
          "VCC1V8": ("ICCAUXQ + 40", 22 + 40),
          "VCC3V3": ("ICCOQ + 40 mA per bank x 5 banks, plus the rest of the rail at rest",
                     5 + 200 + 70 + 30 + 50 + 7)}
    for rail, (txt, mA) in po.items():
        lim = totals[rail][1]
        w(f"| {rail} | {txt} | {mA} mA | {'ok' if mA <= lim else 'NO'} (channel {lim} mA) |")
    w("\n## Input from USB\n")
    w(f"VU = {USB_VBUS} - {D1_DROP} = {VU:.2f} V after D1. Input power per rail is Vout x Iout / efficiency, "
      "efficiency read from the LTC3569 curves at about 4.7 V in.\n")
    w("| Rail | typ W in | max W in | efficiency |")
    w("|---|---:|---:|---:|")
    pt = pm = 0.0
    loss_t = loss_m = 0.0
    for rail, (V, limit, eff, t, m) in totals.items():
        pit = V * t / 1000 / eff
        pim = V * m / 1000 / eff
        loss_t += pit * (1 - eff)
        loss_m += pim * (1 - eff)
        pt += pit
        pm += pim
        w(f"| {rail} | {pit:.2f} | {pim:.2f} | {eff:.0%} |")
    it = pt / VU * 1000 + 1
    im = pm / VU * 1000 + 1
    w(f"| **USB current at {VU:.2f} V** | **{it:.0f} mA** | **{im:.0f} mA** | "
      f"limit {USB_LIMIT} mA configured, {USB_UNCONF} mA before enumeration |")
    w("")
    w(f"- Typical use draws about {it:.0f} mA from the port: "
      f"{'inside' if it <= USB_LIMIT else 'OVER'} the 500 mA a configured USB 2.0 device may take.")
    w(f"- The simultaneous worst case draws about {im:.0f} mA: {'inside' if im <= USB_LIMIT else 'over'} the port "
      "limit, so a design that pushes the FPGA, the SDRAM and a busy microSD at once needs the +5V-INPUT on "
      "X2 pin 44 or VU on pin 22.")
    w("- All three rails start as soon as VBUS appears and the FPGA configures from flash immediately, so the "
      "board is above the 100 mA unconfigured limit before the FT2232H enumerates. Hosts tolerate this in "
      "practice; FT-PWREN# reaches the FPGA (P17) if you ever want to hold heavy loads off until enumeration.")
    w("- C78 (22 uF) hangs directly on VU, which is VBUS through D1: the USB 2.0 limit for bulk capacitance "
      "seen at attach is 10 uF. D1's forward drop softens the inrush, but a host with a strict VBUS current "
      "limiter may still object.")
    w("\n## Thermal, still air, first order\n")
    w("| Part | P typ W | P max W | thJA C/W | rise typ C | rise max C |")
    w("|---|---:|---:|---:|---:|---:|")
    fpga_t = (1.0 * (95 + a.fpga_int + 2 + a.fpga_bram) / 1000
              + 1.8 * (22 + a.fpga_aux + 12) / 1000 + 3.3 * (5 + a.fpga_io) / 1000)
    fpga_m = (1.0 * (95 + a.fpga_int + 2 + a.fpga_bram) / 1000
              + 1.8 * (22 + 2 * a.fpga_aux + 25) / 1000 + 3.3 * (5 + 3 * a.fpga_io) / 1000)
    rows = [("U1 XC7A35T CPG236", fpga_t, fpga_m, FPGA_THJA, ""),
            ("U8 LTC3569 (switching + conduction loss)", loss_t, loss_m, LTC3569_THJA, ""),
            ("U2 FT2232HQ", 3.3 * 0.110, 3.3 * 0.150, FT2232_THJA, " (thJA assumed)"),
            ("U3 SDRAM", 3.3 * 0.100, 3.3 * 0.160, SDRAM_THJA, " (thJA assumed)")]
    for name, ptw, pmw, th, note in rows:
        w(f"| {name}{note} | {ptw:.2f} | {pmw:.2f} | {th} | {ptw * th:.0f} | {pmw * th:.0f} |")
    w("\nNone of these needs airflow or a heatsink at 25 C ambient. The FPGA stays well under its 85 C "
      "commercial junction limit even in the heavy case, and the LTC3569's 125 C limit is far away.\n")
    w("\n## Findings\n")
    w("1. **VCC3V3 is the tight rail.** It carries the FT2232H, the SDRAM, the flash, the microSD card, all five "
      "FPGA I/O banks, the oscillator, the LEDs and both header supplies on the LTC3569's 600 mA channel. "
      "Typical use is fine; the datasheet-maximum sum is over the channel. Realistic simultaneous peaks "
      "(SDRAM burst, USB active, card reading) sit around 450-500 mA, which leaves about 100 mA for the Pmod "
      "and the header's +3.3V pins. Budget the header at 100 mA or less, or feed heavy add-ons from VU.")
    w("2. **The 1.2 A channel on VCC1V0 has the most headroom.** A moderate design draws about a third of it. "
      "Only a very full, fast design would need the rest; get the real number from Vivado's report_power.")
    w("3. **VCC1V8 is lightly loaded**, well under 100 mA even with the XADC running.")
    w(f"4. **USB alone covers typical use** at about {it:.0f} mA from the port. The simultaneous worst case "
      f"({im:.0f} mA) needs the external 5 V input.")
    w("5. **Green and blue of LD0 may not light.** Their forward voltage is 3.3-3.8 V per the VS NRD8 sheet, "
      "and the FPGA sinks them from a 3.3 V supply through 33 ohm, leaving no headroom; only the red "
      "(2.0-2.4 V) has margin. Expect dim or dark green/blue unless the parts fall at the low end of VF. "
      "Not a power problem, but it fell out of the LED current estimate.")
    w("6. **Power-on order is right**: EN1 on VU brings VCCINT/VCCBRAM up first, then Q3 releases EN2/EN3 for "
      "VCCAUX and VCCO.")
    print("\n".join(out))


if __name__ == "__main__":
    main()
