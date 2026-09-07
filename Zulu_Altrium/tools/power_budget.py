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
SC189_THJA = 90     # C/W, SC189 datasheet p3: SOT23-5 on a 10x10 mm 2-layer 1 oz board, free convection; MLPD-UT6 is 60
FPGA_THJA = 24.8    # C/W, XC7A35T CPG236 still air, UG475 thermal table
FT2232_THJA = 28    # C/W, ASSUMED for a 64-QFN 9x9 with exposed pad (datasheet gives none)
SDRAM_THJA = 45     # C/W, ASSUMED for TSOP-II 54 (datasheet gives none)

# channel -> (rail, V, limit mA, efficiency at 5 V in, read from the SC189
# datasheet's SOT23-5 curves (p6) at this rail's typical load)
# 2026-09-06 (later the same day): the LTC3569 was replaced by three fixed
# SC189 bucks, 1.5 A each at 2.5 MHz (tools/sc189_power_section.py).
CHANNELS = {
    "U5 SC189Z (1.5 A)": ("VCC3V3", 3.3, 1500, 0.90),   # 3.3 V curve: 90-92 % from 0.3 to 0.7 A
    "U6 SC189L (1.5 A)": ("VCC1V8", 1.8, 1500, 0.78),   # 1.5 V curve at 50-80 mA: 75-80 %, the 7.5 mA IQ dominates
    "U7 SC189A (1.5 A)": ("VCC1V0", 1.0, 1500, 0.81),   # 1.0 V curve at 0.3-0.4 A: about 81 %
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
      "with D3 (SMF5.0A) clamping it; the two are diode-ORed. VU feeds three fixed SC189 bucks, U5 (3.3 V), "
      "U6 (1.8 V) and U7 (1.0 V), 1.5 A each at 2.5 MHz, enables tied to VU, so all three rails soft-start "
      "together when VU appears; UG483 requires no order between VCCINT, VCCAUX and VCCO.\n")
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
      "efficiency read from the SC189 datasheet's SOT23-5 curves at 5 V in (p6).\n")
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
    w("- VU, which is VBUS through D1, now carries C78 (10 uF) plus the three SC189 input caps C147-C149 "
      "(10 uF each; the datasheet wants at least 4.7 uF effective at every VIN pin): 40 uF nominal, roughly "
      "25 uF effective at 5 V. The USB 2.0 limit for bulk capacitance seen at attach is 10 uF (50 uC of "
      "inrush). Hosts tolerate this in practice; if one objects, drop C78, the regulators have their own caps.")
    w("\n## Thermal, still air, first order\n")
    w("| Part | P typ W | P max W | thJA C/W | rise typ C | rise max C |")
    w("|---|---:|---:|---:|---:|---:|")
    fpga_t = (1.0 * (95 + a.fpga_int + 2 + a.fpga_bram) / 1000
              + 1.8 * (22 + a.fpga_aux + 12) / 1000 + 3.3 * (5 + a.fpga_io) / 1000)
    fpga_m = (1.0 * (95 + a.fpga_int + 2 + a.fpga_bram) / 1000
              + 1.8 * (22 + 2 * a.fpga_aux + 25) / 1000 + 3.3 * (5 + 3 * a.fpga_io) / 1000)
    rows = [("U1 XC7A35T CPG236", fpga_t, fpga_m, FPGA_THJA, "")]
    for ch, (rail, V, limit, eff) in CHANNELS.items():
        t_, m_ = totals[rail][3], totals[rail][4]
        rows.append((f"{ch} for {rail}", V * t_ / 1000 * (1 / eff - 1), V * m_ / 1000 * (1 / eff - 1), SC189_THJA, ""))
    rows += [
            ("U2 FT2232HQ", 3.3 * 0.110, 3.3 * 0.150, FT2232_THJA, " (thJA assumed)"),
            ("U3 SDRAM", 3.3 * 0.100, 3.3 * 0.160, SDRAM_THJA, " (thJA assumed)")]
    for name, ptw, pmw, th, note in rows:
        w(f"| {name}{note} | {ptw:.2f} | {pmw:.2f} | {th} | {ptw * th:.0f} | {pmw * th:.0f} |")
    w("\nThe FPGA stays well under its 85 C commercial junction limit. The SOT23-5 regulators are the warm "
      "parts now: the 3.3 V one dissipates about 0.12 W typical and up to 0.25 W at the datasheet maxima, which at "
      "the datasheet's 90 C/W (SOT23-5 on a 10x10 mm 2-layer 1 oz test board) is an 11-22 C rise. Figure 3 of the "
      "SC189 sheet rates the SOT23-5 for the full 1.5 A at 3.3 V out up to about 65 C ambient, so no derating "
      "applies here. Give the GND pin and the LX/VOUT copper a pour anyway; the 2x2 mm MLPD-UT6 version "
      "(SC189xULTRT, 60 C/W) is the fallback if the board must run hot.\n")
    w("\n## Findings\n")
    w("1. **No rail is near its regulator limit any more.** Each SC189 gives 1.5 A; VCC3V3 uses under a "
      "quarter of that in typical use and under half at the datasheet maxima, VCC1V0 a quarter, VCC1V8 a "
      "twentieth. The header and Pmod +3.3V pins can take several hundred milliamps when the board runs "
      "from the external 5 V.")
    w("2. **The USB port is the only limit left.** On a USB-A port the budget is unchanged: typical use fits, "
      "the datasheet-maximum case does not, and that is what +5V-INPUT is for.")
    w("3. **VCC1V8 is lightly loaded**, well under 100 mA even with the XADC running.")
    w(f"4. **USB alone covers typical use** at about {it:.0f} mA from the port. The simultaneous worst case "
      f"({im:.0f} mA) needs the external 5 V input.")
    w("5. **Green and blue of LD0 may not light.** Their forward voltage is 3.3-3.8 V per the VS NRD8 sheet, "
      "and the FPGA sinks them from a 3.3 V supply through 33 ohm, leaving no headroom; only the red "
      "(2.0-2.4 V) has margin. Expect dim or dark green/blue unless the parts fall at the low end of VF. "
      "Not a power problem, but it fell out of the LED current estimate.")
    w("6. **Sequencing is gone by design.** Every SC189 EN is tied to VU, so the three rails soft-start "
      "together. UG483 recommends VCCINT, VCCBRAM, VCCAUX, VCCO but requires no order and allows simultaneous "
      "ramps. The old LTC3569 EN_BIAS network went with it; it was copied from the Cmod A7 rev B, which "
      "Digilent shipped, so it evidently works in practice, but it holds the gated enables at 0.65-0.8 V, "
      "below the LTC3569 guaranteed 1.2 V high level, and Q3 pulls them low once VCC1V0 is up.")
    w("7. **The rails carry far more capacitance than the SC189 datasheet allows at start-up.** Page 19 says "
      "total output capacitance should not exceed 30 uF to avoid start-up problems: the fixed 100 us soft-start "
      "(current limit stepped 20/25/40/100 % of 2 A, 20 us each) delivers only 40-75 uC, after which the part "
      "runs at its 2 A limit and, after 32 cycles over the limit, folds back to 50-110 mA (Figure 5) until the "
      "load falls below that. UG483 Table 2-2 requires 100 uF on VCCINT, 47 uF on VCCBRAM, 47 uF on VCCAUX and "
      "47 uF per VCCO group for this FPGA, so the sheet has 165 uF nominal on VCC1V0, 167 uF on VCC3V3 and "
      "72 uF on VCC1V8 (about 150, 90 and 60 uF after DC bias), needing 150, 300 and 110 uC. Every rail "
      "therefore finishes its ramp in current limit or foldback, and a load that draws more than the foldback "
      "current before the rail is up (the FPGA's VCCINT power-on current is about 200 mA, the FT2232H on 3.3 V "
      "about 70 mA) could hold it down. The current Cmod A7 revision runs the same three SC189s into this same "
      "FPGA with its UG483 capacitors, so it works in practice, but it is the one datasheet limit this design "
      "does not meet: scope the three rails at power-on on the first board. If a rail hangs, the fixes are a "
      "regulator with a soft-start pin in the same role (TPS62130/TPS62823 class) or staggering the enables "
      "with RC delays so the rails do not all draw from VU at once.")
    print("\n".join(out))


if __name__ == "__main__":
    main()
