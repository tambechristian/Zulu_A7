# -*- coding: utf-8 -*-
"""Connectivity the way Fusion computes it, so the airwire count we predict is
the one Ratsnest will draw.

    python tools/fusion_model.py board.brd [--airwires airwires.txt] [--net NAME]

WHY. Fusion (like EAGLE) joins copper at END POINTS, not by overlap: two wires
of a signal are one piece only where an end of one lies on an end of the
other; a wire reaches a via only when it ends on the via's centre; and every
piece counts, so a leftover via or a floating stub earns an airwire of its
own. check_connectivity.py's overlap model said 46 airwires on the same board
Fusion counted 60 (2026-09-05, read back with tools/airwires.ulp); after
fusion_connect.py the totals agreed but the nets did not. This module is the
model that has to agree net by net.

RULES (per signal)
  wire-wire   same layer, shared end point (within EPS)
  wire-via    via spans the wire's layer, wire ends on the via centre
  wire-pad    pad has copper on the wire's layer, wire END lies inside the pad
  via-pad     via centre inside the pad, on a layer the pad has
  via-via     same centre, overlapping layer spans
  pad-pad     overlapping pads (check_connectivity.pad_pad)
  plane       an inner pour joins the through objects its main piece reaches
              (plane_islands raster, as in check_connectivity)

With --airwires it reads Fusion's own list and prints, per net, predicted vs
Fusion's count, so a wrong rule shows up as a named disagreement.
"""

import collections
import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402

EPS = 0.0025


def same(a, b):
    return abs(a[0] - b[0]) <= EPS and abs(a[1] - b[1]) <= EPS


def inside_pad(pad, pt):
    return (abs(pt[0] - pad["at"][0]) <= pad["hx"] + EPS
            and abs(pt[1] - pad["at"][1]) <= pad["hy"] + EPS)


def fusion_union(objects, planes):
    """The rules now live in check_connectivity.touches, so every tool that
    counts pieces counts them the way Fusion does."""
    return C.connectivity_union(objects, planes)


def pieces(objects, planes):
    """List of components; each a list of object indices."""
    union = fusion_union(objects, planes)
    groups = collections.defaultdict(list)
    for i in range(len(objects)):
        groups[union.find(i)].append(i)
    return list(groups.values())


def describe(objects, group, terminals):
    pads = [objects[i] for i in group if i < terminals]
    if pads:
        p = pads[0]
        return "pad(%.3f,%.3f)%s" % (p["at"][0], p["at"][1], "+%d" % (len(group) - 1) if len(group) > 1 else "")
    o = objects[group[0]]
    if o["kind"] == "via":
        return "via(%.3f,%.3f) L%d-%d n=%d" % (o["at"][0], o["at"][1], min(o["layers"]), max(o["layers"]), len(group))
    return "wire(%.3f,%.3f) L%d n=%d" % (o["a"][0], o["a"][1], min(o["layers"]), len(group))


def analyse(board_text):
    """{net: (objects, terminals, groups)} for nets with 2+ pads."""
    out = {}
    for net, (objects, terminals, planes) in C.parse_signal_objects(board_text).items():
        if terminals < 2:
            continue
        out[net] = (objects, terminals, pieces(objects, planes))
    return out


def read_fusion(path):
    counts = collections.Counter()
    for line in io.open(path, encoding="utf-8", errors="replace"):
        parts = line.split()
        if len(parts) == 5 and parts[0] != "TOTAL":
            counts[parts[0]] += 1
    return counts


def main():
    args = [a for a in sys.argv[1:]]
    fusion = None
    only = None
    if "--airwires" in args:
        i = args.index("--airwires")
        fusion = read_fusion(args[i + 1])
        del args[i:i + 2]
    if "--net" in args:
        i = args.index("--net")
        only = args[i + 1]
        del args[i:i + 2]
    board = io.open(args[0], encoding="utf-8", errors="replace").read()
    total = 0
    rows = []
    for net, (objects, terminals, groups) in sorted(analyse(board).items()):
        if only and net != only:
            continue
        predicted = len(groups) - 1
        total += predicted
        f = fusion.get(net, 0) if fusion is not None else None
        if predicted or f:
            rows.append((net, predicted, f, [describe(objects, g, terminals) for g in groups]))
    for net, predicted, f, descr in rows:
        flag = "" if f is None or f == predicted else "   <-- Fusion %d" % f
        print("%-14s %2d piece(s) -> %d airwire(s)%s" % (net, predicted + 1, predicted, flag))
        if only or (f is not None and f != predicted):
            for d in descr:
                print("      " + d)
    print("PREDICTED TOTAL %d" % total)
    if fusion is not None:
        print("FUSION TOTAL    %d" % sum(fusion.values()))
        missing = sorted(set(fusion) - set(r[0] for r in rows))
        if missing:
            print("nets Fusion lists that the model does not: %s" % ", ".join(missing))


if __name__ == "__main__":
    main()
