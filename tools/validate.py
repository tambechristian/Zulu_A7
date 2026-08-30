# -*- coding: utf-8 -*-
"""Whole-schematic validation for zulu_a7.sch.

Everything this project has learned to check, in one runnable place. Each
section prints PASS or the findings; the exit code is the number of findings
so it can gate a commit.

    python tools/validate.py [path/to/file.sch]
"""
import re, io, os, sys, collections, itertools

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PINOUT = os.path.normpath(os.path.join(ROOT, "Datasheet", "xc7a35tcpg236pkg_pinout.txt"))
findings = []


def head(s):
    print("\n" + s + "\n" + "-" * len(s))


def ok(s):
    print("  PASS  " + s)


def bad(s):
    findings.append(s)
    print("  ****  " + s)


def rp(dx, dy, rot):
    r = re.sub(r"^M", "", rot or "R0")
    x, y = {"R0": (dx, dy), "R90": (-dy, dx), "R180": (-dx, -dy), "R270": (dy, -dx)}[r]
    return (-x, y) if (rot or "").startswith("M") else (x, y)


def main(path):
    t = open(path, encoding="utf-8").read()
    SYM = {m.group(1): m.group(2) for m in re.finditer(r'<symbol name="([^"]+)">(.*?)</symbol>', t, re.S)}
    SYMPINS = {k: [(q.group(1), float(q.group(2)), float(q.group(3)))
                   for q in re.finditer(r'<pin name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', v)]
               for k, v in SYM.items()}
    PKG = {m.group(1): m.group(2) for m in re.finditer(r'<package name="([^"]+)">(.*?)</package>', t, re.S)}
    PARTS = {m.group(1): (m.group(2), m.group(3), m.group(4)) for m in re.finditer(
        r'<part name="([^"]+)" library="([^"]+)" deviceset="([^"]+)" device="([^"]*)"', t)}
    GATES, CONN = {}, {}
    for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', t, re.S):
        GATES[dm.group(1)] = dict(re.findall(r'<gate name="([^"]+)" symbol="([^"]+)"', dm.group(2)))
        for dv in re.finditer(r'<device name="([^"]*)"(?: package="([^"]*)")?>(.*?)</device>', dm.group(2), re.S):
            CONN[(dm.group(1), dv.group(1))] = (dv.group(2), re.findall(
                r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', dv.group(3)))
    NET = collections.defaultdict(set)
    for m in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', t, re.S):
        NET[m.group(1)].update(re.findall(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', m.group(2)))
    SHEETS = re.findall(r"<sheet name[^>]*>.*?</sheet>", t, re.S)

    head("1. Structure")
    names = re.findall(r'<sheet name="([^"]*)">', t)
    (ok if len(names) == len(SHEETS) else bad)("%d sheets, all named: %s" % (len(SHEETS), ", ".join(names)))
    I = set(re.findall(r'<instance part="([^"]+)"', t))
    (ok if set(PARTS) == I else bad)("parts == instances (%d)" % len(PARTS))
    if set(PARTS) != I:
        bad("  part/instance mismatch: %s" % sorted(set(PARTS) ^ I))
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(t)
        ok("XML parses")
    except Exception as e:
        bad("XML: %s" % e)

    # Exact-duplicate children draw on top of themselves. The XESS symbols
    # shipped with four identical ">GATE" texts and repeated arrow polygons, so
    # every pin name on X2, U1 and U4 rendered four times over -- visible as
    # bold, slightly ragged text -- and smashed instances carried four identical
    # <attribute> overrides to match. 184 of them, ~15 kB, and no way to see the
    # cause from the drawing. Nothing here should ever legitimately repeat: two
    # identical elements at identical coordinates are always redundant.
    EL = (r'<polygon\b.*?</polygon>|<text\b[^>]*>.*?</text>'
          r'|<(?:wire|pin|circle|rectangle|attribute)\b[^>]*/>')
    dups = []
    for kind, pat in (("symbol", r'<symbol name="([^"]+)">(.*?)</symbol>'),
                      ("instance", r'<instance part="([^"]+)" gate="[^"]+"[^>]*>(.*?)</instance>')):
        for m in re.finditer(pat, t, re.S):
            c = collections.Counter(" ".join(q.group(0).split())
                                    for q in re.finditer(EL, m.group(2), re.S))
            n = sum(v - 1 for v in c.values() if v > 1)
            if n:
                dups.append("%s %s x%d" % (kind, m.group(1), n))
    (ok if not dups else bad)(
        "no symbol or instance repeats an identical element" if not dups else
        "%d place(s) draw an element on top of itself: %s"
        % (len(dups), sorted(set(dups))[:6]))

    head("2. Library integrity  (connect <-> symbol pin <-> package pad)")
    n = 0
    for ds, gs in GATES.items():
        for (d, dv), (pk, cons) in CONN.items():
            if d != ds:
                continue
            pads = set(re.findall(r'<(?:pad|smd) name="([^"]+)"', PKG[pk])) if pk else None
            for gt, pn, pd in cons:
                if pn not in {p for p, _x, _y in SYMPINS.get(gs.get(gt, ""), [])}:
                    bad("%s.%s pin %s not in symbol" % (ds, gt, pn)); n += 1
                if pads is not None:
                    for one in pd.split():
                        if one not in pads:
                            bad("%s pad %s not in %s" % (ds, one, pk)); n += 1
    if not n:
        ok("every connect resolves to a real symbol pin and a real package pad")

    head("3. Connectivity")
    thin = sorted(k for k, v in NET.items() if len(v) < 2)
    (ok if not thin else bad)("no net has fewer than two pins" if not thin else "nets under two pins: %s" % thin)
    orph = sorted(k for k in NET if re.fullmatch(r"N\$\d+", k))
    (ok if not orph else bad)("no auto-named orphan nets" if not orph else "orphan autonames: %s" % orph)
    connected = {(p, gt, pn) for s in NET.values() for p, gt, pn in s}
    unconn = []
    for part, (lib, ds, dv) in PARTS.items():
        pk, cons = CONN.get((ds, dv), (None, []))
        for gt, sym in GATES.get(ds, {}).items():
            for pn, _x, _y in SYMPINS.get(sym, []):
                if (part, gt, pn) not in connected:
                    unconn.append("%s.%s.%s" % (part, gt, pn))
    # Pins that are meant to float. Listed with the reason, so the check fires on
    # something NEW coming loose instead of always failing and being ignored.
    # (part, gate, pin, why). The GATE matters: U1 is modelled one gate per
    # ball and every one of its pins is named "1", so a rule keyed on the pin
    # name alone matches all 238 of them and would wave through any ball that
    # came loose. Naming the gates keeps this a check rather than a rubber stamp.
    NC_OK = [
        (r"^U2$", r".*", r"^(ACBUS[0-7]|BCBUS[0-7]|ADBUS[67]|BDBUS[567])$",
         "unused FT2232HQ GPIO"),
        (r"^U2$", r".*", r"^OSCO$", "NC in external-oscillator mode, DS_FT2232H 6.3"),
        (r"^U2$", r".*", r"^SUSPEND#$", "unused"),
        (r"^U1$", r"^(MGTPTX[NP][01]|MGTREFCLK[01][NP])$", r"^1$",
         "GTP transmit and refclk, unused transceivers left open per UG482"),
        (r"^R[124]$", r".*", r"^[12]$", "spare element in a resistor pack"),
        (r"^U10$", r".*", r"^NC(@\d+)?$", "93LC46B pins 6 and 7, both no-connect on the fixed-x16 part"),
        (r"^U3$", r".*", r"^P\$1$", "pin 40 is a no-connect on the TSOP-II 54 die"),
        (r"^X1$", r".*", r"^4$", "micro-USB ID pin, unused"),
    ]

    def allowed(part, gate, pin):
        for pp, gg, qq, _why in NC_OK:
            if re.match(pp, part) and re.match(gg, gate) and re.match(qq, pin):
                return True
        return False

    unexpected = [u for u in unconn if not allowed(*u.split(".", 2))]
    if unexpected:
        by = collections.Counter(u.split(".")[0] for u in unexpected)
        bad("%d unexpected unconnected pins: %s"
            % (len(unexpected), ", ".join("%s x%d" % kv for kv in by.most_common(12))))
        for u in unexpected[:20]:
            bad("   " + u)
    else:
        ok("every pin is on a net, or on the intentional-NC list (%d pins: %s)"
           % (len(unconn), ", ".join("%s x%d" % kv for kv in
                                     collections.Counter(u.split(".")[0] for u in unconn).most_common())))

    head("4. U1 power and ground")
    if os.path.exists(PINOUT):
        rows = {}
        for l in open(PINOUT, encoding="utf-8", errors="replace"):
            p = l.split()
            if len(p) >= 8 and re.fullmatch(r"[A-Y]\d{1,2}", p[0]):
                rows[p[0]] = {"name": p[1], "bank": p[3], "io": p[-2], "nc": p[-1]}
        pk, cons = CONN[("XC7A35T-CPG236", PARTS["U1"][2])]
        g2b = {(gt, pn): pd for gt, pn, pd in cons}
        netof = {}
        for nname, s in NET.items():
            for p, gt, pn in s:
                if p == "U1":
                    netof[(gt, pn)] = nname
        EXPECT = [("VCCINT", "VCC1V0"), ("VCCBRAM", "VCC1V0"), ("VCCAUX", "VCC1V8"),
                  ("VCCBATT", "VCC1V8"), ("VCCO_0", "VCC3V3"), ("VCCO_14", "VCC3V3"),
                  ("VCCO_16", "VCC3V3"), ("VCCO_34", "VCC3V3"), ("VCCO_35", "VCC3V3")]
        for prefix, want in EXPECT:
            got = {netof.get(k) for k in g2b if k[1].startswith(prefix)}
            cnt = sum(1 for k in g2b if k[1].startswith(prefix))
            if got == {want}:
                ok("%-9s x%-2d -> %s" % (prefix, cnt, want))
            else:
                bad("%-9s x%-2d -> %s   (expected %s)" % (prefix, cnt, sorted(got), want))
        missing = [(gt, pn) for (gt, pn), pd in g2b.items()
                   if rows.get(pd, {}).get("name", "").startswith(("VCC", "GND")) and (gt, pn) not in netof]
        (ok if not missing else bad)("every VCC/GND ball on the die is connected"
                                     if not missing else "unconnected supply balls: %s" % missing)
        used = {pd: netof[k] for k, pd in g2b.items() if k in netof}
        notin = [b for b in used if b not in rows]
        nc = [b for b in used if b in rows and rows[b]["nc"] != "NA"]
        (ok if not notin and not nc else bad)(
            "all %d driven balls exist in the Xilinx pinout and none is No-Connect" % len(used)
            if not notin and not nc else "bad balls: %s %s" % (notin, nc))
        free = sorted(set(rows) - set(used))
        hr = [b for b in free if rows[b]["io"] == "HR"]
        ok("%d of %d balls driven; the %d spare are %s; free general I/O: %d"
           % (len(used), len(rows), len(free),
              ",".join(sorted({rows[b]["io"] for b in free})) or "-", len(hr)))
    else:
        bad("Xilinx pinout file not found at %s" % PINOUT)

    head("5. Decoupling vs UG483 Table 2-2 (CPG236 / XC7A35T)")
    VAL = {m.group(1): m.group(2) for m in re.finditer(r'<part name="([^"]+)"[^>]*value="([^"]*)"', t)}
    sh7 = SHEETS[6]
    # VCC1V0's bulk was one 100uF 1210 until the back-side height budget ruled it
    # out: 2.50 mm against a 2.54 mm header standoff. Two 47uF 1206 at 1.60 mm
    # replace it, so the bulk reads 3 x 47uF (C85 + C140 on the VCCINT row, C86
    # on the VCCBRAM row) and drops from 147uF to 141uF. See board/STACKUP.md.
    for net, want in (("VCC1V0", {"47uF": 3, "4.7uF": 2, "0.47uF": 4}),
                      ("VCC1V8", {"47uF": 1, "4.7uF": 1, "0.47uF": 2}),
                      ("VCC3V3", {"47uF": 2, "4.7uF": 8, "0.47uF": 16})):
        m = re.search(r'<net name="%s" class="[^"]*">(.*?)</net>' % net, sh7, re.S)
        cs = re.findall(r'<pinref part="(C\d+)" gate="G\$1" pin="1"/>', m.group(1)) if m else []
        got = collections.Counter(VAL.get(c, "?") for c in cs)
        got = {k: v for k, v in got.items() if k in want or k in ("100uF", "47uF", "4.7uF", "0.47uF")}
        (ok if got == want else bad)("%-7s on sheet 7: %s" % (net, dict(sorted(got.items()))) +
                                     ("" if got == want else "   expected %s" % want))

    head("6. Geometry")
    tot = 0
    for si, sh in enumerate(SHEETS, 1):
        pins = set()
        for m in re.finditer(r'<instance part="([^"]+)" gate="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"([^>]*)>', sh):
            ix, iy = float(m.group(3)), float(m.group(4))
            rot = (re.search(r'rot="(M?R\d+)"', m.group(5)) or [None, None])[1]
            for pn, px, py in SYMPINS.get(GATES.get(PARTS.get(m.group(1), ("", "", ""))[1], {}).get(m.group(2), ""), []):
                dx, dy = rp(px, py, rot)
                pins.add((round(ix + dx, 2), round(iy + dy, 2)))
        for nm in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', sh, re.S):
            W, J = [], set()
            for sg in re.finditer(r"<segment>(.*?)</segment>", nm.group(2), re.S):
                W += [tuple(map(float, q.groups())) for q in re.finditer(
                    r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', sg.group(1))]
                J |= {(round(float(q.group(1)), 2), round(float(q.group(2)), 2))
                      for q in re.finditer(r'<junction x="([-\d.]+)" y="([-\d.]+)"/>', sg.group(1))}
            pts = collections.Counter()
            for a, b, c, d in W:
                pts[(round(a, 2), round(b, 2))] += 1
                pts[(round(c, 2), round(d, 2))] += 1
            # ends, pins and existing dots -- a pin landing on a rail has E=0
            need = set()
            for p in set(pts) | {q for q in pins} | set(J):
                cnt = pts[p]
                th = sum(1 for a, b, c, d in W
                         if (round(a, 2), round(b, 2)) != p and (round(c, 2), round(d, 2)) != p
                         and ((abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6 and min(a, c) < p[0] < max(a, c))
                              or (abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6 and min(b, d) < p[1] < max(b, d))))
                if cnt + 2 * th + (1 if p in pins else 0) >= 3:
                    need.add(p)
            if need - J:
                bad("s%d %s missing %d junction(s): %s" % (si, nm.group(1), len(need - J), sorted(need - J)[:4]))
                tot += 1
    if not tot:
        ok("no missing junctions on any sheet")
    stray = 0
    for si, sh in enumerate(SHEETS, 1):
        for nm in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', sh, re.S):
            stray += 0
    # endpoint of one net landing on another net's wire
    cross = 0
    for si, sh in enumerate(SHEETS, 1):
        nets = {}
        for nm in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', sh, re.S):
            nets[nm.group(1)] = [tuple(map(float, q.groups())) for q in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="[\d.]+" layer="91"/>',
                nm.group(2))]
        for na, wa in nets.items():
            pts = {(round(w[0], 2), round(w[1], 2)) for w in wa} | {(round(w[2], 2), round(w[3], 2)) for w in wa}
            for nb, wb in nets.items():
                if na == nb:
                    continue
                for p in pts:
                    for a, b, c, d in wb:
                        onit = ((abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6 and min(a, c) - 1e-6 <= p[0] <= max(a, c) + 1e-6)
                                or (abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6 and min(b, d) - 1e-6 <= p[1] <= max(b, d) + 1e-6))
                        if onit:
                            bad("s%d: %s endpoint %s lies on a %s wire" % (si, na, p, nb)); cross += 1
    if not cross:
        ok("no wire endpoint of one net lands on another net's wire")

    head("7. Housekeeping")
    dup = [k for k, v in collections.Counter(re.findall(r'<part name="([^"]+)"', t)).items() if v > 1]
    (ok if not dup else bad)("no duplicate refdes" if not dup else "duplicate refdes: %s" % dup)
    noval = sorted(p for p in PARTS if re.fullmatch(r"[CRLD]\d+", p) and p not in VAL)
    (ok if not noval else bad)("every passive carries a value" if not noval else "no value: %s" % noval)
    tol = [r for r in PARTS if re.fullmatch(r"R\d+", r) and r in VAL
           and re.match(r"^\d+(\.\d+)?K?$", VAL[r].strip()) is None and "%" in VAL[r]]
    fb = [r for r in ("R66", "R69", "R73") if r in VAL and "%" not in VAL[r]]
    (ok if not fb else bad)("feedback dividers carry a tolerance"
                            if not fb else "feedback resistors with no tolerance: %s"
                            % ", ".join("%s=%s" % (r, VAL[r]) for r in fb))
    # The X2 note on sheet 3 describes the header in prose, and prose does not
    # follow the pinout when the pinout moves. It had drifted to claiming 37
    # pins on a 53.34 x 25.40 board with one ground, three of which were wrong
    # by two separate revisions, while sitting on the sheet where whoever routes
    # this reads it. These are the numbers in it that the design can contradict.
    note = next((m.group(1) for m in re.finditer(r'<text [^>]*layer="97">(X2: .*?)</text>', t, re.S)), None)
    if note is None:
        bad("the X2 pinout note is gone from sheet 3")
    else:
        pk = re.search(r'<package name="ZULU-DIP37">.*?</package>', t, re.S).group(0)
        pad = {int(m.group(1)): (float(m.group(2)), float(m.group(3)))
               for m in re.finditer(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', pk)}
        ds = re.search(r'<deviceset name="ZULU-CONN".*?</deviceset>', t, re.S).group(0)
        p2g = {int(pd): g for g, _pn, pd in
               re.findall(r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', ds)}
        xnet = {}
        for m in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', t, re.S):
            for pp, g, _pn in re.findall(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', m.group(2)):
                if pp == "X2":
                    xnet[g] = m.group(1)
        rows = collections.Counter(y for _x, y in pad.values())
        gnd = sorted(n for n in pad if xnet.get(p2g[n]) == "GND")
        topx = sorted((x for n, (x, y) in pad.items() if y == max(rows)), reverse=True)
        gapx = sorted({round(topx[8] - 2.54 * k, 2) for k in range(1, 5)}, reverse=True)
        claims = [
            ("pin count", r"(\d+) pins on a", str(len(pad))),
            # rows is keyed by y, so rows[max(rows)] is the TOP row's pad count --
            # not max(rows.values()), which is whichever row happens to be larger
            ("row numbering", r"top row 1-(\d+), bottom row (\d+)-(\d+)",
             "%d,%d,%d" % (rows[max(rows)], rows[max(rows)] + 1, len(pad))),
            ("ground pins", r"grounds: pins ([\d, ]+?)\.", ", ".join(str(n) for n in gnd)),
            ("USB positions", r"-- x ([\d., ]+?) --", ", ".join("%g" % v for v in gapx)),
            ("USB clear", r"in ([\d.]+) mm clear", "%.3f" % ((topx[8] - 0.762) - (topx[9] + 0.762))),
        ]
        wrong = []
        for what, pat, want in claims:
            m = re.search(pat, note)
            got = ",".join(g.strip() for g in m.groups()) if m else None
            if got != want:
                wrong.append("%s: note says %r, design says %r" % (what, got, want))
        (ok if not wrong else bad)(
            "the X2 note on sheet 3 matches the pinout (%d claims checked)" % len(claims)
            if not wrong else "the X2 note is stale -- " + "; ".join(wrong))

    print("\n" + "=" * 62)
    print("%d finding(s)" % len(findings))
    return len(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "zulu_a7.sch")))
