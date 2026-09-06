# -*- coding: utf-8 -*-
"""Negotiate routes for remaining two-terminal signals on a partial board."""

import io
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C
import geom as G
import pathfinder as PF
import power as P


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
APPLY = "--apply" in sys.argv
WIDTH = float(os.environ.get("NEGOTIATE_WIDTH", "0.0762"))
LAYERS = tuple(q.strip() for q in
               os.environ.get("NEGOTIATE_LAYERS", "1,3,4,6,7,16").split(",")
               if q.strip())


def g(value):
    text = ("%.4f" % value).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def own_obstacles(objects):
    out = []
    for obj in objects:
        if obj["kind"] == "pad":
            out.extend(G.as_circles([
                (obj["at"][0], obj["at"][1], obj["hx"], obj["hy"], 0.0)
            ], step=0.05))
        elif obj["kind"] == "via":
            out.append((obj["at"][0], obj["at"][1], obj["radius"]))
        elif obj["kind"] == "wire":
            out.extend(G.sample(obj["a"], obj["b"], obj["radius"]))
    return out


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    requested = {q.strip() for q in
                 os.environ.get("NEGOTIATE_NETS", "").split(",") if q.strip()}
    nets = []
    terms = {}
    own = {}
    slay = {}
    dlay = {}
    for net, (objects, terminal_count, planes) in parsed.items():
        if requested and net not in requested:
            continue
        if terminal_count != 2 or len(C.components(
                objects, terminal_count, planes)) == 1:
            continue
        pads = P.pads_of(board, net, skip=())
        if len(pads) != 2:
            continue
        nets.append(net)
        terms[net] = (pads[0][:2], pads[1][:2])
        own[net] = own_obstacles(objects)
        slay[net] = tuple(LAYERS) if pads[0][2] == 0 else (
            str(16 if pads[0][2] == 16 else 1),)
        dlay[net] = tuple(LAYERS) if pads[1][2] == 0 else (
            str(16 if pads[1][2] == 16 else 1),)

    outline = re.findall(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
        r' y2="([-\d.]+)"[^>]*layer="20"', board)
    xs = [float(value) for item in outline for value in (item[0], item[2])]
    ys = [float(value) for item in outline for value in (item[1], item[3])]
    bounds = (min(xs), min(ys), max(xs), max(ys))
    clearance = G.rule_mm(board, "mdWireWire") + 0.005
    print("negotiating %d two-terminal net(s)" % len(nets))
    routes, missed = PF.route_group(
        board, nets, terms, own, bounds, clearance, WIDTH, LAYERS,
        slay=slay, dlay=dlay)
    print("routed %d, missed %d%s" % (
        len(routes), len(missed),
        ": " + ", ".join(missed) if missed else ""))
    if not APPLY:
        return 0 if routes else 1

    updated = board
    for net, (vias, segments) in routes.items():
        additions = [
            '<via x="%s" y="%s" extent="1-16" drill="0.2" diameter="0.3"/>'
            % (g(x), g(y)) for x, y in vias
        ]
        additions.extend(
            '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
            % (g(a[0]), g(a[1]), g(end[0]), g(end[1]), g(WIDTH), layer)
            for a, end, layer in segments)
        match = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), updated)
        updated = updated[:match.end()] + "".join(additions) + updated[match.end():]
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    print("wrote %d negotiated route(s)" % len(routes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
