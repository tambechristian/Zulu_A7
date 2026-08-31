# -*- coding: utf-8 -*-
"""Check zulu_a7.brd against zulu_a7.sch, and report routing progress.

    python tools/check_board.py [board.brd [schematic.sch]]

WHY THIS EXISTS. Fusion links a schematic to a PCB through an Electronics
Design container, not by filename the way classic Eagle did. Editing the two
files loose on disk -- which is what keeps everything in tools/ working, since
they all read from Zulu_A7 -- means Fusion never runs its own consistency
check on them. This is that check, done from the outside.

It shares no code with tools/make_board.py on purpose. Both sides are rebuilt
from the files, so a bug in the generator cannot hide behind a matching bug in
the checker.

WHAT IT CHECKS

  1  structure      both files parse, versions and outline
  2  parts          every part with a package has exactly one element of that
                    package; parts without one (frames, supply symbols) have none
  3  nets           every net is a signal, and its set of (element, pad) pairs
                    matches what the deviceset's <connect> entries say -- including
                    pins that map to several pads, like the microSD shield tabs
  4  pads           every contactref names a pad that exists in that package
  5  libraries      the board's copy of each package still matches the schematic's,
                    so a footprint edited in one file cannot drift from the other
  6  placement      what is on the board, what is parked outside it, what overlaps
  7  rules          layer setup and the design rules actually loaded
  8  routing        how much is routed, and what is not

The exit code is the number of findings, so it can gate a commit.
"""

import re, io, os, sys, math, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# One via parser for the whole toolchain. check_board was self-contained until
# a board came back from Fusion with 868 vias written as open tags with no
# diameter, which every private regex here read as zero.
import geom as G   # noqa: E402

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
findings = []


def head(s):
    print("\n" + s + "\n" + "-" * len(s))


def ok(s):
    print("  PASS  " + s)


def bad(s):
    findings.append(s)
    print("  ****  " + s)


def note(s):
    """Something true and deliberate that would otherwise read as a finding."""
    print("  ----  " + s)


def pads_of(src):
    return {m.group(1): (float(m.group(2)), float(m.group(3)))
            for m in re.finditer(r'<(?:pad|smd) name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', src)}


# Eagle writes a design rule as a length with its unit attached, and which unit
# depends on what the tool last saved in: "0.0762mm", "3mil", "0.003in" are one
# value written three ways. Compare millimetres.
_UNITS = (("mil", 0.0254), ("mm", 1.0), ("inch", 25.4), ("in", 25.4))


def _mm(v):
    t = str(v).strip().lower()
    for suf, k in _UNITS:
        if t.endswith(suf):
            try:
                return float(t[:-len(suf)]) * k
            except ValueError:
                return float("nan")
    try:
        return float(t)            # bare number: Eagle means mm
    except ValueError:
        return float("nan")


def main(brdpath, schpath):
    s = open(schpath, encoding="utf-8").read()
    b = open(brdpath, encoding="utf-8").read()

    head("1. Structure")
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(s); ET.fromstring(b)
        ok("both files parse as XML")
    except Exception as e:
        bad("XML: %s" % e); return len(findings)
    if "<schematic" not in s:
        bad("%s is not a schematic" % schpath)
    if "<board>" not in b:
        bad("%s is not a board" % brdpath)
    seg = [tuple(map(float, m.groups())) for m in re.finditer(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"[^>]*layer="20"', b)]
    if not seg:
        bad("no board outline on layer 20")
        BX0 = BY0 = BX1 = BY1 = 0.0
    else:
        xs = [c for w in seg for c in (w[0], w[2])]; ys = [c for w in seg for c in (w[1], w[3])]
        BX0, BY0, BX1, BY1 = min(xs), min(ys), max(xs), max(ys)
        ok("outline %.2f x %.2f mm = %.3f x %.3f in, %d segments on layer 20"
           % (BX1 - BX0, BY1 - BY0, (BX1 - BX0) / 25.4, (BY1 - BY0) / 25.4, len(seg)))

    # --- schematic model, rebuilt from scratch ------------------------------
    slib = {m.group(1): m.group(2) for m in re.finditer(r'<library name="([^"]+)">(.*?)</library>', s, re.S)}
    spkg = {}
    for L, body in slib.items():
        pm = re.search(r"<packages>(.*?)</packages>", body, re.S)
        if pm:
            for p in re.finditer(r'<package name="([^"]+)">(.*?)</package>', pm.group(1), re.S):
                spkg[(L, p.group(1))] = p.group(2)
    dev = {}
    for L, body in slib.items():
        for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', body, re.S):
            for dv in re.finditer(r'<device name="([^"]*)"(?: package="([^"]+)")?>(.*?)</device>',
                                  dm.group(2), re.S):
                dev[(L, dm.group(1), dv.group(1))] = (dv.group(2), {
                    (g, p): pd.split() for g, p, pd in
                    re.findall(r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', dv.group(3))})
    part = {m.group(1): (m.group(2), m.group(3), m.group(4)) for m in
            re.finditer(r'<part name="([^"]+)" library="([^"]+)" deviceset="([^"]+)" device="([^"]*)"', s)}
    want = {p: dev[k][0] for p, k in part.items() if dev.get(k, (None,))[0]}
    snet = collections.defaultdict(set)
    for m in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', s, re.S):
        snet[m.group(1)]
        for p, g, pn in re.findall(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', m.group(2)):
            k = part[p]
            if dev[k][0]:
                for pad in dev[k][1].get((g, pn), []):
                    snet[m.group(1)].add((p, pad))

    # --- board model --------------------------------------------------------
    el = {m.group(1): (m.group(2), m.group(3)) for m in
          re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"', b)}
    epos = {m.group(1): (float(m.group(2)), float(m.group(3)),
                         (re.search(r'rot="(M?R\d+)"', m.group(4)) or [None, "R0"])[1])
            for m in re.finditer(r'<element name="([^"]+)"[^>]*x="([-\d.]+)" y="([-\d.]+)"([^>]*)>', b)}
    bpkg = {}
    for m in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for p in re.finditer(r'<package name="([^"]+)">(.*?)</package>', m.group(2), re.S):
            bpkg[(m.group(1), p.group(1))] = p.group(2)
    bsig = {m.group(1): m.group(2) for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', b, re.S)}
    def _dru(k, dflt):
        m = re.search(r'<param name="%s" value="([\d.]+)(mm)?"/>' % k, b)
        return float(m.group(1)) if m else dflt
    RVPADI = _dru('rvPadInner', 0.25)
    RLMINPADI = _dru('rlMinPadInner', 0.1)
    RLMAXPADI = _dru('rlMaxPadInner', 0.5)
    bcon = {n: set(re.findall(r'<contactref element="([^"]+)" pad="([^"]+)"/>', v)) for n, v in bsig.items()}

    head("2. Parts and elements")
    (ok if set(want) == set(el) else bad)(
        "%d parts with a package -> %d elements" % (len(want), len(el))
        if set(want) == set(el) else
        "parts and elements differ: only in schematic %s; only on board %s"
        % (sorted(set(want) - set(el))[:6], sorted(set(el) - set(want))[:6]))
    wrong = [(p, el[p][1], want[p]) for p in want if p in el and el[p][1] != want[p]]
    (ok if not wrong else bad)("every element carries the package its deviceset names"
                              if not wrong else "package mismatch: %s" % wrong[:6])
    ghost = [p for p in part if p not in want and p in el]
    (ok if not ghost else bad)(
        "%d schematic-only parts correctly have no element" % (len(part) - len(want))
        if not ghost else "parts with no package but an element anyway: %s" % ghost[:6])

    # Values drift silently: editing a resistor's tolerance in the schematic
    # leaves the board's copy stale, and the stale one is what gets silkscreened
    # and what feeds the BOM. A part whose deviceset fixes the value carries no
    # value= attribute at all, and the board writes that as "" -- not a mismatch.
    sval = {m.group(1): m.group(2) for m in
            re.finditer(r'<part name="([^"]+)"[^>]*?\svalue="([^"]*)"', s)}
    bval = {m.group(1): m.group(2) for m in
            re.finditer(r'<element name="([^"]+)"[^>]*?\svalue="([^"]*)"', b)}
    vdrift = sorted((p, sval.get(p, ""), bval[p]) for p in bval
                    if p in want and sval.get(p, "") != bval[p])
    (ok if not vdrift else bad)(
        "%d element value(s) match the schematic" % len(bval) if not vdrift else
        "value drift between schematic and board: %s"
        % ["%s sch %r brd %r" % v for v in vdrift[:5]])

    head("3. Nets and signals")
    (ok if set(snet) == set(bsig) else bad)(
        "%d nets -> %d signals" % (len(snet), len(bsig)) if set(snet) == set(bsig) else
        "nets and signals differ: %s" % sorted(set(snet) ^ set(bsig))[:6])
    diff = [n for n in snet if n in bcon and snet[n] != bcon[n]]
    if diff:
        bad("%d net(s) whose (element, pad) set differs" % len(diff))
        for n in diff[:4]:
            bad("   %-12s only in sch %s; only on brd %s"
                % (n, sorted(snet[n] - bcon[n])[:4], sorted(bcon[n] - snet[n])[:4]))
    else:
        ok("every signal's contactrefs match the schematic, %d in total"
           % sum(len(v) for v in bcon.values()))
    multi = sum(1 for k, (_pk, cs) in dev.items() for c in cs.values() if len(c) > 1)
    ok("%d pins map to more than one pad and were expanded" % multi)

    head("4. Contactrefs resolve to real pads")
    miss = [(e, pd) for n, cs in bcon.items() for e, pd in cs
            if e in el and pd not in pads_of(bpkg.get(el[e], ""))]
    (ok if not miss else bad)("every contactref names a pad that exists"
                             if not miss else "contactrefs with no such pad: %s" % miss[:6])

    head("5. Library drift")
    drift = []
    for p, (lib, pk) in el.items():
        if (lib, pk) not in bpkg:
            drift.append((pk, "not in the board's libraries")); continue
        if (lib, pk) not in spkg:
            drift.append((pk, "not in the schematic's libraries")); continue
        a, c = pads_of(spkg[(lib, pk)]), pads_of(bpkg[(lib, pk)])
        if a != c:
            drift.append((pk, "pads differ: %s" % sorted(set(a) ^ set(c))[:4]))
    drift = sorted(set(drift))
    (ok if not drift else bad)("all %d packages identical in both files" % len(set(el.values()))
                              if not drift else "footprints have drifted: %s" % drift[:4])

    head("6. Placement")
    def rp(x, y, rot):
        r = re.sub(r"^M", "", rot)
        x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
        return (-x, y) if rot.startswith("M") else (x, y)

    box, art = {}, []
    for p, (lib, pk) in el.items():
        src = bpkg.get((lib, pk), "")
        xs, ys = [], []
        for m in re.finditer(r'<smd name="[^"]*" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"', src):
            x, y, dx, dy = map(float, m.groups()); xs += [x - dx / 2, x + dx / 2]; ys += [y - dy / 2, y + dy / 2]
        for m in re.finditer(r'<pad name="[^"]*" x="([-\d.]+)" y="([-\d.]+)"[^>]*drill="([\d.]+)"', src):
            x, y, d = map(float, m.groups()); r = d / 2 + 0.254; xs += [x - r, x + r]; ys += [y - r, y + r]
        if not xs:
            art.append(p)          # padless: the CC licence artwork, no copper to check
            continue
        ox, oy, rot = epos[p]
        pts = [rp(x, y, rot) for x in (min(xs), max(xs)) for y in (min(ys), max(ys))]
        box[p] = (ox + min(q[0] for q in pts), oy + min(q[1] for q in pts),
                  ox + max(q[0] for q in pts), oy + max(q[1] for q in pts), rot.startswith("M"))
    # Three states, not two. An element that is partly on and partly off the
    # board is neither placed nor parked -- it has copper hanging over the edge,
    # and treating it as parked would also exclude it from the overlap test.
    def inside(v):
        return (v[0] >= BX0 - 1e-6 and v[1] >= BY0 - 1e-6
                and v[2] <= BX1 + 1e-6 and v[3] <= BY1 + 1e-6)

    def clear(v):
        return v[2] <= BX0 + 1e-6 or v[0] >= BX1 - 1e-6 or v[3] <= BY0 + 1e-6 or v[1] >= BY1 - 1e-6

    # X1 hangs over the edge on purpose and the drawing says by how much. Molex
    # SD-105017-001 sheet 1 puts the CONNECTOR FRONT INTERFACE 0.70 mm beyond the
    # PCB EDGE, so the shell overhangs and a footprint that did not would be the
    # wrong one. Everything else straddling is still a finding.
    OVERHANG = {"X1": "Molex SD-105017-001: the mating face sits 0.70 mm past the PCB edge"}
    on = [p for p, v in box.items() if inside(v)]
    off = [p for p, v in box.items() if clear(v)]
    edge = [p for p in box if p not in on and p not in off]
    known = [p for p in edge if p in OVERHANG]
    edge = [p for p in edge if p not in OVERHANG]
    for p in known:
        note("%s hangs over the edge by design -- %s" % (p, OVERHANG[p]))
    (ok if not edge else bad)("no element straddles the board edge" if not edge else
                              "%d element(s) hang over the board edge: %s"
                              % (len(edge), [(p, tuple(round(c, 2) for c in box[p][:4])) for p in edge][:4]))
    edge = edge + known
    on = on + edge          # straddlers still have to be checked for collisions
    tally = len(on) + len(off) + len(art)
    (ok if tally == len(el) else bad)(
        "%d elements on the board, %d parked outside it, %d padless artwork -- %d in all"
        % (len(on), len(off), len(art), tally) if tally == len(el) else
        "placement tally %d does not account for all %d elements" % (tally, len(el)))
    if art:
        ok("padless, so nothing to place-check: %s" % ", ".join(sorted(art)))
    # One element is the board frame rather than a component: the header's
    # package carries the outline itself, so once placed its silk rectangle
    # coincides with the layer-20 outline and its bounding box spans the whole
    # board. Comparing that box against every other part reports an overlap with
    # everything on its side, which is noise. Identify it by that coincidence --
    # not by name -- and check its holes instead of its box.
    # Find it by the SHAPE of its silk, not by where it ended up -- otherwise a
    # frame that is misplaced simply stops being recognised and the check goes
    # quiet, which is exactly the failure being guarded against. X2 spent this
    # whole session parked 20 mm below the board because it was missing from
    # make_board.py's placement table, taking the outline drawing with it.
    frame, framexy = None, None
    for p, (lib, pk) in el.items():
        if p not in box:
            continue
        w21 = [tuple(map(float, q)) for q in re.findall(
            r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"[^>]*layer="21"',
            bpkg.get((lib, pk), ""))]
        if len(w21) < 4:
            continue
        xs = [v for q in w21 for v in (q[0], q[2])]; ys = [v for q in w21 for v in (q[1], q[3])]
        if (abs((max(xs) - min(xs)) - (BX1 - BX0)) < 1e-6
                and abs((max(ys) - min(ys)) - (BY1 - BY0)) < 1e-6):
            frame, framexy = p, (epos[p], (min(xs), min(ys)))
    if frame:
        (ox, oy, rot), (sx, sy) = framexy
        placed = rot == "R0" and abs(ox + sx - BX0) < 1e-6 and abs(oy + sy - BY0) < 1e-6
        (ok if placed else bad)(
            "%s carries the board outline and sits on it exactly, so it is the frame, "
            "not an obstruction" % frame if placed else
            "%s carries the board outline but is placed at (%.2f, %.2f) rot=%s -- its outline "
            "lands at (%.2f, %.2f) instead of (%.2f, %.2f), so every pad it owns is off the board"
            % (frame, ox, oy, rot, ox + sx, oy + sy, BX0, BY0))
        pass

    # A plated hole is copper on EVERY layer, so a through-hole part displaces
    # whatever is behind it as much as whatever is beside it. That is what makes
    # this different from the overlap test above, which ignores opposite-side
    # pairs: here the side is irrelevant. JP3 sat over four of the FPGA's
    # decoupling capacitors this way -- its pads cleared everything on its own
    # side, and its six holes went straight through the field on the other.
    #
    # It used to check only the frame's holes, so the one part whose holes were
    # actually landing on something was the part it never looked at.
    def holes(p):
        ox, oy, rot = epos[p]
        out = []
        for x, y, dr in re.findall(
                r'<pad name="[^"]*" x="([-\d.]+)" y="([-\d.]+)"[^>]*drill="([\d.]+)"',
                bpkg.get(el[p], "")):
            hx, hy = rp(float(x), float(y), rot)      # rotate: a hole map read
            out.append((ox + hx, oy + hy, float(dr) / 2 + 0.254))   # unrotated reports phantoms
        return out

    drilled = sorted(p for p in on if holes(p))
    pierce = []
    for a in drilled:
        for hx, hy, hr in holes(a):
            for c in on:
                if c == a or (a != frame and c == frame):
                    continue          # every part is inside the frame by design
                v = box[c]
                if v[0] < hx + hr and hx - hr < v[2] and v[1] < hy + hr and hy - hr < v[3]:
                    pierce.append("%s hole over %s" % (a, c))
    pierce = sorted(set(pierce))
    (ok if not pierce else bad)(
        "no plated hole of %s lands on another element, either side"
        % ", ".join(drilled) if not pierce else
        "%d hole collision(s), side irrelevant: %s" % (len(pierce), pierce[:6]))
    ov = [(a, c) for a in on for c in on if a < c and a != frame and c != frame
          and box[a][4] == box[c][4]
          and box[a][0] < box[c][2] and box[c][0] < box[a][2]
          and box[a][1] < box[c][3] and box[c][1] < box[a][3]]
    (ok if not ov else bad)("no two elements on the same side overlap"
                           if not ov else "%d overlapping pair(s) on one side: %s" % (len(ov), ov[:5]))

    # A layer-39 keepout is the part of a footprint that is not copper but still
    # cannot be built over: JP3's is its connector body, the microSD's is the
    # 8.70 mm the card travels on its way out. Nothing in the placement path
    # measures them -- make_board.py's bbox() reads layers 21 and 51 only -- so
    # they are compared here instead.
    #
    # Only SAME-SIDE pairs count, and the board frame is excluded. Without both
    # filters this reports 155 collisions on a correct board: the frame's
    # keepout is the whole outline, and the decoupling field sits behind the
    # ball field on purpose. With them it found the microSD rotated so its card
    # ejected into the board through BTN, and nothing else.
    def keepout(p):
        ox, oy, rot = epos[p]
        w = [tuple(map(float, q)) for q in re.findall(
            r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"[^>]*layer="39"',
            bpkg.get(el[p], ""))]
        if not w:
            return None
        # not clipped to the outline: a keepout that leaves the board is often
        # the point of it, and clipping would have hidden the one real defect
        pts = [rp(x, y, rot) for q in w for x, y in ((q[0], q[1]), (q[2], q[3]))]
        return (ox + min(v[0] for v in pts), oy + min(v[1] for v in pts),
                ox + max(v[0] for v in pts), oy + max(v[1] for v in pts))

    kohit = []
    for a in on:
        k = keepout(a) if a != frame else None
        if not k:
            continue
        for c in on:
            if c == a or c == frame or box[a][4] != box[c][4]:
                continue
            v = box[c]
            if k[0] < v[2] and v[0] < k[2] and k[1] < v[3] and v[1] < k[3]:
                kohit.append("%s keepout over %s copper" % (a, c))
    (ok if not kohit else bad)(
        "no keepout covers another element's copper on the same side"
        if not kohit else "%d keepout collision(s): %s" % (len(kohit), sorted(kohit)[:5]))

    # Body against body: everything drawn on 21, 39 or 51 together, which for a
    # connector is its plastic shroud. This is what decides whether two parts can
    # physically be seated, and neither test above sees it -- copper-vs-copper
    # measures pads, keepout-vs-copper measures a keepout against pads. JP3 and
    # the Pmod fouled each other by 0.11 mm of shroud while their holes were
    # 0.91 mm apart and every other check passed.
    def shape(p):
        ox, oy, rot = epos[p]
        src = bpkg.get(el[p], "")
        xs, ys = [], []
        for m in re.finditer(r"<(?:wire|rectangle) ([^>]*)/>", src):
            if re.search(r'layer="(?:21|39|51)"', m.group(1)):
                xs += [float(v) for v in re.findall(r'\b[xX][12]="([-\d.]+)"', m.group(1))]
                ys += [float(v) for v in re.findall(r'\b[yY][12]="([-\d.]+)"', m.group(1))]
        # Circles and polygons too, or this measures a different part from the
        # one make_board.py placed. Silk is not always wires: a pin-1 dot is a
        # <circle>, and several packages fill their outline with a <polygon>.
        # X3, X1 and U8 each carry a 0.15 mm pin-1 dot just outside the body,
        # and neither the placer nor this check could see it -- so a part could
        # be seated on top of the one marking that says which way round the
        # chip goes, and nothing would say a word.
        for m in re.finditer(r'<circle x="([-\d.]+)" y="([-\d.]+)" radius="([\d.]+)"'
                             r' width="[\d.]+" layer="(?:21|39|51)"', src):
            x, y, r = map(float, m.groups()); xs += [x - r, x + r]; ys += [y - r, y + r]
        for pm in re.finditer(r'<polygon [^>]*layer="(?:21|39|51)"[^>]*>(.*?)</polygon>', src, re.S):
            for v in re.finditer(r'<vertex x="([-\d.]+)" y="([-\d.]+)"', pm.group(1)):
                xs.append(float(v.group(1))); ys.append(float(v.group(2)))
        if not xs:
            return None
        pts = [rp(x, y, rot) for x in (min(xs), max(xs)) for y in (min(ys), max(ys))]
        return (ox + min(v[0] for v in pts), oy + min(v[1] for v in pts),
                ox + max(v[0] for v in pts), oy + max(v[1] for v in pts))

    drawn = sorted(p for p in on if p != frame and shape(p))
    foul = []
    for i, a in enumerate(drawn):
        for c in drawn[i + 1:]:
            if box[a][4] != box[c][4]:
                continue
            va, vc = shape(a), shape(c)
            if va[0] < vc[2] and vc[0] < va[2] and va[1] < vc[3] and vc[1] < va[3]:
                foul.append("%s/%s" % (a, c))
    (ok if not foul else bad)(
        "no two bodies foul on the same side (%d have a drawn outline)" % len(drawn)
        if not foul else "%d body collision(s): %s" % (len(foul), foul[:6]))

    # Footprint provenance notes. Three ctambe packages carry prose on layer 51
    # saying what was measured against which datasheet page. Left in the package
    # it travels with the element, and X1's three lines and U8's two sat inside
    # the outline, printed across the layout. make_board.py strips them from the
    # board's copy and re-emits them once above the outline; these two checks are
    # what stop that quietly coming undone.
    LONG = r'<text ([^>]*)>([^<]{25,})</text>'
    inpkg = [m.group(2)[:40] for lm in re.finditer(r"<libraries>.*?</libraries>", b, re.S)
             for m in re.finditer(LONG, lm.group(0)) if 'layer="51"' in m.group(1)]
    (ok if not inpkg else bad)(
        "no footprint prose left inside the board's package definitions" if not inpkg else
        "%d layer-51 note(s) still inside a package, so they ride on the element: %s"
        % (len(inpkg), inpkg[:3]))
    # A footprint may declare where the board edge has to fall, by drawing that
    # line on layer 48. X1 does: Molex SD-105017-001 sheet 1 marks a PCB EDGE
    # 4.141 mm in front of the rear-row centreline, and if the element is placed
    # anywhere else the connector either buries its mouth in the board or hangs
    # off into space. Nothing else in the placement notices, which is exactly the
    # gap that let X3 be built ejecting into the board.
    ref = []
    for p, (lib, pkname) in sorted(el.items()):
        body = bpkg.get((lib, pkname), "")
        for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
                             r'y2="([-\d.]+)"[^>]*layer="48"', body):
            x1, y1, x2, y2 = map(float, w.groups())
            ox, oy, rot = epos[p]
            a, c = rp(x1, y1, rot), rp(x2, y2, rot)
            ax, ay, cx, cy = ox + a[0], oy + a[1], ox + c[0], oy + c[1]
            d = (min(abs(ay - BY0), abs(ay - BY1)) if abs(ay - cy) < 1e-6
                 else min(abs(ax - BX0), abs(ax - BX1)) if abs(ax - cx) < 1e-6 else 9.9)
            ref.append((p, d, ay if abs(ay - cy) < 1e-6 else ax))
    off = [r for r in ref if r[1] > 0.01]
    (ok if ref and not off else (bad if off else ok))(
        "%d layer-48 board-edge reference(s) land on the outline: %s"
        % (len(ref), ", ".join("%s at %.3f" % (r[0], r[2]) for r in ref))
        if ref and not off else
        "%d board-edge reference(s) miss the outline: %s"
        % (len(off), ["%s off by %.3f" % (r[0], r[1]) for r in off]) if off else
        "no footprint declares a board-edge reference on layer 48")

    pm = re.search(r"<plain>.*?</plain>", b, re.S)
    doc = [(float(re.search(r'y="([-\d.]+)"', m.group(1)).group(1)), m.group(2)[:40])
           for m in re.finditer(LONG, pm.group(0) if pm else "") if 'layer="51"' in m.group(1)]
    low = [d for d in doc if d[0] <= BY1]
    (ok if doc and not low else (bad if low else ok))(
        "%d documentation line(s) parked above the outline, y %.2f..%.2f"
        % (len(doc), min(d[0] for d in doc), max(d[0] for d in doc)) if doc and not low else
        "%d documentation line(s) sit at or below y %.2f, on the board: %s"
        % (len(low), BY1, [d[1] for d in low[:3]]) if low else
        "no documentation block in <plain> (nothing to park)")

    head("7. Stackup and design rules")
    m = re.search(r'<param name="layerSetup" value="([^"]+)"/>', b)
    if not m:
        bad("no layerSetup in the design rules")
    else:
        want = [int(v) for v in re.findall(r"\d+", m.group(1))]
        (ok if len(want) >= 4 else bad)(
            "layerSetup %s -> %d copper layers%s"
            % (m.group(1), len(want), "" if len(want) >= 4 else "; a 0.5 mm BGA needs at least 4"))
        # layerSetup is a design rule; whether a layer can actually be drawn on
        # lives in <layers>, and the two can disagree. make_board.py used to copy
        # <layers> straight from the previous board -- the Spartan-6 four-layer
        # one -- so this claimed six copper layers while Route4 and Route5 sat
        # there as active="no". Routing would have had nowhere to go.
        dead = [n for n in want
                if not re.search(r'<layer number="%d"[^>]*active="yes"' % n, b)]
        (ok if not dead else bad)(
            "all %d are active in <layers> and can be routed on" % len(want) if not dead else
            "layerSetup names %s but %s %s not active in <layers>, so nothing can be drawn on %s"
            % (m.group(1), dead, "is" if len(dead) == 1 else "are",
               "it" if len(dead) == 1 else "them"))
    # Two fabs, two rule sets, and the board says which one it was built for. The
    # land is checked against the same table, because it is the number the whole
    # escape argument turns on -- a JLCPCB board carrying 0.275 mm lands would
    # look fine and be unroutable. See board/STACKUP.md, "What the research
    # found". Both entries also exist to stop 0.0635 mm (2.5 mil) coming back:
    # that was set on the belief that PCBWay publishes 2/2 mil for rigid boards,
    # which they do not -- 2 mil is an HDI number.
    FABRULES = {
        "JLCPCB": (0.225, (("mdWireWire", "0.09mm"), ("msWidth", "0.0762mm"),
                           ("msDrill", "0.2mm"), ("msMicroVia", "9.9mm"),
                           ("rlMinViaOuter", "0.05mm"), ("mdCopperDimension", "0.3mm"))),
        # PCBWay answered the DFM enquiry on 2026-08-27: 8 mil BGA pad, 0.4 mm
        # pitch, 0.5 oz or 1 oz outer, HDI ruled out on cost. Plan A now, at the
        # same 0.225 land JLCPCB uses. 0.275 is gone: at 0.275 the gap is
        # 0.225 mm and 3.5/3.5 mil needs 0.2667.
        #
        # THE FOLLOW-UP CAME BACK 2026-08-27: "the min trace wid/spa we can do
        # is 3/3mil" -- 0.0762 mm, finer than the 3.5/3.5 that was in doubt, and
        # stated with no copper-weight qualifier. That settles the contradiction
        # this table used to carry: their published 3.5/3.5 sat only on the
        # 18 um outer row, while the reply said 0.5 oz and 1 oz both work. 3/3
        # is the floor, so 3.5/3.5 at 1 oz is inside it. PCBWay clearance is
        # 0.0762 now, not JLCPCB's 0.09 carried over as a placeholder.
        "PCBWAY": (0.225, (("mdWireWire", "0.0762mm"), ("msWidth", "0.0762mm"),
                           ("msDrill", "0.2mm"), ("msMicroVia", "9.9mm"),
                           ("rlMinViaOuter", "0.05mm"), ("mdCopperDimension", "0.3mm"))),
    }
    dr = (re.search(r'<designrules name="([^"]*)"', b) or [None, ""])[1]
    fab = next((f for f in FABRULES if dr.upper().endswith(f)), None)
    (ok if fab else bad)(
        "built for %s (design rules %r)" % (fab, dr) if fab else
        "design rules %r name no fab this checker knows; expected one of %s"
        % (dr, sorted(FABRULES)))
    if fab:
        land, params = FABRULES[fab]
        for k, wantv in params:
            got = (re.search(r'<param name="%s" value="([^"]+)"/>' % k, b) or [None, None])[1]
            # COMPARE THE VALUE, NOT THE SPELLING. Fusion rewrote msWidth as
            # "3mil" where this table says "0.0762mm". Those are the same number
            # -- 3 x 0.0254 -- and a string compare called it a violation on
            # every run. A design rule is a length; the units it was last saved
            # in are the CAD tool's business.
            same = got is not None and abs(_mm(got) - _mm(wantv)) < 1e-9
            (ok if same else bad)(
                "%-18s %s" % (k, got) if got == wantv else
                "%-18s %s (= %s)" % (k, got, wantv) if same else
                "%-18s %s, expected %s for %s" % (k, got, wantv, fab))
        pk = re.search(r'<package name="XC7A35T-CPG236">.*?</package>', b, re.S)
        if not pk:
            bad("no XC7A35T-CPG236 package in the board")
        else:
            dims = collections.Counter(re.findall(r'<smd name="[^"]+"[^>]*dx="([^"]*)" dy="([^"]*)"',
                                                  pk.group(0)))
            want = (("%.4f" % land).rstrip("0").rstrip("."),) * 2
            (ok if list(dims) == [want] and dims[want] == 238 else bad)(
                "all 238 ball lands are %s mm, the %s land" % (land, fab)
                if list(dims) == [want] and dims[want] == 238 else
                "ball lands are %s; %s wants 238 at %s mm"
                % (dict(dims), fab, land))

    head("8. Routing")
    tot = sum(len(v) for v in bcon.values())
    wires = sum(len(re.findall(r"<wire ", v)) for v in bsig.values())
    vias = sum(len(re.findall(r"<via ", v)) for v in bsig.values())
    unrouted = [n for n, v in bsig.items() if "<wire " not in v and len(bcon[n]) >= 2]
    lay = collections.Counter(re.findall(r'<wire [^>]*layer="(\d+)"',
                                         "".join(bsig.values())))
    ok("%d wires, %d vias across %d signals" % (wires, vias, len(bsig)))
    if lay:
        ok("copper by layer: %s" % dict(sorted(lay.items(), key=lambda kv: int(kv[0]))))
    print("  ----  %d of %d signals carry no copper yet (%d airwire endpoints)"
          % (len(unrouted), len(bsig), tot))
    if len(unrouted) == len(bsig):
        print("        the board is placed but entirely unrouted, which is how it was generated")

    # Clearance on whatever copper is actually drawn, measured here rather than
    # trusted from whoever drew it. tools/escape.py checks its own output; this
    # is the second opinion, and it shares no code with it. Every wire is
    # compared against every pad and every other wire that carries a different
    # net, at the board's own mdWireWire / mdWirePad.
    if wires:
        def d_pt(a, c, p):
            (ax, ay), (cx, cy), (px, py) = a, c, p
            dx, dy = cx - ax, cy - ay
            L = dx * dx + dy * dy
            t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
            return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

        def d_rect(a, c, px, py, hx, hy, n=64):
            """distance from segment a-c to the axis-aligned pad rectangle.

            Sampled. The point-to-rectangle distance is convex along a segment,
            so the sampled minimum overstates the true distance by at most the
            sagitta over one step -- microns here, against a 0.09 mm limit.
            """
            best = 1e9
            for k in range(n + 1):
                t = k / float(n)
                qx, qy = a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t
                d = math.hypot(max(abs(qx - px) - hx, 0.0), max(abs(qy - py) - hy, 0.0))
                if d < best:
                    best = d
            return best

        def d_seg(a, c, p, q):
            def cr(o, x, y):
                return (x[0] - o[0]) * (y[1] - o[1]) - (x[1] - o[1]) * (y[0] - o[0])
            if ((cr(p, q, a) > 0) != (cr(p, q, c) > 0)) and \
               ((cr(a, c, p) > 0) != (cr(a, c, q) > 0)):
                return 0.0
            return min(d_pt(a, c, p), d_pt(a, c, q), d_pt(p, q, a), d_pt(p, q, c))

        par = lambda k: float((re.search(r'<param name="%s" value="([\d.]+)mm"/>' % k, b)
                               or [None, "0"])[1])
        cw, cp = par("mdWireWire"), par("mdWirePad")
        cd, cv = par("mdDrill"), par("mdPadVia")
        seg = []
        for nm, v in bsig.items():
            for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
                                 r'y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"', v):
                x1, y1, x2, y2, wd = map(float, w.groups()[:5])
                # COPPER LAYERS ONLY. 1-16 are the routing layers; 17 is pads,
                # 18 vias, 19 UNROUTED and 20 the dimension. Fusion's autorouter
                # leaves the connections it could not make as layer-19 airwires
                # INSIDE <signals>, and counting those as copper is nonsense in
                # both directions: it reported every signal as carrying copper
                # when 107 of those wires were airwires, and it read airwires
                # crossing each other as 404 clearance violations at exactly
                # 0.0000 mm. Nothing here had ever written layer 19, so the hole
                # only opened when a real CAD tool wrote the file.
                if not 1 <= int(w.group(6)) <= 16:
                    continue
                seg.append((nm, int(w.group(6)), (x1, y1), (x2, y2), wd))
        # every pad and smd on the board, with the net it carries
        pnet = {(e, pd): n for n, cs in bcon.items() for e, pd in cs}
        cop = []
        for p, (lib, pkname) in el.items():
            body = bpkg.get((lib, pkname), "")
            ox, oy, rot = epos[p]
            # An SMD lives on ONE layer, and a mirrored element flips it to 16.
            # Comparing a top-layer wire against the decoupling capacitors tiled
            # on the BACK under the BGA is what the first version of this check
            # did, and it reported 38 shorts that are not there.
            side = 16 if rot.startswith("M") else 1
            for mm in re.finditer(r'<smd ([^>]*)/>', body):
                at = mm.group(1)
                nmm = re.search(r'name="([^"]+)"', at)
                gx = re.search(r'\sx="([-\d.]+)"', at)
                gy = re.search(r'\sy="([-\d.]+)"', at)
                gdx = re.search(r'dx="([\d.]+)"', at)
                gdy = re.search(r'dy="([\d.]+)"', at)
                if not (nmm and gx and gy and gdx and gdy):
                    continue
                mm = nmm
                x, y = float(gx.group(1)), float(gy.group(1))
                dx, dy = float(gdx.group(1)), float(gdy.group(1))
                # ROUNDNESS MATTERS. Eagle's roundness is a percentage of the
                # short axis: 0 is a true rectangle, 100 a stadium (a circle
                # when dx == dy). U1's 238 ball lands are 0.225 square at
                # roundness 100 -- circles of radius 0.1125 -- and squaring them
                # off puts a corner 0.159 from the centre, 0.047 further out
                # than the pad goes. That alone reported 6 violations at exactly
                # 0.0820 in escape and ground copper that is in fact clear.
                #
                # A rounded rectangle is the Minkowski sum of a smaller
                # rectangle with a disc, so measure to the shrunken rectangle
                # and subtract the corner radius. Exact for both extremes.
                rnd = re.search(r'roundness="([\d.]+)"', at)
                cr = (float(rnd.group(1)) / 100.0) * min(dx, dy) / 2.0 if rnd else 0.0
                a = rp(x, y, rot)
                # AN SMD PAD IS A RECTANGLE. It used to be measured as a circle
                # of radius max(dx, dy)/2, which is the circumscribed circle of
                # the LONG axis -- for U3's 0.40 x 1.35 TSOP-II pads that is a
                # 0.675 mm disc on a 0.80 mm pitch, so the discs of two adjacent
                # pads overlap and NOTHING can be routed to that part at all. A
                # normal fan-out stub from a pad to its own via was reported as
                # 202 violations against neighbouring pads it never touches.
                # 180 of this board's 482 SMD pads are worse than 2:1, so the
                # error was not confined to U3.
                #
                # No <smd> here carries its own rot, so the element's rotation
                # just swaps the axes. Roundness is handled above and is not
                # optional: treating a fully-rounded pad as square is wrong in
                # the strict direction, which is how the ball lands produced six
                # violations that were not real.
                hx, hy = ((dx / 2.0, dy / 2.0)
                          if rot.lstrip("M") not in ("R90", "R270")
                          else (dy / 2.0, dx / 2.0))
                cop.append((pnet.get((p, mm.group(1))), ox + a[0], oy + a[1],
                            max(dx, dy) / 2.0, side,
                            max(hx - cr, 0.0), max(hy - cr, 0.0), cr, None))
            for mm in re.finditer(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"'
                                  r'[^>]*drill="([\d.]+)"(?:[^>]*diameter="([\d.]+)")?', body):
                x, y, dr = float(mm.group(2)), float(mm.group(3)), float(mm.group(4))
                di = float(mm.group(5)) if mm.group(5) else dr + 0.5
                a = rp(x, y, rot)
                # A THROUGH-HOLE PAD IS SMALLER ON THE INNER LAYERS. Eagle draws
                # the full pad on top and bottom and a RESTRING ANNULUS on the
                # layers in between -- drill plus rvPadInner, clamped by
                # rlMinPadInner and rlMaxPadInner. Applying the drawn diameter to
                # all six read 233 clearances against X2's DIP pads that are not
                # there. It never showed up before because nothing routed heavily
                # on L3/L4 near X2 until Fusion's autorouter did.
                _rs = min(max(dr * RVPADI, RLMINPADI), RLMAXPADI)
                _ri = min(dr / 2.0 + _rs, di / 2.0)
                cop.append((pnet.get((p, mm.group(1))), ox + a[0], oy + a[1], di / 2.0, 0,
                            None, None, 0.0, _ri))
        # Vias are copper on every layer and a wire may legitimately end on one.
        vlist, dlist = [], []
        for nm, v in bsig.items():
            for vx, vy, vd in G.vias(v):
                vlist.append((nm, vx, vy, vd))
        for nm, v in bsig.items():
            for _x, _y, _dr in re.findall(
                    r'<via x="([-\d.]+)" y="([-\d.]+)" extent="[^"]*" drill="([\d.]+)"', v):
                dlist.append((nm, float(_x), float(_y), float(_dr)))
        for nm, vx, vy, dia in vlist:
            cop.append((nm, vx, vy, dia / 2.0, 0, None, None, 0.0, None))

        viol = []
        for i in range(len(vlist)):
            for j in range(i + 1, len(vlist)):
                if vlist[i][0] == vlist[j][0]:
                    continue
                d = math.hypot(vlist[i][1] - vlist[j][1], vlist[i][2] - vlist[j][2])                     - vlist[i][3] / 2 - vlist[j][3] / 2
                if d < cw - 1e-6:
                    viol.append("%s via vs %s via: %.4f" % (vlist[i][0], vlist[j][0], d))
        # DRILL TO DRILL, AND IT DOES NOT CARE WHOSE NET IT IS. Everything above
        # is a COPPER rule, so it skips same-net pairs -- correctly, two traces
        # of one signal may touch. A drill is not copper, it is a mechanical
        # operation, and two holes 0.01 mm apart cannot be made whatever they
        # are connected to. Nothing here checked it at all, and Fusion's own DRC
        # found 107 where this file reported a clean board: 93 of them the escape
        # ring at 0.390 mm pitch on 0.2 mm drills, which is 0.190 edge to edge
        # against mdDrill 0.200, and three of them SAME-NET vias sitting on top
        # of each other -- EN_BIAS at 0.010 mm apart, SW2_NET overlapping by
        # 0.048. A checker that reports 0 findings on that is worse than no
        # checker.
        for i in range(len(dlist)):
            for j in range(i + 1, len(dlist)):
                d = math.hypot(dlist[i][1] - dlist[j][1], dlist[i][2] - dlist[j][2])                     - dlist[i][3] / 2 - dlist[j][3] / 2
                if d < cd - 1e-6:
                    viol.append("%s drill vs %s drill: %.4f, needs %.4f"
                                % (dlist[i][0], dlist[j][0], d, cd))
        # A VIA AGAINST A FOREIGN PAD. Wires were checked against pads and vias
        # against vias; the pair in between was never tested, so an escape via
        # 0.0445 mm from a ball land passed in silence.
        for nm, vx, vy, dia in vlist:
            for onet, px, py, r, side, hx, hy, cr, ri in cop:
                if onet == nm or onet is None or hx is None:
                    continue
                dx = max(0.0, abs(vx - px) - hx)
                dy = max(0.0, abs(vy - py) - hy)
                d = math.hypot(dx, dy) - cr - dia / 2.0
                if d < cv - 1e-6:
                    viol.append("%s via vs %s pad: %.4f, needs %.4f" % (nm, onet, d, cv))
        for nm, ly, a, c, wd in seg:
            for onet, px, py, r, side, hx, hy, cr, ri in cop:
                if onet == nm or (side and side != ly):    # side 0 = plated, all layers
                    continue
                rr = ri if (ri is not None and ly not in (1, 16)) else r
                d = (d_rect(a, c, px, py, hx, hy) - cr if hx is not None
                     else d_pt(a, c, (px, py)) - rr) - wd / 2.0
                if d < cp - 1e-6:
                    viol.append("%s wire vs %s pad: %.4f, needs %.4f" % (nm, onet, d, cp))
        for i in range(len(seg)):
            for j in range(i + 1, len(seg)):
                if seg[i][0] == seg[j][0] or seg[i][1] != seg[j][1]:
                    continue
                d = d_seg(seg[i][2], seg[i][3], seg[j][2], seg[j][3]) \
                    - seg[i][4] / 2.0 - seg[j][4] / 2.0
                if d < cw - 1e-6:
                    viol.append("%s vs %s wire: %.4f, needs %.4f" % (seg[i][0], seg[j][0], d, cw))
        (ok if not viol else bad)(
            "all %d wires and %d vias clear foreign copper by >= %.3f / %.3f"
            % (len(seg), len(vlist), cp, cw) if not viol else
            "%d clearance violation(s): %s" % (len(viol), sorted(set(viol))[:4]))

        # Copper that clears everything can still connect nothing. Every wire end
        # has to land on a pad of its own net or meet another wire of it -- a
        # gang trace slid off its row keeps its clearance and stops being a
        # connection, and nothing else here would notice.
        own = collections.defaultdict(set)
        for onet, px, py, r, side, hx, hy, cr, _ri in cop:
            own[onet].add((round(px, 3), round(py, 3)))     # pads, smds and vias
        ends = collections.defaultdict(collections.Counter)
        for nm, ly, aa, cc, wd in seg:
            for e in (aa, cc):
                ends[nm][(round(e[0], 3), round(e[1], 3))] += 1
        loose = [(nm, e) for nm, cnt in ends.items() for e, k in cnt.items()
                 if k == 1 and e not in own[nm]]
        (ok if not loose else bad)(
            "every wire end lands on its own net's copper" if not loose else
            "%d wire end(s) connect to nothing: %s" % (len(loose), loose[:4]))

    print("\n" + "=" * 62)
    print("%d finding(s)" % len(findings))
    return len(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "zulu_a7.brd"),
                  sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "zulu_a7.sch")))
