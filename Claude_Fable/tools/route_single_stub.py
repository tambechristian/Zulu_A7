# -*- coding: utf-8 -*-
"""Add ONE new routed stub between two EXISTING points already belonging to
the same net (e.g. bridging a nearby via-to-via gap, or escaping a single
still-bare pad to the nearest already-connected via/pad) -- WITHOUT stripping
or touching any of that net's other, already-good copper.

Uniquely-named helper for the "close a near-miss gap" / "route a single
missing last-mile stub" pattern discovered during the passive-relocation
investigation phase (some nets reported "split" by check_connectivity are not
deeply un-routable -- they are two islands of otherwise-good copper sitting a
few mm apart, or one bare pad a modest distance from the rest of the net).
Does not modify any existing shared tool -- it only imports pathfinder.py,
geom.py, escape.py and check_connectivity.py.

Usage (PowerShell):
  $env:STUB_BOARD = "<candidate .brd path>"
  $env:STUB_NET   = "RST#"
  $env:STUB_SRC   = "43.5864,23.5839"
  $env:STUB_DST   = "42.7101,24.765"
  python tools\\route_single_stub.py [--apply]

STUB_SRC_LAYERS / STUB_DST_LAYERS restrict which layer(s) the router may
enter/leave that terminal on (comma list of layer numbers). Default is the
full signal-layer set (1,3,4,6,7,16); pass a single layer if the terminal is
a one-sided SMD pad rather than a through via.
"""

import io
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C
import geom as G
import pathfinder as PF


APPLY = "--apply" in sys.argv
BRD = os.environ.get("STUB_BOARD", "")
if not BRD:
    raise SystemExit("STUB_BOARD env var is required (candidate path) -- "
                      "refusing to default to root zulu_a7.brd")
NET = os.environ.get("STUB_NET", "")
if not NET:
    raise SystemExit("STUB_NET env var is required")
LAYERS = tuple(q.strip() for q in os.environ.get(
    "STUB_LAYERS", "1,3,4,6,7,16").split(",") if q.strip())
WIDTH = float(os.environ.get("STUB_WIDTH", "0.0762"))


def g(value):
    text = ("%.4f" % value).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def parse_point(text):
    x, y = (float(v) for v in text.split(","))
    return (x, y)


def parse_layers(text, default):
    if not text:
        return default
    return tuple(q.strip() for q in text.split(",") if q.strip())


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    src = parse_point(os.environ["STUB_SRC"])
    dst = parse_point(os.environ["STUB_DST"])
    slay = parse_layers(os.environ.get("STUB_SRC_LAYERS", ""), LAYERS)
    dlay = parse_layers(os.environ.get("STUB_DST_LAYERS", ""), LAYERS)

    before_parsed = C.parse_signal_objects(board)
    if NET not in before_parsed:
        print("net not found on board: %s" % NET)
        return 1
    objects, terminals, planes = before_parsed[NET]
    before_comps = C.components(objects, terminals, planes)
    before_n = len(before_comps)
    print("before: %s has %d component(s) across %d object(s)" %
          (NET, before_n, len(objects)))

    outline = re.findall(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
        r'y2="([-\d.]+)"[^>]*layer="20"', board)
    xs = [float(value) for row in outline for value in (row[0], row[2])]
    ys = [float(value) for row in outline for value in (row[1], row[3])]
    bounds = (min(xs), min(ys), max(xs), max(ys))
    clearance = G.rule_mm(board, "mdWireWire") + 0.005

    terms = {NET: (src, dst)}
    own = {NET: G.as_circles([
        (src[0], src[1], 0.16, 0.16, 0.0),
        (dst[0], dst[1], 0.16, 0.16, 0.0),
    ])}
    slays = {NET: slay}
    dlays = {NET: dlay}

    maxit = int(os.environ.get("STUB_MAXIT", "8"))
    box_mm = float(os.environ.get("STUB_BOX_MM", "6.0"))
    print("routing single stub for %s: %s (layers %s) -> %s (layers %s)" %
          (NET, src, ",".join(slay), dst, ",".join(dlay)))

    got, missed = PF.route_group(
        board, [NET], terms, own, bounds, clearance, WIDTH, LAYERS,
        maxit=maxit, box_mm=box_mm, slay=slays, dlay=dlays, log=print)

    if missed or NET not in got:
        print("FAILED to find a legal stub route for %s -- board untouched" %
              NET)
        return 1

    vias, segments = got[NET]
    additions = []
    vias_u = sorted(set((round(x, 4), round(y, 4)) for x, y in vias))
    for x, y in vias_u:
        additions.append(
            '<via x="%s" y="%s" extent="1-16" drill="0.2" '
            'diameter="0.3"/>' % (g(x), g(y)))
    for first, second, layer in segments:
        if math.hypot(second[0] - first[0], second[1] - first[1]) < 1e-9:
            continue
        additions.append(
            '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" '
            'layer="%s"/>' % (
                g(first[0]), g(first[1]), g(second[0]), g(second[1]),
                g(WIDTH), layer))
    # stitch the found path onto the exact requested terminals if the router
    # landed on a slightly different point on the SAME net's own copper
    for endpoint, allowed_layers in ((src, slay), (dst, dlay)):
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

    match = re.search(r'<signal name="%s"[^>]*>' % re.escape(NET), board)
    out = board[:match.end()] + "".join(additions) + board[match.end():]

    ET.fromstring(out)
    after_parsed = C.parse_signal_objects(out)
    objects2, terminals2, planes2 = after_parsed[NET]
    after_comps = C.components(objects2, terminals2, planes2)
    after_n = len(after_comps)
    print("after: %s has %d component(s) across %d object(s)" %
          (NET, after_n, len(objects2)))
    if after_n > before_n:
        print("connectivity WORSENED (more components) -- refusing to apply")
        return 1

    print("stub added: %d via(s), %d wire segment(s)" %
          (len(vias_u), len(additions) - len(vias_u)))
    if not APPLY:
        print("report only -- re-run with --apply to write %s" % BRD)
        return 0
    io.open(BRD, "w", encoding="utf-8", newline="").write(out)
    print("wrote stub route to %s" % BRD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
