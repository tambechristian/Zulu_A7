# -*- coding: utf-8 -*-
"""Rip and coordinately reroute split two-terminal signal nets.

Uniquely-named copy of reroute_split.py made for the signal-phase working
copy (zulu_a7.signal-phase.brd) so the shared original stays untouched.
Fixes one bug in the shared tool: PF.route_group() returns `missed` as a
list, not a set, so `missed.update(unavailable)` raised AttributeError.
"""

import collections
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


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.environ.get("REROUTE_BOARD", os.path.join(ROOT, "zulu_a7.brd"))
APPLY = "--apply" in sys.argv
LAYERS = tuple(q.strip() for q in os.environ.get(
    "REROUTE_LAYERS", "1,3,4,6,7,16").split(",") if q.strip())
WIDTH = float(os.environ.get("REROUTE_WIDTH", "0.0762"))
VIA_DRILL = float(os.environ.get("REROUTE_VIA_DRILL", "0.2"))
VIA_LAND = float(os.environ.get("REROUTE_VIA_LAND", "0.3"))
EXCLUDE = frozenset(("GND", "VCC3V3"))


def attr(attrs, name):
    match = re.search(r'\b%s="([^"]+)"' % name, attrs)
    return match.group(1) if match else None


def trim_split_copper(board, nets, padmap, radius):
    def strip_signal(match):
        name, attrs, body = match.group(1), match.group(2), match.group(3)
        if name not in nets:
            return match.group(0)
        pads = padmap[name]
        kept_ends = []

        def keep_wire(wire):
            attrs2 = wire.group(1)
            layer = attr(attrs2, "layer")
            if layer not in ("1", "3", "4", "6", "7", "16"):
                return wire.group(0)
            first = (float(attr(attrs2, "x1")), float(attr(attrs2, "y1")))
            second = (float(attr(attrs2, "x2")), float(attr(attrs2, "y2")))
            keep = any(
                min(math.hypot(first[0] - px, first[1] - py),
                    math.hypot(second[0] - px, second[1] - py)) <= radius
                for px, py, _side in pads)
            if keep:
                kept_ends.extend((first, second))
                return wire.group(0)
            return ""

        body = re.sub(r"<wire\s+([^>]*)/>", keep_wire, body)

        def keep_via(via):
            attrs2 = via.group(1)
            point = (float(attr(attrs2, "x")), float(attr(attrs2, "y")))
            keep = (any(math.hypot(point[0] - px, point[1] - py) <= radius
                        for px, py, _side in pads)
                    or any(math.hypot(point[0] - x, point[1] - y) <= 0.01
                           for x, y in kept_ends))
            return via.group(0) if keep else ""

        body = re.sub(
            r"<via\s+([^>]*)(?:/>|>.*?</via>)", keep_via, body, flags=re.S)
        return '<signal name="%s"%s>%s</signal>' % (name, attrs, body)

    return re.sub(
        r'<signal name="([^"]+)"([^>]*)>(.*?)</signal>',
        strip_signal, board, flags=re.S)


def strip_all_copper(board, nets):
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


def pad_layers(side):
    return set(LAYERS) if side == 0 else {str(side)}


def component_anchors(objects, terminal, union):
    root = union.find(terminal)
    out = []
    for index, obj in enumerate(objects):
        if union.find(index) != root:
            continue
        if obj["kind"] in ("pad", "via"):
            out.append((obj["at"], {str(layer) for layer in obj["layers"]
                                    if str(layer) in LAYERS}))
        elif obj["kind"] == "wire":
            layers = {str(layer) for layer in obj["layers"]
                      if str(layer) in LAYERS}
            out.extend(((obj["a"], layers), (obj["b"], layers)))
    return [(point, layers) for point, layers in out if layers]


def g(value):
    text = ("%.4f" % value).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    terminal_pair_text = os.environ.get("REROUTE_TERMINALS", "")
    terminal_pair = (
        tuple(int(value) for value in terminal_pair_text.split(","))
        if terminal_pair_text else None)
    if terminal_pair is not None and len(terminal_pair) != 2:
        raise ValueError("REROUTE_TERMINALS must contain two terminal indices")
    all_nets = sorted(
        net for net, (objects, terminals, planes) in parsed.items()
        if net not in EXCLUDE
        and (terminals == 2 or (
            terminal_pair is not None and max(terminal_pair) < terminals))
        and len(C.components(objects, terminals, planes)) > 1)
    nets = list(all_nets)
    selected = {item.strip() for item in
                os.environ.get("REROUTE_NETS", "").split(",") if item.strip()}
    if selected:
        nets = [net for net in nets if net in selected]
    if not nets:
        print("no split two-terminal nets")
        return 0

    strip_nets = (set(all_nets) if
                  os.environ.get("REROUTE_STRIP_ALL", "0") == "1"
                  else set(nets))
    padmap = dict((net, P.pads_of(board, net, skip=())) for net in strip_nets)
    trim_radius = float(os.environ.get("REROUTE_TRIM_RADIUS", "1.5"))
    if os.environ.get("REROUTE_FULL_STRIP_OTHERS", "0") == "1":
        board = strip_all_copper(board, strip_nets - set(nets))
        strip_nets = set(nets)
    clean = trim_split_copper(board, strip_nets, padmap, trim_radius)
    clean_parsed = C.parse_signal_objects(clean)
    outline = re.findall(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
        r'y2="([-\d.]+)"[^>]*layer="20"', clean)
    xs = [float(value) for row in outline for value in (row[0], row[2])]
    ys = [float(value) for row in outline for value in (row[1], row[3])]
    bounds = (min(xs), min(ys), max(xs), max(ys))
    clearance = G.rule_mm(clean, "mdWireWire") + 0.005

    terms, own, slay, dlay = {}, {}, {}, {}
    copper = collections.defaultdict(list)
    for net, x, y, hx, hy, side in E.board_copper(clean, skip=()):
        if net in nets:
            copper[net].append((x, y, hx, hy, side))
    for net in nets:
        pads = P.pads_of(clean, net, skip=())
        if len(pads) < 2:
            continue
        objects, terminals, planes = clean_parsed[net]
        union = C.connectivity_union(objects, planes)
        first_terminal, second_terminal = terminal_pair or (0, 1)
        first = component_anchors(objects, first_terminal, union)
        second = component_anchors(objects, second_terminal, union)
        if not first or not second:
            continue
        (sp, slayers), (dp, dlayers) = min(
            ((a, b) for a in first for b in second),
            key=lambda pair: math.hypot(
                pair[0][0][0] - pair[1][0][0],
                pair[0][0][1] - pair[1][0][1]))
        terms[net] = (sp, dp)
        slay[net] = slayers
        dlay[net] = dlayers
        own_copper = G.as_circles([
            (x, y, hx, hy, 0.0) for x, y, hx, hy, _side in copper[net]])
        signal = re.search(
            r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net),
            clean, re.S).group(1)
        own_copper.extend(
            (x, y, diameter / 2.0) for x, y, diameter in G.vias(signal))
        for wire in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
                r'y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"', signal):
            first = (float(wire.group(1)), float(wire.group(2)))
            second = (float(wire.group(3)), float(wire.group(4)))
            own_copper.extend(
                G.sample(first, second, float(wire.group(5)) / 2.0))
        own[net] = own_copper

    unavailable = sorted(set(nets) - set(terms))
    nets = [net for net in nets if net in terms]
    maxit = int(os.environ.get("REROUTE_MAXIT", "40"))
    got, missed = PF.route_group(
        clean, nets, terms, own, bounds, clearance, WIDTH, LAYERS,
        maxit=maxit, box_mm=1e9, slay=slay, dlay=dlay)
    missed = set(missed)
    missed.update(unavailable)
    print("routed %d/%d split two-terminal nets; missed %d" %
          (len(got), len(nets), len(missed)))
    print("   routed: %s" % (", ".join(sorted(got)) or "-"))
    print("   missed: %s" % (", ".join(sorted(missed)) or "-"))

    out = clean
    for net, (vias, segments) in got.items():
        additions = []
        endpoints = terms[net]
        vias = [
            point for point in vias
            if all(math.hypot(point[0] - endpoint[0],
                              point[1] - endpoint[1]) > 0.31
                   for endpoint in endpoints)]
        for x, y in sorted(set((round(x, 4), round(y, 4)) for x, y in vias)):
            additions.append(
                '<via x="%s" y="%s" extent="1-16" drill="%s" '
                'diameter="%s"/>' % (
                    g(x), g(y), g(VIA_DRILL), g(VIA_LAND)))
        for first, second, layer in segments:
            if math.hypot(second[0] - first[0], second[1] - first[1]) < 1e-9:
                continue
            additions.append(
                '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" '
                'layer="%s"/>' % (
                    g(first[0]), g(first[1]), g(second[0]), g(second[1]),
                    g(WIDTH), layer))
        for endpoint, allowed_layers in zip(
                endpoints, (slay[net], dlay[net])):
            candidates = [
                (math.hypot(point[0] - endpoint[0],
                            point[1] - endpoint[1]), point, layer)
                for first, second, layer in segments
                if str(layer) in allowed_layers
                for point in (first, second)]
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
    after = C.parse_signal_objects(out)
    if terminal_pair is None:
        incomplete = [
            net for net in got
            if len(C.components(*after[net])) > 1]
    else:
        incomplete = []
        for net in got:
            objects, _terminals, planes = after[net]
            union = C.connectivity_union(objects, planes)
            if union.find(terminal_pair[0]) != union.find(terminal_pair[1]):
                incomplete.append(net)
    if incomplete:
        print("connectivity verification failed: %s" % ", ".join(incomplete))
        return 1
    if not APPLY:
        print("report only -- re-run with --apply to replace split-net copper")
        return 0
    if missed:
        print("refusing partial apply: %d selected net(s) were not routed" %
              len(missed))
        return 1
    io.open(BRD, "w", encoding="utf-8", newline="").write(out)
    print("wrote coordinated routes to %s" % BRD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
