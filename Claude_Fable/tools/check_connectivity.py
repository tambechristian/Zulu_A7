# -*- coding: utf-8 -*-
"""Report pad-to-pad connectivity of every signal in an EAGLE/Fusion board.

This checks actual copper components, not whether a signal merely contains a
wire. Wires connect only on their own layer; vias and plated pads span the
board. Inner plane polygons connect matching through objects on that layer.

FUSION WRITES A POUR AS <polygonpour>, NOT <polygon>. The plane regex matched
only the classic Eagle tag, so a board saved by Fusion had no planes at all as
far as this checker knew: GND read as 65 pieces and VCC3V3 as 37, when both sit
on solid inner planes. tools/plane_islands.py is the raster check that the plane
really does reach every one of those through objects.
"""

import collections
import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E
import geom as G


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "zulu_a7.brd")
COPPER_LAYERS = frozenset((1, 2, 3, 4, 5, 6, 7, 16))
# FUSION'S TOLERANCE IS ZERO. Its coordinates are integers of 1/320000 mm, so
# two ends 0.0011 mm apart (FB2_NODE) or 0.00005 mm apart (FLASH-D02) are two
# points and an airwire. Anything the file can express at five decimals is
# distinct; 1e-5 only absorbs float parsing.
EPS = 1e-5


class UnionFind(object):
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, value):
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, first, second):
        first, second = self.find(first), self.find(second)
        if first != second:
            self.parent[first] = second


def layer_overlap(first, second):
    return bool(first & second)


def pad_wire(pad, wire):
    if not layer_overlap(pad["layers"], wire["layers"]):
        return False
    if pad["through"]:
        return E.seg_pt(wire["a"], wire["b"], pad["at"]) <= (
            pad["hx"] + wire["radius"] + EPS)
    rect = (pad["at"][0], pad["at"][1], pad["hx"], pad["hy"], 0.0)
    return G.rect_seg(rect, wire["a"], wire["b"]) <= wire["radius"] + EPS


def pad_disc(pad, disc):
    if not layer_overlap(pad["layers"], disc["layers"]):
        return False
    if pad["through"]:
        return math.hypot(pad["at"][0] - disc["at"][0],
                          pad["at"][1] - disc["at"][1]) <= (
            pad["hx"] + disc["radius"] + EPS)
    return G.rect_pt((pad["at"][0], pad["at"][1], pad["hx"], pad["hy"]),
                     disc["at"][0], disc["at"][1]) <= disc["radius"] + EPS


def pad_pad(first, second):
    if not layer_overlap(first["layers"], second["layers"]):
        return False
    return (abs(first["at"][0] - second["at"][0]) <=
            first["hx"] + second["hx"] + EPS and
            abs(first["at"][1] - second["at"][1]) <=
            first["hy"] + second["hy"] + EPS)


def parse_signal_objects(board):
    pads = collections.defaultdict(list)
    for net, x, y, hx, hy, side in E.board_copper(board, skip=()):
        if net is None:
            continue
        pads[net].append({
            "kind": "pad",
            "at": (x, y),
            "hx": hx,
            "hy": hy,
            "through": side == 0,
            "layers": COPPER_LAYERS if side == 0 else frozenset((side,)),
        })

    signals = {}
    sm = re.search(r"<signals>(.*)</signals>", board, re.S)
    for match in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>',
                             sm.group(1) if sm else "", re.S):
        net, body = match.group(1), match.group(2)
        objects = list(pads.get(net, ()))
        terminals = len(objects)
        for via_match in re.finditer(r"<via\s([^>]*)>", body):
            attrs = dict(re.findall(
                r'(\w+)="([^"]*)"', via_match.group(1)))
            if "x" not in attrs or "y" not in attrs:
                continue
            x, y = float(attrs["x"]), float(attrs["y"])
            if "diameter" in attrs:
                diameter = float(attrs["diameter"])
            else:
                drill = float(attrs.get("drill", "0.2"))
                diameter = drill + 2 * max(drill * 0.25, 0.05)
            first, last = (int(value) for value in
                           attrs.get("extent", "1-16").split("-"))
            lo, hi = sorted((first, last))
            objects.append({
                "kind": "via",
                "at": (x, y),
                "radius": diameter / 2.0,
                "layers": frozenset(
                    layer for layer in COPPER_LAYERS if lo <= layer <= hi),
            })
        for wire in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                r' y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"', body):
            layer = int(wire.group(6))
            if layer not in COPPER_LAYERS:
                continue
            objects.append({
                "kind": "wire",
                "a": (float(wire.group(1)), float(wire.group(2))),
                "b": (float(wire.group(3)), float(wire.group(4))),
                "radius": float(wire.group(5)) / 2.0,
                "layers": frozenset((layer,)),
            })
        planes = set(int(layer) for layer in re.findall(
            r'<polygon(?:pour)?\b[^>]*layer="(\d+)"', body))
        # A PLANE IS ONLY AS SOLID AS THE FLOOD SAYS. Rather than take the pour
        # as one piece, raster it (tools/plane_islands.py) and keep the set of
        # own through objects the MAIN piece actually reaches; only those are
        # joined below. On this board that is the difference between "GND is
        # 15 pieces" and the truth.
        inner = set(layer for layer in planes if layer in COPPER_LAYERS)
        if inner:
            planes = dict((layer, plane_reach(board, layer, net))
                          for layer in sorted(inner))
        signals[net] = (objects, terminals, planes)
    return signals


_PLANE_CACHE = {}


def plane_reach(board, layer, net):
    """(x, y) of the net's through objects the main pour piece on `layer`
    reaches, rounded to 3 places; cached per board text."""
    key = (hash(board), len(board), layer, net)
    if key not in _PLANE_CACHE:
        import plane_islands as PI
        result = PI.analyse(board, layer, net, log=lambda *a: None)
        _PLANE_CACHE.clear()
        _PLANE_CACHE[key] = result["groups"] if result else []
    return _PLANE_CACHE[key]


def same_point(a, b):
    return abs(a[0] - b[0]) <= EPS and abs(a[1] - b[1]) <= EPS


def inside_pad(pad, pt):
    return (abs(pt[0] - pad["at"][0]) <= pad["hx"] + EPS
            and abs(pt[1] - pad["at"][1]) <= pad["hy"] + EPS)


def touches(a, b):
    """FUSION'S RULE, NOT OVERLAP. Fusion (like EAGLE) joins copper at END
    POINTS: two wires are one piece only where an end of one lies on an end
    of the other; a wire reaches a via only when it ends on the via's
    centre; a wire reaches a pad when an END lies inside it; a via sits in a
    pad when its centre does. A wire ending on the body of another (a T), or
    0.05 mm short of it with the copper plainly overlapping, is an open
    circuit to Ratsnest. The overlap model this replaced said 46 airwires
    where Fusion drew 60 (read back with tools/airwires.ulp, 2026-09-05);
    with these rules, and every piece counted, the two agree net by net."""
    if not layer_overlap(a["layers"], b["layers"]):
        return False
    ka, kb = a["kind"], b["kind"]
    if ka == "wire" and kb == "wire":
        return any(same_point(p, q) for p in (a["a"], a["b"]) for q in (b["a"], b["b"]))
    if ka == "wire" and kb == "via":
        return same_point(a["a"], b["at"]) or same_point(a["b"], b["at"])
    if ka == "via" and kb == "wire":
        return same_point(b["a"], a["at"]) or same_point(b["b"], a["at"])
    if ka == "wire" and kb == "pad":
        return inside_pad(b, a["a"]) or inside_pad(b, a["b"])
    if ka == "pad" and kb == "wire":
        return inside_pad(a, b["a"]) or inside_pad(a, b["b"])
    if ka == "via" and kb == "pad":
        return inside_pad(b, a["at"])
    if ka == "pad" and kb == "via":
        return inside_pad(a, b["at"])
    if ka == "via" and kb == "via":
        return same_point(a["at"], b["at"])
    return pad_pad(a, b)


def connectivity_union(objects, planes):
    union = UnionFind(len(objects))
    for first in range(len(objects)):
        a = objects[first]
        for second in range(first + 1, len(objects)):
            if touches(a, objects[second]):
                union.union(first, second)

    # A pour connects whatever of its net its MAIN piece reaches (planes as a
    # dict from parse_signal_objects): vias and plated pads on inner layers,
    # and on the outer layers also the SMD pads and own wires the copper
    # flows into. Wires are keyed by their first point, as plane_islands
    # reports them. The old set-of-layers form still means "solid".
    if isinstance(planes, dict):
        for layer, groups in planes.items():
            keyed = collections.defaultdict(list)
            for i, obj in enumerate(objects):
                if layer in obj["layers"]:
                    key = obj["a"] if obj["kind"] == "wire" else obj["at"]
                    keyed[(round(key[0], 3), round(key[1], 3))].append(i)
            for keys in groups:
                members = [i for key in keys for i in keyed.get(key, ())]
                for item in members[1:]:
                    union.union(members[0], item)
    else:
        for layer in (L for L in planes if 2 <= L <= 7):
            through = [i for i, obj in enumerate(objects)
                       if obj["kind"] in ("via", "pad")
                       and layer in obj["layers"] and
                       (obj["kind"] == "via" or obj["through"])]
            for item in through[1:]:
                union.union(through[0], item)

    return union


def components(objects, terminals, planes):
    """Every piece of the net, pads or not: Fusion draws an airwire to a
    leftover via or a floating stub just as it does to a stranded pad."""
    union = connectivity_union(objects, planes)
    groups = collections.defaultdict(list)
    for index in range(len(objects)):
        groups[union.find(index)].append(index)
    return list(groups.values())


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    total = 0
    split = []
    for net, (objects, terminals, planes) in parse_signal_objects(board).items():
        if terminals < 2:
            continue
        groups = components(objects, terminals, planes)
        gaps = len(groups) - 1
        if gaps:
            split.append((net, terminals, len(groups),
                          sorted((len(group) for group in groups), reverse=True)))
            total += gaps
    for net, terminals, count, sizes in sorted(
            split, key=lambda item: (-item[2], item[0])):
        print("%-20s pads=%3d components=%3d airwires=%3d groups=%s"
              % (net, terminals, count, count - 1, sizes[:10]))
    print("\n%d split net(s), %d explicit-copper airwire(s)" % (len(split), total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
