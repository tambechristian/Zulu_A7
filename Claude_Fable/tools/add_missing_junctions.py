# -*- coding: utf-8 -*-
"""Insert the junction dots a net is missing, without disturbing the stray ones.

A junction belongs where E + 2T + (1 if a pin sits there) >= 3 -- E wires
ending at the point, T passing through. This adds every such point that has no
junction and touches nothing else, so the 59 long-standing stray dots on the
supply rails stay exactly as they are rather than being swept up in a change
that was not about them.

Junctions live inside a <segment>, so each missing point is added to whichever
segment of its net actually owns wires at that point.

    python tools/add_missing_junctions.py [path/to/file.sch]
"""
import re, io, os, sys, collections

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def rp(dx, dy, rot):
    r = re.sub(r"^M", "", rot or "R0")
    x, y = {"R0": (dx, dy), "R90": (-dy, dx), "R180": (-dx, -dy), "R270": (dy, -dx)}[r]
    return (-x, y) if (rot or "").startswith("M") else (x, y)


def run(path):
    text = open(path, encoding="utf-8").read()
    SYM = {m.group(1): m.group(2) for m in re.finditer(r'<symbol name="([^"]+)">(.*?)</symbol>', text, re.S)}
    SP = {k: [(q.group(1), float(q.group(2)), float(q.group(3)))
              for q in re.finditer(r'<pin name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', v)]
          for k, v in SYM.items()}
    GATE = {}
    for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', text, re.S):
        for gt, s in re.findall(r'<gate name="([^"]+)" symbol="([^"]+)"', dm.group(2)):
            GATE[(dm.group(1), gt)] = s
    DS = {m.group(1): m.group(2) for m in
          re.finditer(r'<part name="([^"]+)" library="[^"]+" deviceset="([^"]+)"', text)}

    added = 0
    for sh in re.findall(r"<sheet name[^>]*>.*?</sheet>", text, re.S):
        pins = set()
        for m in re.finditer(r'<instance part="([^"]+)" gate="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"([^>]*)>', sh):
            ix, iy = float(m.group(3)), float(m.group(4))
            rot = (re.search(r'rot="(M?R\d+)"', m.group(5)) or [None, None])[1]
            for _pn, px, py in SP.get(GATE.get((DS.get(m.group(1), ""), m.group(2)), ""), []):
                dx, dy = rp(px, py, rot)
                pins.add((round(ix + dx, 2), round(iy + dy, 2)))
        newsh = sh
        for nm in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', sh, re.S):
            segs = [s.group(0) for s in re.finditer(r"<segment>.*?</segment>", nm.group(2), re.S)]
            W, J = [], set()
            for s in segs:
                W += [tuple(map(float, q.groups())) for q in re.finditer(
                    r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', s)]
                J |= {(round(float(q.group(1)), 2), round(float(q.group(2)), 2))
                      for q in re.finditer(r'<junction x="([-\d.]+)" y="([-\d.]+)"/>', s)}
            pts = collections.Counter()
            for a, b, c, d in W:
                pts[(round(a, 2), round(b, 2))] += 1
                pts[(round(c, 2), round(d, 2))] += 1
            need = set()
            for p, cnt in pts.items():
                th = sum(1 for a, b, c, d in W
                         if (round(a, 2), round(b, 2)) != p and (round(c, 2), round(d, 2)) != p
                         and ((abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6 and min(a, c) < p[0] < max(a, c))
                              or (abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6 and min(b, d) < p[1] < max(b, d))))
                if cnt + 2 * th + (1 if p in pins else 0) >= 3:
                    need.add(p)
            for p in sorted(need - J):
                owner = None
                for s in segs:
                    for q in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', s):
                        a, b, c, d = map(float, q.groups())
                        if ((round(a, 2), round(b, 2)) == p or (round(c, 2), round(d, 2)) == p):
                            owner = s
                            break
                    if owner:
                        break
                assert owner, (nm.group(1), p)
                fixed = owner.replace("</segment>", '<junction x="%s" y="%s"/>\n</segment>'
                                      % (("%.4f" % p[0]).rstrip("0").rstrip("."),
                                         ("%.4f" % p[1]).rstrip("0").rstrip(".")), 1)
                newsh = newsh.replace(owner, fixed, 1)
                segs[segs.index(owner)] = fixed
                added += 1
                print("    %-12s junction added at (%s, %s)" % (nm.group(1), p[0], p[1]))
        if newsh != sh:
            text = text.replace(sh, newsh, 1)
    import xml.etree.ElementTree as ET
    ET.fromstring(text)
    open(path, "w", encoding="utf-8").write(text)
    print("added %d junctions in %s" % (added, path))
    return 0


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "zulu_a7.sch"))
    sys.exit(run(t))
