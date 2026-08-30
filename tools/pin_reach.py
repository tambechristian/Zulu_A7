# -*- coding: utf-8 -*-
"""Every pinref must have a wire of its own net actually touching the pin.

WHY THIS IS A SEPARATE CHECK. The netlist diff that gates every schematic edit
here reads <pinref> elements. A pinref is a claim, not a connection: Eagle
writes it when the wire is drawn and keeps it afterwards even if the wire is
later moved, shortened or deleted. So a net can lose a pin geometrically while
the diff -- and ERC, and junction_audit -- all report nothing wrong.

That is the defect behind "net has fallen apart". Two instances found on
2026-08-29:

  * HEAD itself had EN_BIAS reaching for Q3.A.C with a dog-leg ending at
    (45.72,133.35). The pin is at (46.99,133.35). It missed by 1.27 mm, one
    grid step, and had presumably done so for as long as that net existed.
  * fix_export.py then deleted the one wire reaching that same pin, believing
    it was a stacked duplicate because it had been one in the previous export.
    Netlist diff: no change. Junction audit: clean. validate: 0 findings.

A pin is reached if a wire of its net ends on it or passes through it -- the
same predicate junction_audit uses for the T term, minus the dot requirement.

SCOPE IS THE WHOLE NET ON THE SHEET, NOT THE SEGMENT. The first cut of this
file tested each pinref against the wires of its own <segment> and reported
GND4 on sheet 3 as unreachable. It is not: its pin at (227.33,100.33) is a
three-wire node on the sheet-3 ground rail with a junction on it. The export
had simply left its pinref alone in a wire-less segment while the wires sat in
another one. Segments are a drawing grouping that Eagle re-derives from
geometry on load, so scoping to them invents faults that are not there --
and very nearly cost a working ground symbol its place on the rail.

Wire-less segments are still worth knowing about, so they are reported
separately as an anomaly. They do not gate.

    python tools/pin_reach.py           check zulu_a7.sch
    python tools/pin_reach.py <file>    check any exported copy
"""
import io
import os
import re
import sys

_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "zulu_a7.sch")


def rp(dx, dy, rot):
    r = re.sub(r"^M", "", rot or "R0")
    x, y = {"R0": (dx, dy), "R90": (-dy, dx),
            "R180": (-dx, -dy), "R270": (dy, -dx)}[r]
    return (-x, y) if (rot or "").startswith("M") else (x, y)


def main():
    t = io.open(SCH, encoding="utf-8", errors="replace").read()
    sym = {m.group(1): m.group(2)
           for m in re.finditer(r'<symbol name="([^"]+)">(.*?)</symbol>', t, re.S)}
    sp = {k: [(q.group(1), float(q.group(2)), float(q.group(3)))
              for q in re.finditer(r'<pin name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', v)]
          for k, v in sym.items()}
    gate = {}
    for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', t, re.S):
        for a, s in re.findall(r'<gate name="([^"]+)" symbol="([^"]+)"', dm.group(2)):
            gate[(dm.group(1), a)] = s
    ds = {m.group(1): m.group(2) for m in re.finditer(
        r'<part name="([^"]+)" library="[^"]+" deviceset="([^"]+)"', t)}

    sheets = re.findall(r"<sheet name[^>]*>.*?</sheet>", t, re.S)
    if not sheets:
        print("!! no named sheets -- run tools/restore_sheet_names.py first")
        return 1
    bad = 0
    lone = []
    for si, sh in enumerate(sheets, 1):
        # every pin of every instance, by (part, gate, pin)
        at = {}
        for m in re.finditer(r'<instance part="([^"]+)" gate="([^"]+)" x="([-\d.]+)"'
                             r' y="([-\d.]+)"([^>]*)>', sh):
            ix, iy = float(m.group(3)), float(m.group(4))
            rot = (re.search(r'rot="(M?R\d+)"', m.group(5)) or [None, None])[1]
            for pn, px, py in sp.get(gate.get((ds.get(m.group(1), ""), m.group(2)), ""), []):
                dx, dy = rp(px, py, rot)
                at[(m.group(1), m.group(2), pn)] = (round(ix + dx, 2), round(iy + dy, 2))
        for nm in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', sh, re.S):
            segs = re.findall(r"<segment>(.*?)</segment>", nm.group(2), re.S)
            wl = [tuple(map(float, q.groups())) for sg in segs for q in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                r' width="[\d.]+" layer="91"/>', sg)]
            for sg in segs:
                if not re.search(r"<wire", sg) and re.search(r"<pinref", sg):
                    lone.append("s%d %s %s" % (si, nm.group(1), ", ".join(
                        "%s.%s.%s" % q for q in re.findall(
                            r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', sg))))
            for pr in re.finditer(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>',
                                  nm.group(2)):
                kk = (pr.group(1), pr.group(2), pr.group(3))
                p = at.get(kk)
                if p is None:
                    continue              # off-sheet or supply, not our business
                ok = False
                for a, b, c, d in wl:
                    if (round(a, 2), round(b, 2)) == p or (round(c, 2), round(d, 2)) == p:
                        ok = True
                        break
                    if (abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6
                            and min(a, c) <= p[0] <= max(a, c)):
                        ok = True
                        break
                    if (abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6
                            and min(b, d) <= p[1] <= max(b, d)):
                        ok = True
                        break
                if not ok:
                    near = min([(abs(p[0] - x) + abs(p[1] - y), (x, y))
                                for a, b, c, d in wl
                                for x, y in ((a, b), (c, d))] or [(0, None)])
                    print("  ****  s%d %-12s %s.%s.%s at %s -- no wire reaches it"
                          "%s" % (si, nm.group(1), kk[0], kk[1], kk[2], p,
                                  "; nearest wire end %s is %.2f mm away"
                                  % (near[1], near[0]) if near[1] else ""))
                    bad += 1
    for q in lone:
        print("  note  %s -- pinref in a segment with no wires; Eagle's"
              " own re-derive merges it, so this is drawing structure,"
              " not a fault" % q)
    print("%d finding(s), %d wire-less segment(s)" % (bad, len(lone)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
