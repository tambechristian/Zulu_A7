# -*- coding: utf-8 -*-
"""Write the notes and via-in-pad CSV, then build and validate the PROVISIONAL
Asar A7 Feather PCBWay fabrication ZIP.

    python tools/package_fabrication_release.py

Adapted from Zulu_A7_Fab_B/tools/package_fabrication_release.py.  The expected
drill counts below are the Altium export of 2026-11-11 09:13:43
(asar_feather.DRR / .LDP); every other figure in the notes is measured from the
PcbDoc, the drill files and the mask Gerbers by tools/fab_facts.py at run time.
The script never regenerates CAM outputs and never touches Altium; it fails if
any input is missing, empty, older than the PcbDoc, or does not match.

The release is PROVISIONAL until PCBWay answers docs/pcbway_vip_enquiry.md.
"""

import argparse
import csv
import hashlib
import io
import math
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fab_facts  # noqa: E402

ROOT = os.path.dirname(HERE)
PROJECT = os.path.join(ROOT, "Asar_feather.PrjPcb")
OUTPUTS = os.path.join(PROJECT, "Project Outputs for asar_feather")
FABRICATION = os.path.join(ROOT, "fabrication")
PCB = os.path.join(PROJECT, "asar_feather.PcbDoc")
DRC = os.path.join(OUTPUTS, "Design Rule Check - asar_feather.drc")
DEFAULT_NOTE = os.path.join(FABRICATION, "Asar_Feather_PCBWay_FAB_NOTES.txt")
DEFAULT_CSV = os.path.join(FABRICATION, "Asar_Feather_VIA_IN_PAD.csv")
DEFAULT_ARCHIVE = os.path.join(FABRICATION, "Asar_Feather_PCBWay_Fabrication_2026-11-11_PROVISIONAL.zip")
EXPECTED_PCB_SHA256 = "4A9A971430CF72848D477669B824418F1333AD07DC8490B8F9253F96095BBA1D"
EXPECTED_PCB_MD5 = "d22906e17ffc2d908914f34efcd5acd0"
REVISION = "Asar A7 Feather"
RELEASE_DATE = "2026-11-11"
FORBIDDEN = "W1150632AS3P6"
BASE = "asar_feather"
OUTLINE = (0.0, 0.0, 50.80, 22.86)  # GM profile, mm
CORNER_R = 2.54
GERBER_EXTENSIONS = ["GTL", "G1", "G2", "G3", "G4", "GBL", "GTS", "GBS", "GTO", "GBO", "GTP", "GBP", "GM"]
# file suffix -> {tool: (diameter mm, hits)}, from asar_feather.DRR 2026-11-11 09:13:43
EXPECTED_DRILLS = {
    "RoundHoles-Plated.TXT": {"03": (0.20, 160), "05": (1.00, 28)},
    "RoundHoles-NonPlated.TXT": {"06": (0.65, 2), "07": (2.50, 4)},
    "SlotHoles-Plated.TXT": {"04": (0.60, 4)},
    "RoundHoles-Plated.TX3": {"02": (0.15, 249)},
    "RoundHoles-Plated.TX6": {"01": (0.10, 173), "02": (0.15, 214)},
    "RoundHoles-Plated.TX7": {"01": (0.10, 105), "02": (0.15, 178)},
    "RoundHoles-Plated.TX9": {"01": (0.10, 47), "02": (0.15, 196)},
    "RoundHoles-Plated.TX10": {"01": (0.10, 23), "02": (0.15, 240)},
}
FILE_TYPE = {"RoundHoles-NonPlated.TXT": "NON_PLATED"}
MICROVIA_FILES = ("RoundHoles-Plated.TX6", "RoundHoles-Plated.TX7", "RoundHoles-Plated.TX9", "RoundHoles-Plated.TX10")
EXPECTED_MICROVIA_TOTAL = 1176
EXPECTED_LAYER_MAP = {
    "RoundHoles-Plated.TXT": "gtl,g1,g2,g3,g4,gbl",
    "SlotHoles-Plated.TXT": "gtl,g1,g2,g3,g4,gbl",
    "RoundHoles-NonPlated.TXT": "gtl,g1,g2,g3,g4,gbl",
    "RoundHoles-Plated.TX3": "g2,g3",
    "RoundHoles-Plated.TX6": "gtl,g1",
    "RoundHoles-Plated.TX7": "g1,g2",
    "RoundHoles-Plated.TX9": "g3,g4",
    "RoundHoles-Plated.TX10": "g4,gbl",
}
DRILL_ORDER = ["RoundHoles-Plated.TXT", "RoundHoles-NonPlated.TXT", "SlotHoles-Plated.TXT",
               "RoundHoles-Plated.TX3", "RoundHoles-Plated.TX6", "RoundHoles-Plated.TX7",
               "RoundHoles-Plated.TX9", "RoundHoles-Plated.TX10"]
EXPECTED_ENTRIES = 13 + 8 + 2 + 2  # Gerbers, drills, LDP + DRR, notes + CSV


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def md5(path):
    with open(path, "rb") as handle:
        return hashlib.md5(handle.read()).hexdigest()


def out(name):
    return os.path.join(OUTPUTS, name)


def drill_name(suffix):
    return "%s-%s" % (BASE, suffix)


# ---- validation of the CAM files ---------------------------------------------
def read_excellon(path, kind):
    with open(path, encoding="ascii") as handle:
        lines = [line.strip() for line in handle]
    for header in (";FILE_FORMAT=4:4", "METRIC,LZ", ";TYPE=" + kind):
        if header not in lines:
            raise ValueError("%s lacks header %s" % (os.path.basename(path), header))
    tools, hits = {}, {}
    tool = None
    x = y = None
    in_header = True
    for line in lines:
        if in_header:
            m = re.fullmatch(r"T(\d{2})F\d+S\d+C(\d+\.\d+)", line)
            if m:
                tools[m.group(1)] = float(m.group(2))
            elif line == "%":
                in_header = False
            continue
        m = re.fullmatch(r"T(\d{2})", line)
        if m:
            tool = m.group(1)
            if tool not in tools:
                raise ValueError("%s selects undefined tool T%s" % (os.path.basename(path), tool))
            hits.setdefault(tool, [])
            continue
        m = re.fullmatch(r"(?:X([-+]?\d+))?(?:Y([-+]?\d+))?(?:G85(?:X([-+]?\d+))?(?:Y([-+]?\d+))?)?", line)
        if m and (m.group(1) or m.group(2)):
            if tool is None:
                raise ValueError("%s has a hit before a tool" % os.path.basename(path))
            if m.group(1):
                x = fab_facts.coord(m.group(1))
            if m.group(2):
                y = fab_facts.coord(m.group(2))
            if x is None or y is None:
                raise ValueError("%s modal coordinate unset: %s" % (os.path.basename(path), line))
            if "G85" in line:
                hits[tool].append((x, y, fab_facts.coord(m.group(3)) if m.group(3) else x,
                                   fab_facts.coord(m.group(4)) if m.group(4) else y))
            else:
                hits[tool].append((x, y))
            continue
        if line in ("G90", "G05", "M30", "") or line.startswith(";"):
            continue
        raise ValueError("%s: unexpected line %r" % (os.path.basename(path), line))
    return tools, hits


def inside_outline(x, y):
    x0, y0, x1, y1 = OUTLINE
    if not (x0 < x < x1 and y0 < y < y1):
        return False
    cx = min(max(x, x0 + CORNER_R), x1 - CORNER_R)
    cy = min(max(y, y0 + CORNER_R), y1 - CORNER_R)
    return math.hypot(x - cx, y - cy) < CORNER_R


def validate_drills():
    found = {}
    for suffix, expected in EXPECTED_DRILLS.items():
        path = out(drill_name(suffix))
        tools, hits = read_excellon(path, FILE_TYPE.get(suffix, "PLATED"))
        actual = {t: (tools[t], len(h)) for t, h in hits.items()}
        if set(actual) != set(expected) or any(abs(actual[t][0] - expected[t][0]) > 0.0015 or actual[t][1] != expected[t][1] for t in expected):
            raise ValueError("%s changed: %s != %s" % (suffix, actual, expected))
        for t, pts in hits.items():
            for p in pts:
                for x, y in ((p[0], p[1]),) + (((p[2], p[3]),) if len(p) == 4 else ()):
                    if not inside_outline(x, y):
                        raise ValueError("%s T%s hit outside the rounded outline: %s" % (suffix, t, p))
        found[suffix] = (tools, hits)
    total = sum(len(h) for s in MICROVIA_FILES for h in found[s][1].values())
    if total != EXPECTED_MICROVIA_TOTAL:
        raise ValueError("microvia total %d != %d" % (total, EXPECTED_MICROVIA_TOTAL))
    # slots: X1 shell legs, horizontal, 0.60 tool
    slots = found["SlotHoles-Plated.TXT"][1]["04"]
    for x1, y1, x2, y2 in slots:
        if abs(y1 - y2) > 1e-4:
            raise ValueError("slot is not horizontal")
        if round(abs(x2 - x1), 4) not in (0.6, 1.1):
            raise ValueError("slot route length changed: %s" % abs(x2 - x1))
    return found


def validate_drr(found):
    text = open(out(BASE + ".DRR"), encoding="ascii").read()
    sections = []
    for line in text.splitlines():
        if line.startswith(("Layer Pair :", "MicroVia :")):
            sections.append(dict(files=[], rows=[]))
            continue
        m = re.match(r"ASCII (?:Plated|Non-Plated) (?:RoundHoles|SlotHoles) File : (\S+)", line)
        if m:
            sections[-1]["files"].append(m.group(1))
            continue
        m = re.match(r"T(\d+)\s+(\d+(?:\.\d+)?)mm.*?\s(Round|Slot)\s+(\d+)\s+(PTH|NPTH)", line)
        if m:
            sections[-1]["rows"].append((m.group(1).zfill(2), float(m.group(2)), m.group(3), int(m.group(4)), m.group(5)))
    report = defaultdict(dict)
    for sec in sections:
        for tool, size, shape, count, plated in sec["rows"]:
            owners = []
            for name in sec["files"]:
                suffix = name[len(BASE) + 1:]
                tools = found[suffix][0]
                if tool in tools and abs(tools[tool] - size) < 0.0015:
                    owners.append(suffix)
            if len(owners) != 1:
                raise ValueError("DRR row T%s %.2f maps to %s" % (tool, size, owners))
            suffix = owners[0]
            if (plated == "NPTH") != (suffix in FILE_TYPE) or (shape == "Slot") != suffix.startswith("Slot"):
                raise ValueError("DRR row T%s type %s/%s does not fit %s" % (tool, shape, plated, suffix))
            report[suffix][tool] = (size, count)
    if dict(report) != EXPECTED_DRILLS:
        raise ValueError("DRR differs: %s != %s" % (dict(report), EXPECTED_DRILLS))
    m = re.search(r"MicroVia Totals\s+(\d+)", text)
    if not m or int(m.group(1)) != EXPECTED_MICROVIA_TOTAL:
        raise ValueError("DRR microvia total changed")


def validate_ldp():
    text = open(out(BASE + ".LDP"), encoding="ascii").read().lower()
    for suffix, layers in EXPECTED_LAYER_MAP.items():
        pattern = r"drillfile=%s\|drilllayers=%s(?:\r?\n|$)" % (re.escape(drill_name(suffix).lower()), re.escape(layers))
        if not re.search(pattern, text):
            raise ValueError("LDP lacks %s -> %s" % (suffix, layers))
    if text.count("drillfile=") != len(EXPECTED_LAYER_MAP):
        raise ValueError("LDP lists an unexpected drill file")


def read_outline():
    """Rounded rectangle from GM: (bbox, [(centre, radius)], line count)."""
    text = open(out(BASE + ".GM"), encoding="ascii").read()
    if "%MOMM*%" not in text or "%FSLAX44Y44*%" not in text:
        raise ValueError("GM is not metric 4.4")
    x = y = 0
    mode = "G01"
    pts, arcs, lines = [], [], 0
    for raw in text.splitlines():
        s = raw.strip()
        if s in ("G01*", "G02*", "G03*"):
            mode = s[:3]
            continue
        m = re.fullmatch(r"(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+)J(-?\d+))?D0([12])\*", s)
        if not m:
            continue
        nx = int(m.group(1)) if m.group(1) else x
        ny = int(m.group(2)) if m.group(2) else y
        if m.group(5) == "1":
            if mode == "G01":
                lines += 1
            else:
                cx, cy = x + int(m.group(3)), y + int(m.group(4))
                r0, r1 = math.hypot(x - cx, y - cy), math.hypot(nx - cx, ny - cy)
                if abs(r0 - r1) > 1:
                    raise ValueError("GM arc is not circular")
                arcs.append(((cx / 1e4, cy / 1e4), r0 / 1e4, mode))
        x, y = nx, ny
        pts.append((x / 1e4, y / 1e4))
    box = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    return box, arcs, lines


def validate_outline():
    box, arcs, lines = read_outline()
    if box != OUTLINE:
        raise ValueError("outline changed: %s != %s" % (box, OUTLINE))
    want = sorted([(CORNER_R, CORNER_R), (CORNER_R, OUTLINE[3] - CORNER_R), (OUTLINE[2] - CORNER_R, CORNER_R),
                   (OUTLINE[2] - CORNER_R, OUTLINE[3] - CORNER_R)])
    got = sorted((round(c[0], 4), round(c[1], 4)) for c, r, m in arcs)
    if got != [(round(a, 4), round(b, 4)) for a, b in want] or any(abs(r - CORNER_R) > 1e-4 for c, r, m in arcs) or lines != 4:
        raise ValueError("outline corners changed: %s, %d lines" % (arcs, lines))
    return box, arcs, lines


def read_drc():
    text = open(DRC, encoding="latin-1").read()
    date = re.search(r"Date\s*:\s*(\S+)", text).group(1)
    time = re.search(r"Time\s*:\s*([\d:]+ [AP]M)", text).group(1)
    viol = int(re.search(r"Violations Detected : (\d+)", text).group(1))
    waived = int(re.search(r"Waived Violations : (\d+)", text).group(1))
    rules = len(re.findall(r"Processing Rule :", text))
    if not re.search(r"PCB File : .*asar_feather\.PcbDoc", text):
        raise ValueError("DRC report is not for asar_feather.PcbDoc")
    html = re.sub(r"<[^>]+>", " ", open(DRC[:-4] + ".html", encoding="utf-8", errors="replace").read())
    warn = re.search(r"Warnings:\s*(\d+)", html)
    return dict(date=date, time=time, violations=viol, waived=waived, rules=rules, warnings=int(warn.group(1)) if warn else None)


# ---- notes ---------------------------------------------------------------------
def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def wrap(text, width=78, indent=""):
    words = text.split()
    lines, cur = [], indent
    for w in words:
        if len(cur) + len(w) + (0 if cur == indent else 1) > width:
            lines.append(cur)
            cur = indent + w
        else:
            cur = cur + ("" if cur == indent else " ") + w
    if cur.strip():
        lines.append(cur)
    return lines


def vtype(e):
    return "%s %.2f/%.2f" % (e["span"], e["hole"], e["land"])


def build_notes(F, drc, sha, pcb_md5, csv_name):
    L = []
    P = L.append

    def para(text, indent=""):
        L.extend(wrap(text, indent=indent))

    vg = {(g["span"], g["hole"], g["land"]): g["count"] for g in F["via_geometry"]}
    st = F["stacked"]
    vs = F["via_in_pad_summary"]
    tv = F["through_vias_in_smd_pads"]
    tvc = F["through_vias_in_smd_pads_count"]
    off = F["u1_off_centre_overlaps"]
    combos = F["u1_centred_combos"]
    nets = F["u1_centred_combo_nets"]
    l10 = F["lasers_010"]
    sp = F["min_spacing_track_to_other_copper"]
    hh = F["min_hole_to_hole"]
    hw = F["hole_wall_to_other_net_track"]
    tent = F["tenting"]
    usb = F
    box, arcs, nlines = read_outline()
    dv = F["drill_vs_board"]
    thru_sites = sorted({(e["via_x"], e["via_y"]) for e in tv})
    n_thru_vip = len(thru_sites)
    lasers_np = F["lasers_in_non_u1_smd_pads"]
    u1_lasers = F["u1_centred_lasers"]
    pos_tv = tvc["by_position"]

    P("ASAR A7 FEATHER - PCBWAY FABRICATION NOTES - *** PROVISIONAL ***")
    P("Revision: %s  (silkscreen \"ASAR A7\")" % REVISION)
    P("Release date: %s" % RELEASE_DATE)
    P("PCB SHA-256: %s" % sha)
    P("Source: asar_feather.PcbDoc (MD5 %s)" % pcb_md5)
    P("")
    P("*** PROVISIONAL RELEASE - DO NOT START PRODUCTION ***")
    para("This data set is released for quotation and CAM/engineering review only. It "
         "depends on PCBWay's answers to our engineering enquiry about 0.10 mm laser "
         "via-in-pad on the 0.5 mm-pitch BGA lands, 3/3 mil, resin-plugged through vias "
         "in SMD pads, stacking and hole spacing, which are still outstanding. Every "
         "assumption that enquiry asks about is restated in the next section with the "
         "counts of THIS board. The enquiry quoted counts of an older layout (before "
         "the LTC3556 power-block change); where they differ, the enquiry's figure is "
         "shown in brackets and the figure in these notes is the one that applies. "
         "Please answer each numbered item, or confirm it, before fabrication is "
         "released.")
    P("")
    P("ASSUMPTIONS PENDING PCBWAY CONFIRMATION (one per enquiry question)")
    P("")
    P("Q1  Laser via-in-pad in the BGA lands (U1, XC7A35T CPG236, 0.5 mm pitch).")
    para("A 0.10 mm laser via in a 0.25 mm land (0.075 mm ring) sits at the centre "
         "of %d of the %d ball lands, copper-filled and capped flat, on Top and on the "
         "inner lands L2 to L5. The U1 lands cannot grow: above about 0.27 mm a 3 mil "
         "track no longer fits between two balls. Centred vias per ball:"
         % (F["u1_lands"]["count"] - combos.get("none", 0), F["u1_lands"]["count"]), "    ")
    label = {"Top-L2": "Top-L2 only", "Top-L2 + L2-L3": "Top-L2 + L2-L3 stacked",
             "Top-L2 + L2-L3 + L3-L4": "Top-L2 + L2-L3 on a buried L3-L4 (0.15/0.27)",
             "Top-L2 + L2-L3 + L3-L4 + L4-L5": "Top-L2 + L2-L3 + buried L3-L4 + L4-L5 column"}
    for k in ("Top-L2", "Top-L2 + L2-L3", "Top-L2 + L2-L3 + L3-L4", "Top-L2 + L2-L3 + L3-L4 + L4-L5"):
        n = nets.get(k, {})
        P("      %3d balls  %-46s (%s)" % (combos.get(k, 0), label[k], ", ".join("%s %d" % (a, b) for a, b in sorted(n.items()))))
    other = {k: v for k, v in combos.items() if k not in label and k != "none"}
    for k, v in sorted(other.items()):
        P("      %3d balls  %s" % (v, k))
    P("      %3d balls  no centred via" % combos.get("none", 0))
    para("Totals in the U1 lands: %d laser vias of 0.10/0.25 (Top-L2 %d, L2-L3 %d, "
         "L4-L5 %d) and %d buried vias under them [enquiry: 258 = 149/81/28, 54]; no "
         "0.15 laser and no through via is centred on a U1 land."
         % (F["u1_centred_lasers_total"], u1_lasers.get("Top-L2 0.10/0.25", 0), u1_lasers.get("L2-L3 0.10/0.25", 0),
            u1_lasers.get("L4-L5 0.10/0.25", 0), F["u1_centred_buried"]), "    ")
    para("Off-centre: on %d of the balls without a centred via, a via overlaps the "
         "land off-centre: %s [enquiry: 9 balls, 8 lasers + 1 through via]. They are "
         "listed in %s and must be filled and capped like the centred ones."
         % (off["balls"], ", ".join("%d x %s" % (c, k) for k, c in off["by_type"].items()), csv_name), "    ")
    for s in off["list"]:
        P("      " + s)
    P("")
    P("Q2  Laser hole size.")
    para("The 0.10 mm laser holes are to be lasered at 0.10 mm (not 0.127 mm) through "
         "the 0.1016 mm 3313 (Top-L2, L5-Bottom) and 0.071 mm 1080 (L2-L3, L4-L5) "
         "prepregs: %d holes (TX6 %d, TX7 %d, TX9 %d, TX10 %d) [enquiry: 349]. If "
         "PCBWay must use 0.127 mm, the 0.25 mm land leaves a 0.0615 mm ring - please "
         "say whether that is acceptable or propose a thinner outer prepreg."
         % (l10["total"], vg.get(("Top-L2", 0.1, 0.25), 0), vg.get(("L2-L3", 0.1, 0.25), 0),
            vg.get(("L4-L5", 0.1, 0.25), 0), vg.get(("L5-Bot", 0.1, 0.25), 0)), "    ")
    para("%d of them are centred in U1 lands (Q1); the other %d are not on a ball "
         "(Top-L2 %d, L2-L3 %d, L4-L5 %d, L5-Bottom %d), %d of those inside the U1 land "
         "field, where a 0.30 mm land does not fit [enquiry: 91, 43 under the FPGA]. "
         "All other %d laser vias are 0.15/0.30 [enquiry: 764]."
         % (l10["centred_on_u1_ball"], l10["not_on_ball"], l10["not_on_ball_by_span"].get("Top-L2", 0),
            l10["not_on_ball_by_span"].get("L2-L3", 0), l10["not_on_ball_by_span"].get("L4-L5", 0),
            l10["not_on_ball_by_span"].get("L5-Bot", 0), l10["not_on_ball_under_u1"], F["lasers_015"]), "    ")
    P("")
    P("Q3  Stacking, with no mechanical L2-L5 drill.")
    para("All stacks are separate drills at one XY, on filled and capped vias, as "
         "drawn. There is no L2-L5 drill in the data; do not merge stacks into one. "
         "Counts of coincident sites:", "    ")
    P("      (a) Top-L2 on L2-L3 laser:                %4d  (0.10/0.10 %d, 0.15/0.15 %d)"
      % (st["top_l2_on_l2_l3"], st["top_l2_on_l2_l3_by_holes"].get("0.1/0.1", 0), st["top_l2_on_l2_l3_by_holes"].get("0.15/0.15", 0)))
    P("      (b) L2-L3 laser on a buried L3-L4 via:    %4d  (0.10 laser %d, 0.15 laser %d)"
      % (st["l2_l3_on_buried"], st["l2_l3_on_buried_by_laser_hole"].get("0.1", 0), st["l2_l3_on_buried_by_laser_hole"].get("0.15", 0)))
    P("          L4-L5 laser on a buried L3-L4 via:    %4d  (0.10 laser %d, 0.15 laser %d)"
      % (st["l4_l5_on_buried"], st["l4_l5_on_buried_by_laser_hole"].get("0.1", 0), st["l4_l5_on_buried_by_laser_hole"].get("0.15", 0)))
    P("      (c) L2-L3 + L3-L4 + L4-L5 coincident:     %4d  (with Top-L2 too: %d)"
      % (st["L2_L5_sites"], st["L2_L5_plus_top"] + st["L2_L5_full_top_bottom"]))
    P("      (d) full Top-to-Bottom column (5 drills): %4d  [enquiry: 4]; %d mix 0.10 and 0.15"
      % (st["L2_L5_full_top_bottom"], st["full_columns_mixed_laser_sizes"]))
    for c in F["full_columns"]:
        P("            (%.3f, %.3f) %-10s %s" % (c["x"], c["y"], c["net"],
                                              " ".join("%s %.2f" % (k, c["holes"][k]) for k in ("Top-L2", "L2-L3", "L3-L4", "L4-L5", "L5-Bot"))))
    P("          L4-L5 on L5-Bottom laser:             %4d  (0.10/0.10 %d, 0.15/0.15 %d)"
      % (st["l5_bot_on_l4_l5"], st["l4_l5_on_l5_bot_by_holes"].get("0.1/0.1", 0), st["l4_l5_on_l5_bot_by_holes"].get("0.15/0.15", 0)))
    para("Physical blind/buried XY sites: %d; none coincides with a through via. "
         "Sites by number of stacked drills: %s."
         % (st["hdi_sites"], ", ".join("%s: %d" % (k, v) for k, v in sorted(st["max_stack_depth_sites"].items()))), "    ")
    P("")
    P("Q4  Mechanical vias built as drawn, lands not enlarged.")
    para("Buried L3-L4: 0.15 mm drill in a 0.27 mm land, %d vias, plus %d in a 0.30 mm "
         "land (%s) = %d [enquiry: 230]. Through: 0.20 mm drill in a 0.35 mm land, %d "
         "vias [enquiry: 169]. %d buried vias sit under U1 balls. The clearance rule to "
         "these lands is 0.0762 mm and tracks run close to it, so the drill and land cannot be enlarged; if PCBWay cannot "
         "build them as drawn, please give the minimum tool and land for each."
         % (vg.get(("L3-L4", 0.15, 0.27), 0), len(F["buried_non_027"]),
            ", ".join("%s (%.3f, %.3f)" % (b["net"], b["x"], b["y"]) for b in F["buried_non_027"]),
            F["buried_total"], F["through_total"], F["u1_centred_buried"]), "    ")
    P("")
    P("Q5  Hole spacing (measured on this board).")
    P("      Minimum hole edge to hole edge, holes meeting on a common layer: %.3f mm"
      % hh["gap"])
    P("      (DRC Hole To Hole rule 0.24 mm). By pair of hole types:")
    pairs = list(hh["by_pair"].items())
    for i in range(0, len(pairs), 2):
        P("      " + "   ".join("%-24s %.3f" % (k, v) for k, v in pairs[i:i + 2]))
    para("Hole wall to the nearest other-net TRACK on a layer the hole passes: laser "
         "%.3f mm, buried %.3f mm, through via %.3f mm. Hole wall to PLANE copper is "
         "governed by the rules (planes to through vias 0.175 mm, everything else "
         "0.0762 mm, both pass DRC); the enquiry quoted 0.15 / 0.136 / 0.151 mm "
         "(laser / buried / through) from the earlier layout and the solid pours were "
         "not re-measured here. Non-plated holes: %.3f mm to the nearest track, %.3f mm "
         "to the nearest via land, 0.25 mm to the plane pours (rule Clearance_Plane_NPTH, "
         "passes DRC) [enquiry: 0.086 / 0.25]."
         % (hw["laser"]["gap"], hw["buried"]["gap"], hw["through_via"]["gap"], F["npth_to_track"]["gap"], F["npth_to_via_land"]), "    ")
    P("")
    P("Q6  Plane copper between clearance holes.")
    para("Between adjacent via-in-pad balls of U1 the L2 GND plane keeps strips of "
         "about 0.085-0.09 mm, none under 0.0762 mm (necks were removed at 3 mil). "
         "This was measured on the saved pours of 2026-11-05 and was NOT re-measured "
         "on this file. No connection depends on these strips: PCBWay may clear any "
         "strip below its minimum.", "    ")
    P("")
    P("Q7  3/3 mil on all six layers at the stack's copper weights.")
    para("Minimum track width 0.0762 mm on Top, L3, L4 and Bottom (L2 and L5 carry "
         "only plane pours). Global clearance rule 0.0762 mm (3 mil). Measured "
         "minimum track to other-net copper: %s. (a) One 3 mil track between two "
         "0.25 mm U1 lands on Top: track-to-land minimum %.4f mm [enquiry: "
         "0.082-0.087]; the U1 mask openings are drawn 1:1 (%d openings of 0.25 mm in "
         "GTS) - please keep the track under mask. (b) Track to laser via land: L3 "
         "%.4f mm, L4 %.4f mm. If any layer needs thinner copper for 3/3 mil, say "
         "which."
         % (", ".join("%s %.4f mm" % (k, v) for k, v in sp["by_layer"].items() if v < 9),
            F["track_to_u1_land_min"], sum(tent["Top"]["u1_openings"].values()),
            F["track_to_laser_land_min"]["L3-SIG"], F["track_to_laser_land_min"]["L4-SIG"]), "    ")
    P("")
    P("Q8  Through vias in SMD pads: resin-plugged and plated over.")
    para("%d through vias (0.20/0.35) touch an SMD pad (%d pad contacts: hole inside "
         "the pad %d, hole on the pad edge %d, land only %d) [enquiry: 114], "
         "including U1 balls W8 and A13 and SDRAM U3 balls G9, H2 and H8. They stay in "
         "the pads by design. Please resin-plug them and plate over flat (IPC-4761 "
         "type VII, VIPPO), and say whether this changes your minimum hole or land. "
         "Full list under THROUGH VIAS IN SMD PADS below."
         % (n_thru_vip, tvc["entries"], pos_tv.get("hole in pad", 0), pos_tv.get("hole on pad edge", 0),
            pos_tv.get("land only", 0)), "    ")
    P("")
    P("Q9  Planarity of the filled lasers in the U1 field.")
    bx = F["u1_box"]
    off10_in = sum(1 for e in F["via_in_pad"] if e["ref"] == "U1" and not e["centred"] and e["hole"] < 0.12
                   and bx[0] <= e["via_x"] <= bx[2] and bx[1] <= e["via_y"] <= bx[3])
    para("%d U1 lands carry a centred filled 0.10 mm laser; %d more vias overlap U1 "
         "lands off-centre (Q1); %d 0.10 mm lasers inside the U1 land field (ball "
         "centres +/-0.25 mm) are not centred on a ball, %d of them among the "
         "off-centre ones. Please state any DFM concern (dimple depth, planarity) "
         "[enquiry: 149 + about 30]."
         % (combos.get("Top-L2", 0) + combos.get("Top-L2 + L2-L3", 0) + combos.get("Top-L2 + L2-L3 + L3-L4", 0)
            + combos.get("Top-L2 + L2-L3 + L3-L4 + L4-L5", 0), off["vias"], l10["not_on_ball_under_u1"], off10_in), "    ")
    P("")
    P("Q10 Price for 5 and 10 pieces, with and without the plugged through vias, and")
    P("    lead time: pending.")
    P("")
    P("Other laser via-in-pad (not U1), also copper-filled and capped flat:")
    para("%d laser vias touch non-U1 SMD pads (%d of 0.15/0.30, %d of 0.10/0.25) "
         "[enquiry: about 270, 256 of them 0.15/0.30]."
         % (lasers_np["total"], lasers_np["by_hole"].get("0.15", 0), lasers_np["by_hole"].get("0.1", 0)), "    ")
    P("")
    P("ORDER AND CAM GATE")
    para("Bare board, six layers, two-step sequential HDI, in the same family as the "
         "earlier Zulu A7 HDI order: same layer use, same agreed stack, same via "
         "classes plus a 0.10 mm laser class. Route it to PCBWay HDI engineering/CAM "
         "review. Do not release fabrication as a standard six-layer prototype and do "
         "not start production until the items above are answered in writing.")
    P("")
    P("BOARD")
    P("Finished outline: %.2f mm x %.2f mm, rectangle with four %.2f mm corner radii"
      % (box[2] - box[0], box[3] - box[1], CORNER_R))
    P("  (from the GM profile: %d straight edges, %d arcs centred %.2f mm in from each"
      % (nlines, len(arcs), CORNER_R))
    P("  corner; Adafruit Feather form factor)")
    P("Finished thickness: 1.60 mm +/-0.16 mm")
    P("Material: Shengyi S1000-2M, Tg 180")
    P("Surface finish: ENIG")
    P("Solder mask: green;  Silkscreen: white")
    P("Layer order (PcbDoc layer names):")
    use = ["signal/components", "GND plane polygon", "signal", "signal", "VCC3V3 plane polygon", "signal/components"]
    for i, (name, u) in enumerate(zip(F["layer_order"], use), 1):
        P("  L%d  %-13s %s" % (i, name, u))
    para("The L2 and L5 Gerbers are positive signal-layer polygon plots, not negative "
         "plane files.")
    P("")
    P("STACK (AS AGREED WITH PCBWAY ENGINEERING FOR THE EARLIER ZULU A7 HDI ORDER,")
    P("PCBWay stackup file of 2026-10-27)")
    P("  Layer/material                     Thickness")
    P("  L1 copper                          0.5 oz base, plated to 1 oz")
    P("  3313 prepreg, L1-L2                0.1016 mm")
    P("  L2 copper                          0.5 oz")
    P("  1080 prepreg, L2-L3                0.071 mm")
    P("  L3 copper                          0.5 oz")
    P("  Core, L3-L4                        1.065 mm")
    P("  L4 copper                          0.5 oz")
    P("  1080 prepreg, L4-L5                0.071 mm")
    P("  L5 copper                          0.5 oz")
    P("  3313 prepreg, L5-L6                0.1016 mm")
    P("  L6 copper                          0.5 oz base, plated to 1 oz")
    para("Inner copper is 0.5 oz; do not substitute 1 oz without confirming 3/3 mil "
         "(Q7). Any change to the construction needs our written approval.")
    P("")
    P("HDI CONSTRUCTION, VIA TYPES AND DRILL COUNTS (PcbDoc and drill files agree)")
    P("  Span           Type                Hole   Land   Ring    Count  File, tool")
    rows = [("Top-L2", "laser microvia", 0.10, 0.25, "TX6", "T01"), ("Top-L2", "laser microvia", 0.15, 0.30, "TX6", "T02"),
            ("L2-L3", "laser microvia", 0.10, 0.25, "TX7", "T01"), ("L2-L3", "laser microvia", 0.15, 0.30, "TX7", "T02"),
            ("L3-L4", "buried, mechanical", 0.15, 0.27, "TX3", "T02"), ("L3-L4", "buried, mechanical", 0.15, 0.30, "TX3", "T02"),
            ("L4-L5", "laser microvia", 0.10, 0.25, "TX9", "T01"), ("L4-L5", "laser microvia", 0.15, 0.30, "TX9", "T02"),
            ("L5-Bot", "laser microvia", 0.10, 0.25, "TX10", "T01"), ("L5-Bot", "laser microvia", 0.15, 0.30, "TX10", "T02"),
            ("Top-Bot", "plated through via", 0.20, 0.35, "TXT", "T03")]
    total_rows = 0
    for span, kind, h, land, f, t in rows:
        n = vg.get((span, h, land), 0)
        total_rows += n
        P("  %-14s %-19s %.2f   %.2f   %.3f  %5d  %s, %s" % (span.replace("Bot", "Bottom") if span != "Top-Bot" else "Top-Bottom",
                                                            kind, h, land, (land - h) / 2, n, f, t))
    if total_rows != F["via_total"]:
        raise ValueError("via table %d != %d vias" % (total_rows, F["via_total"]))
    P("  Laser microvias %d (0.10 mm: %d, 0.15 mm: %d), buried %d, through %d;"
      % (F["laser_total"], F["laser_by_hole"].get("0.1", 0), F["laser_by_hole"].get("0.15", 0), F["buried_total"], F["through_total"]))
    P("  %d via objects in all." % F["via_total"])
    para("Drill-file hit counts per tool equal the PcbDoc via counts above, matched "
         "one-to-one by position and hole size. The L3-L4 buried via is a 0.15 mm "
         "mechanical drill through the 1.065 mm core (aspect ratio about 7.1:1), as on "
         "the earlier Zulu A7 HDI order. Fill and planarize every receiving microvia "
         "and buried via before the next build-up step; confirm the lamination and "
         "fill/cap sequence in the CAM response.")
    P("")
    P("PLATED HOLES, PLATED SLOTS AND NON-PLATED HOLES (Top-Bottom)")
    for ph in F["pad_holes"]:
        P("  %.2f mm plated round x%-3d %s Feather header pins (0.1 in), %.2f mm lands"
          % (ph["hole"], ph["count"], ph["ref"], ph["land"]))
    P("  0.60 mm plated slots x%d    X1 USB-C receptacle (HRO TYPE-C-31-M-12) shell legs:"
      % len(F["plated_slots"]))
    for s in F["plated_slots"]:
        P("    X1-%s  %.2f x %.2f mm, %s, centre (%.4f, %.4f), land %s mm, net %s"
          % (s["pad"], s["tool"], s["length"], s["orientation"], s["x"], s["y"], s["land_top"], s["net"]))
    para("The slots are in %s as G85 routes of a 0.60 mm tool (route length + tool = "
         "overall length). Do not convert them to round holes or make them non-plated."
         % drill_name("SlotHoles-Plated.TXT"), "    ")
    P("  Non-plated holes (%s):" % drill_name("RoundHoles-NonPlated.TXT"))
    for n in F["npth"]:
        what = "Feather mounting hole" if n["hole"] > 2 else "X1 USB-C locating peg"
        P("    %.2f mm  (%7.3f, %7.3f)  %s" % (n["hole"], n["x"], n["y"], what))
    para("The plane pours are pulled back 0.25 mm from all six non-plated holes.", "    ")
    P("")
    P("TRACK AND SPACE")
    P("  Minimum designed track: %.4f mm (3 mil), used on Top, L3, L4 and Bottom." % F["track_min_width_routed"])
    P("  Clearance rules (all pass DRC):")
    gaps = {"Clearance": "0.0762 mm  all copper, all layers (global)",
            "Clearance_SDRAM_INNER": "0.10 mm    SDRAM data/address/control nets on L3/L4",
            "Clearance_SDRAM_CLK": "0.20 mm    SDRAM-CLK on L3/L4",
            "Clearance_Plane_ThruVia": "0.175 mm   L2/L5 plane pours to through vias",
            "Clearance_Plane_NPTH": "0.25 mm    L2/L5 plane pours to the X1/X2 holes"}
    for r in F["clearance_rules"]:
        P("    " + gaps.get(r["name"], "%s %s" % (r["name"], r["gap"])))
    P("  Measured minimum track to other-net copper: %.4f mm (%s, %s to %s %s-%s)."
      % (sp["gap"], sp["where"]["layer"], sp["where"]["a"], sp["where"]["kind"], sp["where"]["ref"], sp["where"]["pad"]))
    P("  Do not globally resize copper without approval.")
    P("")
    P("BGA U1")
    para("U1 is an XC7A35T in CPG236 (0.5 mm pitch, %d balls) on Top, with %s lands "
         "on this board (the earlier Zulu A7 HDI order had 0.225 mm). Mask openings "
         "are 1:1 (%s in GTS); minimum mask web (DRC rule) 0.10 mm. Do not enlarge the "
         "U1 mask openings without approval. Via-in-pad on U1: Q1."
         % (F["u1_lands"]["count"], ", ".join(F["u1_lands"]["sizes"]).replace("0.250 round Top", "0.25 mm round"),
            ", ".join("%d x %s" % (v, k.split(" r")[0]) for k, v in tent["Top"]["u1_openings"].items())))
    P("")
    P("VIA-IN-PAD (FILL AND CAP REQUIRED)")
    para("%d vias have a land that overlaps an SMD pad (%d pad contacts; %d vias touch "
         "two pads of the same net). By via type: %s. Position of the hole: centred in "
         "the pad %d (U1 balls and one resistor pad), inside the pad %d, on the pad edge %d, land only %d (counted per "
         "pad contact). Every microvia in a pad is copper-filled and capped flat; every "
         "through via in a pad is resin-plugged and plated over (Q8). The complete "
         "table (ref, pad, net, side, via type, hole, land, XY, position) is in %s, "
         "which is part of this package."
         % (vs["vias"], vs["entries"], vs["vias_touching_two_pads"],
            ", ".join("%s %d" % (k, v) for k, v in vs["by_type"].items()),
            vs["by_position"].get("centred", 0), vs["by_position"].get("hole in pad", 0),
            vs["by_position"].get("hole on pad edge", 0), vs["by_position"].get("land only", 0), csv_name))
    P("  Pad contacts per part (type: L=laser 0.15/0.30, l=laser 0.10/0.25, T=through):")
    per = defaultdict(Counter)
    for e in F["via_in_pad"]:
        per[e["ref"]]["T" if e["span"] == "Top-Bot" else ("l" if e["hole"] < 0.12 else "L")] += 1
    items = ["%s %s" % (r, "+".join("%d%s" % (c[k], k) for k in ("l", "L", "T") if c[k])) for r, c in sorted(per.items(), key=lambda kv: natural(kv[0]))]
    line = "   "
    for it in items:
        if len(line) + len(it) + 3 > 78:
            P(line)
            line = "   "
        line += "  " + it + ";"
    P(line)
    P("")
    P("THROUGH VIAS IN SMD PADS (resin plug + plate over; %d vias, %d pad contacts)" % (n_thru_vip, len(tv)))
    P("  Ref-pad     Side    Net             Hole vs pad       Via centre (mm)")
    for e in sorted(tv, key=lambda e: (natural(e["ref"]), natural(e["pad"]), e["via_x"])):
        P("  %-11s %-7s %-15s %-17s (%7.3f, %7.3f)" % ("%s-%s" % (e["ref"], e["pad"]), e["side"], e["via_net"],
                                                       e["position"], e["via_x"], e["via_y"]))
    P("")
    P("SOLDER MASK AND VIA TENTING (checked against GTS/GBS)")
    t_open, b_open = tent["Top"], tent["Bottom"]
    para("Every mask opening sits on a pad (%d Top, %d Bottom; none on a bare via). "
         "Vias whose land reaches into a mask opening: Top %d (%s), Bottom %d (%s); "
         "all of them are via-in-pad vias listed above except the %d below (%d "
         "openings). Every other via is tented on both sides."
         % (t_open["openings"], b_open["openings"], t_open["vias_with_land_in_opening"],
            ", ".join("%s %d, hole exposed %d" % (k, v["vias"], v["hole_reached"]) for k, v in t_open["exposed_by_span"].items()),
            b_open["vias_with_land_in_opening"],
            ", ".join("%s %d, hole exposed %d" % (k, v["vias"], v["hole_reached"]) for k, v in b_open["exposed_by_span"].items()),
            len({(e["x"], e["y"]) for s in ("Top", "Bottom") for e in tent[s]["not_in_vip_list"]}),
            sum(len(tent[s]["not_in_vip_list"]) for s in ("Top", "Bottom"))))
    for s in ("Top", "Bottom"):
        for e in tent[s]["not_in_vip_list"]:
            P("  %-6s %-7s %-7s (%7.3f, %7.3f) land overlapped %.3f mm by the opening of %s"
              % (s, e["span"], e["net"], e["x"], e["y"], e["land_overlap"], e["opening"]))
            P("                  (same net), hole not exposed (hole edge %.3f mm from the opening)" % e["hole_margin"])
    exposed_thru = sum(tent[s]["exposed_by_span"].get("Top-Bot", {}).get("vias", 0) for s in ("Top", "Bottom"))
    para("The %d through vias that are not in pads are tented. PLEASE PLUG ALL %d "
         "THROUGH VIAS (the %d in pads resin-plugged and plated over, the rest at "
         "least resin-plugged, IPC-4761 type VI or VII) so that mask registration "
         "cannot leave an open hole beside a pad, and state the method in the CAM "
         "response. All microvias and buried vias are filled anyway for the stacking."
         % (F["through_total"] - n_thru_vip, F["through_total"], n_thru_vip))
    P("")
    P("CONTROLLED IMPEDANCE")
    para("None requested. The only high-speed pair, USB 2.0 D+/D- between the "
         "USB-C receptacle X1 (HRO TYPE-C-31-M-12) and the FT2232HQ U2, is not "
         "routed as a coupled pair: USB_D_P runs %.2f mm on L3 (0.15 mm wide, with "
         "%d stacked Top-L2 + L2-L3 0.15 mm laser sites, %d vias), USB_D_N runs %.2f mm on Top "
         "(0.15 mm wide). It is electrically short; do not adjust it."
         % (usb["usb_track_length"]["USB_D_P"], len(usb["usb_vias"]) // 2, len(usb["usb_vias"]), usb["usb_track_length"]["USB_D_N"]))
    P("")
    P("PANEL")
    para("Please propose a panel for approval. The outline has %.2f mm corner radii, "
         "so the boards must be routed out (tabs/mouse bites), not V-cut through the "
         "corners." % CORNER_R)
    P("")
    P("FILE MAP")
    fm = [("GTL", "L1 Top copper"), ("G1", "L2 GND"), ("G2", "L3 signal"), ("G3", "L4 signal"), ("G4", "L5 VCC3V3"),
          ("GBL", "L6 Bottom copper"), ("GTS", "Top solder mask"), ("GBS", "Bottom solder mask"),
          ("GTO", "Top silkscreen"), ("GBO", "Bottom silkscreen"), ("GTP", "Top paste"), ("GBP", "Bottom paste"),
          ("GM", "Board profile (rounded corners)")]
    for ext, what in fm:
        P("  %-38s %s" % ("%s.%s" % (BASE, ext), what))
    dm = {"RoundHoles-Plated.TXT": "Top-Bottom plated: through vias, X2 pins",
          "RoundHoles-NonPlated.TXT": "Top-Bottom non-plated holes",
          "SlotHoles-Plated.TXT": "Top-Bottom plated X1 slots (G85)",
          "RoundHoles-Plated.TX3": "L3-L4 buried vias",
          "RoundHoles-Plated.TX6": "Top-L2 microvias (0.10 + 0.15)",
          "RoundHoles-Plated.TX7": "L2-L3 microvias (0.10 + 0.15)",
          "RoundHoles-Plated.TX9": "L4-L5 microvias (0.10 + 0.15)",
          "RoundHoles-Plated.TX10": "L5-Bottom microvias (0.10 + 0.15)"}
    for suffix in DRILL_ORDER:
        P("  %-38s %s" % (drill_name(suffix), dm[suffix]))
    P("  %-38s %s" % (BASE + ".LDP", "Drill-pair layer map"))
    P("  %-38s %s" % (BASE + ".DRR", "Drill sizes and counts"))
    P("  %-38s %s" % (csv_name, "Complete via-in-pad table"))
    P("")
    P("FINAL VERIFICATION")
    P("Altium DRC %s %s on asar_feather.PcbDoc:" % (drc["date"], drc["time"]))
    P("%s warnings, %d rule violations, %d waived (%d rules checked)."
      % (drc["warnings"], drc["violations"], drc["waived"], drc["rules"]))
    P("Gerbers: metric RS-274X, 0.0001 mm coordinate resolution")
    P("NC drill: metric Excellon 4:4, separate plated / non-plated / slot files")
    per_file = ", ".join("%s %s" % (s.split(".")[-1] if s.startswith("RoundHoles-Plated") else s.split("-")[0] + ("-NP" if "Non" in s else ""),
                                    "/".join(str(v["file"]) for v in dv[s].values())) for s in DRILL_ORDER)
    para("Every drill hit was matched one-to-one against the PcbDoc via and pad "
         "positions by tool size (0 missing, 0 extra in every file): " + per_file + ".")
    P("")
    para("This ZIP contains fabrication data only. Assembly BOM, CPL and assembly "
         "instructions are supplied separately if assembly is quoted.")
    return L


def write_csv(F, path):
    rows = []
    for e in sorted(F["via_in_pad"], key=lambda e: (natural(e["ref"]), natural(e["pad"]), e["side"], e["span"], e["via_x"], e["via_y"])):
        rows.append([e["ref"], e["pad"], e["pad_net"], e["side"], e["span"], "%.2f" % e["hole"], "%.2f" % e["land"],
                     "%.4f" % e["via_x"], "%.4f" % e["via_y"], e["position"], "%.4f" % e["overlap"], e["pad_shape"],
                     e["pad_size"].replace(" ", ""),
                     "resin plug + plate over (VIPPO)" if e["span"] == "Top-Bot" else "copper fill + cap flat"])
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(["ref", "pad", "net", "pad_side", "via_span", "hole_mm", "land_mm", "via_x_mm", "via_y_mm",
                "hole_vs_pad", "land_overlap_mm", "pad_shape", "pad_size_mm", "fill_request"])
    w.writerows(rows)
    data = buf.getvalue().encode("ascii")
    with open(path, "wb") as handle:
        handle.write(data)
    return len(rows)


def validate_note(path, sha):
    raw = open(path, "rb").read()
    text = raw.decode("ascii")
    if "\n" in text.replace("\r\n", "") or not text.endswith("\r\n"):
        raise ValueError("notes are not CRLF throughout")
    if FORBIDDEN.lower() in text.lower():
        raise ValueError("notes name the earlier order number")
    m = re.search(r"PCB SHA-256: ([0-9A-F]{64})", text)
    if not m or m.group(1) != sha:
        raise ValueError("notes record the wrong PCB SHA-256")
    if "PROVISIONAL" not in text.splitlines()[0] or REVISION not in text:
        raise ValueError("notes header does not say PROVISIONAL / revision")
    for q in range(1, 11):
        if not re.search(r"^Q%d\s" % q, text, re.M):
            raise ValueError("notes lack enquiry item Q%d" % q)


# ---- main ------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--note", default=DEFAULT_NOTE)
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--archive", default=DEFAULT_ARCHIVE)
    return parser.parse_args()


def main():
    args = parse_args()
    note, csv_path, archive_path = (os.path.abspath(p) for p in (args.note, args.csv, args.archive))
    for p in (note, csv_path, archive_path):
        if not os.path.abspath(p).startswith(os.path.abspath(ROOT)):
            raise ValueError("refusing to write outside the Asar_feather folder: %s" % p)

    sha = sha256(PCB)
    if sha != EXPECTED_PCB_SHA256 or md5(PCB) != EXPECTED_PCB_MD5:
        raise ValueError("PcbDoc changed: %s" % sha)
    filenames = (["%s.%s" % (BASE, e) for e in GERBER_EXTENSIONS] + [drill_name(s) for s in DRILL_ORDER]
                 + [BASE + ".LDP", BASE + ".DRR"])
    sources = [out(f) for f in filenames]
    missing = [p for p in sources + [DRC] if not os.path.isfile(p)]
    if missing:
        raise FileNotFoundError("missing: " + ", ".join(missing))
    if any(os.path.getsize(p) == 0 for p in sources):
        raise ValueError("empty CAM file")
    stale = [p for p in sources + [DRC] if os.path.getmtime(p) < os.path.getmtime(PCB)]
    if stale:
        raise ValueError("outputs predate the PcbDoc: " + ", ".join(stale))

    validate_outline()
    found = validate_drills()
    validate_drr(found)
    validate_ldp()
    drc = read_drc()
    if drc["violations"] or drc["warnings"]:
        raise ValueError("DRC is not clean: %s" % drc)

    F = fab_facts.measure(PCB)
    for suffix, tools in F["drill_vs_board"].items():
        for t, r in tools.items():
            if r["file"] != r["board"] or r["board_not_in_file"] or r["file_not_on_board"]:
                raise ValueError("drill file %s %s does not match the PcbDoc one-to-one: %s" % (suffix, t, r))
            exp = EXPECTED_DRILLS[suffix][t[1:]]
            if r["file"] != exp[1] or abs(r["size"] - exp[0]) > 0.0015:
                raise ValueError("%s %s: %s != DRR %s" % (suffix, t, r, exp))
    if F["layer_order"] != ["Top Layer", "L2-GND", "L3-SIG", "L4-SIG", "L5-VCC3V3", "Bottom Layer"]:
        raise ValueError("layer order changed: %s" % F["layer_order"])
    if F["laser_total"] != EXPECTED_MICROVIA_TOTAL:
        raise ValueError("PcbDoc laser count %d != DRR %d" % (F["laser_total"], EXPECTED_MICROVIA_TOTAL))
    if any(e["pad_net"] != e["via_net"] for e in F["via_in_pad"]):
        raise ValueError("a via sits in a pad of another net")
    if F["tenting"]["Top"]["unmatched_openings"] or F["tenting"]["Bottom"]["unmatched_openings"]:
        raise ValueError("mask opening without a pad")

    os.makedirs(FABRICATION, exist_ok=True)
    n_csv = write_csv(F, csv_path)
    if n_csv != len(F["via_in_pad"]):
        raise ValueError("CSV rows %d != %d" % (n_csv, len(F["via_in_pad"])))
    lines = build_notes(F, drc, sha, md5(PCB), os.path.basename(csv_path))
    with open(note, "wb") as handle:
        handle.write(("\r\n".join(lines) + "\r\n").encode("ascii"))
    validate_note(note, sha)

    sources = sources + [note, csv_path]
    if any(FORBIDDEN.lower() in os.path.basename(p).lower() for p in sources + [archive_path]):
        raise ValueError("an order file must never be packaged")
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for p in sources:
            archive.write(p, arcname=os.path.basename(p))
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("corrupt archive entry")
        names = [os.path.basename(p) for p in sources]
        if archive.namelist() != names or len(names) != EXPECTED_ENTRIES:
            raise ValueError("archive entries changed: %s" % archive.namelist())
        for p in sources:
            if archive.read(os.path.basename(p)) != open(p, "rb").read():
                raise ValueError("archive entry differs from source: %s" % p)
            if FORBIDDEN.encode() in open(p, "rb").read():
                raise ValueError("%s contains the earlier order number" % p)
    print("ASAR_FEATHER_PCBWAY_FABRICATION_RELEASE_PROVISIONAL PASS")
    print("%d flat entries; notes %d lines; via-in-pad CSV %d rows" % (len(sources), len(lines), n_csv))
    print("%s | %d bytes | SHA256 %s" % (os.path.basename(archive_path), os.path.getsize(archive_path), sha256(archive_path)))
    print("notes SHA256 %s" % sha256(note))
    print("csv   SHA256 %s" % sha256(csv_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
