# -*- coding: utf-8 -*-
"""Put every instance, wire and junction on one sheet back on the 1.27 mm grid.

    python tools/regrid_sheet.py "FPGA POWER" [path/to/file.sch]

WHY. Most sheets in this file are partly off-grid, and by many different
amounts. Anything wired between two parts whose offsets differ needs a dogleg
wire to close the gap -- there were 22 on sheet 5 alone, between 0.013 and
0.19 mm. They are invisible at normal zoom, they render as small rings when you
zoom in, and they make a sheet fragile: nudge one part in Fusion and its runs
come away from the taps, which happened to the EEPROM block twice running.

HOW. Every x and y is snapped independently with round(v/1.27)*1.27. Doing it
per coordinate rather than per point is what makes this safe:

  - a horizontal wire has one y, so both ends snap to the same y and it stays
    horizontal; likewise vertical. No wire can go diagonal.
  - a T-point sits on a wire because it shares that wire's y (or x) and lies
    between its ends. Snapping is monotonic, so it still does.
  - a pin lands where the wire meeting it lands, PROVIDED the symbol's pin
    offsets are multiples of the grid -- so snap(instance + offset) equals
    snap(instance) + offset. The script asserts this per sheet and refuses to
    run otherwise.

Wires whose two ends snap together become zero-length and are dropped; that is
the dogleg disappearing, and it cannot disconnect anything because whatever met
the wire at either end now meets at the one surviving point. Wires that become
exact duplicates of another wire on the same net are dropped too.

JUNCTIONS are recomputed rather than carried across, and the candidate points
are wire ends, pin positions AND existing dots. Enumerating only wire ends --
which this project did for a long time -- misses the commonest case on a supply
rail: a decoupling pin landing straight on the rail with no stub of its own has
E=0, so it was never even considered and its perfectly correct dot was reported
as stray. That single omission accounted for 55 of the 56 "strays" this project
believed it had.

They are also evaluated per net, not per segment: a dot can legitimately live
in a segment that owns no wire at that point, because the wires meeting there
belong to sibling segments of the same net.

Removing a dot is safe when fewer than three things meet there -- except at an
X crossing, where Eagle treats the dot itself as the connection. The script
checks every dot it is about to drop and aborts if one sits on a crossing.

Smashed attributes move by their instance's own delta so text stays put
relative to its part, and each label moves by the delta of the nearest wire
point in its own segment. <plain> is left alone; it carries no connectivity.
"""

import re, io, os, sys, shutil, collections, math

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = 1.27


def sn(v):
    return round(round(float(v) / G) * G, 4)


def g(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def netlist(t):
    d = collections.defaultdict(set)
    for m in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', t, re.S):
        d[m.group(1)].update(re.findall(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', m.group(2)))
    return {k: frozenset(v) for k, v in d.items()}


def rp(dx, dy, rot):
    r = re.sub(r"^M", "", rot or "R0")
    x, y = {"R0": (dx, dy), "R90": (-dy, dx), "R180": (-dx, -dy), "R270": (dy, -dx)}[r]
    return (-x, y) if (rot or "").startswith("M") else (x, y)


def through(p, w):
    """does wire w pass strictly through p, without ending there?"""
    a, b, c, d = w
    return (((round(a, 3), round(b, 3)) != p and (round(c, 3), round(d, 3)) != p)
            and ((abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6 and min(a, c) < p[0] < max(a, c))
                 or (abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6 and min(b, d) < p[1] < max(b, d))))


def needed(ws, pins, extra=()):
    """E + 2T + (1 if a pin sits there) >= 3, over ends + pins + existing dots"""
    E = collections.Counter()
    for a, b, c, d in ws:
        E[(round(a, 3), round(b, 3))] += 1
        E[(round(c, 3), round(d, 3))] += 1
    out = set()
    for p in set(E) | set(pins) | set(extra):
        if E[p] + 2 * sum(1 for w in ws if through(p, w)) + (1 if p in pins else 0) >= 3:
            out.add(p)
    return out


def components(ws, pts):
    adj = collections.defaultdict(set)
    nodes = set(pts)
    for a, b, c, d in ws:
        p, q = (round(a, 3), round(b, 3)), (round(c, 3), round(d, 3))
        nodes |= {p, q}; adj[p].add(q); adj[q].add(p)
    for p in list(nodes):
        for w in ws:
            if through(p, w):
                e = [(round(w[0], 3), round(w[1], 3)), (round(w[2], 3), round(w[3], 3))]
                adj[p] |= set(e)
                for x in e:
                    adj[x].add(p)
    seen, comps = set(), []
    for s in nodes:
        if s in seen:
            continue
        stack, cur = [s], set(); seen.add(s)
        while stack:
            u = stack.pop(); cur.add(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); stack.append(v)
        comps.append(frozenset(cur))
    return comps


def run(SHEET, SRC):
    text = open(SRC, encoding="utf-8").read()
    N0 = netlist(text)
    SYM = {m.group(1): m.group(2) for m in re.finditer(r'<symbol name="([^"]+)">(.*?)</symbol>', text, re.S)}
    SP = {k: [(q.group(1), float(q.group(2)), float(q.group(3)))
              for q in re.finditer(r'<pin name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', v)]
          for k, v in SYM.items()}
    GA = {}
    for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', text, re.S):
        for gt, s in re.findall(r'<gate name="([^"]+)" symbol="([^"]+)"', dm.group(2)):
            GA[(dm.group(1), gt)] = s
    DS = {m.group(1): m.group(2) for m in
          re.finditer(r'<part name="([^"]+)" library="[^"]+" deviceset="([^"]+)"', text)}

    def pins_of(block):
        out = set()
        for m in re.finditer(r'<instance part="([^"]+)" gate="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"([^>]*)>', block):
            ix, iy = float(m.group(3)), float(m.group(4))
            rot = (re.search(r'rot="(M?R\d+)"', m.group(5)) or [None, None])[1]
            for _n, px, py in SP.get(GA.get((DS.get(m.group(1), ""), m.group(2)), ""), []):
                dx, dy = rp(px, py, rot)
                out.add((round(ix + dx, 3), round(iy + dy, 3)))
        return out

    def parse(nb):
        out = []
        for m in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', nb, re.S):
            for s in re.finditer(r"<segment>(.*?)</segment>", m.group(2), re.S):
                ws = [tuple(map(float, q.groups())) for q in re.finditer(
                    r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', s.group(1))]
                js = {(round(float(q.group(1)), 3), round(float(q.group(2)), 3))
                      for q in re.finditer(r'<junction x="([-\d.]+)" y="([-\d.]+)"/>', s.group(1))}
                out.append((m.group(1), s.group(1), ws, js))
        return out

    def by_net(segs):
        w, j = collections.defaultdict(list), collections.defaultdict(set)
        for n, _s, ws, js in segs:
            w[n] += ws; j[n] |= js
        return w, j

    def grouping(segs, pins):
        out = []
        for n, _s, ws, _js in segs:
            own = {p for p in pins if any(p in ((round(a, 3), round(b, 3)), (round(c, 3), round(d, 3)))
                                          for a, b, c, d in ws) or any(through(p, w) for w in ws)}
            out.append((n, len([c for c in components(ws, own) if c & own])))
        return out

    sm = re.search(r'(<sheet name="%s">)(.*?)(</sheet>)' % re.escape(SHEET), text, re.S)
    assert sm, "no sheet named %r" % SHEET
    head, body, tail = sm.group(1), sm.group(2), sm.group(3)
    nm = re.search(r"(<nets>)(.*?)(</nets>)", body, re.S)
    im = re.search(r"(<instances>)(.*?)(</instances>)", body, re.S)
    print("=== %s ===" % SHEET)
    if not nm or not im:
        print("    no nets or no instances; nothing to do"); return 0
    PINS0 = pins_of(body)

    # -- precondition: this sheet's symbols must have grid-aligned pin offsets
    syms = {GA.get((DS.get(m.group(1), ""), m.group(2)), "")
            for m in re.finditer(r'<instance part="([^"]+)" gate="([^"]+)"', body)}
    off = {s for s in syms if any(abs(x / G - round(x / G)) > 1e-9 or abs(y / G - round(y / G)) > 1e-9
                                  for _n, x, y in SP.get(s, []))}
    assert not off, "symbols with off-grid pin offsets: %s" % sorted(off)

    segs0 = parse(nm.group(2))
    W0, J0 = by_net(segs0)
    miss0 = sum(len(needed(W0[n], PINS0, J0[n]) - J0[n]) for n in W0)
    stray0 = sum(len(J0[n] - needed(W0[n], PINS0, J0[n])) for n in W0)
    GROUP0 = grouping(segs0, PINS0)
    print("    before: %d instances, %d wires, %d dots (%d missing, %d stray)"
          % (len(re.findall(r'<instance part=', body)), sum(len(v) for v in W0.values()),
             sum(len(v) for v in J0.values()), miss0, stray0))

    # -- 1. instances ------------------------------------------------------
    moved = [0]

    def do_instance(m):
        blk, x, y = m.group(0), float(m.group(2)), float(m.group(3))
        dx, dy = round(sn(x) - x, 4), round(sn(y) - y, 4)
        if dx == 0 and dy == 0:
            return blk
        moved[0] += 1
        nb = blk.replace('x="%s" y="%s"' % (m.group(2), m.group(3)),
                         'x="%s" y="%s"' % (g(sn(x)), g(sn(y))), 1)
        return re.sub(r'(<attribute name="[^"]+" x=")([-\d.]+)(" y=")([-\d.]+)(")',
                      lambda a: a.group(1) + g(float(a.group(2)) + dx) + a.group(3)
                      + g(float(a.group(4)) + dy) + a.group(5), nb)

    inst_new = re.sub(r'<instance part="([^"]+)" gate="[^"]+" x="([-\d.]+)" y="([-\d.]+)".*?(?:</instance>|/>)',
                      do_instance, im.group(2), flags=re.S)

    # -- 2. wires and labels ----------------------------------------------
    stat = collections.Counter()

    def do_segment(m):
        s = m.group(1)
        pts = [(float(q.group(1)), float(q.group(2))) for q in
               re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)"', s)]
        pts += [(float(q.group(3)), float(q.group(4))) for q in re.finditer(
            r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', s)]
        seen = set()

        def wire(q):
            a, b, c, d = (float(q.group(i)) for i in (1, 2, 3, 4))
            p, r = (sn(a), sn(b)), (sn(c), sn(d))
            if p == r:
                stat["collapsed"] += 1
                return ""
            k = tuple(sorted((p, r)))
            if k in seen:
                stat["duplicate"] += 1
                return ""
            seen.add(k)
            return '<wire x1="%s" y1="%s" x2="%s" y2="%s"%s' % (g(p[0]), g(p[1]), g(r[0]), g(r[1]), q.group(5))

        s = re.sub(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"([^>]*/>\n?)', wire, s)

        def label(q):
            x, y = float(q.group(1)), float(q.group(2))
            if pts:
                nx, ny = min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
                return '<label x="%s" y="%s"%s' % (g(x + sn(nx) - nx), g(y + sn(ny) - ny), q.group(3))
            return '<label x="%s" y="%s"%s' % (g(sn(x)), g(sn(y)), q.group(3))

        s = re.sub(r'<label x="([-\d.]+)" y="([-\d.]+)"([^>]*/>)', label, s)
        s = re.sub(r'<junction x="[-\d.]+" y="[-\d.]+"/>\n?', "", s)
        return "<segment>%s</segment>" % s

    nets_new = re.sub(r"<segment>(.*?)</segment>", do_segment, nm.group(2), flags=re.S)
    print("    %d instances moved (max %.4f mm); %d wires collapsed, %d duplicates dropped"
          % (moved[0], max([abs(sn(float(q.group(2))) - float(q.group(2))) for q in
                            re.finditer(r'<instance part="([^"]+)" gate="[^"]+" x="([-\d.]+)"', body)] +
                           [abs(sn(float(q.group(2))) - float(q.group(2))) for q in
                            re.finditer(r'<instance part="([^"]+)" gate="[^"]+" x="[-\d.]+" y="([-\d.]+)"', body)]),
             stat["collapsed"], stat["duplicate"]))

    body_new = body.replace(im.group(0), im.group(1) + inst_new + im.group(3), 1)
    body_new = body_new.replace(nm.group(0), nm.group(1) + nets_new + nm.group(3), 1)

    # -- 3. junctions ------------------------------------------------------
    PINS1 = pins_of(body_new)
    segs1 = parse(re.search(r"<nets>(.*?)</nets>", body_new, re.S).group(1))
    W1, _ = by_net(segs1)
    OLD = {}
    for n, s, _ws, js in segs0:
        for p in js:
            OLD.setdefault((n, (sn(p[0]), sn(p[1]))), s)
    place, added = collections.defaultdict(list), 0
    for n in W1:
        want = needed(W1[n], PINS1)
        # a dot about to be dropped must not be holding an X crossing together
        for p in {(sn(a), sn(b)) for a, b in J0[n]} - want:
            h = [w for w in W1[n] if through(p, w) and abs(w[1] - w[3]) < 1e-6]
            v = [w for w in W1[n] if through(p, w) and abs(w[0] - w[2]) < 1e-6]
            assert not (h and v), "dot at an X crossing on %s at %s -- refusing to drop it" % (n, p)
        for p in sorted(want):
            owner = None
            for m, s, ws, _js in segs1:
                if m == n and any((round(a, 3), round(b, 3)) == p or (round(c, 3), round(d, 3)) == p
                                  or through(p, (a, b, c, d)) for a, b, c, d in ws):
                    owner = s; break
            owner = owner if owner is not None else OLD.get((n, p))
            assert owner is not None, (n, p)
            place[owner].append(p); added += 1
    for s, ps in place.items():
        body_new = body_new.replace(
            "<segment>%s</segment>" % s,
            "<segment>%s%s</segment>" % (s, "".join('<junction x="%s" y="%s"/>\n' % (g(a), g(b))
                                                    for a, b in sorted(ps))), 1)

    text = text.replace(sm.group(0), head + body_new + tail, 1)

    # -- 4. verify ---------------------------------------------------------
    import xml.etree.ElementTree as ET
    ET.fromstring(text)
    assert netlist(text) == N0, "netlist changed"
    body2 = re.search(r'<sheet name="%s">(.*?)</sheet>' % re.escape(SHEET), text, re.S).group(1)
    segs2 = parse(re.search(r"<nets>(.*?)</nets>", body2, re.S).group(1))
    PINS2 = pins_of(body2)
    assert grouping(segs2, PINS2) == GROUP0, "a segment's pins changed how they group"
    W2, J2 = by_net(segs2)
    miss = sum(len(needed(W2[n], PINS2, J2[n]) - J2[n]) for n in W2)
    stray = sum(len(J2[n] - needed(W2[n], PINS2, J2[n])) for n in W2)
    ep = [p for _n, _s, ws, _j in segs2 for a, b, c, d in ws for p in ((a, b), (c, d))]
    bad = sum(1 for x, y in ep if abs(x / G - round(x / G)) > 1e-9 or abs(y / G - round(y / G)) > 1e-9)
    ib = sum(1 for q in re.finditer(r'<instance part="[^"]+" gate="[^"]+" x="([-\d.]+)" y="([-\d.]+)"', body2)
             if abs(float(q.group(1)) / G - round(float(q.group(1)) / G)) > 1e-9
             or abs(float(q.group(2)) / G - round(float(q.group(2)) / G)) > 1e-9)
    tiny = sum(1 for _n, _s, ws, _j in segs2 for a, b, c, d in ws if math.hypot(c - a, d - b) < 1.0)
    print("    after : %d wires, %d dots (%d missing, %d stray); off-grid endpoints %d, instances %d, wires <1mm %d"
          % (sum(len(v) for v in W2.values()), added, miss, stray, bad, ib, tiny))
    assert (miss, stray, bad, ib, tiny) == (0, 0, 0, 0, 0)
    open(SRC, "w", encoding="utf-8").write(text)
    return 0


if __name__ == "__main__":
    src = sys.argv[2] if len(sys.argv) > 2 else os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "zulu_a7.sch"))
    sys.exit(run(sys.argv[1], src))
