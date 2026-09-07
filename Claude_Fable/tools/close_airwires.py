# -*- coding: utf-8 -*-
"""Close the remaining airwires: strip stale partial routes, rip the walls
around boxed-in pads, then negotiate every open net over six signal layers.

    $env:CLOSE_BOARD = "<candidate .brd>"          required
    $env:CLOSE_OUT   = "<where to write>"           default: CLOSE_BOARD
    python tools/close_airwires.py                  report only
    python tools/close_airwires.py --apply          write CLOSE_OUT

WHY THIS AND NOT reroute_negotiated_group.py. That tool takes exactly-two-pad
nets, strips ALL their copper, and routes pad to pad. The 40 nets still open on
this board are not that shape. Most carry copper worth keeping -- the BGA
fan-out from ball to ring via took a day to make legal -- and many carry copper
worth throwing away: PROG# had 14 vias and traces out to x = 0.65 on a net whose
pads all sit between x = 33 and 47, RAS# had 78 segments on L4 that never reach
U3, and A5 wandered through five vias and stopped 5 mm short. That is the debris
of earlier attempts, and it is why later attempts found no room. The nets are
not all two-pad either: VCC1V0 is 26 pads in five pieces, RST# four pads in two.

AND THE REAL BLOCKER IS NOT CONGESTION. Twelve BGA balls have no fan-out at
all: their pockets on L1 are a dozen cells wide, walled in by neighbouring
escapes, and U3's SDRAM pads sit in the same kind of pocket on L16 behind the
stubs of the bus nets that did route. A router that treats placed copper as
sacred can never reach them -- the earlier answer was a laser via in the pad
down to the GND plane, which is HDI and cuts the plane to pieces. Here the
copper forming a pocket's wall is RIPPED, one segment at a time, and its net
joins the negotiation, so the wall re-forms around the freed ball.

WHAT IT DOES.
  1. Per open net, find the pieces of copper it is in. A piece joining two or
     more pads is a real connection and is kept whole. A piece holding one pad
     is kept only as far as its ESCAPE: from the pad along its surface layer,
     inside the fan-out zone of a BGA/QFN part, up to and including the first
     through via. Everything else of the net, every piece holding no pad, and
     every blind or laser via, goes. Nets named in CLOSE_FORCE are stripped to
     their escapes even though they are connected, so they route afresh.
  2. Flood from every piece. A piece whose flood dies in a pocket without
     reaching its partner is boxed in; the copper bounding the pocket is
     ripped and its net becomes a target too (CLOSE_RIP=auto, two rounds).
  3. Route. Rails (VCC1V0, VCC1V8, VU, VEXT, USB5V0) go first, greedily, at the
     widest of CLOSE_WIDTHS that finds a path. Signals then negotiate together
     with PathFinder, every piece a SET of seed cells rather than one point, so
     a route may leave from the escape via, the ball, or any wire of the piece.
     Vias are through, 0.20 / 0.30, and keep 0.40 mm centre to centre.
  4. GND and VCC3V3 last: every stranded piece routes to the nearest cell where
     a new via would land on the MAIN piece of its plane (the raster of
     tools/plane_islands.py is a routing layer), or to copper already there.
  5. Snap every route end onto the exact centre of the pad or via it reached,
     or onto the body of the wire, so check_board's landing test agrees.
  6. Verify with check_connectivity's honest plane model. A ripped or forced
     net that failed gets its original copper back, and any new route that
     copper collides with is dropped -- nothing ends worse than it began.

Environment: CLOSE_NETS limits the run to named nets; CLOSE_EXCLUDE adds to
the GND, VCC3V3 exclusion for the signal pass; CLOSE_FORCE names connected nets
to reroute; CLOSE_RIP off|auto; CLOSE_MAXIT (8) negotiation rounds; CLOSE_LAYERS
(1,3,4,6,7,16); CLOSE_WIDTH (0.0762); CLOSE_WIDTHS (0.25,0.2,0.15,0.1,0.0762)
the rail cascade; CLOSE_WIDE_NETS the rails; CLOSE_PLANES (GND:2,VCC3V3:5), or
empty to skip the plane pass; CLOSE_ZONES (U1:7.9,U2:6.6,U8:3.2) the escape
zone radius, chebyshev, about each part's pad-field centre.
"""

import collections
import heapq
import io
import math
import os
import re
import sys
import time
from array import array

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import escape as E               # noqa: E402
import geom as G                 # noqa: E402
import pathfinder as PF          # noqa: E402
import fusion_connect as FC      # noqa: E402
import plane_islands as PI       # noqa: E402
import power as P                # noqa: E402

APPLY = "--apply" in sys.argv
BRD = os.environ.get("CLOSE_BOARD", "")
if not BRD:
    raise SystemExit("CLOSE_BOARD is required (a candidate path); refusing to"
                     " default to the root zulu_a7.brd")
OUT = os.environ.get("CLOSE_OUT", BRD)


def env_list(name, default):
    return [q.strip() for q in os.environ.get(name, default).split(",") if q.strip()]


LAYERS = tuple(env_list("CLOSE_LAYERS", "1,3,4,6,7,16"))
CORRIDOR = tuple(float(v) for v in env_list("CLOSE_CORRIDOR", "")) or None   # x0,y0,x1,y1
LAYER_I = [int(q) for q in LAYERS]
THIN = float(os.environ.get("CLOSE_WIDTH", "0.0762"))
WIDTHS = [float(q) for q in env_list("CLOSE_WIDTHS", "0.25,0.2,0.15,0.1,0.0762")]
WIDE_NETS = set(env_list("CLOSE_WIDE_NETS", "VCC1V0,VCC1V8,VU,VEXT,USB5V0"))
STEP = float(os.environ.get("CLOSE_STEP", "0.05"))
VIA_D, VIA_L = P.VIA_D, P.VIA_L
MAXIT = int(os.environ.get("CLOSE_MAXIT", "20"))
ATTEMPTS = int(os.environ.get("CLOSE_ATTEMPTS", "3"))
SEQUENTIAL = int(os.environ.get("CLOSE_SEQUENTIAL", "0") or 0)   # 1: strip one at a time; 2: strip all, route one at a time
ACCEPT_TOTAL = os.environ.get("CLOSE_ACCEPT", "") == "total"      # judge an attempt by total airwires, trades allowed
PROTECT = set(env_list("CLOSE_PROTECT", ""))
BOX0 = float(os.environ.get("CLOSE_BOX_MM", "6.0"))
EXCLUDE = set(("GND", "VCC3V3")) | set(env_list("CLOSE_EXCLUDE", ""))
ONLY = env_list("CLOSE_NETS", "")
FORCE = set(env_list("CLOSE_FORCE", ""))
RIP = os.environ.get("CLOSE_RIP", "auto")
# ONE WALL PER POCKET PER ROUND. Ripping every net that bounds a pocket
# opened 76 nets for 34 pockets, and a negotiation that size never settled.
# Taking the single largest wall each round, then flooding again, rips the
# minimum that actually lets the piece out.
RIP_ROUNDS = int(os.environ.get("CLOSE_RIP_ROUNDS", "6"))
RIP_WINDOW = float(os.environ.get("CLOSE_RIP_WINDOW", "2.5"))
RIP_GANGS = os.environ.get("CLOSE_RIP_GANGS", "1") == "1"
# A pocket is a POCKET: a few square millimetres walled in. A flood that
# reaches 20 mm2 and still misses its partner is blocked at board scale, and
# ripping its whole boundary opened 84 nets in one go. 8000 cells is 20 mm2.
POCKET_CAP = int(os.environ.get("CLOSE_POCKET_CAP", "8000"))
PLANES = dict((q.split(":")[0], int(q.split(":")[1]))
              for q in env_list("CLOSE_PLANES", "GND:2,VCC3V3:5"))
# CLOSE_EXTRA_ZONES="cx,cy,r;cx,cy,r": escape zones given by centre, for a
# part whose element origin is a corner (U3's is at its south-east pin). A
# forced net keeps its pad stub up to the first through via inside a zone;
# without one for U3, the 2026-09-06 HDI re-route stripped 29 working U3-end
# escapes and had to find a fresh via beside every pad.
EXTRA_ZONES = [tuple(float(v) for v in q.split(",")) for q in os.environ.get("CLOSE_EXTRA_ZONES", "").split(";") if q.count(",") == 2]
ZONE_R = dict((k, float(v)) for k, v in (
    q.split(":") for q in env_list("CLOSE_ZONES", "U1:7.9,U2:6.6,U8:3.2")))
MIN_DRILL_CC = 0.4          # two 0.20 drills at 0.20 hole to hole
STUB_R = 3.0                # a planned escape stub (bga_escape.py, bga_inward.py) stays within this of its ball
SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)
VIA_RE = re.compile(r"<via\b[^>]*?(?:/>|>.*?</via>)", re.S)
WIRE_RE = re.compile(r"<wire\b[^>]*/>")
T0 = time.time()


def log(msg):
    print("[%6.1fs] %s" % (time.time() - T0, msg))
    sys.stdout.flush()


def g(value):
    text = ("%.4f" % value).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def attrs_of(tag):
    return dict(re.findall(r'(\w+)="([^"]*)"', tag))


# ------------------------------------------------------------------ pads
def rp(x, y, rot):
    r = rot[1:] if rot.startswith("M") else rot
    ang = int(r[1:]) % 360 if len(r) > 1 else 0
    x, y = {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[ang]
    return (-x, y) if rot.startswith("M") else (x, y)


def pad_index(board):
    """(element, pad) -> pad object, plus element -> pad-field centre."""
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', board, re.S):
        for pm in re.finditer(r'<package name="([^"]+)"[^>]*>(.*?)</package>',
                              lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)
    pnet = {}
    for sm in SIG_RE.finditer(board):
        for c in re.finditer(r'<contactref element="([^"]+)" pad="([^"]+)"',
                             sm.group(3)):
            pnet[(c.group(1), c.group(2))] = sm.group(2)
    pads, fields = {}, {}
    for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"'
                         r'[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', board):
        nm, lib, pk = m.group(1), m.group(2), m.group(3)
        ex, ey, rot = float(m.group(4)), float(m.group(5)), m.group(6) or "R0"
        side = 16 if rot.startswith("M") else 1
        swap = rot.lstrip("M") in ("R90", "R270")
        body = pkg.get((lib, pk), "")
        pts = []
        for s in re.finditer(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" '
                             r'dx="([\d.]+)" dy="([\d.]+)"([^>]*)>', body):
            x, y, dx, dy = (float(v) for v in s.groups()[1:5])
            rnd = re.search(r'roundness="(\d+)"', s.group(6))
            a = rp(x, y, rot)
            hx, hy = (dy / 2, dx / 2) if swap else (dx / 2, dy / 2)
            pads[(nm, s.group(1))] = {
                "kind": "pad", "at": (ex + a[0], ey + a[1]), "hx": hx, "hy": hy,
                "through": False, "layers": frozenset((side,)),
                "round": bool(rnd and rnd.group(1) == "100"),
                "net": pnet.get((nm, s.group(1))), "name": "%s.%s" % (nm, s.group(1))}
            pts.append((ex + a[0], ey + a[1]))
        for s in re.finditer(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"[^>]*'
                             r'drill="([\d.]+)"(?:[^>]*diameter="([\d.]+)")?', body):
            x, y, dr = float(s.group(2)), float(s.group(3)), float(s.group(4))
            di = float(s.group(5)) if s.group(5) else dr + 0.5
            a = rp(x, y, rot)
            pads[(nm, s.group(1))] = {
                "kind": "pad", "at": (ex + a[0], ey + a[1]), "hx": di / 2, "hy": di / 2,
                "through": True, "layers": C.COPPER_LAYERS, "round": True,
                "net": pnet.get((nm, s.group(1))), "name": "%s.%s" % (nm, s.group(1))}
            pts.append((ex + a[0], ey + a[1]))
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            fields[nm] = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
    return pads, fields


# --------------------------------------------------------------- signals
def parse_items(body):
    """vias and wires of one signal body as connectivity objects + tag text."""
    items = []
    for m in VIA_RE.finditer(body):
        a = attrs_of(m.group(0))
        if "x" not in a or "y" not in a:
            continue
        drill = float(a.get("drill", "0.2"))
        dia = float(a["diameter"]) if "diameter" in a else drill + 2 * max(drill * 0.25, 0.05)
        first, last = (int(v) for v in a.get("extent", "1-16").split("-"))
        lo, hi = sorted((first, last))
        items.append({"kind": "via", "at": (float(a["x"]), float(a["y"])),
                      "radius": dia / 2.0, "drill": drill, "lo": lo, "hi": hi,
                      "layers": frozenset(L for L in C.COPPER_LAYERS if lo <= L <= hi),
                      "text": m.group(0)})
    for m in WIRE_RE.finditer(body):
        a = attrs_of(m.group(0))
        try:
            layer = int(a["layer"])
            x1, y1, x2, y2, wd = (float(a[k]) for k in ("x1", "y1", "x2", "y2", "width"))
        except (KeyError, ValueError):
            continue
        items.append({"kind": "wire", "a": (x1, y1), "b": (x2, y2), "radius": wd / 2.0,
                      "layer": layer,
                      "layers": frozenset((layer,)) if layer in C.COPPER_LAYERS else frozenset(),
                      "text": m.group(0)})
    return items


MICROVIAS = set(env_list("CLOSE_MICROVIA", "1-2,7-16"))


def same_pt(a, b):
    return abs(a[0] - b[0]) <= 1e-5 and abs(a[1] - b[1]) <= 1e-5


def blind(o):
    """a via this tool will not keep: anything that is not a 0.20 mm through
    hole -- except the HDI microvias, one dielectric deep from either outer
    layer, once the build is 1+6+1 (CLOSE_MICROVIA lists their spans)"""
    if o["kind"] != "via":
        return False
    span = "%d-%d" % (o["lo"], o["hi"])
    if span in MICROVIAS and o["drill"] < 0.2 - 1e-6:
        return False
    return o["drill"] < 0.2 - 1e-6 or (o["lo"], o["hi"]) != (1, 16)


def connected(a, b):
    """the pairwise test check_connectivity uses, as a predicate."""
    if not (a["layers"] & b["layers"]):
        return False
    eps = C.EPS
    if a["kind"] == "wire" and b["kind"] == "wire":
        return E.seg_seg(a["a"], a["b"], b["a"], b["b"]) <= a["radius"] + b["radius"] + eps
    if a["kind"] == "pad" and b["kind"] == "wire":
        return C.pad_wire(a, b)
    if a["kind"] == "wire" and b["kind"] == "pad":
        return C.pad_wire(b, a)
    if a["kind"] == "pad" and b["kind"] == "pad":
        return C.pad_pad(a, b)
    if a["kind"] == "wire":
        return E.seg_pt(a["a"], a["b"], b["at"]) <= a["radius"] + b["radius"] + eps
    if b["kind"] == "wire":
        return E.seg_pt(b["a"], b["b"], a["at"]) <= b["radius"] + a["radius"] + eps
    if a["kind"] == "pad":
        return C.pad_disc(a, b)
    if b["kind"] == "pad":
        return C.pad_disc(b, a)
    return math.hypot(a["at"][0] - b["at"][0], a["at"][1] - b["at"][1]) <= (
        a["radius"] + b["radius"] + eps)


def pieces_of(objects):
    union = C.connectivity_union(objects, set())
    groups = collections.defaultdict(list)
    for i in range(len(objects)):
        groups[union.find(i)].append(i)
    return list(groups.values())


def escape_of(objects, grp, p0, zones):
    """the escape copper of pad p0 inside `grp`: surface wires inside the
    zone, up to and including the first through via"""
    keep = set([p0])
    # A VIA IN THE PAD IS THE ESCAPE, wherever the pad is. The HDI build puts
    # 7-16 microvias in U3's pads, and U3 is in nobody's zone; dropping those
    # cost seven of them in one run before this line existed.
    for j in grp:
        oj = objects[j]
        if oj["kind"] == "via" and not blind(oj) and connected(objects[p0], oj):
            keep.add(j)
    # AND NOTHING ELSE. A ball with a microvia in it escapes on L2 from the
    # microvia; keeping its old L1 stub and the through via 3 mm away as well
    # is what kept the SDRAM bus's exit column fixed through every re-plan on
    # 2026-09-06 (the column at x 39.2 was "escape copper" of 23 nets).
    if len(keep) > 1:
        # a staggered microvia chain is part of the escape: the L2 hop from
        # the 1-2 via to the 2-3 via beside it, and that via (2+4+2 build)
        p0at = objects[p0]["at"]
        for v in list(keep):
            ov = objects[v]
            if ov["kind"] != "via":
                continue
            for j in grp:
                oj = objects[j]
                if oj["kind"] == "wire" and (oj["layers"] & ov["layers"]) and j not in keep \
                        and max(math.hypot(oj["a"][0] - p0at[0], oj["a"][1] - p0at[1]),
                                math.hypot(oj["b"][0] - p0at[0], oj["b"][1] - p0at[1])) <= 0.6 \
                        and (same_pt(oj["a"], ov["at"]) or same_pt(oj["b"], ov["at"])):
                    keep.add(j)
                    far = oj["b"] if same_pt(oj["a"], ov["at"]) else oj["a"]
                    # the via at the far end of the hop is a microvia the
                    # build allows (blind() is False for those); the test
                    # used to read blind(ok_) and so dropped every 2-3 via
                    # the ring-3 fan-out placed -- run t1 (2026-09-06) never
                    # had an L3 escape to work from.
                    for k in grp:
                        ok_ = objects[k]
                        if ok_["kind"] == "via" and not blind(ok_) and same_pt(ok_["at"], far):
                            keep.add(k)
        # THE PLANNED STUB IS PART OF THE ESCAPE. tools/bga_escape.py lays a
        # short stub from the microvia out of the ball field; it is what the
        # router must start from. Walk wires on the kept microvias' layers
        # while both ends stay within STUB_R of the ball, and keep a microvia
        # met at their far ends. Old copper further out is still dropped.
        frontier = [k for k in keep if objects[k]["kind"] == "via"]
        seen = set(frontier)
        while frontier:
            i = frontier.pop()
            for j in grp:
                if j in seen:
                    continue
                oj = objects[j]
                if oj["kind"] == "wire":
                    if not (oj["layers"] & objects[i]["layers"]) or 1 in oj["layers"] or 16 in oj["layers"]:
                        continue
                    if max(math.hypot(oj["a"][0] - p0at[0], oj["a"][1] - p0at[1]),
                           math.hypot(oj["b"][0] - p0at[0], oj["b"][1] - p0at[1])) > STUB_R:
                        continue
                    if connected(objects[i], oj):
                        seen.add(j)
                        keep.add(j)
                        frontier.append(j)
                elif oj["kind"] == "via" and not blind(oj) and connected(objects[i], oj):
                    seen.add(j)
                    keep.add(j)
                    frontier.append(j)
        return keep
    zone = None
    for cx, cy, r in zones:
        if max(abs(objects[p0]["at"][0] - cx), abs(objects[p0]["at"][1] - cy)) <= r:
            zone = (cx, cy, r)
    if zone is None:
        return keep
    cx, cy, r = zone

    def inzone(pt):
        return max(abs(pt[0] - cx), abs(pt[1] - cy)) <= r

    surface = frozenset((1, 16)) if objects[p0]["through"] else objects[p0]["layers"]
    frontier, seen = [p0], set([p0])
    while frontier:
        i = frontier.pop()
        for j in grp:
            if j in seen:
                continue
            oj = objects[j]
            if oj["kind"] == "wire":
                if not (oj["layers"] & surface) or not (inzone(oj["a"]) and inzone(oj["b"])):
                    continue
                if connected(objects[i], oj):
                    seen.add(j)
                    keep.add(j)
                    frontier.append(j)
            elif oj["kind"] == "via" and not blind(oj):
                if connected(objects[i], oj):
                    seen.add(j)
                    keep.add(j)
    return keep


class Net(object):
    """one net under work: what it had, what it keeps, what it is now"""

    def __init__(self, name, open_tag, body, terms, zones, force=False, ripped=()):
        self.name, self.open_tag, self.original = name, open_tag, body
        self.terms = terms
        self.items = parse_items(body)
        self.objects = terms + self.items
        self.forced = force
        groups = pieces_of(self.objects)
        keep = set()
        rip_texts = set(o["text"] for o in ripped)
        for grp in groups:
            pads_in = [i for i in grp if i < len(terms)]
            if not pads_in:
                continue
            if len(pads_in) >= 2 and not force:
                keep.update(grp)
                continue
            for p0 in pads_in:
                keep |= escape_of(self.objects, grp, p0, zones)
        # A WALL NET LOSES A WINDOW, NOT A SEGMENT AND NOT ITS WHOLE ROUTE.
        # Removing only the wall segment leaves a one-trace hole between copper
        # laid at exactly 3 mil, and a 0.05 mm grid cannot see a corridor of
        # zero width: 85 of 118 such nets found no way back. Stripping the net
        # to its escapes let it route afresh -- and when one such net failed,
        # restoring its long original crossed dozens of new routes, and the
        # attempt collapsed. So a wall net loses the wall plus everything of
        # its own within RIP_WINDOW of it: room to detour, and a failure that
        # stays local.
        if ripped:
            xs = [v for o in ripped for v in ((o["a"][0], o["b"][0]) if o["kind"] == "wire" else (o["at"][0],))]
            ys = [v for o in ripped for v in ((o["a"][1], o["b"][1]) if o["kind"] == "wire" else (o["at"][1],))]
            wx0, wx1 = min(xs) - RIP_WINDOW, max(xs) + RIP_WINDOW
            wy0, wy1 = min(ys) - RIP_WINDOW, max(ys) + RIP_WINDOW

            def in_window(o):
                if o["kind"] == "wire":
                    return (min(o["a"][0], o["b"][0]) <= wx1 and max(o["a"][0], o["b"][0]) >= wx0 and
                            min(o["a"][1], o["b"][1]) <= wy1 and max(o["a"][1], o["b"][1]) >= wy0)
                return wx0 <= o["at"][0] <= wx1 and wy0 <= o["at"][1] <= wy1

            keep = set(i for i, o in enumerate(self.objects)
                       if o["kind"] == "pad" or not in_window(o))
        self.kept = [self.objects[i] for i in sorted(keep)
                     if not blind(self.objects[i]) and self.objects[i].get("text") not in rip_texts]
        self.split_before = len([grp for grp in groups
                                 if any(i < len(terms) for i in grp)]) > 1
        self.body = self.strip_body(body) + "".join(o["text"] for o in self.kept if "text" in o)
        self.pieces = self.compute_pieces()
        self.dropped = [o for o in self.items if o not in self.kept]

    def rip(self, texts):
        """drop kept segments by their tag text; pieces follow"""
        texts = set(texts)
        self.kept = [o for o in self.kept if o.get("text") not in texts]
        self.body = self.strip_body(self.original) + "".join(o["text"] for o in self.kept if "text" in o)
        self.pieces = self.compute_pieces()
        self.dropped = [o for o in self.items if o not in self.kept]

    @staticmethod
    def strip_body(body):
        nb = VIA_RE.sub("", body)
        nb = WIRE_RE.sub("", nb)
        return re.sub(r"\n\s*\n+", "\n", nb)

    def compute_pieces(self):
        objs = self.kept
        groups = pieces_of(objs)
        out = [[objs[i] for i in grp] for grp in groups
               if any(objs[i]["kind"] == "pad" for i in grp)]
        out.sort(key=lambda objs: (-sum(1 for o in objs if o["kind"] == "pad"), -len(objs)))
        return out


def rebuild(text, bodies):
    def sub(m):
        if m.group(2) in bodies:
            return m.group(1) + bodies[m.group(2)] + m.group(4)
        return m.group(0)
    return SIG_RE.sub(sub, text)


def honest_pieces(text, pname, player, open_tag, body, terms, zones, ripped=()):
    """a plane net as check_connectivity sees it: kept whole (blind vias
    included) except for `ripped` stub segments, its pieces grouped by the
    honest plane model, and which pieces the main pour piece already reaches"""
    pnet = Net(pname, open_tag, body, terms, zones)
    ripped = set(ripped)
    pnet.kept = [o for o in pnet.objects if o.get("text") not in ripped]
    pnet.ripped_texts = ripped
    pnet.body = Net.strip_body(body) + "".join(o["text"] for o in pnet.kept if "text" in o)
    parsed = C.parse_signal_objects(text)[pname]
    union = C.connectivity_union(parsed[0], parsed[2])
    groups = collections.defaultdict(list)
    for i, o in enumerate(parsed[0]):
        groups[union.find(i)].append(i)

    def key(o):
        if o["kind"] == "wire":
            return ("wire", round(o["a"][0], 3), round(o["a"][1], 3), round(o["b"][0], 3), round(o["b"][1], 3))
        return (o["kind"], round(o["at"][0], 3), round(o["at"][1], 3))

    gid = {}
    for root, members in groups.items():
        for i in members:
            gid[key(parsed[0][i])] = root
    by_group = collections.defaultdict(list)
    for o in pnet.kept:
        by_group[gid.get(key(o), id(o))].append(o)
    pnet.pieces = sorted([objs for objs in by_group.values() if any(o["kind"] == "pad" for o in objs)],
                         key=lambda objs: -len(objs))
    reached = parsed[2].get(player, set()) if isinstance(parsed[2], dict) else set()
    pnet.main_idx = [k for k, objs in enumerate(pnet.pieces)
                     if any(o["kind"] in ("via", "pad") and (o["kind"] == "via" or o["through"])
                            and (round(o["at"][0], 3), round(o["at"][1], 3)) in reached for o in objs)]
    return pnet


# ------------------------------------------------------------------ grid
class Astar(PF.Router):
    """PathFinder's router with an admissible Manhattan heuristic to the
    destination set's bounding box. Same costs, same result, far fewer
    nodes touched on a 1400 x 500 grid with six layers."""

    def route(self, srcs, dsts, pfac, box):
        self.gen += 1
        gen = self.gen
        dist, prev, stamp, occ, hist = (self.dist, self.prev, self.stamp,
                                        self.occ, self.hist)
        NN, W = self.NN, self.W
        i0, j0, i1, j1 = box
        pf = int(round(pfac * PF.STEP_COST))
        hf = self.hfac
        SC = PF.STEP_COST
        dset = set(li * NN + c for li, c in dsts)
        if not dset:
            return None
        dis = [c % W for li, c in dsts]
        djs = [c // W for li, c in dsts]
        bi0, bi1, bj0, bj1 = min(dis), max(dis), min(djs), max(djs)

        def h(c):
            i, j = c % W, c // W
            di = bi0 - i if i < bi0 else (i - bi1 if i > bi1 else 0)
            dj = bj0 - j if j < bj0 else (j - bj1 if j > bj1 else 0)
            return (di + dj) * SC

        pq = []
        for li, c in srcs:
            if not self.free[li][c]:
                continue
            n = li * NN + c
            if stamp[n] == gen and dist[n] <= 0:
                continue
            dist[n] = 0
            prev[n] = -1
            stamp[n] = gen
            heapq.heappush(pq, (h(c), 0, n))
        if not pq:
            return None
        nl = len(self.layers)
        while pq:
            f, d, n = heapq.heappop(pq)
            if stamp[n] != gen or d > dist[n]:
                continue
            if n in dset:
                out = []
                while n >= 0:
                    out.append(n)
                    n = prev[n]
                out.reverse()
                return out
            li, c = divmod(n, NN)
            i, j = c % W, c // W
            fl = self.free[li]
            for step, ni, nj in ((-1, i - 1, j), (1, i + 1, j),
                                 (-W, i, j - 1), (W, i, j + 1)):
                if not (i0 <= ni <= i1 and j0 <= nj <= j1):
                    continue
                q = c + step
                if not fl[q]:
                    continue
                m = li * NN + q
                w = d + SC + hf * hist[m] + pf * occ[m]
                if stamp[m] != gen or w < dist[m]:
                    stamp[m] = gen
                    dist[m] = w
                    prev[m] = n
                    heapq.heappush(pq, (w + h(q), w, m))
            if nl > 1 and self.vfree[c]:
                for lo in range(nl):
                    if lo == li or not self.free[lo][c]:
                        continue
                    m = lo * NN + c
                    w = d + PF.VIA_COST + hf * hist[m] + pf * occ[m]
                    if stamp[m] != gen or w < dist[m]:
                        stamp[m] = gen
                        dist[m] = w
                        prev[m] = n
                        heapq.heappush(pq, (w + h(c), w, m))
        return None


def circles_of(objs, layer):
    """obstacle circles for a set of own objects, on one layer or all (None)"""
    rects, circs, segs = [], [], []
    for o in objs:
        if o["kind"] == "pad":
            if o["through"] or layer is None or layer in o["layers"]:
                if o["round"] and abs(o["hx"] - o["hy"]) < 1e-9:
                    circs.append((o["at"][0], o["at"][1], o["hx"]))
                else:
                    rects.append((o["at"][0], o["at"][1], o["hx"], o["hy"], 0.0))
        elif o["kind"] == "via":
            if layer is None or layer in o["layers"]:
                circs.append((o["at"][0], o["at"][1], o["radius"]))
        else:
            if o["layers"] and (layer is None or layer in o["layers"]):
                segs.append((o["a"], o["b"], o["radius"]))
    out = G.as_circles(rects, step=0.05) + circs
    for a, c, r in segs:
        out += G.sample(a, c, r)
    return out


class Stub(object):
    def __init__(self, free):
        self.free = free


class Grid(object):
    """the routing grids for one pass: every net not in `own` is a hard
    obstacle; own nets' kept copper is counted so it can be opened per net"""

    def __init__(self, text, own_nets, w, bx, clr, via_clr, plane_free=None):
        self.text, self.w, self.bx, self.clr = text, w, bx, clr
        own = frozenset(n.name for n in own_nets)
        self.base = dict((L, P.Maze(G.obstacles(text, own, int(L)), bx, clr, w, STEP))
                         for L in LAYERS)
        # THE VIA GRID HAS TWO RULES IN IT. A via land needs copper clearance
        # from pads and wires (3 mil) but DRILL clearance from other holes:
        # two 0.20 drills must stay 0.40 centre to centre. One maze at the
        # drill figure sealed the diagonal between four BGA balls, which is
        # the only place a dogbone can go; two mazes ANDed keep both rules
        # and nothing more.
        rects, circs, segs = G.copper_model(text, own, None)
        copper = G.as_circles(rects, step=0.05) + circs
        for u, v, r in segs:
            copper += G.sample(u, v, r)
        mc = P.Maze(copper, bx, clr, VIA_L, STEP)
        holes = []
        sig = re.search(r"<signals>(.*)</signals>", text, re.S)
        for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>',
                             sig.group(1) if sig else "", re.S):
            if m.group(1) in own:
                continue
            holes += [(x, y, d / 2.0) for x, y, d in G.vias(m.group(2))]
        for onet, x, y, hx, hy, side in E.board_copper(text, skip=()):
            if side == 0 and onet not in own:
                holes.append((x, y, hx))
        mh = P.Maze(holes, bx, via_clr, VIA_L, STEP)
        self.vbase = bytearray(a & b for a, b in zip(mc.free, mh.free))
        layers = list(LAYERS)
        mz = dict(self.base)
        if plane_free is not None:
            mz["P"] = Stub(plane_free)
            layers.append("P")
        self.layers = layers
        self.rt = Astar(mz, bytearray(self.vbase), layers)
        self.rt.set_footprint(w, clr, MIN_DRILL_CC - clr)
        self.NN, self.W, self.H = self.rt.NN, self.rt.W, self.rt.H
        self.m0 = self.base[LAYERS[0]]
        self.li_of = dict((int(L), li) for li, L in enumerate(LAYERS))
        self.cnt = [array("i", [0]) * self.NN for _ in LAYERS]
        self.vcnt = array("i", [0]) * self.NN
        self.owncells, self.ownv, self.keepv, self.seedcells = {}, {}, {}, {}
        for net in own_nets:
            self.register(net)
        for li in range(len(LAYERS)):
            fr, cn = self.rt.free[li], self.cnt[li]
            for c in range(self.NN):
                if cn[c]:
                    fr[c] = 0
        vf = self.rt.vfree
        for c in range(self.NN):
            if self.vcnt[c]:
                vf[c] = 0

    def register(self, net):
        rt, W, H, m0 = self.rt, self.W, self.H, self.m0
        objs = net.kept
        rows = []
        for li, L in enumerate(LAYERS):
            cells = sorted(set(PF.cells_of(circles_of(objs, int(L)), self.base[L], self.clr, self.w)))
            rows.append(cells)
            for c in cells:
                self.cnt[li][c] += 1
        self.owncells[net.name] = rows
        vc = sorted(set(PF.cells_of(circles_of(objs, None), m0, self.clr, VIA_L, margin=0.15)))
        self.ownv[net.name] = vc
        for c in vc:
            self.vcnt[c] += 1
        kv = set()
        for o in objs:
            if o["kind"] == "pad" and not o["through"]:
                px, py = o["at"]
                margin = VIA_L / 2.0 + 0.03
                for i in range(max(0, m0.i(px - o["hx"] - margin)), min(W, m0.i(px + o["hx"] + margin) + 1)):
                    for j in range(max(0, m0.j(py - o["hy"] - margin)), min(H, m0.j(py + o["hy"] + margin) + 1)):
                        qx, qy = m0.xy(j * W + i)
                        if G.rect_pt((px, py, o["hx"], o["hy"]), qx, qy) < margin:
                            kv.add(j * W + i)
            elif o["kind"] == "via":
                vx, vy = o["at"]
                rr = int(MIN_DRILL_CC / STEP) + 1
                ci, cj = m0.i(vx), m0.j(vy)
                for i in range(max(0, ci - rr), min(W, ci + rr + 1)):
                    for j in range(max(0, cj - rr), min(H, cj + rr + 1)):
                        qx, qy = m0.xy(j * W + i)
                        dd = math.hypot(qx - vx, qy - vy)
                        if STEP * 0.6 < dd < MIN_DRILL_CC:
                            kv.add(j * W + i)
        self.keepv[net.name] = sorted(kv)
        # ITS OWN COPPER IS ALWAYS A LEGAL PLACE TO START. The grids dilate
        # foreign copper by the rule plus 0.01 mm of margin, so a trace laid at
        # exactly 3 mil from its neighbour -- which is what most of this board
        # is -- has every cell of its own centreline marked blocked. A route
        # that starts on that centreline is as legal as the trace already
        # there, so those cells are forced open while the net routes.
        nodes, anchors = self.seeds(objs, check_free=False)
        self.seedcells[net.name] = sorted(set(nodes))

    def open_net(self, name, on):
        d = -1 if on else 1
        rt = self.rt
        for li in range(len(LAYERS)):
            fr, bs, cn = rt.free[li], self.base[LAYERS[li]].free, self.cnt[li]
            for c in self.owncells[name][li]:
                cn[c] += d
                fr[c] = 1 if (bs[c] and cn[c] == 0) else 0
        for li, c in self.seedcells[name]:
            if on:
                rt.free[li][c] = 1
            else:
                bs, cn = self.base[LAYERS[li]].free, self.cnt[li]
                rt.free[li][c] = 1 if (bs[c] and cn[c] == 0) else 0
        vf, vb = rt.vfree, self.vbase
        for c in self.ownv[name]:
            self.vcnt[c] += d
            vf[c] = 1 if (vb[c] and self.vcnt[c] == 0) else 0
        if on:
            for c in self.keepv[name]:
                vf[c] = 0
        else:
            for c in self.keepv[name]:
                vf[c] = 1 if (vb[c] and self.vcnt[c] == 0) else 0

    def seeds(self, objs, check_free=True):
        rt, W, H, m0, NN, li_of = self.rt, self.W, self.H, self.m0, self.NN, self.li_of
        nodes, anchors = [], {}

        def free(li, c):
            return (not check_free) or rt.free[li][c]
        for o in objs:
            if o["kind"] == "pad":
                lays = LAYER_I if o["through"] else [L for L in o["layers"] if L in li_of]
                px, py = o["at"]
                cells = []
                for i in range(max(0, m0.i(px - o["hx"])), min(W, m0.i(px + o["hx"]) + 1)):
                    for j in range(max(0, m0.j(py - o["hy"])), min(H, m0.j(py + o["hy"]) + 1)):
                        qx, qy = m0.xy(j * W + i)
                        if o["round"] and abs(o["hx"] - o["hy"]) < 1e-9:
                            inside = math.hypot(qx - px, qy - py) <= o["hx"] - 0.005
                        else:
                            inside = abs(qx - px) <= o["hx"] - 0.005 and abs(qy - py) <= o["hy"] - 0.005
                        if inside:
                            cells.append(j * W + i)
                if not cells:
                    cells = [rt.cell((px, py))]
                for L in lays:
                    li = li_of[L]
                    for c in cells:
                        if free(li, c):
                            nodes.append((li, c))
                            anchors[li * NN + c] = (px, py)
            elif o["kind"] == "via":
                vx, vy = o["at"]
                rr = int(o["radius"] / STEP) + 1
                ci, cj = m0.i(vx), m0.j(vy)
                for L in LAYER_I:
                    if L not in o["layers"]:
                        continue
                    li = li_of[L]
                    for i in range(max(0, ci - rr), min(W, ci + rr + 1)):
                        for j in range(max(0, cj - rr), min(H, cj + rr + 1)):
                            c = j * W + i
                            qx, qy = m0.xy(c)
                            if math.hypot(qx - vx, qy - vy) <= o["radius"] and free(li, c):
                                nodes.append((li, c))
                                anchors[li * NN + c] = (vx, vy)
            else:
                if not o["layers"]:
                    continue
                L = next(iter(o["layers"]))
                if L not in li_of:
                    continue
                li = li_of[L]
                a, b = o["a"], o["b"]
                length = math.hypot(b[0] - a[0], b[1] - a[1])
                n = max(1, int(length / STEP))
                for k in range(n + 1):
                    t = k / float(n)
                    px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                    c = rt.cell((px, py))
                    if not (0 <= c < NN) or not free(li, c):
                        continue
                    qx, qy = m0.xy(c)
                    if E.seg_pt(a, b, (qx, qy)) > o["radius"]:
                        continue
                    if length < 1e-9:
                        proj = a
                    else:
                        tt = max(0.0, min(1.0, ((qx - a[0]) * (b[0] - a[0]) + (qy - a[1]) * (b[1] - a[1])) / (length * length)))
                        proj = (a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt)
                    nodes.append((li, c))
                    anchors[li * NN + c] = proj
        return nodes, anchors

    def flood(self, nodes, cap):
        """cells reachable from `nodes` through free cells and via sites;
        None once more than `cap` cells are reached (not a pocket)"""
        rt, NN, W, H = self.rt, self.NN, self.W, self.H
        seen = set(li * NN + c for li, c in nodes)
        stack = list(seen)
        nl = len(LAYERS)
        while stack:
            n = stack.pop()
            li, c = divmod(n, NN)
            i, j = c % W, c // W
            for step, ni, nj in ((-1, i - 1, j), (1, i + 1, j), (-W, i, j - 1), (W, i, j + 1)):
                if not (0 <= ni < W and 0 <= nj < H):
                    continue
                q = c + step
                if rt.free[li][q]:
                    m = li * NN + q
                    if m not in seen:
                        seen.add(m)
                        stack.append(m)
            if rt.vfree[c]:
                for lo in range(nl):
                    if lo != li and rt.free[lo][c]:
                        m = lo * NN + c
                        if m not in seen:
                            seen.add(m)
                            stack.append(m)
            if len(seen) > cap:
                return None
        return seen

    def wall_of(self, pocket):
        """(li, cell) blocked cells bounding a pocket, on the pocket's layers"""
        rt, NN, W, H = self.rt, self.NN, self.W, self.H
        wall = set()
        for n in pocket:
            li, c = divmod(n, NN)
            i, j = c % W, c // W
            for step, ni, nj in ((-1, i - 1, j), (1, i + 1, j), (-W, i, j - 1), (W, i, j + 1)):
                if 0 <= ni < W and 0 <= nj < H and not rt.free[li][c + step]:
                    wall.add((li, c + step))
        return wall


# --------------------------------------------------------------- routing
def box_for(grid, src_nodes, dst_nodes, slack_mm):
    W, H = grid.W, grid.H
    cells = [c for li, c in src_nodes] + [c for li, c in dst_nodes]
    iis = [c % W for c in cells]
    jjs = [c // W for c in cells]
    s = int(slack_mm / STEP)
    return (max(0, min(iis) - s), max(0, min(jjs) - s),
            min(W - 1, max(iis) + s), min(H - 1, max(jjs) + s))


def route_item(grid, item, pfac, it):
    """one item = (src nodes, [dst node sets]); the tree grows by each path"""
    src, dsts = item["src"], item["dsts"]
    rt, NN = grid.rt, grid.NN
    tree = list(src)
    paths = []
    for dst in dsts:
        grow = BOX0 + 4.0 * it
        path = None
        for slack in (grow, grow * 3, 1e9):
            path = rt.route(tree, dst, pfac, box_for(grid, tree, dst, slack))
            if path:
                break
        if not path:
            return None
        paths.append(path)
        tree = tree + [(n // NN, n % NN) for n in path]
    return paths


def footprint_of(grid, paths):
    fp = set()
    for p in paths:
        fp |= grid.rt.footprint(p)
    return fp


def legalise(grid, items, order, routes, foot, priority):
    """accept clean routes and re-route the rest against the accepted set as
    hard obstacles -- in two tiers. Nets that were WHOLE before this run
    (priority) are settled first, clean or re-routed, before any net that was
    open gets to claim space: a net that fails here costs a restore, and a
    restore costs every new route its old copper crosses."""
    rt, NN = grid.rt, grid.NN
    keep, used_foot, used_line = {}, set(), set()

    def accept(name, paths):
        nodes = set(x for p in paths for x in p)
        fp = footprint_of(grid, paths) if name not in foot else foot[name]
        if (nodes & used_foot) or (fp & used_line):
            return False
        keep[name] = paths
        used_foot.update(fp)
        used_line.update(nodes)
        return True

    def reroute(name):
        blocked = []
        for n in used_foot:
            li, c = divmod(n, NN)
            if rt.free[li][c]:
                rt.free[li][c] = 0
                blocked.append((li, c))
        grid.open_net(items[name]["net"], True)
        paths = route_item(grid, items[name], 0.0, MAXIT)
        grid.open_net(items[name]["net"], False)
        for li, c in blocked:
            rt.free[li][c] = 1
        if not paths:
            log("   **** %-14s no path against the accepted set" % name)
            return
        nodes = set(x for p in paths for x in p)
        fp = footprint_of(grid, paths)
        if (nodes & used_foot) or (fp & used_line):
            log("   **** %-14s re-route still conflicts" % name)
            return
        keep[name] = paths
        used_foot.update(fp)
        used_line.update(nodes)

    for tier in (True, False):
        names = [n for n in order if (n in priority) == tier]
        pending = []
        for name in names:
            paths = routes.get(name)
            if paths and accept(name, paths):
                continue
            pending.append(name)
        for name in pending:
            reroute(name)
    return keep


def negotiate(grid, items, order, maxit, priority):
    rt = grid.rt
    routes, foot = {}, {}
    hopeless = set()
    pfac = PF.PFAC0
    best = (10 ** 9, None, None)
    over = set()
    for it in range(maxit):
        for name in order:
            if name in hopeless:
                continue
            if name in routes:
                rt.add(foot[name], -1)
                del routes[name]
                del foot[name]
            grid.open_net(items[name]["net"], True)
            paths = route_item(grid, items[name], pfac, it)
            grid.open_net(items[name]["net"], False)
            if paths:
                routes[name] = paths
                foot[name] = footprint_of(grid, paths)
                rt.add(foot[name], 1)
            else:
                hopeless.add(name)
        flat = dict((n, [x for p in ps for x in p]) for n, ps in routes.items())
        over = rt.shared(flat)
        log("   iter %2d  pfac %7.2f  routed %2d/%d  shared cells %d%s"
            % (it + 1, pfac, len(routes), len(order), len(over),
               "  (%d with no path at all)" % len(hopeless) if hopeless else ""))
        if not over and len(routes) + len(hopeless) == len(order):
            break
        if len(over) < best[0]:
            best = (len(over), dict(routes), dict(foot))
        rt.bump_history(over)
        pfac = min(pfac * PF.PGROW, PF.PCAP)
    if over and best[1] is not None and len(over) > best[0]:
        log("   keeping iteration with %d shared cells" % best[0])
        routes, foot = best[1], best[2]
    return legalise(grid, items, order, routes, foot, priority)


def greedy(grid, items, order):
    rt, NN = grid.rt, grid.NN
    keep = {}
    for name in order:
        grid.open_net(items[name]["net"], True)
        paths = route_item(grid, items[name], 0.0, MAXIT)
        grid.open_net(items[name]["net"], False)
        if not paths:
            log("   **** %-14s no path" % name)
            continue
        keep[name] = paths
        for n in footprint_of(grid, paths):
            li, c = divmod(n, NN)
            rt.free[li][c] = 0
    return keep


def to_copper(grid, net, paths, anchors, w):
    """paths -> (wires, vias), ends snapped onto real copper"""
    rt = grid.rt
    own_fixed = [(o["at"][0], o["at"][1]) for o in net.kept
                 if o["kind"] == "via" or (o["kind"] == "pad" and o["through"])]
    wires, vias = [], []
    for nodes in paths:
        runs, vs = PF.to_segments(rt, nodes, grid.layers)
        # SNAP WITH A SEGMENT, NOT A TILT. Replacing the run's first point by
        # the via centre made a 2 mm run diagonal by 0.1 mm and cost 0.04 mm
        # of clearance against a neighbour; the short hop from the anchor to
        # the grid cell lies inside the via land or pad, so it is always legal.
        if nodes[0] in anchors:
            runs[0][1].insert(0, anchors[nodes[0]])
        if nodes[-1] in anchors:
            runs[-1][1].append(anchors[nodes[-1]])
        for k, (vx, vy) in enumerate(vs):
            near = [q for q in own_fixed + vias if math.hypot(q[0] - vx, q[1] - vy) < MIN_DRILL_CC]
            if near:
                q = min(near, key=lambda q: math.hypot(q[0] - vx, q[1] - vy))
                runs[k][1][-1] = q
                runs[k + 1][1][0] = q
            else:
                vias.append((vx, vy))
        for lay, pts in runs:
            if lay == "P":
                continue
            for a, c in zip(pts, pts[1:]):
                if math.hypot(c[0] - a[0], c[1] - a[1]) > 1e-9:
                    wires.append((a, c, int(lay)))
    return wires, vias


def copper_text(wires, vias, w):
    add = "".join('<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>'
                  % (g(x), g(y), g(VIA_D), g(VIA_L)) for x, y in vias)
    add += "".join('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>'
                   % (g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(w), lay) for a, c, lay in wires)
    return add


def prune_loose(text, names, pads_by_net):
    """drop wires and vias of `names` that end in nothing, until none do. A
    window rip leaves the stump of the old route pointing at the gap; the
    reroute goes elsewhere and the stump stays, which check_board (and Fusion's
    wire-stub check) report. Leaf pruning never changes what pads reach."""
    def sub(m):
        name = m.group(2)
        if name not in names:
            return m.group(0)
        body = m.group(3)
        pads = pads_by_net.get(name, [])
        items = parse_items(body)
        changed = True
        while changed:
            changed = False
            # check_board's rule, exactly: a wire end is anchored if it sits on
            # the centre of a pad or via of the net, or on the body of another
            # wire of the net on the same layer. Nothing else counts.
            centres = set((round(p["at"][0], 3), round(p["at"][1], 3)) for p in pads)
            centres |= set((round(o["at"][0], 3), round(o["at"][1], 3)) for o in items if o["kind"] == "via")
            wires = [o for o in items if o["kind"] == "wire"]
            keep = []
            for o in items:
                if o["kind"] == "wire":
                    ok = True
                    for e in (o["a"], o["b"]):
                        if (round(e[0], 3), round(e[1], 3)) in centres:
                            continue
                        if any(q is not o and q["layers"] == o["layers"] and
                               E.seg_pt(q["a"], q["b"], e) <= q["radius"] + o["radius"] + 1e-6
                               for q in wires):
                            continue
                        ok = False
                        break
                    if not ok:
                        changed = True
                        continue
                elif o["kind"] == "via":
                    if not any(q is not o and connected(o, q) for q in pads + items):
                        changed = True
                        continue
                keep.append(o)
            items = keep
        # FLOATING PIECES COUNT. Fusion draws an airwire to a leftover via or
        # a stump that touches nothing, so a piece of a non-plane net that
        # holds no pad is deleted outright (leaf pruning cannot reach a loop).
        if name not in PLANES and items:
            objs = list(pads) + items
            union = C.connectivity_union(objs, set())
            with_pad = set(union.find(i) for i in range(len(pads)))
            items = [o for i, o in enumerate(items) if union.find(len(pads) + i) in with_pad]
        nb = Net.strip_body(body) + "".join(o["text"] for o in items)
        return m.group(1) + nb + m.group(4)
    return SIG_RE.sub(sub, text)


_FC_PADS = {}


def fc_pads(text):
    if not _FC_PADS:
        _FC_PADS.update(FC.pads_by_net(text))
    return _FC_PADS


def conflicts(old_objs, new_wires, new_vias, clr):
    """does restored copper collide with new copper of another net"""
    for o in old_objs:
        if o["kind"] == "wire" and o["layers"]:
            L = next(iter(o["layers"]))
            for a, c, lay in new_wires:
                if lay == L and E.seg_seg(o["a"], o["b"], a, c) < o["radius"] + THIN / 2 + clr:
                    return True
            for x, y in new_vias:
                if E.seg_pt(o["a"], o["b"], (x, y)) < o["radius"] + VIA_L / 2 + clr:
                    return True
        elif o["kind"] == "via":
            for a, c, lay in new_wires:
                if lay in o["layers"] and E.seg_pt(a, c, o["at"]) < o["radius"] + THIN / 2 + clr:
                    return True
            for x, y in new_vias:
                if math.hypot(x - o["at"][0], y - o["at"][1]) < MIN_DRILL_CC:
                    return True
    return False


# ------------------------------------------------------------------ main
def run_pass(text, group, w, mode, bx, clr, via_clr, routed, plane=None, priority=()):
    """route `group` nets at width w; returns (text, missed names)"""
    if not group:
        return text, []
    log("-- %d net(s) at %.4f mm, %s%s" % (len(group), w, mode, " on plane L%d" % plane[1] if plane else ""))
    plane_free = None
    if plane:
        probe = P.Maze([], bx, clr, w, STEP)
        res = PI.analyse(text, plane[1], plane[0], log=lambda *a: None,
                         grid=(bx[0], bx[1], probe.W, probe.H))
        lab, main_piece = res["label"], res["main"]
        plane_free = bytearray(1 if lab[c] == main_piece else 0 for c in range(probe.W * probe.H))
        log("   plane raster: main piece %d cells" % sum(plane_free))
    grid = Grid(text, group, w, bx, clr, via_clr, plane_free)
    log("   grids built: %d x %d cells, via sites %.1f %%" % (grid.W, grid.H, 100.0 * sum(grid.rt.vfree) / grid.NN))
    items = {}
    for net in group:
        grid.open_net(net.name, True)
        pcs = net.pieces
        if plane:
            # the main piece is whatever the plane already reaches; every
            # other piece is its own item aimed at plane or main copper
            main_idx = net.main_idx
            main_seeds, main_anc = [], {}
            for k in main_idx:
                s, a = grid.seeds(pcs[k])
                main_seeds += s
                main_anc.update(a)
            liP = len(LAYERS)
            pcells = [(liP, c) for c in range(grid.NN) if plane_free[c]]
            for k, objs in enumerate(pcs):
                if k in main_idx:
                    continue
                s, a = grid.seeds(objs)
                if not s:
                    log("   **** %s piece %d has no reachable seed" % (net.name, k))
                    continue
                a.update(main_anc)
                items["%s#%d" % (net.name, k)] = {"net": net.name, "netobj": net, "src": s,
                                                   "dsts": [main_seeds + pcells], "anc": a}
        else:
            src, anc = grid.seeds(pcs[0])
            dsts = []
            for objs in pcs[1:]:
                d, a2 = grid.seeds(objs)
                anc.update(a2)
                dsts.append(d)
            if not src or any(not d for d in dsts):
                log("   **** %-14s has a piece with no reachable seed cell (src %d, dsts %s)"
                    % (net.name, len(src), [len(d) for d in dsts]))
            else:
                sx = [grid.rt.xy(c) for li, c in src]
                cx0 = sum(p[0] for p in sx) / len(sx)
                cy0 = sum(p[1] for p in sx) / len(sx)
                dsts.sort(key=lambda d: min(math.hypot(grid.rt.xy(c)[0] - cx0, grid.rt.xy(c)[1] - cy0) for li, c in d))
                items[net.name] = {"net": net.name, "netobj": net, "src": src, "dsts": dsts, "anc": anc}
        grid.open_net(net.name, False)
    order = sorted(items, key=lambda n: sum(len(d) for d in items[n]["dsts"]))
    if mode == "negotiate":
        keep = negotiate(grid, items, order, MAXIT, set(priority))
    else:
        keep = greedy(grid, items, order)
    done = set(items[n]["net"] for n in keep)
    missed = [n.name for n in group if n.name not in done or
              any(k not in keep for k in items if items[k]["net"] == n.name)]
    log("   %d of %d item(s) routed legally; nets missed: %s"
        % (len(keep), len(items), ", ".join(sorted(set(missed))) or "-"))
    bodies = {}
    for netname in done:
        if netname in missed:
            continue
        net = next(n for n in group if n.name == netname)
        wires, vias = [], []
        for iname, paths in keep.items():
            if items[iname]["net"] != netname:
                continue
            ws, vs = to_copper(grid, net, paths, items[iname]["anc"], w)
            wires += ws
            vias += vs
        routed[netname] = (wires, vias, w)
        # A ROUTE THAT LANDS ON A WIRE'S BODY IS OPEN TO FUSION. to_copper
        # snaps ends onto copper; fusion_connect splits the host wire there so
        # the joint is a shared end point, which is the only joint Fusion counts.
        bodies[netname] = FC.repair(netname, net.body + copper_text(wires, vias, w),
                                    fc_pads(text).get(netname, []), has_pour=netname in PLANES)[0]
        log("   %-14s %3d wire(s) %2d via(s)  %.1f mm" % (
            netname, len(wires), len(vias), sum(math.hypot(c[0] - a[0], c[1] - a[1]) for a, c, lay in wires)))
    return rebuild(text, bodies), sorted(set(missed))


def run_attempt(protect):
    """one full pass from the original board; nets in `protect` are never
    ripped or forced. Returns (text, first_failures, still) where
    first_failures are the forced nets that could not be rerouted."""
    force_set = FORCE - protect
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    pads, fields = pad_index(board)
    zones = [(fields[el][0], fields[el][1], r) for el, r in ZONE_R.items() if el in fields] + EXTRA_ZONES
    outline = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                         r' y2="([-\d.]+)"[^>]*layer="20"', board)
    xs = [float(v) for q in outline for v in (q[0], q[2])]
    ys = [float(v) for q in outline for v in (q[1], q[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))
    clr = G.rule_mm(board, "mdWireWire") + 0.005
    drill_clr = G.drill_clearance(board, VIA_D)
    via_clr = max(clr, drill_clr - (VIA_L - VIA_D))
    sig = dict((m.group(2), (m.group(1), m.group(3))) for m in SIG_RE.finditer(board))
    padobjs = collections.defaultdict(list)
    for key, p in pads.items():
        if p["net"]:
            padobjs[p["net"]].append(p)

    # ---- targets
    nets = {}
    for name, (open_tag, body) in sig.items():
        if name in EXCLUDE or (ONLY and name not in ONLY and name not in force_set):
            continue
        terms = padobjs.get(name, [])
        if len(terms) < 2:
            continue
        probe = Net(name, open_tag, body, terms, zones, force=(name in force_set))
        if not probe.split_before and name not in force_set:
            continue
        nets[name] = probe
        log("%-14s pads %2d pieces %d  keep %3d via/wire  drop %3d (%d vias)%s"
            % (name, len(terms), len(probe.pieces), len(probe.kept) - len(terms),
               len(probe.dropped), sum(1 for o in probe.dropped if o["kind"] == "via"),
               "  FORCED" if name in force_set else ""))
    if not nets:
        log("nothing to route")
        return board, [], []
    log("%d net(s) to close; zones %s" % (len(nets), ["(%.2f,%.2f) r%.1f" % z for z in zones]))

    def text_now(extra=None):
        bodies = dict((n.name, n.body) for n in nets.values())
        if extra:
            bodies.update(extra)
        return rebuild(board, bodies)

    # ---- rip the walls of boxed pockets
    plane_rips = collections.defaultdict(set)
    if RIP == "auto":
        for rnd in range(RIP_ROUNDS):
            plane_nets = []
            for pname, player in PLANES.items():
                if pname in sig and pname not in protect:
                    open_tag, body = sig[pname]
                    nets[pname] = honest_pieces(text_now(), pname, player, open_tag, body,
                                                padobjs.get(pname, []), zones, plane_rips[pname])
                    plane_nets.append(nets[pname])
            text = text_now()
            signal_nets = [n for n in nets.values() if n.name not in PLANES]
            grid = Grid(text, signal_nets + plane_nets, THIN, bx, clr, via_clr)
            log("-- rip round %d: grids built, via sites %.1f %%"
                % (rnd + 1, 100.0 * sum(grid.rt.vfree) / grid.NN))
            # index of rippable copper: wires and vias of nets not under work,
            # the kept escapes of nets that ARE under work, and the thin surface
            # stubs of the plane nets -- a decoupling pad's stub to its via can
            # be re-tied by the plane pass, so it may go
            # Plane-net stitching vias away from the BGA and from U2's thermal
            # array may go too: whatever pad they tied, the plane pass re-ties.
            def plane_rippable(o):
                if o["kind"] == "wire":
                    return o["radius"] <= 0.051 and bool(o["layers"] & frozenset((1, 16)))
                if o["kind"] == "via" and not blind(o):
                    return all(max(abs(o["at"][0] - cx), abs(o["at"][1] - cy)) > r for cx, cy, r in zones)
                return False

            bucket = collections.defaultdict(list)     # (layer, i, j) -> [(name, o)]
            allbucket = collections.defaultdict(list)  # (i, j) -> [(name, o)]  any layer

            def insert(name, o):
                if o["kind"] == "wire":
                    x0_, x1_ = sorted((o["a"][0], o["b"][0]))
                    y0_, y1_ = sorted((o["a"][1], o["b"][1]))
                else:
                    x0_ = x1_ = o["at"][0]
                    y0_ = y1_ = o["at"][1]
                for i in range(int(x0_) - 1, int(x1_) + 2):
                    for j in range(int(y0_) - 1, int(y1_) + 2):
                        allbucket[(i, j)].append((name, o))
                        for L in o["layers"]:
                            bucket[(L, i, j)].append((name, o))

            for name, (open_tag, body) in sig.items():
                if name in protect:
                    continue
                if name in PLANES:
                    kept_texts = None
                    if name in nets:
                        kept_texts = set(o.get("text") for o in nets[name].kept)
                    for o in parse_items(body):
                        if plane_rippable(o) and (kept_texts is None or o["text"] in kept_texts):
                            insert(name, o)
                    continue
                if name in EXCLUDE:
                    continue
                items = nets[name].kept if name in nets else parse_items(body)
                for o in items:
                    if o["kind"] != "pad":
                        insert(name, o)

            def near(x, y, L=None):
                src = bucket if L is not None else allbucket
                key = (L, int(x), int(y)) if L is not None else (int(x), int(y))
                return src.get(key, ())

            def gap(o, x, y):
                if o["kind"] == "wire":
                    return E.seg_pt(o["a"], o["b"], (x, y)) - o["radius"]
                return math.hypot(o["at"][0] - x, o["at"][1] - y) - o["radius"]

            npads = dict((name, len(padobjs.get(name, []))) for name in sig)
            rips = collections.defaultdict(set)
            boxed = 0
            for net in signal_nets + plane_nets:
                grid.open_net(net.name, True)
                seeds = [grid.seeds(objs)[0] for objs in net.pieces]
                is_plane = net.name in PLANES
                main = set()
                if is_plane:
                    main = set(li * grid.NN + c for k in net.main_idx for li, c in seeds[k])
                for k, s in enumerate(seeds):
                    if not s or (is_plane and k in net.main_idx):
                        continue
                    pocket = grid.flood(s, POCKET_CAP)
                    if pocket is None:
                        continue
                    if is_plane:
                        # a stranded plane pad is fine if it can reach main
                        # copper or any cell where a via to the plane could go
                        if pocket & main or any(grid.rt.vfree[n % grid.NN] for n in pocket):
                            continue
                    else:
                        others = set(li * grid.NN + c for j, s2 in enumerate(seeds) if j != k for li, c in s2)
                        if pocket & others:
                            continue
                    boxed += 1
                    walls = collections.Counter()
                    texts = collections.defaultdict(set)
                    for li, c in grid.wall_of(pocket):
                        L = int(LAYERS[li])
                        qx, qy = grid.m0.xy(c)
                        for oname, o in near(qx, qy, L):
                            if oname == net.name:
                                continue
                            if gap(o, qx, qy) <= clr + THIN / 2 + 0.006:
                                walls[oname] += 1
                                texts[oname].add(o["text"])
                    # AND WHAT DENIES IT A VIA. A pocket with no via site cannot
                    # dive to the inner layers; the copper on OTHER layers under
                    # it is as much a wall as the trace beside it.
                    seen_cells = set()
                    for n in pocket:
                        c = n % grid.NN
                        if c in seen_cells or grid.rt.vfree[c]:
                            continue
                        seen_cells.add(c)
                        qx, qy = grid.m0.xy(c)
                        for oname, o in near(qx, qy):
                            if oname == net.name:
                                continue
                            need = (via_clr if o["kind"] == "via" else clr) + VIA_L / 2 + 0.006
                            if gap(o, qx, qy) <= need:
                                walls[oname] += 1
                                texts[oname].add(o["text"])
                    if not walls:
                        log("   %-14s piece %d boxed in %d cell(s): nothing rippable around it"
                            % (net.name, k, len(pocket)))
                        continue
                    # a two-pad net reroutes; a four-pad JTAG net through a
                    # crowded corner does not, and then costs a restore
                    pick = max(walls, key=lambda n: (npads.get(n, 0) <= 3, walls[n], -npads.get(n, 0)))
                    rips[pick] |= texts[pick]
                    log("   %-14s piece %d boxed in %d cell(s): wall %s (%d cell(s), %d segment(s)); %d other net(s) also bound it"
                        % (net.name, k, len(pocket), pick, walls[pick], len(texts[pick]), len(walls) - 1))
                grid.open_net(net.name, False)
            if not rips:
                log("   no boxed piece with a rippable wall left")
                break
            for oname, texts in sorted(rips.items()):
                open_tag, body = sig[oname]
                terms = padobjs.get(oname, [])
                if oname in PLANES:
                    plane_rips[oname] |= texts
                    nets[oname] = honest_pieces(text_now(), oname, PLANES[oname], open_tag, body,
                                                terms, zones, plane_rips[oname])
                    log("   ripped %-14s %d stub segment(s), plane pass re-ties" % (oname, len(texts)))
                    continue
                if oname in nets:
                    nets[oname].rip(texts)
                    log("   ripped %-14s %d kept segment(s) -> %d piece(s)" % (oname, len(texts), len(nets[oname].pieces)))
                    continue
                ripped = [o for o in parse_items(body) if o["text"] in texts]
                nets[oname] = Net(oname, open_tag, body, terms, zones, force=True, ripped=ripped)
                log("   ripped %-14s %d segment(s) -> %d piece(s)" % (oname, len(texts), len(nets[oname].pieces)))
            log("   round %d: %d boxed piece(s), %d net(s) touched" % (rnd + 1, boxed, len(rips)))

    routed = {}       # name -> (wires, vias, width)

    text = text_now()
    wide = [n for n in nets.values() if n.name in WIDE_NETS]
    thin = [n for n in nets.values() if n.name not in WIDE_NETS and n.name not in PLANES]
    remaining = list(wide)
    if SEQUENTIAL == 2:
        # STRIP THEM ALL, ROUTE ONE AT A TIME, THEN PUT FAILURES BACK ONLY
        # WHERE THEY FIT. Stripping one net at a time (mode 1) leaves the
        # wall of the others standing: a west ball's L2 pocket is sealed by
        # the very nets in the group, and A3 found no path on 2026-09-06.
        # With everything stripped, 16 of 27 routed; the losses came from
        # restoring the failures blindly (run h8: 344 shorts). Here a failed
        # net's original copper returns only if it collides with no new
        # route; otherwise it gets one more try against the finished board,
        # and if that fails it stays open and is reported as a trade.
        failed_now, traded = [], []
        order = env_list("CLOSE_WIDE_NETS", "")
        remaining.sort(key=lambda n: order.index(n.name) if n.name in order else len(order))
        for net in list(remaining):
            done_net = False
            for w in WIDTHS:
                t_new, missed = run_pass(text, [net], w, "greedy", bx, clr, via_clr, routed)
                if net.name not in missed:
                    text = t_new
                    done_net = True
                    break
            if not done_net:
                routed.pop(net.name, None)
                failed_now.append(net)
                log("   %-14s no route yet; retried after the others" % net.name)
        for net in failed_now:
            old = [o for o in net.objects if o["kind"] != "pad"]
            hit = [other for other, (wires, vias, w) in routed.items() if other != net.name and conflicts(old, wires, vias, clr)]
            if not hit and not net.split_before and net.original is not None:
                text = rebuild(text, {net.name: net.original})
                log("   %-14s original copper restored, it collides with nothing new" % net.name)
                continue
            done_net = False
            for w in WIDTHS:
                t_new, missed = run_pass(text, [net], w, "greedy", bx, clr, via_clr, routed)
                if net.name not in missed:
                    text = t_new
                    done_net = True
                    log("   %-14s routed on the second try" % net.name)
                    break
            if not done_net:
                routed.pop(net.name, None)
                traded.append(net.name)
                log("   %-14s stays open: its old copper would cross %s" % (net.name, ", ".join(hit) or "nothing"))
        remaining = []
        thin = [n for n in thin if n.name not in set(m.name for m in nets.values() if m.forced)]
        if traded:
            log("== strip-all pass: %d net(s) traded open: %s" % (len(traded), ", ".join(traded)))
        if APPLY:
            # an hour of routing is not lost to a crash in the plane pass or
            # the verification (run c4, 2026-09-06: GND had no pour on the
            # layer it was told to use, and 104 routed nets went with it)
            io.open(OUT, "w", encoding="utf-8", newline="").write(text)
            log("== checkpoint written to %s (after the strip-all pass)" % OUT)
    elif SEQUENTIAL:
        # ONE NET AT A TIME, STRIPPING ONLY THAT NET. Every other net keeps
        # its original copper until its own turn, so a net that cannot be
        # re-routed simply stays as it was and nothing is ever put back under
        # a route laid earlier. (Restoring failures after the fact shorted
        # 344 clearances in run h8, 2026-09-06: UDQM's old copper came back
        # through A0's new route.) Rip-up and re-route, the classic way.
        failed_now = []
        order = env_list("CLOSE_WIDE_NETS", "")
        remaining.sort(key=lambda n: order.index(n.name) if n.name in order else len(order))
        others = dict((n.name, n.original) for n in nets.values() if n.name not in PLANES)
        text = rebuild(board, others)          # everyone whole, nobody stripped yet
        for net in list(remaining):
            t_try = rebuild(text, {net.name: net.body})   # strip this one only
            done_net = False
            for w in WIDTHS:
                t_new, missed = run_pass(t_try, [net], w, "greedy", bx, clr, via_clr, routed)
                if net.name not in missed:
                    text = t_new
                    done_net = True
                    break
            if not done_net:
                routed.pop(net.name, None)
                failed_now.append(net.name)
                log("   %-14s could not be re-routed; it keeps its original copper" % net.name)
        remaining = []
        thin = [n for n in thin if n.name not in others]   # the sequence covered them
        if failed_now:
            log("== sequential pass: %d net(s) kept as they were: %s" % (len(failed_now), ", ".join(failed_now)))
    for w in WIDTHS:
        if not remaining:
            break
        text, missed = run_pass(text, remaining, w, "greedy", bx, clr, via_clr, routed)
        remaining = [n for n in remaining if n.name in missed]
    forced = set(n.name for n in nets.values() if n.forced)
    text, missed_thin = run_pass(text, thin, THIN, "negotiate", bx, clr, via_clr, routed, priority=forced)
    for pname, player in PLANES.items():
        if pname not in sig:
            continue
        open_tag, body = sig[pname]
        pnet = honest_pieces(text, pname, player, open_tag, body, padobjs.get(pname, []), zones,
                             plane_rips.get(pname, ()))
        nets[pname] = pnet
        log("%-14s %d piece(s) with pads on the honest plane model" % (pname, len(pnet.pieces)))
        if len(pnet.pieces) > 1:
            text, missed_p = run_pass(text, [pnet], THIN, "greedy", bx, clr, via_clr, routed, plane=(pname, player))

    # ---- verify, and never leave a net worse than it began
    import xml.etree.ElementTree as ET
    ET.fromstring(text)
    before = C.parse_signal_objects(board)
    count0 = dict((name, len(C.components(*before[name]))) for name in nets)

    def counts(text):
        after = C.parse_signal_objects(text)
        return dict((name, len(C.components(*after[name]))) for name in nets)

    count1 = counts(text)
    # A PLANE NET GETS ITS STUBS BACK, NOT ITS WHOLE BODY. If a ripped GND
    # stub left a pad the plane pass could not re-tie, only the ripped
    # segments return; routes crossing them are dropped like any other.
    bodies = {}
    restore = collections.deque()
    for pname in PLANES:
        if pname in nets and count1.get(pname, 0) > count0[pname] and plane_rips.get(pname):
            cur = next((m.group(3) for m in SIG_RE.finditer(text) if m.group(2) == pname), "")
            bodies[pname] = cur + "".join(sorted(plane_rips[pname]))
            log("**** %s: %d piece(s) before, %d now -- %d ripped stub(s) restored"
                % (pname, count0[pname], count1[pname], len(plane_rips[pname])))
            old = [o for o in nets[pname].objects if o.get("text") in plane_rips[pname]]
            for other, (wires, vias, w) in list(routed.items()):
                if other != pname and conflicts(old, wires, vias, clr):
                    log("**** %s's new route collides with a restored stub and is dropped" % other)
                    del routed[other]
                    if not nets[other].split_before or nets[other].forced:
                        restore.append(other)
                    else:
                        bodies[other] = nets[other].body
    if bodies:
        text = rebuild(text, bodies)
        count1 = counts(text)
    if SEQUENTIAL == 2:
        # the strip-all pass already restored what fits and traded the
        # rest; the cascade below would put the traded copper back through
        # every new route and undo the pass (run h11, 2026-09-06)
        restore.clear()
    else:
        restore.extend(n for n in nets if count1[n] > count0[n] and n not in restore)
    first_failures = [n for n in restore if nets[n].forced]
    while restore:
        name = restore.popleft()
        if bodies.get(name) is nets[name].original:
            continue
        bodies[name] = nets[name].original
        log("**** %s: %d piece(s) before, %d now -- original copper restored"
            % (name, count0[name], count1.get(name, 0)))
        old = [o for o in nets[name].objects if o["kind"] != "pad"]
        for other, (wires, vias, w) in list(routed.items()):
            if other == name:
                continue
            if conflicts(old, wires, vias, clr):
                log("**** %s's new route collides with it and is dropped" % other)
                del routed[other]
                if not nets[other].split_before or nets[other].forced:
                    # it was whole before: its original goes back, and
                    # whatever THAT collides with is dropped in turn
                    restore.append(other)
                else:
                    bodies[other] = nets[other].body
    if bodies:
        text = rebuild(text, bodies)
        count1 = counts(text)
    still = sorted(n for n in nets if count1[n] > 1)
    ok = [n for n in nets if count1[n] == 1]
    log("verified: %d net(s) one piece, %d still split (%s)"
        % (len(ok), len(still), ", ".join("%s:%d" % (n, count1[n]) for n in still) or "-"))
    worse = [n for n in nets if count1[n] > count0[n]]
    if worse:
        if ACCEPT_TOTAL and sum(count1.values()) <= sum(count0.values()):
            log("**** worse for %s, but the total is %d -> %d airwires: accepted as a trade (CLOSE_ACCEPT=total)"
                % (", ".join(worse), sum(c - 1 for c in count0.values()), sum(c - 1 for c in count1.values())))
            return text, first_failures, still
        log("**** WORSE THAN BEFORE: %s -- this attempt is discarded" % ", ".join(worse))
        return None, first_failures or worse, still
    return text, first_failures, still


def boxed_walls(grid, signal_nets, plane_nets, sig, nets, padobjs, zones, protect):
    """for every boxed piece of every net under work: the one wall net worth
    ripping and the segments of it that bound the pocket. Returns
    {boxed net name: {wall net: set(texts)} or None if some piece has no
    rippable wall at all}."""

    def plane_rippable(o):
        # surface wires of a plane net: pad stubs, and -- with RIP_GANGS -- the
        # 0.225 mm gang traces that tie the BGA's ground and power balls, since
        # the plane pass can give a stranded ball its own dogbone or re-gang it
        if o["kind"] == "wire":
            if not (o["layers"] & frozenset((1, 16))):
                return False
            return RIP_GANGS or o["radius"] <= 0.051
        if o["kind"] == "via" and not blind(o):
            return all(max(abs(o["at"][0] - cx), abs(o["at"][1] - cy)) > r for cx, cy, r in zones)
        return False

    bucket = collections.defaultdict(list)
    allbucket = collections.defaultdict(list)

    def insert(name, o):
        if o["kind"] == "wire":
            x0_, x1_ = sorted((o["a"][0], o["b"][0]))
            y0_, y1_ = sorted((o["a"][1], o["b"][1]))
        else:
            x0_ = x1_ = o["at"][0]
            y0_ = y1_ = o["at"][1]
        for i in range(int(x0_) - 1, int(x1_) + 2):
            for j in range(int(y0_) - 1, int(y1_) + 2):
                allbucket[(i, j)].append((name, o))
                for L in o["layers"]:
                    bucket[(L, i, j)].append((name, o))

    for name, (open_tag, body) in sig.items():
        if name in protect:
            continue
        if name in PLANES:
            kept = None
            for pn in plane_nets:
                if pn.name == name:
                    kept = set(o.get("text") for o in pn.kept)
            for o in parse_items(body):
                if plane_rippable(o) and (kept is None or o["text"] in kept):
                    insert(name, o)
            continue
        if name in EXCLUDE:
            continue
        items = nets[name].kept if name in nets else parse_items(body)
        for o in items:
            if o["kind"] != "pad":
                insert(name, o)

    def gap(o, x, y):
        if o["kind"] == "wire":
            return E.seg_pt(o["a"], o["b"], (x, y)) - o["radius"]
        return math.hypot(o["at"][0] - x, o["at"][1] - y) - o["radius"]

    npads = dict((name, len(padobjs.get(name, []))) for name in sig)
    clr, via_clr = grid.clr, max(grid.clr, G.drill_clearance(grid.text, VIA_D) - (VIA_L - VIA_D))
    objmap = dict((o["text"], o) for lst in allbucket.values() for name, o in lst)

    def attribution(pocket, own):
        walls = collections.Counter()
        texts = collections.defaultdict(set)
        for li, c in grid.wall_of(pocket):
            L = int(LAYERS[li])
            qx, qy = grid.m0.xy(c)
            for oname, o in bucket.get((L, int(qx), int(qy)), ()):
                if oname != own and gap(o, qx, qy) <= clr + THIN / 2 + 0.006:
                    walls[oname] += 1
                    texts[oname].add(o["text"])
        seen_cells = set()
        for n in pocket:
            c = n % grid.NN
            if c in seen_cells or grid.rt.vfree[c]:
                continue
            seen_cells.add(c)
            qx, qy = grid.m0.xy(c)
            for oname, o in allbucket.get((int(qx), int(qy)), ()):
                if oname == own:
                    continue
                need = (via_clr if o["kind"] == "via" else clr) + VIA_L / 2 + 0.006
                if gap(o, qx, qy) <= need:
                    walls[oname] += 1
                    texts[oname].add(o["text"])
        return walls, texts

    out = {}
    for net in signal_nets + plane_nets:
        grid.open_net(net.name, True)
        seeds = [grid.seeds(objs)[0] for objs in net.pieces]
        is_plane = net.name in PLANES
        main = set()
        if is_plane:
            main = set(li * grid.NN + c for k in net.main_idx for li, c in seeds[k])

        def opened(pocket, k):
            if is_plane:
                return bool(pocket & main) or any(grid.rt.vfree[n % grid.NN] for n in pocket)
            others = set(li * grid.NN + c for j, s2 in enumerate(seeds) if j != k for li, c in s2)
            return bool(pocket & others)

        picks = {}
        dead = False
        freed = []
        for k, s in enumerate(seeds):
            if not s or (is_plane and k in net.main_idx):
                continue
            # RIP UNTIL IT OPENS. One wall is rarely the whole wall: a boxed
            # ball is bounded by six or more nets. Take the largest, free the
            # cells it blocked (optimistically -- another net may block some of
            # them too), flood again, repeat, up to MAX_WALLS nets.
            for step in range(MAX_WALLS + 1):
                pocket = grid.flood(s, POCKET_CAP)
                if pocket is None or opened(pocket, k):
                    break
                if step == MAX_WALLS:
                    dead = True
                    log("   %-14s piece %d still boxed after %d wall(s)" % (net.name, k, MAX_WALLS))
                    break
                walls, texts = attribution(pocket, net.name)
                if not walls:
                    dead = True
                    log("   %-14s piece %d boxed in %d cell(s): nothing rippable around it" % (net.name, k, len(pocket)))
                    break
                # THE WALL THAT BOUNDS THE MOST CELLS GOES FIRST. Ranking plane
                # nets first made CHAN13's L2 pocket rip VCC3V3 and GND gang
                # traces on L1 ten times over while the L2 escapes that
                # actually box it stood (r3, 2026-09-05). A plane net's copper
                # is still cheap (the plane pass re-ties it), so it counts at
                # half weight rather than winning outright; and a wall whose
                # segments are all picked already cannot be picked again.
                fresh = [n for n in walls if texts[n] - picks.get(n, set())]
                if not fresh:
                    dead = True
                    log("   %-14s piece %d boxed in %d cell(s): every wall around it is already ripped" % (net.name, k, len(pocket)))
                    break
                pick = max(fresh, key=lambda n: (walls[n] * (0.5 if n in PLANES else 1.0), npads.get(n, 0) <= 3, -npads.get(n, 0)))
                picks.setdefault(pick, set()).update(texts[pick])
                log("   %-14s piece %d boxed in %d cell(s): rip %s (%d segment(s)); %d other net(s) bound it"
                    % (net.name, k, len(pocket), pick, len(texts[pick]), len(walls) - 1))
                gone = set(t for ts in picks.values() for t in ts)

                def still_covered(qx, qy, L, need):
                    src = bucket.get((L, int(qx), int(qy)), ()) if L is not None else allbucket.get((int(qx), int(qy)), ())
                    for oname, q in src:
                        if q["text"] in gone or oname == net.name:
                            continue
                        if L is None:
                            need_q = (via_clr if q["kind"] == "via" else clr) + VIA_L / 2 + 0.006
                        else:
                            need_q = need
                        if gap(q, qx, qy) <= need_q:
                            return True
                    return False

                # FREE ONLY WHAT NOTHING ELSE STILL COVERS. Freeing every cell
                # the ripped wall had blocked called the pocket open after one
                # rip, and the route then failed against the walls that were
                # still there: cells another object also covers stay blocked,
                # so the flood only opens when the pocket really does.
                for t in texts[pick]:
                    o = objmap.get(t)
                    if o is None:
                        continue
                    for li, L in enumerate(LAYERS):
                        if int(L) not in o["layers"]:
                            continue
                        for c in PF.cells_of(circles_of([o], int(L)), grid.base[L], clr, THIN):
                            if grid.rt.free[li][c]:
                                continue
                            qx, qy = grid.m0.xy(c)
                            if still_covered(qx, qy, int(L), clr + THIN / 2 + 0.006):
                                continue
                            freed.append((li, c))
                            grid.rt.free[li][c] = 1
                    for c in PF.cells_of(circles_of([o], None), grid.m0, clr, VIA_L, margin=0.15):
                        if grid.rt.vfree[c]:
                            continue
                        qx, qy = grid.m0.xy(c)
                        if still_covered(qx, qy, None, None):
                            continue
                        freed.append((-1, c))
                        grid.rt.vfree[c] = 1
        for li, c in freed:
            if li < 0:
                grid.rt.vfree[c] = 0
            else:
                grid.rt.free[li][c] = 0
        # NOT BOXED, STILL APART. With a microvia at each end both pieces of
        # A10 flood thousands of cells and never meet: the BGA ring, or a bus
        # running the length of U3, separates them at board scale. Flood both
        # sides fully and rip the copper that BOTH floods press against.
        if not picks and not dead and not is_plane and len(seeds) >= 2 and seeds[0] and seeds[1]:
            f0 = grid.flood(seeds[0], 10 ** 9)
            others = set(li * grid.NN + c for j, s2 in enumerate(seeds) if j != 0 for li, c in s2)
            if f0 and not (f0 & others):
                f1 = grid.flood(seeds[1], 10 ** 9)
                pts = [grid.rt.xy(c) for li, c in seeds[0] + seeds[1]]
                bx0, bx1 = min(p[0] for p in pts) - 3.0, max(p[0] for p in pts) + 3.0
                by0, by1 = min(p[1] for p in pts) - 3.0, max(p[1] for p in pts) + 3.0

                def inside(nodes):
                    keep_ = set()
                    for n in nodes:
                        x, y = grid.rt.xy(n % grid.NN)
                        if bx0 <= x <= bx1 and by0 <= y <= by1:
                            keep_.add(n)
                    return keep_

                w0, t0 = attribution(inside(f0), net.name)
                w1, t1 = attribution(inside(f1), net.name)
                common = [n for n in w0 if n in w1]
                if common:
                    pick = max(common, key=lambda n: (n in PLANES, npads.get(n, 0) <= 3, min(w0[n], w1[n]), -npads.get(n, 0)))
                    picks[pick] = set(t0[pick]) | set(t1[pick])
                    log("   %-14s pieces apart at board scale (%d and %d cells): frontier wall %s (%d segment(s)); %d net(s) on the frontier"
                        % (net.name, len(f0), len(f1), pick, len(picks[pick]), len(common)))
                else:
                    log("   %-14s pieces apart at board scale, no common rippable wall" % net.name)
        grid.open_net(net.name, False)
        if picks and not dead:
            out[net.name] = picks
    return out


def pockets_mode():
    """One pocket at a time. Rip the walls of ONE boxed net, route it together
    with the wall nets and nothing else, and keep the result only if no net
    has more pieces than it had. Nothing else moves, so nothing can cascade:
    a pocket that will not open costs one rejected try, not the layout."""
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    pads, fields = pad_index(board)
    zones = [(fields[el][0], fields[el][1], r) for el, r in ZONE_R.items() if el in fields] + EXTRA_ZONES
    outline = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                         r' y2="([-\d.]+)"[^>]*layer="20"', board)
    xs = [float(v) for q in outline for v in (q[0], q[2])]
    ys = [float(v) for q in outline for v in (q[1], q[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))
    clr = G.rule_mm(board, "mdWireWire") + 0.005
    via_clr = max(clr, G.drill_clearance(board, VIA_D) - (VIA_L - VIA_D))
    padobjs = collections.defaultdict(list)
    for key, p in pads.items():
        if p["net"]:
            padobjs[p["net"]].append(p)
    routed = {}

    def current(text):
        sig = dict((m.group(2), (m.group(1), m.group(3))) for m in SIG_RE.finditer(text))
        nets = {}
        for name, (open_tag, body) in sig.items():
            if name in EXCLUDE or (ONLY and name not in ONLY):
                continue
            terms = padobjs.get(name, [])
            if len(terms) < 2:
                continue
            probe = Net(name, open_tag, body, terms, zones)
            if probe.split_before:
                nets[name] = probe
        planes = [honest_pieces(text, p, L, sig[p][0], sig[p][1], padobjs.get(p, []), zones)
                  for p, L in PLANES.items() if p in sig and p not in PROTECT]
        return sig, nets, planes

    def counts(text, names):
        after = C.parse_signal_objects(text)
        return dict((n, len(C.components(*after[n]))) for n in names if n in after)

    every = [m.group(2) for m in SIG_RE.finditer(board) if len(padobjs.get(m.group(2), [])) >= 2]
    base = counts(board, every)
    text = board

    def retie(t, before):
        """a new signal via can strand a plane via behind its antipad; tie
        whatever the planes lost before judging the result"""
        sig_t = dict((m.group(2), (m.group(1), m.group(3))) for m in SIG_RE.finditer(t))
        c = counts(t, list(PLANES))
        for pname, player in PLANES.items():
            if pname not in sig_t or pname in PROTECT or c.get(pname, 0) <= before.get(pname, 0):
                continue
            pn = honest_pieces(t, pname, player, sig_t[pname][0], sig_t[pname][1], padobjs.get(pname, []), zones)
            if len(pn.pieces) > 1:
                t, _ = run_pass(t, [pn], THIN, "greedy", bx, clr, via_clr, routed, plane=(pname, player))
        return t

    # ---- corridor rip (optional): CLOSE_CORRIDOR="x0,y0,x1,y1" takes every
    # non-plane wire that crosses the window out of the board before phase A,
    # so the nets that saturate a corridor on all six layers negotiate it
    # again together with the open ones. All-or-nothing: if phase A cannot
    # put them all back, the board reverts to what it was.
    text_before_corridor = text
    if CORRIDOR:
        cx0, cy0, cx1, cy1 = CORRIDOR
        rect = ((cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0, (cx1 - cx0) / 2.0, (cy1 - cy0) / 2.0, 0.0)
        ripped_n = collections.Counter()

        def corridor_sub(m):
            name = m.group(2)
            if name in PLANES or name in EXCLUDE or name in PROTECT or len(padobjs.get(name, [])) < 2:
                return m.group(0)
            body = m.group(3)
            for o in parse_items(body):
                if o["kind"] == "wire" and G.rect_seg(rect, o["a"], o["b"]) <= o["radius"]:
                    body = body.replace(o["text"], "", 1)
                    ripped_n[name] += 1
            return m.group(1) + body + m.group(4)

        text = SIG_RE.sub(corridor_sub, text)
        log("== corridor x %.1f..%.1f y %.1f..%.1f: ripped %d segment(s) of %d net(s): %s"
            % (cx0, cx1, cy0, cy1, sum(ripped_n.values()), len(ripped_n),
               ", ".join("%s(%d)" % kv for kv in ripped_n.most_common(12))))

    # ---- phase A: the free wins, no ripping
    sig, nets, planes = current(text)
    if not nets:
        log("nothing open")
        return 0
    log("== pocket mode: %d open net(s); phase A routes them as they are" % len(nets))
    t = rebuild(text, dict((n.name, n.body) for n in nets.values()))
    remaining = [n for n in nets.values() if n.name in WIDE_NETS]
    for w in WIDTHS:
        if not remaining:
            break
        t, missed = run_pass(t, remaining, w, "greedy", bx, clr, via_clr, routed)
        remaining = [n for n in remaining if n.name in missed]
    thin = [n for n in nets.values() if n.name not in WIDE_NETS and n.name not in PLANES]
    t, missed = run_pass(t, thin, THIN, "negotiate", bx, clr, via_clr, routed)
    t = prune_loose(t, set(n.name for n in nets.values()), padobjs)
    t = retie(t, base)
    c = counts(t, every)
    worse = [n for n in every if c.get(n, 0) > base[n]]
    if worse:
        log("== phase A rejected, worse for %s" % ", ".join(worse))
        if CORRIDOR:
            text = text_before_corridor
            log("== corridor rip reverted; the board is as it was")
    else:
        text = t
        log("== phase A accepted: %d net(s) closed" % sum(1 for n in nets if c.get(n, 9) == 1))
        if APPLY:
            io.open(OUT, "w", encoding="utf-8", newline="").write(text)
            log("== checkpoint written to %s (after phase A)" % OUT)

    def attempt_pocket(text, stripped, sig, nets, bname, picks, want=None):
        """rip `picks` around boxed net `bname`, route the group, and return
        the new text if `bname` gained (or reached `want` pieces) and nothing
        else lost; None otherwise. Nothing but this group ever changes."""
        group = [nets[bname]]
        bodies = {bname: nets[bname].body}
        plane_touched = {}
        for pick, texts in picks.items():
            if pick in PLANES:
                pn = honest_pieces(stripped, pick, PLANES[pick], sig[pick][0], sig[pick][1],
                                   padobjs.get(pick, []), zones, texts)
                bodies[pick] = pn.body
                plane_touched[pick] = texts
            elif pick in nets:
                nets[pick].rip(texts)
                group.append(nets[pick])
                bodies[pick] = nets[pick].body
            else:
                ripped = [o for o in parse_items(sig[pick][1]) if o["text"] in texts]
                wall = Net(pick, sig[pick][0], sig[pick][1], padobjs.get(pick, []), zones, force=True, ripped=ripped)
                group.append(wall)
                bodies[pick] = wall.body
        names = [n.name for n in group] + list(plane_touched) + list(PLANES)
        before = counts(text, names)
        log("   try %s: rip %s" % (bname, ", ".join("%s(%d)" % (p, len(t_)) for p, t_ in picks.items()) or "nothing"))
        t_try = rebuild(stripped, bodies)
        # THE BOXED NET SETTLES FIRST. Giving the wall nets first claim let
        # them take the freed corridor straight back, and every try ended
        # "no gain". A wall net that cannot detour around the boxed net's
        # new route makes this a cheap rejection, not a loss.
        t_new, missed = run_pass(t_try, group, THIN, "negotiate", bx, clr, via_clr, routed,
                                 priority=set([bname]))
        for pname, texts in plane_touched.items():
            pn = honest_pieces(t_new, pname, PLANES[pname], sig[pname][0], sig[pname][1],
                               padobjs.get(pname, []), zones, texts)
            if len(pn.pieces) > 1:
                t_new, _ = run_pass(t_new, [pn], THIN, "greedy", bx, clr, via_clr, routed, plane=(pname, PLANES[pname]))
        t_new = prune_loose(t_new, set(names), padobjs)
        t_new = retie(t_new, before)
        after = counts(t_new, names)
        target = want if want is not None else before.get(bname, 9) - 1
        gain = after.get(bname, 9) <= target
        harm = [n for n in names if n != bname and after.get(n, 9) > before.get(n, 0)]
        if gain and not harm:
            log("   ACCEPTED %s: %d -> %d piece(s)" % (bname, before.get(bname, 9), after[bname]))
            return t_new, t_try
        log("   rejected %s: %s" % (bname, "no gain" if not gain else "worse for %s" % ", ".join(harm)))
        return None, t_try

    def escalate(text, stripped, sig, nets, bname, picks, want=None, tried=None):
        """try the pocket; on "no gain", analyse the board WITH those rips
        applied, add the walls that still box the piece, and try again -- the
        flood that chose the first walls is optimistic about cells that pads
        and unindexed copper also cover, so one pass rarely picks them all."""
        picks = dict((p, set(t)) for p, t in picks.items())
        for step in range(ESCALATE + 1):
            key = (bname, tuple(sorted((p, len(t)) for p, t in picks.items())))
            if tried is not None:
                if key in tried:
                    return None
                tried.add(key)
            done, t_try = attempt_pocket(text, stripped, sig, nets, bname, picks, want)
            if done is not None:
                return done
            if step == ESCALATE:
                return None
            sig_t, nets_t, planes_t = current(t_try)
            if bname not in nets_t:
                return None
            stripped_t = rebuild(t_try, dict((n.name, n.body) for n in nets_t.values()))
            grid_t = Grid(stripped_t, list(nets_t.values()) + planes_t, THIN, bx, clr, via_clr)
            more = boxed_walls(grid_t, [nets_t[bname]], planes_t, sig_t, nets_t, padobjs, zones, PROTECT)
            if bname not in more or not more[bname]:
                return None
            grew = False
            for p, ts in more[bname].items():
                if p == bname:
                    continue
                before_n = len(picks.get(p, ()))
                picks.setdefault(p, set()).update(ts)
                grew = grew or len(picks[p]) > before_n
            if not grew:
                return None
            log("   escalate %s: now ripping %s" % (bname, ", ".join("%s(%d)" % (p, len(t)) for p, t in picks.items())))
        return None

    # ---- evict through-routing from the escape layer under a part. On the
    # HDI build L2 under the BGA belongs to the microvia escapes; the L3 copper
    # renumbered onto it (the SDRAM bus, mostly) is moved out one net at a
    # time, each kept only if it comes back whole.
    for ev in EVICT:
        ev_layer, ev_el = int(ev[0]), ev[1]
        hx_ = float(ev[2])
        hy_ = float(ev[3]) if len(ev) > 3 else hx_
        if ev_el in fields:
            ecx, ecy = fields[ev_el]
            sig = dict((m.group(2), (m.group(1), m.group(3))) for m in SIG_RE.finditer(text))
            victims = []
            for name, (ot, body) in sorted(sig.items()):
                if name in EXCLUDE or name in PROTECT or name in PLANES:
                    continue
                inzone = [o for o in parse_items(body) if o["kind"] == "wire" and o["layer"] == ev_layer and
                          ((abs(o["a"][0] - ecx) <= hx_ and abs(o["a"][1] - ecy) <= hy_) or
                           (abs(o["b"][0] - ecx) <= hx_ and abs(o["b"][1] - ecy) <= hy_))]
                if inzone:
                    victims.append((name, inzone))
            log("== evicting L%d copper under %s from %d net(s)" % (ev_layer, ev_el, len(victims)))
            for name, inzone in victims:
                sig = dict((m.group(2), (m.group(1), m.group(3))) for m in SIG_RE.finditer(text))
                if counts(text, [name]).get(name, 9) != 1:
                    continue
                fnet = Net(name, sig[name][0], sig[name][1], padobjs.get(name, []), zones, force=True, ripped=inzone)
                nets = {name: fnet}
                stripped = rebuild(text, {name: fnet.body})
                done, _ = attempt_pocket(text, stripped, sig, nets, name, {}, want=1)
                if done is not None:
                    text = done
                    log("   evicted %s (%d segment(s))" % (name, len(inzone)))
                else:
                    log("   %s stays on L%d" % (name, ev_layer))

    # ---- forced nets, one at a time: strip to escapes (laser vias go),
    # route alone, rip walls if boxed, keep only if it comes back whole
    for fname in [q for q in FORCE if q not in PROTECT]:
        sig = dict((m.group(2), (m.group(1), m.group(3))) for m in SIG_RE.finditer(text))
        if fname not in sig:
            continue
        terms = padobjs.get(fname, [])
        fnet = Net(fname, sig[fname][0], sig[fname][1], terms, zones, force=True)
        nets = {fname: fnet}
        planes = [honest_pieces(text, p, L, sig[p][0], sig[p][1], padobjs.get(p, []), zones)
                  for p, L in PLANES.items() if p in sig and p not in PROTECT]
        stripped = rebuild(text, {fname: fnet.body})
        log("== forced %s: %d piece(s) after stripping" % (fname, len(fnet.pieces)))
        done, _ = attempt_pocket(text, stripped, sig, nets, fname, {}, want=1)
        if done is None:
            grid = Grid(stripped, [fnet] + planes, THIN, bx, clr, via_clr)
            cands = boxed_walls(grid, [fnet], planes, sig, nets, padobjs, zones, PROTECT)
            if fname in cands:
                done = escalate(text, stripped, sig, nets, fname, cands[fname], want=1)
        if done is not None:
            text = done
        else:
            log("== forced %s stays as it was" % fname)

    # CHECKPOINT. A run is hours long and the pocket phase can end with nothing
    # gained; what phase A and the evictions won is written as soon as it is
    # won (with --apply), so a stop or a crash costs a round, not the run.
    def checkpoint(t, why):
        if APPLY:
            io.open(OUT, "w", encoding="utf-8", newline="").write(t)
            log("== checkpoint written to %s (%s)" % (OUT, why))

    checkpoint(text, "after phase A and evictions")

    # ---- phase B: pockets
    tried = set()
    for rnd in range(POCKET_ROUNDS):
        sig, nets, planes = current(text)
        if not nets:
            break
        stripped = rebuild(text, dict((n.name, n.body) for n in nets.values()))
        signal_nets = list(nets.values())
        grid = Grid(stripped, signal_nets + planes, THIN, bx, clr, via_clr)
        log("-- pocket round %d: %d open net(s), via sites %.1f %%" % (rnd + 1, len(nets), 100.0 * sum(grid.rt.vfree) / grid.NN))
        cands = boxed_walls(grid, signal_nets, planes, sig, nets, padobjs, zones, PROTECT)
        progress = False
        for bname in sorted(cands, key=lambda n: sum(len(v) for v in cands[n].values())):
            picks = cands[bname]
            if bname in PLANES:
                continue
            if (bname, tuple(sorted((p, len(t)) for p, t in picks.items()))) in tried:
                continue
            done = escalate(text, stripped, sig, nets, bname, picks, tried=tried)
            if done is not None:
                text = done
                progress = True
                checkpoint(text, "pocket %s closed" % bname)
                break
        if not progress:
            log("== no pocket left that opens")
            break

    # ---- plane pass on what is left stranded
    for pname, player in PLANES.items():
        sig = dict((m.group(2), (m.group(1), m.group(3))) for m in SIG_RE.finditer(text))
        if pname not in sig or pname in PROTECT:
            continue
        pn = honest_pieces(text, pname, player, sig[pname][0], sig[pname][1], padobjs.get(pname, []), zones)
        if len(pn.pieces) > 1:
            before = counts(text, every)
            t_new, _ = run_pass(text, [pn], THIN, "greedy", bx, clr, via_clr, routed, plane=(pname, player))
            after = counts(t_new, every)
            if all(after.get(n, 0) <= before.get(n, 0) for n in every):
                text = t_new

    c = counts(text, every)
    worse = [n for n in every if c.get(n, 0) > base[n]]
    still = sorted(n for n in every if c.get(n, 0) > 1)
    log("verified: %d still split (%s); airwires %d -> %d"
        % (len(still), ", ".join("%s:%d" % (n, c[n]) for n in still) or "-",
           sum(base[n] - 1 for n in every), sum(c.get(n, 1) - 1 for n in every)))
    if worse:
        log("**** WORSE THAN BEFORE: %s -- nothing written" % ", ".join(worse))
        return 2
    if not APPLY:
        log("report only -- re-run with --apply to write %s" % OUT)
        return 0 if not still else 1
    io.open(OUT, "w", encoding="utf-8", newline="").write(text)
    log("wrote %s (%d net(s) still split)" % (OUT, len(still)))
    return 0 if not still else 1


POCKET_ROUNDS = int(os.environ.get("CLOSE_POCKET_ROUNDS", "40"))
MAX_WALLS = int(os.environ.get("CLOSE_MAX_WALLS", "10"))
ESCALATE = int(os.environ.get("CLOSE_ESCALATE", "3"))
# "2:U1:7.9,7:U3:12:7.3" -- clear layer 2 within 7.9 mm (chebyshev) of U1's
# pad-field centre, and layer 7 within a 12 x 7.3 mm half-extent box about U3's
EVICT = [tuple(e.split(":")) for e in env_list("CLOSE_EVICT", "") if e.count(":") >= 2]
MODE = os.environ.get("CLOSE_MODE", "pockets")


def main():
    if MODE == "pockets":
        return pockets_mode()
    return attempts_mode()


def attempts_mode():
    """attempt after attempt from the original board. A net that was whole
    and could not be rerouted is PROTECTED next time -- never ripped, never
    forced -- so its walls stand and whatever hides behind them stays open,
    rather than restoring its copper into a layout routed without it."""
    protect = set(PROTECT)
    final = None
    for attempt in range(ATTEMPTS):
        log("== attempt %d of %d; protected: %s" % (attempt + 1, ATTEMPTS, ", ".join(sorted(protect)) or "-"))
        text, failed, still = run_attempt(protect)
        # KEEP THE BEST ATTEMPT, NOT THE LAST. Protecting a failure can cost
        # two other nets their routes (attempt 2 of the CHAN bus re-plan lost
        # CHAN27 and CHAN28); the board with the fewest split nets is the one
        # to write.
        if text is not None and (final is None or len(still) < len(final[1])):
            final = (text, still)
            log("== attempt %d is the best so far: %d net(s) still split" % (attempt + 1, len(still)))
        if not failed:
            break
        log("== %d net(s) could not be rerouted and will be protected: %s" % (len(failed), ", ".join(sorted(failed))))
        protect |= set(failed)
    if final is None:
        log("no attempt produced a board that is nowhere worse -- nothing written")
        return 2
    text, still = final
    if not APPLY:
        log("report only -- re-run with --apply to write %s" % OUT)
        return 0 if not still else 1
    io.open(OUT, "w", encoding="utf-8", newline="").write(text)
    log("wrote %s (%d net(s) still split)" % (OUT, len(still)))
    return 0 if not still else 1


if __name__ == "__main__":
    sys.exit(main())
