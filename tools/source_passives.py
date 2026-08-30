# -*- coding: utf-8 -*-
"""Put MANF / MANF# / SPEC on every passive in zulu_a7.sch.

    python tools/source_passives.py [--apply]

Without --apply it only reports. Re-running is safe: parts that already
carry a MANF# are left alone, so hand-picked parts are never overwritten.

WHY THIS IS A TOOL AND NOT A ONE-OFF EDIT. A value alone does not describe
a part. "47uF" says nothing about dielectric, voltage rating or thickness,
and thickness is what decides whether the board fits a breadboard --
board/STACKUP.md has the budget, and a 1206 that arrives 1.9 mm thick
instead of 1.6 breaks it. Encoding the choice here means the reasoning is
visible, the numbering scheme can be checked, and a mistake is systematic
rather than scattered through 900 kB of XML.

MANF# VALUES ARE DERIVED FROM PUBLISHED PART-NUMBERING SCHEMES, NOT FROM A
LIVE CATALOGUE. Check stock and the exact suffix before ordering; the
suffix encodes thickness and packaging and is the easiest thing to get
wrong. The SPEC attribute carries the requirement that actually matters,
so an equivalent from another vendor is a safe substitution as long as it
meets SPEC. SPEC is the specification; MANF# is one part that meets it.

Resistors are Yageo RC thick film. The scheme is
RC<size><F=1%|J=5%>R-07<code>L, where the code marks the decimal with the
multiplier letter: 100R, 4K7, 2K21, 57K6, 0R. Every resistor is specified
at 1% -- in 0402 thick film it costs the same as 5%, and several values in
this design (2.21k, 2.32K, 845, 182, 140, 57.6K, 3.48K) are E96-only and
could never have been 5% anyway. The one exception is the 0 ohm jumper,
which is always a J part.
"""

import re, io, os, sys, collections

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCH = os.path.join(ROOT, "zulu_a7.sch")

# (MANF#, SPEC) by package and value. Voltage ratings allow for MLCC DC-bias
# derating: a 6.3 V X5R on a 3.3 V rail keeps roughly half its capacitance,
# which the LTC3569 datasheet p16 explicitly asks for ("retain at least 50%
# of rated capacitance over temperature and bias voltage").
CAPS = {
    ("C0402", "20pF"):   ("GRM1555C1H200JA01D",  "C0G 50V +-5%, 0.50 mm max -- C0G for the feedback feedforward"),
    ("C0402", "1nF"):    ("GRM155R71H102KA01D",  "X7R 50V +-10%, 0.50 mm max"),
    ("C0402", "0.01uF"): ("GRM155R71H103KA88D",  "X7R 50V +-10%, 0.50 mm max"),
    ("C0402", "0.1uF"):  ("GRM155R71C104KA88D",  "X7R 16V +-10%, 0.50 mm max"),
    ("C0402", "100nF"):  ("GRM155R71C104KA88D",  "X7R 16V +-10%, 0.50 mm max -- same part as the 0.1uF line"),
    ("C0402", "0.47uF"): ("GRM155R61C474KA88D",  "X5R 16V +-10%, 0.50 mm max"),
    ("C0402", "470nF"):  ("GRM155R61C474KA88D",  "X5R 16V +-10%, 0.50 mm max -- same part as the 0.47uF line"),
    ("C0402", "3.3uF"):  ("GRM155R60J335ME15D",  "X5R 6.3V +-20%, 0.50 mm max -- FT2232H VCORE, DS_FT2232H asks for 3.3uF"),
    ("C0603", "4.7uF"):  ("GRM188R61A475KE15D",  "X5R 10V +-10%, 0.90 mm max"),
    ("C0603", "10uF"):   ("GRM188R60J106ME47D",  "X5R 6.3V +-20%, 0.90 mm max"),
    ("C1206", "47uF"):   ("GRM31CR60J476ME19L",  "X5R 6.3V +-20%, 1.60 mm MAX -- back side, see board/STACKUP.md"),
    # LTC3569 input and output capacitors, repackaged out of 0402 where the
    # values were not manufacturable. 10V on the 0805s: C78 sits on the 5V USB
    # rail, and a 10V X5R at 5V bias still keeps roughly half its capacitance,
    # which is what the datasheet p16 asks for.
    ("C0805", "22uF"):   ("GRM21BR61A226ME44L",  "X5R 10V +-20%, 1.45 mm max -- LTC3569 COUT buck 1"),
    ("C0805", "22uF 10V"): ("GRM21BR61A226ME44L", "X5R 10V +-20%, 1.45 mm max -- LTC3569 CIN on VU (5V USB)"),
}
# Ferrite beads and power inductors. The three DFE parts replace 0603s that
# could not meet the LTC3569 p15 rule -- a DC rating of at least 1.5x the load
# current. Required: 1.8A on buck 1 (1.2A), 0.9A on bucks 2 and 3 (600mA each).
INDS = {
    ("IND0603", "FB 600R@100MHz"): ("BLM18PG601SN1D",     "600 ohm at 100MHz, 1.5A, 0.90 mm max"),
    ("IND2520", "1.5uH"):          ("DFE252010P-1R5M=P2", "1.5uH +-20%, Idc >=1.8A REQUIRED, 1.00 mm max -- SW1, 1.2A buck"),
    ("IND2520", "2.2uH"):          ("DFE252010P-2R2M=P2", "2.2uH +-20%, Idc >=0.9A REQUIRED, 1.00 mm max -- SW3, 600mA buck"),
    ("IND2520", "3.3uH"):          ("DFE252010P-3R3M=P2", "3.3uH +-20%, Idc >=0.9A REQUIRED, 1.00 mm max -- SW2, 600mA buck"),
}

# Sourced elsewhere or not a passive; left alone entirely.
SKIP_PKG = re.compile(r"^(CC_|LED0603|SOD123|SOT|TSOPII|SOIC|XC7A35T|FT2232|LTC3569|MOLEX|PTA|VS-|ZULU|2X0|32X25|742C083)")

# Parts that cannot be sourced as drawn. Each is reported, none is given a
# MANF#, because inventing one would paper over a real defect.
# Nothing is blocked. The seven parts that used to sit here -- C78, C80, C82,
# C84 in 0402 and L1-L3 in 0603 -- were repackaged to 0805, 0603 and IND2520
# once the packages, not the values, turned out to be the defect.
BLOCKED = {}


def block(t, name):
    """The whole <part> element for `name`.

    Not a regex: `<part ...>.*?(/>|</part>)` stops at the first `/>`, which
    for a part that already has attributes is an inner <attribute/> -- so the
    block comes back truncated, the MANF# check misses, and on --apply the
    replacement writes a mangled element. Find the end of the opening tag
    first, then decide.
    """
    i = t.index('<part name="%s" ' % name)
    j = t.index(">", i)
    return t[i:j + 1] if t[j - 1] == "/" else t[i:t.index("</part>", j) + 7]


def rcode(v):
    """Yageo value code: 100 -> 100R, 4.7K -> 4K7, 2.21k -> 2K21, 0 -> 0R."""
    m = re.match(r"^([\d.]+)\s*([kKmM]?)$", v.strip())
    if not m:
        return None
    num, mult = m.group(1), m.group(2).upper()
    if float(num) == 0:
        return "0R"
    letter = mult if mult else "R"
    if "." in num:
        a, b = num.split(".")
        return a + letter + b.rstrip("0")
    return num + letter if letter != "R" else num + "R"


def main(apply_it):
    t = open(SCH, encoding="utf-8").read()
    dev = {}
    for lib in re.finditer(r'<library name="([^"]+)">(.*?)</library>', t, re.S):
        for ds in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', lib.group(2), re.S):
            for d in re.finditer(r'<device name="([^"]*)"(?: package="([^"]+)")?', ds.group(2)):
                dev[(lib.group(1), ds.group(1), d.group(1))] = d.group(2)

    plan, blocked, already, skipped = [], [], [], 0
    for m in re.finditer(r'<part name="([^"]+)" library="([^"]+)" deviceset="([^"]+)" device="([^"]*)"'
                         r'(?: value="([^"]*)")?\s*(/>|>)', t):
        name, lib, dset, d, val = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or ""
        pkg = dev.get((lib, dset, d))
        if not pkg or SKIP_PKG.match(pkg):
            skipped += 1
            continue
        if name in BLOCKED:
            blocked.append((name, val, pkg))
            continue
        if 'name="MANF#"' in block(t, name):
            already.append(name)
            continue
        if pkg.startswith("R0"):
            code = rcode(re.sub(r"\s*1%$", "", val))
            if code is None:
                continue
            tol = "J" if code == "0R" else "F"
            mpn = "RC%s%sR-07%sL" % (pkg[1:], tol, code)
            spec = ("0 ohm jumper, 0402" if code == "0R"
                    else "thick film +-1%%, 1/16W, %s" % ("0402" if pkg == "R0402" else "0603"))
            plan.append((name, val, pkg, "Yageo", mpn, spec))
        elif (pkg, val) in CAPS:
            mpn, spec = CAPS[(pkg, val)]
            plan.append((name, val, pkg, "Murata", mpn, spec))
        elif (pkg, val) in INDS:
            mpn, spec = INDS[(pkg, val)]
            plan.append((name, val, pkg, "Murata", mpn, spec))
    print("  %d passives to source, %d already carry a MANF#, %d blocked, %d not passives\n"
          % (len(plan), len(already), len(blocked), skipped))
    by = collections.defaultdict(list)
    for name, val, pkg, mf, mpn, spec in plan:
        by[(pkg, val, mf, mpn, spec)].append(name)
    print("  %-8s %-16s %-22s %-4s  %s" % ("package", "value", "MANF#", "qty", "refdes"))
    print("  " + "-" * 108)
    for (pkg, val, mf, mpn, spec), ns in sorted(by.items()):
        print("  %-8s %-16s %-22s x%-3d %s" % (pkg, val, mpn, len(ns), ", ".join(sorted(ns))[:44]))
    if blocked:
        print("\n  NOT SOURCED -- these cannot be built as drawn:")
        for n, v, pkg in sorted(blocked):
            print("    %-4s %-10s %-9s %s" % (n, v, pkg, BLOCKED[n]))
    # Two spellings of one value split a BOM line in two for no reason. The
    # MANF# collapses them again, but the schematic still reads inconsistently.
    variants = collections.defaultdict(set)
    for name, val, pkg, mf, mpn, spec in plan:
        variants[mpn].add(val)
    dupes = {m: sorted(v) for m, v in variants.items() if len(v) > 1}
    if dupes:
        print("\n  same part, spelled more than one way in the value field:")
        for m, v in sorted(dupes.items()):
            print("    %-22s %s" % (m, " / ".join(v)))
        print("    harmless electrically -- the MANF# unifies them -- but the schematic reads")
        print("    inconsistently and a BOM grouped by value would show them as separate lines.")

    if not apply_it:
        print("\n  report only; re-run with --apply to write them into the schematic")
        return 0
    for name, val, pkg, mf, mpn, spec in plan:
        old = block(t, name)
        attrs = ('<attribute name="MANF" value="%s"/>'
                 '<attribute name="MANF#" value="%s"/>'
                 '<attribute name="SPEC" value="%s"/>' % (mf, mpn, spec))
        new = (old[:-2] + ">" + attrs + "</part>") if old.endswith("/>") else old.replace("</part>", attrs + "</part>")
        t = t.replace(old, new, 1)
    open(SCH, "w", encoding="utf-8").write(t)
    print("\n  wrote %s -- %d parts given MANF / MANF# / SPEC" % (SCH, len(plan)))
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
