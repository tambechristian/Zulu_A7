# -*- coding: utf-8 -*-
"""Turn the board into a 1+6+1 HDI build: L2 becomes the escape layer under
the BGA, the GND plane moves to L3, and every boxed pad gets a laser via.

    python tools/hdi_swap.py in.brd out.brd

WHY. Twelve BGA balls have no L1 escape and U3's SDRAM pads are walled in on
L16; 48 airwires are the result and no amount of rip-up opens them (see
board/STACKUP.md, "Closing the airwires"). The earlier sessions had already
reached for 0.10 mm laser vias in those pads -- but they landed on L2, which
was the GND plane, and cut it to pieces. Decision 2026-09-05: make it a real
HDI build. L2 is a signal layer reached by 0.10 / 0.20 mm microvias from L1;
L3 carries the GND pour; L16's boxed pads get 0.10 / 0.20 microvias to L7.

WHAT IT DOES, in order
  1. moves the GND <polygonpour> from layer 2 to layer 3;
  2. renumbers every layer-3 wire to layer 2 (through vias reach both, so
     connectivity is unchanged);
  3. sets msMicroVia to 0.10 mm so Fusion stops calling every laser via a
     Drill Size error;
  4. strips the nets that were routed on the plane layers with deep laser
     vias (1-5, 2-16, 1-4, 1-7, 5-16 spans cannot be laser drilled) down to
     their pads, turning each such via into a 1-2 or 7-16 microvia where it
     sits in or beside a pad, so close_airwires reroutes them from there;
  5. for every still-open net, gives each bare U1 ball a 1-2 microvia and
     each bare U3 pad a 7-16 microvia, land 0.20 mm centred in the pad;
  6. rips any moved copper on L2 or L7 that a new microvia land now
     collides with, so its owner reroutes rather than shorts.

close_airwires.py then runs with CLOSE_LAYERS=1,2,4,6,7,16 and
CLOSE_PLANES=GND:3,VCC3V3:5. PCBWay must approve: laser 0.10/0.20 microvias
L1-L2 and L16-L7, filled and capped where they sit in BGA and TSOP pads, and
the 1+6+1 lamination sequence.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CLOSE_BOARD", sys.argv[1] if len(sys.argv) > 1 else "x")
import close_airwires as CA   # noqa: E402
import check_connectivity as C   # noqa: E402

MICRO_D, MICRO_L = 0.1, 0.2
DEEP_NETS_HINT = ("CHAN8", "CHAN18", "CHAN23", "LED2", "D12", "D6", "FLASH-D00", "LDQM", "PUDC_B")


def g(v):
    return CA.g(v)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    only_micro = "--microvias-only" in sys.argv
    text = io.open(src, encoding="utf-8", errors="replace").read()
    pads, fields = CA.pad_index(text)
    padobjs = {}
    for key, p in pads.items():
        if p["net"]:
            padobjs.setdefault(p["net"], []).append(p)

    if not only_micro:
        # 1. GND pour L2 -> L3
        n_pour = text.count('<polygonpour layer="2"')
        assert n_pour == 1, "expected exactly one layer-2 pour, found %d" % n_pour
        text = text.replace('<polygonpour layer="2"', '<polygonpour layer="3"', 1)
        # 2. L3 wires -> L2 (inside <signals> only)
        sm = re.search(r"<signals>.*</signals>", text, re.S)
        body = sm.group(0)
        body2, n_moved = re.subn(r'(<wire\b[^>]*\blayer=")3(")', r"\g<1>2\2", body)
        text = text[:sm.start()] + body2 + text[sm.end():]
        print("pour moved to L3; %d wire(s) moved L3 -> L2" % n_moved)
        # 3. rules
        text, n_rule = re.subn(r'(<param name="msMicroVia" value=")[^"]*(")', r"\g<1>0.1mm\2", text)
        # FUSION READS THE NEW-STYLE <rule> ELEMENTS, NOT THE <param> LIST. With
        # msDrill and msMicroVia at 0.1 mm it still called every microvia a
        # Drill Size error until this rule said 0.1 mm too (2026-09-05).
        text, n_new = re.subn(r'(<rule type="Minimum Drill Size"[^>]*\bvalue=")[^"]*("[^>]*\bpreferredvalue=")[^"]*(")',
                              r"\g<1>0.1mm\g<2>0.1mm\3", text)
        print("msMicroVia -> 0.1mm (%d rule); Minimum Drill Size rule -> 0.1mm (%d rule)" % (n_rule, n_new))

    sig = dict((m.group(2), (m.group(1), m.group(3))) for m in CA.SIG_RE.finditer(text))

    def is_pad_of(x, y, el, tol=0.3):
        for (nm, pn), p in pads.items():
            if nm == el and math.hypot(p["at"][0] - x, p["at"][1] - y) <= tol:
                return p
        return None

    # 4. deep laser vias -> microvias; strip those nets to pads + microvias
    stripped = []
    for name, (ot, body) in list(sig.items()):
        if only_micro:
            break
        items = CA.parse_items(body)
        deep = [o for o in items if o["kind"] == "via" and o["drill"] < 0.2 - 1e-6]
        if not deep:
            continue
        keep = []
        for o in deep:
            span = (o["lo"], o["hi"])
            x, y = o["at"]
            if span == (1, 2) or span == (7, 16):
                keep.append((x, y, span))
            elif o["lo"] == 1:
                keep.append((x, y, (1, 2)))
            elif o["hi"] == 16:
                keep.append((x, y, (7, 16)))
        new = CA.Net.strip_body(body)
        for x, y, span in keep:
            new += '<via x="%s" y="%s" extent="%d-%d" drill="%s" diameter="%s"/>' % (
                g(x), g(y), span[0], span[1], g(MICRO_D), g(MICRO_L))
        sig[name] = (ot, new)
        stripped.append("%s (%d microvia(s))" % (name, len(keep)))
    print("stripped to pads + microvias: %s" % ", ".join(stripped))
    text = CA.rebuild(text, dict((n, sig[n][1]) for n in sig))

    # 5. microvias for bare boxed pads of open nets
    parsed = C.parse_signal_objects(text)
    added = []
    for name, (objects, terminals, planes) in parsed.items():
        if terminals < 2 or name in ("GND", "VCC3V3"):
            continue
        union = C.connectivity_union(objects, planes)
        groups = {}
        for i, o in enumerate(objects):
            groups.setdefault(union.find(i), []).append(i)
        with_pads = [grp for grp in groups.values() if any(i < terminals for i in grp)]
        if len(with_pads) < 2:
            continue
        adds = ""
        for grp in with_pads:
            if len(grp) != 1:
                continue
            pad = objects[grp[0]]
            if pad["kind"] != "pad" or pad["through"]:
                continue
            x, y = pad["at"]
            if is_pad_of(x, y, "U1", 0.05) and 1 in pad["layers"]:
                adds += '<via x="%s" y="%s" extent="1-2" drill="%s" diameter="%s"/>' % (g(x), g(y), g(MICRO_D), g(MICRO_L))
                added.append("%s U1 (%.2f,%.2f)" % (name, x, y))
            elif is_pad_of(x, y, "U3", 0.05) and 16 in pad["layers"]:
                adds += '<via x="%s" y="%s" extent="7-16" drill="%s" diameter="%s"/>' % (g(x), g(y), g(MICRO_D), g(MICRO_L))
                added.append("%s U3 (%.2f,%.2f)" % (name, x, y))
        if adds:
            ot, body = sig[name]
            sig[name] = (ot, body + adds)
    text = CA.rebuild(text, dict((n, sig[n][1]) for n in sig))
    print("microvias added at bare pads: %d -> %s" % (len(added), ", ".join(added)))

    # 6. rip moved copper that a microvia land now collides with
    micro = []
    for name, (ot, body) in sig.items():
        for o in CA.parse_items(body):
            if o["kind"] == "via" and o["drill"] < 0.2 - 1e-6:
                micro.append((name, o))
    clr = 0.0762
    ripped = {}
    for name, (ot, body) in sig.items():
        items = CA.parse_items(body)
        drop = []
        for o in items:
            for mname, mv in micro:
                if mname == name:
                    continue
                inner = 2 if mv["lo"] == 1 else 7
                if o["kind"] == "wire" and o["layer"] == inner:
                    d = CA.E.seg_pt(o["a"], o["b"], mv["at"]) - o["radius"] - MICRO_L / 2
                    if d < clr:
                        drop.append(o)
                        break
                if o["kind"] == "via":
                    if not (o["lo"] <= inner <= o["hi"]):
                        continue
                    d = math.hypot(o["at"][0] - mv["at"][0], o["at"][1] - mv["at"][1])
                    if d < MICRO_D / 2 + o["drill"] / 2 + 0.1 or d < MICRO_L / 2 + o["radius"] + clr:
                        drop.append(o)
                        break
        if drop:
            new = body
            for o in drop:
                new = new.replace(o["text"], "", 1)
            sig[name] = (ot, new)
            ripped[name] = len(drop)
    text = CA.rebuild(text, dict((n, sig[n][1]) for n in sig))
    print("copper ripped for microvia room: %s" % (", ".join("%s(%d)" % kv for kv in sorted(ripped.items())) or "none"))

    import xml.etree.ElementTree as ET
    ET.fromstring(text)
    io.open(dst, "w", encoding="utf-8", newline="").write(text)
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
