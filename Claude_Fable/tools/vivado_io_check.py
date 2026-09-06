# -*- coding: utf-8 -*-
"""Run the FPGA ball assignment in zulu_a7.sch through Vivado's I/O planner.

    python tools/vivado_io_check.py [path/to/file.sch]

WHAT THIS IS FOR. Everything else in tools/ checks the schematic against
itself, or against a text pinout file. Neither can tell you whether a ball is
*legal* for the job it has been given -- clock-capability, VREF, DQS byte
groups, bank voltage compatibility, config-mode conflicts. Vivado can, so this
asks it.

HOW IT WORKS. Pure pin-planning mode turns out to check almost nothing: with no
netlist there is no clock, so the clock rules never fire. What does work is a
synthesised stub. The script reads U1's ball/net map out of the schematic,
writes a Verilog top with one port per user I/O and the two clock inputs
through BUFGs, writes an XDC with PACKAGE_PIN and IOSTANDARD, then runs
synth_design -> opt_design -> place_design -> report_drc. Placement is the step
that enforces the I/O rules, so a clean place is the result worth having.

The stub deliberately splits its registers across both clock domains. With
everything on one clock the second BUFG gets optimised away and its pin is
never checked -- which is exactly how the CHAN-CLK error below hid.

WHAT IT FOUND. DRC PLIO-9, an error, not a warning:

    "The following clock source has been LOCed to a N-Type CCIO : CHAN_CLK"

CHAN-CLK sat on R18 = IO_L14N_T2_SRCC_14, the N half of a clock-capable pair.
A single-ended clock input has to be on the P half. place_design refuses to
run. Swapping it with SDRAM WE# on P18 = IO_L14P_T2_SRCC_14 -- same bank, and
WE# is a plain output that does not care which half it sits on -- clears it.
CLK-12M-FPGA on L17 = IO_L12P_T1_MRCC_14 was already on a P pin.

NOT DECLARED AS PORTS. The four XADC aux inputs (AIN15_P/N, AIN16_P/N) are
analog and would need the XADC IP rather than an IOSTANDARD, and PUDC_B is a
config strap tied high through R23, not user I/O. Constraining any of them as
LVCMOS33 would invent findings rather than reveal them.
"""

import re, io, os, sys, csv, subprocess, collections, shutil, tempfile

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PINOUT = os.path.normpath(os.path.join(ROOT, "Datasheet", "xc7a35tcpg236pkg_pinout.txt"))
PART = "xc7a35tcpg236-1"

# direction as seen from the FPGA; everything else is treated as bidirectional
DIR_IN = set("CHAN-CLK CLK-12M-FPGA BTN UART_FT_TXD UART_FT_RTS# UART_FT_DTR# FT-PWREN#".split())
DIR_OUT = set(("A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 BS0 BS1 CAS# RAS# WE# CKE LDQM UDQM "
               "SDRAM-CLK SDRAM-CS# SD-CLK SD-CMD FLASH-CS# UART_FT_RXD UART_FT_CTS# "
               "LED0_R LED0_G LED0_B LED1 LED2").split())
SKIP = {"AIN15_P", "AIN15_N", "AIN16_P", "AIN16_N", "PUDC_B"}
CLK_PORTS = ("CLK_12M_FPGA", "CHAN_CLK")


def safe(n):
    return re.sub(r"[^A-Za-z0-9_]", "_", n.replace("#", "_N"))


def extract(path):
    t = open(path, encoding="utf-8").read()
    ds = re.search(r'<deviceset name="XC7A35T-CPG236".*?</deviceset>', t, re.S).group(0)
    dev = re.search(r'<part name="U1"[^>]*device="([^"]*)"', t).group(1)
    dv = re.search(r'<device name="%s".*?</device>' % re.escape(dev), ds, re.S).group(0)
    g2b = {(g, p): pd for g, p, pd in re.findall(r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', dv)}
    netof = {}
    for m in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', t, re.S):
        for p, g, pn in re.findall(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', m.group(2)):
            if p == "U1":
                netof[(g, pn)] = m.group(1)
    rows = {}
    for l in open(PINOUT, encoding="utf-8", errors="replace"):
        p = l.split()
        if len(p) >= 8 and re.fullmatch(r"[A-Y]\d{1,2}", p[0]):
            rows[p[0]] = {"name": p[1], "bank": p[3]}
    out = []
    for k, ball in g2b.items():
        n = netof.get(k)
        nm = rows.get(ball, {}).get("name", "")
        if not n or not nm.startswith("IO_") or n in SKIP:
            continue
        d = "IN" if n in DIR_IN else ("OUT" if n in DIR_OUT else "INOUT")
        out.append({"port": safe(n), "net": n, "ball": ball, "dir": d,
                    "bank": rows[ball]["bank"], "pin_name": nm})
    return sorted(out, key=lambda r: r["port"])


def write_sources(ports, d):
    ins = [r for r in ports if r["dir"] == "IN"]
    outs = [r for r in ports if r["dir"] == "OUT"]
    ios = [r for r in ports if r["dir"] == "INOUT"]
    dins = [r for r in ins if r["port"] not in CLK_PORTS]
    ioA, ioB = ios[:len(ios) // 2], ios[len(ios) // 2:]
    oA, oB = outs[:len(outs) // 2], outs[len(outs) // 2:]
    v = ["`timescale 1ns/1ps", "module zulu_a7_top ("]
    v.append(",\n".join(["  input  wire %s" % r["port"] for r in ins]
                        + ["  output wire %s" % r["port"] for r in outs]
                        + ["  inout  wire %s" % r["port"] for r in ios]))
    v += [");", "  wire sysclk, chanclk;",
          "  BUFG u_bufg0 (.I(CLK_12M_FPGA), .O(sysclk));",
          "  BUFG u_bufg1 (.I(CHAN_CLK),     .O(chanclk));",
          "  reg [%d:0] qa = 0;  reg oea = 0;" % (len(ioA) + len(oA) - 1),
          "  reg [%d:0] qb = 0;  reg oeb = 0;" % (len(ioB) + len(oB) - 1)]
    for i, r in enumerate(ioA):
        v.append("  assign %s = oea ? qa[%d] : 1'bz;" % (r["port"], i))
    for j, r in enumerate(oA):
        v.append("  assign %s = qa[%d];" % (r["port"], len(ioA) + j))
    for i, r in enumerate(ioB):
        v.append("  assign %s = oeb ? qb[%d] : 1'bz;" % (r["port"], i))
    for j, r in enumerate(oB):
        v.append("  assign %s = qb[%d];" % (r["port"], len(ioB) + j))
    v += ["  always @(posedge sysclk)  begin oea <= %s; qa <= {qa[%d:0], oea}; end"
          % (" ^ ".join([r["port"] for r in dins] + [r["port"] for r in ioA]), len(ioA) + len(oA) - 2),
          "  always @(posedge chanclk) begin oeb <= %s; qb <= {qb[%d:0], oeb}; end"
          % (" ^ ".join([r["port"] for r in ioB]), len(ioB) + len(oB) - 2),
          "endmodule"]
    open(os.path.join(d, "zulu_a7_top.v"), "w").write("\n".join(v) + "\n")
    with open(os.path.join(d, "zulu_a7_pins.xdc"), "w") as f:
        f.write("# generated from zulu_a7.sch -- ball assignments exactly as drawn\n")
        f.write("set_property CFGBVS VCCO [current_design]\n")
        f.write("set_property CONFIG_VOLTAGE 3.3 [current_design]\n")
        f.write("set_property CONFIG_MODE SPIx4 [current_design]\n\n")
        for r in ports:
            f.write("set_property -dict {PACKAGE_PIN %-4s IOSTANDARD LVCMOS33} [get_ports {%s}]"
                    "  ;# %s  bank %s  %s\n" % (r["ball"], r["port"], r["net"], r["bank"], r["pin_name"]))
        f.write("\ncreate_clock -period 83.333 -name sysclk  [get_ports CLK_12M_FPGA]\n")
        f.write("create_clock -period 20.000 -name chanclk [get_ports CHAN_CLK]\n")
    return len(ins), len(outs), len(ios)


def main(path):
    ports = extract(path)
    d = os.path.join(tempfile.gettempdir(), "zulu_a7_iocheck")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    ni, no, nio = write_sources(ports, d)
    print("%d user I/O ports from %s (%d in, %d out, %d inout); %d not declared: %s"
          % (len(ports), os.path.basename(path), ni, no, nio, len(SKIP), ", ".join(sorted(SKIP))))
    print("banks:", dict(collections.Counter(r["bank"] for r in ports)))
    dd = d.replace("\\", "/")
    out = os.path.join(ROOT, "vivado")
    os.makedirs(out, exist_ok=True)
    oo = out.replace("\\", "/")
    open(os.path.join(d, "run.tcl"), "w").write("\n".join([
        "read_verilog %s/zulu_a7_top.v" % dd,
        "read_xdc %s/zulu_a7_pins.xdc" % dd,
        "synth_design -top zulu_a7_top -part %s" % PART,
        "opt_design", "place_design",
        "report_drc -ruledecks {default placer_checks bitstream_checks} -file %s/drc.rpt" % dd,
        # the I/O Planner's own outputs, kept in the repo
        "report_io -file %s/zulu_a7_io.rpt" % oo,
        "write_csv -force %s/zulu_a7_io.csv" % oo,
        "report_clock_utilization -file %s/zulu_a7_clocks.rpt" % oo,
        'puts "IOCHECK DONE"']) + "\n")
    print("running Vivado (synth -> opt -> place -> drc), this takes a couple of minutes...")
    r = subprocess.run(["vivado", "-mode", "batch", "-nojournal", "-nolog", "-notrace",
                        "-source", os.path.join(d, "run.tcl")], cwd=d,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
    log = r.stdout + r.stderr
    open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(log)
    errs = [l for l in log.splitlines() if l.startswith(("ERROR", "CRITICAL WARNING"))]
    warns = [l for l in log.splitlines() if l.startswith("WARNING")]
    print()
    for l in errs:
        print("  ****  " + l)
    for l in warns[:10]:
        print("  warn  " + l)
    if "IOCHECK DONE" in log and not errs:
        print("  PASS  synth, opt and place all completed on this ball assignment")
    # RTSTAT-12 only says the stub was never routed, which is expected
    rpt = os.path.join(d, "drc.rpt")
    if os.path.exists(rpt):
        body = open(rpt, encoding="utf-8", errors="replace").read()
        rules = re.findall(r"^\| (\w+-\d+)\s*\| (\w+)\s*\| (.*?)\s*\|\s*(\d+) \|", body, re.M)
        real = [x for x in rules if x[0] != "RTSTAT-12"]
        print("\nDRC after placement: %d check(s)%s"
              % (len(real), "" if real else "  (RTSTAT-12 'unrouted' excluded -- the stub is never routed)"))
        for x in real:
            print("   %-12s %-9s %s x%s" % x)
    if not errs:
        for f in ("zulu_a7_top.v", "zulu_a7_pins.xdc"):
            shutil.copyfile(os.path.join(d, f), os.path.join(out, f))
        print("\nI/O planner output, kept in the repo:")
        for f in ("zulu_a7_io.rpt", "zulu_a7_io.csv", "zulu_a7_clocks.rpt", "zulu_a7_pins.xdc", "zulu_a7_top.v"):
            q = os.path.join(out, f)
            print("   %-22s %s" % (f, ("%7.1f kB" % (os.path.getsize(q) / 1024.0))
                                    if os.path.exists(q) else "MISSING"))
    print("\nworking files in", d)
    return len(errs)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "zulu_a7.sch")))
