# -*- coding: utf-8 -*-
"""Rip up a coordinated GROUP of nets (targets + their blocking obstructions,
whether currently split or already fully connected) and negotiate a fresh set
of routes for the whole group together via the shared PathFinder engine.

Uniquely-named helper for the "negotiated-congestion rip-up" phase. Does not
modify any of the existing shared tools (reroute_split.py,
reroute_split_signalphase.py, reroute_split_sdram_phase.py, pathfinder.py,
geom.py, power.py, check_connectivity.py, escape.py) -- it only imports them.

Key difference from reroute_split_sdram_phase.py: that tool only considers
nets that are CURRENTLY SPLIT (components > 1), so it can never touch a
fully-routed net purely because its existing trace happens to block a
different net's escape. This tool accepts ANY explicitly-named 2-pad net --
split or fully connected -- strips ALL of its existing copper (vias + signal
layer wires), and hands the whole set to pathfinder.route_group so every
member may negotiate space with every other member (allowed to share cells
during the search, penalised more each iteration, until no cell is shared).

SAFETY: nothing is written to disk unless every single net in the group came
back legally routed (0 missed). A partially-successful negotiation is
reported but NOT applied, because a previously-connected net whose copper we
already stripped would otherwise end up newly split -- exactly the
"worsened net" this task forbids.

Usage (PowerShell):
  $env:REROUTE_BOARD = "<candidate .brd path>"
  $env:REROUTE_NETS  = "A5,BS0,CAS#,PROG#,LDQM,CHAN11"
  python tools\reroute_negotiated_group.py [--apply]
"""

import io
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C
import escape as E
import geom as G
import pathfinder as PF
import power as P


APPLY = "--apply" in sys.argv
BRD = os.environ.get("REROUTE_BOARD", "")
if not BRD:
    raise SystemExit("REROUTE_BOARD env var is required (candidate path) -- "
                      "refusing to default to root zulu_a7.brd")
LAYERS = tuple(q.strip() for q in os.environ.get(
    "REROUTE_LAYERS", "1,3,4,6,7,16").split(",") if q.strip())
WIDTH = float(os.environ.get("REROUTE_WIDTH", "0.0762"))
VIA_DRILL = float(os.environ.get("REROUTE_VIA_DRILL", "0.2"))
VIA_LAND = float(os.environ.get("REROUTE_VIA_LAND", "0.3"))
EXCLUDE = frozenset(("GND", "VCC3V3"))


def g(value):
    text = ("%.4f" % value).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def strip_all_copper(board, nets):
    """remove every via and every signal-layer wire belonging to `nets`,
    leaving only the pads (and any plane/L2/L5 copper, untouched since those
    layers are not matched by the wire regex below)."""
    def strip_signal(match):
        name, attrs, body = match.group(1), match.group(2), match.group(3)
        if name not in nets:
            return match.group(0)
        body = re.sub(r"<via\b[^>]*(?:/>|>.*?</via>)", "", body, flags=re.S)
        body = re.sub(
            r'<wire\b[^>]*\blayer="(?:1|3|4|6|7|16|19)"[^>]*/>', "", body)
        return '<signal name="%s"%s>%s</signal>' % (name, attrs, body)

    return re.sub(
        r'<signal name="([^"]+)"([^>]*)>(.*?)</signal>',
        strip_signal, board, flags=re.S)


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    requested = [q.strip() for q in
                 os.environ.get("REROUTE_NETS", "").split(",") if q.strip()]
    nets = [n for n in requested if n not in EXCLUDE]
    if not nets:
        print("no nets requested (set REROUTE_NETS)")
        return 1
    bad = [n for n in nets if n in EXCLUDE]
    if bad:
        print("refusing to touch preserved net(s): %s" % ", ".join(bad))
        return 1

    before_parsed = C.parse_signal_objects(board)
    before_state = {}
    for net in nets:
        if net not in before_parsed:
            print("net not found on board: %s" % net)
            return 1
        objects, terminals, planes = before_parsed[net]
        comps = C.components(objects, terminals, planes)
        before_state[net] = len(comps) == 1  # True == currently fully connected

    clean = strip_all_copper(board, set(nets))

    bounds_override = os.environ.get("REROUTE_BOUNDS", "")
    if bounds_override:
        bounds = tuple(float(v) for v in bounds_override.split(","))
        if len(bounds) != 4:
            raise SystemExit("REROUTE_BOUNDS must be 'xmin,ymin,xmax,ymax'")
    else:
        outline = re.findall(
            r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
            r'y2="([-\d.]+)"[^>]*layer="20"', clean)
        xs = [float(value) for row in outline for value in (row[0], row[2])]
        ys = [float(value) for row in outline for value in (row[1], row[3])]
        bounds = (min(xs), min(ys), max(xs), max(ys))
    clearance = G.rule_mm(clean, "mdWireWire") + 0.005

    terms, own, slay, dlay = {}, {}, {}, {}
    skipped = []
    for net in nets:
        copper = [(x, y, hx, hy, side) for onet, x, y, hx, hy, side in
                  E.board_copper(clean, skip=()) if onet == net]
        if len(copper) != 2:
            print("skipping %s: needs exactly 2 pads (found %d)" %
                  (net, len(copper)))
            skipped.append(net)
            continue
        (x0, y0, hx0, hy0, s0), (x1, y1, hx1, hy1, s1) = copper
        terms[net] = ((x0, y0), (x1, y1))
        slay[net] = tuple(LAYERS) if s0 == 0 else (
            str(16 if s0 == 16 else 1),)
        dlay[net] = tuple(LAYERS) if s1 == 0 else (
            str(16 if s1 == 16 else 1),)
        own[net] = G.as_circles([(x0, y0, hx0, hy0, 0.0),
                                  (x1, y1, hx1, hy1, 0.0)])

    nets = [n for n in nets if n in terms]
    if not nets:
        print("nothing left to route")
        return 1

    maxit = int(os.environ.get("REROUTE_MAXIT", "60"))
    box_mm = float(os.environ.get("REROUTE_BOX_MM", "6.0"))
    print("negotiating %d net(s): %s" % (len(nets), ", ".join(nets)))

    logpath = os.environ.get("REROUTE_LOG", "")
    if logpath:
        logfile = io.open(logpath, "w", encoding="utf-8", newline="")

        def log(msg):
            print(msg)
            logfile.write(msg + "\n")
            logfile.flush()
    else:
        log = print

    got, missed = PF.route_group(
        clean, nets, terms, own, bounds, clearance, WIDTH, LAYERS,
        maxit=maxit, box_mm=box_mm, slay=slay, dlay=dlay, log=log)
    missed = set(missed) | set(skipped)
    print("routed %d/%d; missed %d" % (len(got), len(requested), len(missed)))
    print("   routed: %s" % (", ".join(sorted(got)) or "-"))
    print("   missed: %s" % (", ".join(sorted(missed)) or "-"))

    if missed:
        print("REFUSING to apply: %d net(s) did not come back legally "
              "routed, and their old copper was already stripped in this "
              "in-memory draft only -- disk is untouched." % len(missed))
        return 1

    out = clean
    for net, (vias, segments) in got.items():
        additions = []
        endpoints = terms[net]
        vias_u = sorted(set((round(x, 4), round(y, 4)) for x, y in vias))
        for x, y in vias_u:
            additions.append(
                '<via x="%s" y="%s" extent="1-16" drill="%s" '
                'diameter="%s"/>' % (g(x), g(y), g(VIA_DRILL), g(VIA_LAND)))
        for first, second, layer in segments:
            if math.hypot(second[0] - first[0], second[1] - first[1]) < 1e-9:
                continue
            additions.append(
                '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" '
                'layer="%s"/>' % (
                    g(first[0]), g(first[1]), g(second[0]), g(second[1]),
                    g(WIDTH), layer))
        for endpoint, allowed_layers in zip(endpoints, (slay[net], dlay[net])):
            candidates = [
                (math.hypot(point[0] - endpoint[0], point[1] - endpoint[1]),
                 point, layer)
                for first, second, layer in segments
                if str(layer) in allowed_layers
                for point in (first, second)
            ] + [
                (math.hypot(vx - endpoint[0], vy - endpoint[1]),
                 (vx, vy), sorted(allowed_layers)[0])
                for vx, vy in vias
            ]
            if not candidates:
                continue
            distance, point, layer = min(candidates)
            if distance > 1e-9:
                additions.append(
                    '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" '
                    'layer="%s"/>' % (
                        g(endpoint[0]), g(endpoint[1]), g(point[0]),
                        g(point[1]), g(WIDTH), layer))
        match = re.search(r'<signal name="%s"[^>]*>' % re.escape(net), out)
        out = out[:match.end()] + "".join(additions) + out[match.end():]

    ET.fromstring(out)
    after_parsed = C.parse_signal_objects(out)
    worsened = []
    for net in nets:
        objects, terminals, planes = after_parsed[net]
        comps = C.components(objects, terminals, planes)
        now_connected = len(comps) == 1
        if before_state[net] and not now_connected:
            worsened.append(net)
    if worsened:
        print("connectivity WORSENED for: %s -- refusing to apply" %
              ", ".join(worsened))
        return 1

    print("all %d net(s) verified: fully connected, none worsened" % len(nets))
    if not APPLY:
        print("report only -- re-run with --apply to write %s" % BRD)
        return 0
    io.open(BRD, "w", encoding="utf-8", newline="").write(out)
    print("wrote negotiated group route to %s" % BRD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
