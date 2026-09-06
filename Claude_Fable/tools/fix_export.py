# -*- coding: utf-8 -*-
"""Repair the two nets the hand-redraw broke, and put back every missing dot.

WHY THIS EXISTS. Fusion's export of 2026-08-29 came back with 177 nets where
HEAD has 175. Redrawing the "fallen apart" wires by hand deleted one wire and
left one junction 1.27 mm off its landing point, and the two pieces that came
loose were auto-named N$1 and N$2:

    EN_BIAS  lost R75.1, Q3.A.C, Q3.B.B -- the bridge wire
             (46.99,153.67)-(55.88,153.67) was deleted, leaving the two runs
             dead-ending 8.89 mm apart.
    VCC3V3   lost J1.6 -- its wire ends ON the rail at (53.34,107.95) with no
             junction, so Eagle reads a crossing; the dot that should be there
             was placed at (53.34,109.22), mid-run on a collinear split where
             it does nothing.

ERC cannot see either one: a two-pin net and a one-pin net are both perfectly
"connected" as far as it is concerned. Only the netlist diff against HEAD finds
them, which is why that diff is the gate for every schematic edit.

THE JUNCTION PASS IS GENERAL, THE MERGE IS NOT. Reconnecting a net means
deciding which two things were meant to touch, and that is a judgement -- so
the merges are a table of four coordinates each, checked against HEAD. Adding
the dots is mechanical, so it runs over the whole file under junction_audit's
own rule: E + 2T + (1 if a pin sits there) >= 3. A fix measured by a different
model than the check is not a fix, so junction_audit.py is the verifier here
and this file must track its rule.

    python tools/fix_export.py            report
    python tools/fix_export.py --apply    write it

The file is CRLF. Read it through text mode and write it back with newline=""
and all 18 000 lines change; this reads bytes and keeps the EOL it found.
"""
import io
import os
import re
import sys
import collections
import xml.etree.ElementTree as ET

_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(ROOT, "zulu_a7.sch")
W = 'width="0.1524" layer="91"'

# sheet, the orphan to absorb, the net it belongs to, a wire that identifies
# which segment of that net to absorb it into, wires to draw, wires to delete.
REPAIRS = [
    dict(sheet=2, orphan="N$1", into="EN_BIAS",
         anchor=(55.88, 153.67, 55.88, 148.59),
         add=[(46.99, 153.67, 55.88, 153.67)]),
    dict(sheet=3, orphan="N$2", into="VCC3V3",
         anchor=(48.26, 107.95, 81.28, 107.95),
         add=[]),
]


def g(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def key(w):
    """a wire as an unordered pair -- Eagle writes them either way round"""
    a, b, c, d = [round(float(q), 2) for q in w]
    return tuple(sorted([(a, b), (c, d)]))


def wires_of(txt):
    return [q.groups() for q in re.finditer(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
        r' width="[\d.]+" layer="91"/>', txt)]


def pinmap(t):
    """every pin position on every sheet -- junction_audit's transform"""
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

    def rp(dx, dy, rot):
        r = re.sub(r"^M", "", rot or "R0")
        x, y = {"R0": (dx, dy), "R90": (-dy, dx),
                "R180": (-dx, -dy), "R270": (dy, -dx)}[r]
        return (-x, y) if (rot or "").startswith("M") else (x, y)

    out = []
    for sh in re.findall(r"<sheet name[^>]*>.*?</sheet>", t, re.S):
        pins = set()
        for m in re.finditer(r'<instance part="([^"]+)" gate="([^"]+)" x="([-\d.]+)"'
                             r' y="([-\d.]+)"([^>]*)>', sh):
            ix, iy = float(m.group(3)), float(m.group(4))
            rot = (re.search(r'rot="(M?R\d+)"', m.group(5)) or [None, None])[1]
            for _pn, px, py in sp.get(gate.get((ds.get(m.group(1), ""), m.group(2)), ""), []):
                dx, dy = rp(px, py, rot)
                pins.add((round(ix + dx, 2), round(iy + dy, 2)))
        out.append(pins)
    return out


def needed(wl, pins):
    """the points that must carry a dot, by junction_audit's rule"""
    pts = collections.Counter()
    for a, b, c, d in wl:
        pts[(round(float(a), 2), round(float(b), 2))] += 1
        pts[(round(float(c), 2), round(float(d), 2))] += 1
    fw = [tuple(map(float, w)) for w in wl]
    need = set()
    for p in set(pts) | pins:
        th = sum(1 for a, b, c, d in fw
                 if (round(a, 2), round(b, 2)) != p and (round(c, 2), round(d, 2)) != p
                 and ((abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6 and min(a, c) < p[0] < max(a, c))
                      or (abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6 and min(b, d) < p[1] < max(b, d))))
        if pts[p] + 2 * th + (1 if p in pins else 0) >= 3:
            need.add(p)
    return need


def contained(w, v):
    """w lies entirely inside collinear wire v, so deleting w changes nothing.

    NEVER DELETE A WIRE BY COORDINATE. The first cut of this file carried a
    hand-written drop list holding (46.99,135.89)-(46.99,133.35), which in the
    export of the day genuinely was a duplicate stacked inside the long
    vertical. The next export had split that same vertical in two at y=135.89,
    so the identical coordinates now named the ONLY wire reaching Q3.A.C at
    (46.99,133.35) -- and deleting it left the pinref in place, which means the
    netlist diff saw nothing at all. Containment has to be proved against the
    wires actually present, every run.
    """
    (ax, ay), (bx, by) = key(w)
    (cx, cy), (dx, dy) = key(v)
    if abs(ay - by) < 1e-9 and abs(cy - dy) < 1e-9 and abs(ay - cy) < 1e-9:
        return cx - 1e-9 <= ax and bx <= dx + 1e-9
    if abs(ax - bx) < 1e-9 and abs(cx - dx) < 1e-9 and abs(ax - cx) < 1e-9:
        return cy - 1e-9 <= ay and by <= dy + 1e-9
    return False


def dedup(seg, log):
    """drop wires stacked inside a longer collinear one, longest kept first"""
    ws = wires_of(seg)

    def ln(w):
        a, b, c, d = [float(q) for q in w]
        return abs(c - a) + abs(d - b)

    keep, drop = [], []
    for i in sorted(range(len(ws)), key=lambda q: -ln(ws[q])):
        if any(contained(ws[i], ws[j]) for j in keep):
            drop.append(ws[i])
        else:
            keep.append(i)
    for w in drop:
        el = ('<wire x1="%s" y1="%s" x2="%s" y2="%s" %s/>'
              % (w[0], w[1], w[2], w[3], W))
        seg = seg.replace(el + "\r\n", "", 1).replace(el + "\n", "", 1).replace(el, "", 1)
        log.append("   dropped wire stacked inside a longer one: (%s,%s)-(%s,%s)" % w)
    return seg


def touches(seg, p):
    for a, b, c, d in [tuple(map(float, w)) for w in wires_of(seg)]:
        if (round(a, 2), round(b, 2)) == p or (round(c, 2), round(d, 2)) == p:
            return True
        if abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6 and min(a, c) < p[0] < max(a, c):
            return True
        if abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6 and min(b, d) < p[1] < max(b, d):
            return True
    return False


def main():
    raw = io.open(SCH, "rb").read()
    eol = "\r\n" if b"\r\n" in raw else "\n"
    t = raw.decode("utf-8")
    log = []

    # ---- 1. absorb the orphans -------------------------------------------
    for r in sorted(REPAIRS, key=lambda q: -q["sheet"]):
        sheets = [m.span() for m in re.finditer(r"<sheet name[^>]*>.*?</sheet>", t, re.S)]
        s0, s1 = sheets[r["sheet"] - 1]
        sh = t[s0:s1]
        om = re.search(r'<net name="%s" class="[^"]*">(.*?)</net>(%s)?'
                       % (re.escape(r["orphan"]), eol), sh, re.S)
        if not om:
            log.append("   %-8s already absorbed" % r["orphan"])
            continue
        body = om.group(1)
        keep = []
        for el in re.findall(r"<(?:pinref|wire|junction|label)[^>]*/>", body):
            if el.startswith("<junction"):
                continue          # the junction pass below decides these
            keep.append(el)
        for a, b, c, d in r["add"]:
            keep.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" %s/>'
                        % (g(a), g(b), g(c), g(d), W))
            log.append("   drew wire (%s,%s)-(%s,%s)" % (g(a), g(b), g(c), g(d)))
        sh = sh[:om.start()] + sh[om.end():]

        tm = re.search(r'(<net name="%s" class="[^"]*">)(.*?)(</net>)'
                       % re.escape(r["into"]), sh, re.S)
        segs = re.findall(r"<segment>.*?</segment>", tm.group(2), re.S)
        want = {key(r["anchor"])}
        hit = [i for i, sg in enumerate(segs) if want & {key(q) for q in wires_of(sg)}]
        if len(hit) != 1:
            print("   !! %s: anchor wire matched %d segment(s), expected 1"
                  % (r["into"], len(hit)))
            return 1
        i = hit[0]
        segs[i] = segs[i][:segs[i].rindex("</segment>")] + \
            eol.join(keep) + eol + "</segment>"
        segs[i] = dedup(segs[i], log)
        sh = sh[:tm.start()] + tm.group(1) + eol + eol.join(segs) + eol + \
            tm.group(3) + sh[tm.end():]
        log.append("   %-8s -> %s (segment %d), %d element(s) moved"
                   % (r["orphan"], r["into"], i, len(keep)))
        t = t[:s0] + sh + t[s1:]

    # ---- 2. every dot the rule asks for, nothing it does not -------------
    PINS = pinmap(t)
    added = dropped = 0
    done = set()
    while True:
        sheets = [m.span() for m in re.finditer(r"<sheet name[^>]*>.*?</sheet>", t, re.S)]
        change = False
        for si in range(len(sheets)):
            s0, s1 = sheets[si]
            sh = t[s0:s1]
            for nm in re.finditer(r'(<net name="([^"]+)" class="[^"]*">)(.*?)(</net>)',
                                  sh, re.S):
                if (si, nm.group(2)) in done:
                    continue
                segs = re.findall(r"<segment>.*?</segment>", nm.group(3), re.S)
                wl = [q for sg in segs for q in wires_of(sg)]
                have = {(round(float(q.group(1)), 2), round(float(q.group(2)), 2))
                        for sg in segs
                        for q in re.finditer(r'<junction x="([-\d.]+)" y="([-\d.]+)"/>', sg)}
                need = needed(wl, PINS[si])
                done.add((si, nm.group(2)))
                if need == have:
                    continue
                for p in sorted(need - have):
                    tgt = [i for i, sg in enumerate(segs) if touches(sg, p)]
                    if not tgt:
                        print("   !! s%d %s: no segment touches %s"
                              % (si + 1, nm.group(2), p))
                        return 1
                    i = tgt[0]
                    segs[i] = segs[i][:segs[i].rindex("</segment>")] + \
                        '<junction x="%s" y="%s"/>' % (g(p[0]), g(p[1])) + eol + "</segment>"
                    added += 1
                for p in sorted(have - need):
                    j = '<junction x="%s" y="%s"/>' % (g(p[0]), g(p[1]))
                    for i, sg in enumerate(segs):
                        if j in sg:
                            segs[i] = sg.replace(j + eol, "", 1).replace(j, "", 1)
                            dropped += 1
                            break
                log.append("   s%d %-10s +%d dot(s) -%d stray"
                           % (si + 1, nm.group(2), len(need - have), len(have - need)))
                sh = sh[:nm.start()] + nm.group(1) + eol + eol.join(segs) + eol + \
                    nm.group(4) + sh[nm.end():]
                t = t[:s0] + sh + t[s1:]
                change = True
                break
            if change:
                break
        if not change:
            break

    for q in log:
        print(q)
    print("\n%d junction(s) added, %d stray removed" % (added, dropped))
    ET.fromstring(t)
    if "--apply" not in sys.argv:
        print("report only -- re-run with --apply to write")
        return 0
    io.open(SCH, "wb").write(t.encode("utf-8"))
    print("wrote %s (%s preserved)" % (SCH, "CRLF" if eol == "\r\n" else "LF"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
