# -*- coding: utf-8 -*-
"""Generate and validate the Zulu A7 JLCPCB assembly release.

The BOM is read from the current Altium schematics. Component locations,
rotations, layers, and pad geometry are read from the current PcbDoc.

    python tools/generate_jlcpcb_assembly.py
"""

import csv
import hashlib
import os
import re
import struct
import subprocess
import sys
from collections import defaultdict

import olefile
import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.join(ROOT, "Imported zulu_a7.PrjPcb")
PCB = os.path.join(PROJECT, "zulu_a7.PcbDoc")
ASSEMBLY = os.path.join(ROOT, "assembly")

sys.path.insert(0, HERE)
import bom_audit
from route_inputs import LAYER, U, kvs

RELEASE_DATE = "2026-10-02"
BOARD_WIDTH = 69.85
BOARD_HEIGHT = 25.40
ARTWORK_REFS = {"U$2", "U$3", "U$4", "U$5"}
NON_PART_LIBS = {"DOCFIELD", "CC_BY", "CC_CC", "CC_SA", "CC_COPYRIGHT"}
ASSEMBLY_LAYER_OVERRIDES = {"X2": "Bottom"}

# Exact MPN-to-LCSC identities recorded in the project's September 2026
# sourcing audit. Stock status is intentionally not asserted here.
LCSC_CODES = {
    "PTS810SJM250SMTR LFS": "C116501",
    "GRM155R71C104KA88D": "C71629",
    "GRM188R60J106ME47D": "C77041",
    "GRM155R71H102KA01D": "C77018",
    "GRM033R71E103KE14D": "C85930",
    "MSASJ105BB5475MFNA01": "C7235186",
    "GRM033R61A104KE15D": "C76934",
    "CL21A106KPFNNNG": "C307523",
    "GRM21BR61A226ME44L": "C441864",
    "CL10A226MP8NUNE": "C86295",
    "GRM188R61C475KE11D": "C77045",
    "GRM033R60J474KE90D": "C85926",
    "PPTC062LFBN-RC": "C3321957",
    "BLM18KG601SN1D": "C85833",
    "LTST-C191KRKT": "C125099",
    "LTST-C191KGKT": "C125098",
    "ECS-3225SMV-120-FP-TR": "C17218076",
    "2N7002LT1G": "C16338",
    "RC0201FR-075K1L": "C274341",
    "RC0201FR-071KL": "C138165",
    "RC0201FR-07845RL": "C474846",
    "RC0402FR-0712KL": "C114760",
    "RC0201FR-0710KL": "C106225",
    "RC0402FR-071KL": "C106235",
    "RC0201FR-0733RL": "C295794",
    "RC0201FR-07200RL": "C274337",
    "742C083472JP": "C2961927",
    "RC0402FR-074K7L": "C105871",
    "RC0402FR-07100KL": "C60491",
    "RC0402FR-07680RL": "C137948",
    "RC0402FR-0733RL": "C138002",
    "RC0402FR-07330RL": "C105875",
    "RC0402FR-0710KL": "C60490",
    "XC7A35T-1CPG236C": "C1521738",
    "FT2232HL-REEL": "C27882",
    "W25Q128JVSIQ": "C97521",
    "SC189ZSKTRT": "C2650317",
    "SC189LSKTRT": "C842844",
    "BQ24232RGTR": "C528622",
    "93LC46BT-I/SN": "C16253",
    "105017-0001": "C136000",
    "DM3D-SF": "C719027",
    "B2B-PH-SM4-TB(LF)(SN)": "C160352",
}


def clean(value):
    return " ".join((value or "").split())


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def git_commit():
    result = subprocess.run(
        ["git", "-C", ROOT, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def read_board():
    board_file = olefile.OleFileIO(PCB)
    indexed_components = {
        index: record
        for index, record in kvs(
            board_file, "Components6/Data", "SOURCEDESIGNATOR="
        ).items()
    }
    components = {
        record["SOURCEDESIGNATOR"]: record for record in indexed_components.values()
    }

    data = board_file.openstream("Pads6/Data").read()
    pads = []
    offset = 0
    while offset + 5 <= len(data):
        record_type = data[offset]
        record_length = struct.unpack("<I", data[offset + 1 : offset + 5])[0]
        if record_type != 2:
            break
        name = data[offset + 6 : offset + 6 + data[offset + 5]].decode("latin-1")
        offset += 5 + record_length
        for _ in range(3):
            block_length = struct.unpack("<I", data[offset : offset + 4])[0]
            offset += 4 + block_length
        block_length = struct.unpack("<I", data[offset : offset + 4])[0]
        body = data[offset + 4 : offset + 4 + block_length]
        offset += 4 + block_length
        block_length = struct.unpack("<I", data[offset : offset + 4])[0]
        offset += 4 + block_length
        if len(body) < 60:
            continue

        component_index = struct.unpack("<h", body[7:9])[0]
        component = indexed_components.get(component_index, {})
        ref = component.get("SOURCEDESIGNATOR")
        if not ref:
            continue
        x = struct.unpack("<i", body[13:17])[0] * U
        y = struct.unpack("<i", body[17:21])[0] * U
        size_x = struct.unpack("<i", body[21:25])[0] * U
        size_y = struct.unpack("<i", body[25:29])[0] * U
        hole = struct.unpack("<i", body[45:49])[0] * U
        rotation = struct.unpack("<d", body[52:60])[0]
        if round(rotation) % 180 == 90:
            size_x, size_y = size_y, size_x
        round_pad = body[49] == body[50] == body[51] == 1
        pads.append(
            {
                "ref": ref,
                "pad": name,
                "layer": LAYER.get(body[0], str(body[0])),
                "x": x,
                "y": y,
                "sx": size_x,
                "sy": size_y,
                "hole": hole,
                "round": round_pad,
            }
        )
    board_file.close()
    return components, pads


def component_geometry(components, pads):
    grouped = defaultdict(list)
    for pad in pads:
        grouped[pad["ref"]].append(pad)

    geometry = {}
    for ref, component in components.items():
        if ref in ARTWORK_REFS:
            continue
        component_pads = grouped.get(ref, [])
        if not component_pads:
            raise ValueError(f"{ref} has no PCB pads")
        x0 = min(pad["x"] - pad["sx"] / 2 for pad in component_pads)
        x1 = max(pad["x"] + pad["sx"] / 2 for pad in component_pads)
        y0 = min(pad["y"] - pad["sy"] / 2 for pad in component_pads)
        y1 = max(pad["y"] + pad["sy"] / 2 for pad in component_pads)
        pcb_layer = "Bottom" if component.get("LAYER") == "BOTTOM" else "Top"
        geometry[ref] = {
            "ref": ref,
            "footprint": component.get("PATTERN", ""),
            "layer": ASSEMBLY_LAYER_OVERRIDES.get(ref, pcb_layer),
            "pcb_layer": pcb_layer,
            "rotation": int(round(float(component.get("ROTATION", "0")))) % 360,
            "x": (x0 + x1) / 2,
            "y": (y0 + y1) / 2,
            "bbox": (x0, y0, x1, y1),
            "pads": component_pads,
            "has_smd": any(pad["hole"] <= 1e-6 for pad in component_pads),
            "has_th": any(pad["hole"] > 1e-6 for pad in component_pads),
        }
    return geometry


def schematic_parts():
    return {
        ref: component
        for ref, component in bom_audit.load_components().items()
        if component["lib"] not in NON_PART_LIBS
    }


def make_bom(parts, geometry):
    groups = {}
    for ref, component in parts.items():
        params = component["params"]
        if params.get("DNS") == "Yes":
            continue
        mpn = clean(params.get("MANF#")) or clean(params.get("Comment"))
        manufacturer = clean(params.get("MANF"))
        footprint = component["fp"] or geometry[ref]["footprint"]
        key = (mpn, manufacturer, footprint)
        groups.setdefault(key, []).append(ref)

    rows = []
    for (mpn, manufacturer, footprint), refs in groups.items():
        refs = sorted(refs, key=bom_audit.natkey)
        comments = sorted(
            {
                clean(parts[ref]["params"].get("Comment"))
                for ref in refs
                if clean(parts[ref]["params"].get("Comment"))
            }
        )
        assembly_types = {
            "Mixed"
            if geometry[ref]["has_smd"] and geometry[ref]["has_th"]
            else "THT"
            if geometry[ref]["has_th"]
            else "SMT"
            for ref in refs
        }
        if len(assembly_types) != 1:
            raise ValueError(f"mixed assembly types in BOM group {refs}")
        lcsc = LCSC_CODES.get(mpn, "")
        physical_quantity = 4 if refs == ["X2"] else len(refs)
        if refs == ["X2"]:
            sourcing_note = (
                "MANUAL REVIEW: one PCB designator represents two 9-pin and two "
                "11-pin underside THT header strips"
            )
        elif lcsc:
            sourcing_note = (
                "Exact LCSC identity from the 2026-09 sourcing audit; revalidate "
                "identity, stock, and lifecycle before ordering"
            )
        else:
            sourcing_note = (
                "No exact LCSC code verified; resolve an exact approved part or "
                "consign before ordering"
            )
        rows.append(
            {
                "Comment": " / ".join(comments) or mpn,
                "Designator": ",".join(refs),
                "Footprint": footprint,
                "LCSC Part #": lcsc,
                "Manufacturer": manufacturer,
                "Manufacturer Part Number": mpn,
                "Qty per PCB": str(physical_quantity),
                "Assembly Type": next(iter(assembly_types)),
                "Sourcing Note": sourcing_note,
                "_refs": refs,
            }
        )
    rows.sort(key=lambda row: bom_audit.natkey(row["_refs"][0]))
    return rows


def write_bom(rows):
    path = os.path.join(ASSEMBLY, "Zulu_A7_JLCPCB_BOM.csv")
    columns = [
        "Comment",
        "Designator",
        "Footprint",
        "LCSC Part #",
        "Manufacturer",
        "Manufacturer Part Number",
        "Qty per PCB",
        "Assembly Type",
        "Sourcing Note",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_cpl(parts, geometry):
    path = os.path.join(ASSEMBLY, "Zulu_A7_JLCPCB_CPL.csv")
    columns = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    fitted = [
        ref
        for ref, component in parts.items()
        if component["params"].get("DNS") != "Yes"
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for ref in sorted(fitted, key=bom_audit.natkey):
            item = geometry[ref]
            writer.writerow(
                {
                    "Designator": ref,
                    "Mid X": f'{item["x"]:.4f}mm',
                    "Mid Y": f'{item["y"]:.4f}mm',
                    "Layer": item["layer"],
                    "Rotation": item["rotation"],
                }
            )
    return path


def assembly_counts(parts, geometry):
    fitted = {
        ref
        for ref, component in parts.items()
        if component["params"].get("DNS") != "Yes"
    }
    return {
        side: sum(geometry[ref]["layer"] == side for ref in fitted)
        for side in ("Top", "Bottom")
    }


def write_notes(parts, geometry, bom_rows):
    fitted = {
        ref
        for ref, component in parts.items()
        if component["params"].get("DNS") != "Yes"
    }
    dnp = sorted(
        (
            ref
            for ref, component in parts.items()
            if component["params"].get("DNS") == "Yes"
        ),
        key=bom_audit.natkey,
    )
    counts = assembly_counts(parts, geometry)
    unresolved = [
        row
        for row in bom_rows
        if not row["LCSC Part #"]
    ]
    lines = [
        "ZULU A7 - JLCPCB ASSEMBLY NOTES",
        f"Release date: {RELEASE_DATE}",
        f"Source commit: {git_commit()}",
        f"PCB SHA-256: {sha256(PCB)}",
        "",
        "UPLOAD SET",
        "Upload the fabrication ZIP, BOM CSV, and CPL CSV in their separate",
        "JLCPCB order fields. Copy all critical instructions from this file into",
        "the online order remarks; do not rely on this file being read automatically.",
        "",
        "ASSEMBLY SCOPE",
        f"Fitted PCB designators: {len(fitted)}",
        f"Top-side fitted designators: {counts['Top']}",
        f"Bottom-side fitted designators: {counts['Bottom']}",
        f"Do not populate: {', '.join(dnp)}",
        "Assembly is required on both sides.",
        "",
        "HDI ORDER GATE",
        "This is a six-layer, two-step sequential HDI board with stacked laser",
        "microvias and an L3-L4 buried-via stage. Obtain written confirmation that",
        "JLCPCB PCBA can be attached to the manually reviewed HDI fabrication quote",
        "before relying on turnkey assembly.",
        "",
        "CPL AND ORIENTATION",
        "CPL units are millimetres from the board lower-left origin. The top drawing",
        "is viewed from the top; the bottom drawing is mirrored and viewed from the",
        "bottom. CPL rotations are the rotations stored in the final Altium PCB.",
        "Review every polarized part and all rotations in JLCPCB's placement preview.",
        "Do not approve the order if the preview disagrees with either assembly drawing.",
        "",
        "SPECIAL COMPONENT INSTRUCTIONS",
        "- X2 is not one 40-pin component. It is four underside-mounted THT strips:",
        "  2 x PRPC009SAAN-RC (9-pin) and 2 x PRPC011SAAN-RC (11-pin). The BOM",
        "  therefore reports physical quantity 4 for the single PCB designator X2.",
        "  Quote this as manual THT work. If JLCPCB cannot process that exception,",
        "  leave X2 unpopulated for post-assembly installation.",
        "- J1 is a vertical 2x6 female through-hole Pmod header on the top side.",
        "- JP3 and JP4 are intentional DNP flying-lead/pogo positions.",
        "- X4 pin 1 is battery positive.",
        "- X3's microSD card opening faces the left board edge.",
        "- X1's micro-USB opening faces the upper board edge.",
        "- Verify pin 1/A1 on U1, U2, U3, U4, U8, U10, Q1, and every polarized LED.",
        "- LD0 cathodes are pads 2, 4, and 6; its anodes are pads 1, 3, and 5.",
        "",
        "SOURCING",
        "The LCSC codes in the BOM are exact identities captured by the project's",
        "September 2026 sourcing audit, not a claim of current stock. Revalidate",
        "manufacturer, MPN, package, lifecycle, authenticity, and stock in the live",
        "JLCPCB parts selector. Do not make substitutions without written approval.",
        f"BOM lines without a verified exact LCSC code: {len(unresolved)}",
    ]
    for row in unresolved:
        lines.append(
            f"  {row['Designator']}: {row['Manufacturer Part Number']} "
            f"({row['Footprint']})"
        )
    lines.extend(
        [
            "",
            "QUALITY AND TEST",
            "- Inspect all BGA joints for U1 with the process controls appropriate to",
            "  an Artix-7 CPG236 package; follow MSL storage/bake requirements.",
            "- No firmware programming or functional test is included unless separately",
            "  quoted and supplied with a test procedure and programming image.",
            "- Request first-article inspection and placement-photo approval before the",
            "  remainder of the build.",
            "",
            "REQUIRED ORDER REVIEW",
            "Confirm HDI fabrication plus two-sided SMT/THT assembly, X2's four-piece",
            "manual installation, unresolved/consigned parts, polarity, and placement",
            "preview before releasing the order.",
        ]
    )
    path = os.path.join(ASSEMBLY, "Zulu_A7_Assembly_Notes.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def board_to_page(x, y, region, plot, side):
    x0, y0, x1, y1 = region
    scale = min(plot.width / (x1 - x0), plot.height / (y1 - y0))
    drawn_width = (x1 - x0) * scale
    drawn_height = (y1 - y0) * scale
    left = plot.x0 + (plot.width - drawn_width) / 2
    top = plot.y0 + (plot.height - drawn_height) / 2
    source_x = x1 - (x - x0) if side == "Bottom" else x
    page_x = left + (source_x - x0) * scale
    page_y = top + (y1 - y) * scale
    return page_x, page_y, scale


def draw_assembly_page(doc, side, region, label, parts, geometry):
    page = doc.new_page(width=1190.55, height=841.89)
    page.insert_text(
        (42, 37),
        f"Zulu A7 - {side} Assembly Drawing - {label}",
        fontsize=18,
        fontname="hebo",
        color=(0.08, 0.10, 0.14),
    )
    view_note = (
        "MIRRORED - viewed from bottom"
        if side == "Bottom"
        else "Viewed from top"
    )
    page.insert_text(
        (42, 57),
        f"{view_note}; dimensions and coordinate grid in millimetres",
        fontsize=9,
        color=(0.25, 0.28, 0.32),
    )
    plot = fitz.Rect(52, 78, page.rect.width - 42, page.rect.height - 58)
    x0, y0, x1, y1 = region

    p0 = board_to_page(x0, y0, region, plot, side)
    p1 = board_to_page(x1, y1, region, plot, side)
    board_rect = fitz.Rect(
        min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1])
    )
    page.draw_rect(
        board_rect,
        color=(0.08, 0.10, 0.14),
        fill=(0.97, 0.98, 0.98),
        width=1.2,
    )

    for grid_x in range(int(x0 // 5) * 5, int(x1) + 1, 5):
        if grid_x < x0:
            continue
        a = board_to_page(grid_x, y0, region, plot, side)
        b = board_to_page(grid_x, y1, region, plot, side)
        page.draw_line((a[0], a[1]), (b[0], b[1]), color=(0.87, 0.88, 0.89), width=0.35)
        page.insert_text((a[0] - 7, board_rect.y1 + 13), str(grid_x), fontsize=6.5)
    for grid_y in range(int(y0 // 5) * 5, int(y1) + 1, 5):
        if grid_y < y0:
            continue
        a = board_to_page(x0, grid_y, region, plot, side)
        b = board_to_page(x1, grid_y, region, plot, side)
        page.draw_line((a[0], a[1]), (b[0], b[1]), color=(0.87, 0.88, 0.89), width=0.35)
        page.insert_text((board_rect.x0 - 23, a[1] + 2), str(grid_y), fontsize=6.5)

    side_refs = [
        ref
        for ref, component in parts.items()
        if geometry[ref]["layer"] == side
        and x0 <= geometry[ref]["x"] <= x1
        and y0 <= geometry[ref]["y"] <= y1
    ]
    side_ref_set = set(side_refs)

    for item in geometry.values():
        for pad in item["pads"]:
            through_hole = pad["hole"] > 1e-6
            if not through_hole and item["ref"] not in side_ref_set:
                continue
            if not through_hole and pad["layer"] != side:
                continue
            if not (x0 <= pad["x"] <= x1 and y0 <= pad["y"] <= y1):
                continue
            center = board_to_page(pad["x"], pad["y"], region, plot, side)
            scale = center[2]
            width = max(pad["sx"] * scale, 0.8)
            height = max(pad["sy"] * scale, 0.8)
            pad_rect = fitz.Rect(
                center[0] - width / 2,
                center[1] - height / 2,
                center[0] + width / 2,
                center[1] + height / 2,
            )
            fill = (0.72, 0.77, 0.82) if through_hole else (0.42, 0.62, 0.78)
            if pad["round"] and abs(width - height) < 0.25:
                page.draw_circle(
                    (center[0], center[1]),
                    width / 2,
                    color=(0.22, 0.30, 0.38),
                    fill=fill,
                    width=0.35,
                )
            else:
                page.draw_rect(
                    pad_rect,
                    color=(0.22, 0.30, 0.38),
                    fill=fill,
                    width=0.35,
                )
            if through_hole:
                page.draw_circle(
                    (center[0], center[1]),
                    max(pad["hole"] * scale / 2, 0.45),
                    color=(0.2, 0.2, 0.2),
                    fill=(1, 1, 1),
                    width=0.3,
                )

    detail = (x1 - x0) < BOARD_WIDTH - 1
    font_size = 7.0 if detail else 4.6
    for ref in sorted(side_refs, key=bom_audit.natkey):
        item = geometry[ref]
        bx0, by0, bx1, by1 = item["bbox"]
        c0 = board_to_page(bx0, by0, region, plot, side)
        c1 = board_to_page(bx1, by1, region, plot, side)
        box = fitz.Rect(
            min(c0[0], c1[0]), min(c0[1], c1[1]), max(c0[0], c1[0]), max(c0[1], c1[1])
        )
        dnp = parts[ref]["params"].get("DNS") == "Yes"
        if ref == "X2":
            for label_text, label_y in (
                ("X2 - two upper-row header strips", 23.1),
                ("X2 - two lower-row header strips", 2.3),
            ):
                label = board_to_page(item["x"], label_y, region, plot, side)
                text_width = fitz.get_text_length(
                    label_text, fontname="helv", fontsize=font_size
                )
                text_box = fitz.Rect(
                    label[0] - text_width / 2 - 1.2,
                    label[1] - font_size * 0.75,
                    label[0] + text_width / 2 + 1.2,
                    label[1] + font_size * 0.55,
                )
                page.draw_rect(
                    text_box,
                    color=None,
                    fill=(1, 1, 1),
                    fill_opacity=0.86,
                )
                page.insert_text(
                    (label[0] - text_width / 2, label[1] + font_size * 0.30),
                    label_text,
                    fontsize=font_size,
                    fontname="helv",
                    color=(0.05, 0.07, 0.09),
                )
        else:
            page.draw_rect(
                box,
                color=(0.60, 0.60, 0.60) if dnp else (0.10, 0.40, 0.24),
                width=0.55,
                dashes="[2 2]" if dnp else None,
            )
            label_text = f"DNP {ref}" if dnp else ref
            text_width = fitz.get_text_length(
                label_text, fontname="helv", fontsize=font_size
            )
            center_x = (box.x0 + box.x1) / 2
            center_y = (box.y0 + box.y1) / 2
            text_box = fitz.Rect(
                center_x - text_width / 2 - 1.2,
                center_y - font_size * 0.75,
                center_x + text_width / 2 + 1.2,
                center_y + font_size * 0.55,
            )
            page.draw_rect(
                text_box,
                color=None,
                fill=(1, 1, 1),
                fill_opacity=0.82,
            )
            page.insert_text(
                (center_x - text_width / 2, center_y + font_size * 0.30),
                label_text,
                fontsize=font_size,
                fontname="helv",
                color=(0.55, 0.12, 0.10) if dnp else (0.05, 0.07, 0.09),
            )

        pin_one = next(
            (pad for pad in item["pads"] if pad["pad"] == "1"),
            next((pad for pad in item["pads"] if pad["pad"] == "A1"), None),
        )
        if pin_one is not None:
            marker = board_to_page(pin_one["x"], pin_one["y"], region, plot, side)
            page.draw_circle(
                (marker[0], marker[1]),
                2.1 if detail else 1.35,
                color=(0.78, 0.08, 0.08),
                fill=(0.92, 0.15, 0.12),
                width=0.4,
            )

    page.insert_text(
        (52, page.rect.height - 28),
        "Red dot = pin 1/A1. Dashed red label = DNP. "
        "Verify every rotation and polarity in JLCPCB's placement preview.",
        fontsize=8,
        color=(0.24, 0.27, 0.31),
    )
    return set(side_refs)


def write_drawing(side, parts, geometry):
    output = os.path.join(ASSEMBLY, f"Zulu_A7_Assembly_Drawing_{side}.pdf")
    document = fitz.open()
    regions = [
        ((0.0, 0.0, BOARD_WIDTH, BOARD_HEIGHT), "Overview"),
        ((0.0, 0.0, 36.5, BOARD_HEIGHT), "West Detail"),
        ((33.35, 0.0, BOARD_WIDTH, BOARD_HEIGHT), "East Detail"),
    ]
    shown = set()
    for region, label in regions:
        shown.update(draw_assembly_page(document, side, region, label, parts, geometry))
    document.set_metadata(
        {
            "title": f"Zulu A7 {side} Assembly Drawing",
            "author": "Zulu A7 project",
            "subject": "JLCPCB assembly reference",
            "keywords": "Zulu A7, JLCPCB, assembly, pick and place",
            "creator": "tools/generate_jlcpcb_assembly.py",
            "producer": "PyMuPDF",
            "creationDate": "D:20261002000000-07'00'",
        }
    )
    document.save(output, garbage=4, deflate=True)
    document.close()
    return output, shown


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def validate(outputs, parts, geometry, bom_rows, drawing_refs):
    fitted = {
        ref
        for ref, component in parts.items()
        if component["params"].get("DNS") != "Yes"
    }
    dnp = set(parts) - fitted
    bom_refs = {
        ref
        for row in read_csv(outputs["bom"])
        for ref in row["Designator"].split(",")
        if ref
    }
    cpl_rows = read_csv(outputs["cpl"])
    cpl_refs = {row["Designator"] for row in cpl_rows}
    if bom_refs != fitted:
        raise ValueError(
            f"BOM designator mismatch: missing={sorted(fitted - bom_refs)} "
            f"extra={sorted(bom_refs - fitted)}"
        )
    if cpl_refs != fitted:
        raise ValueError(
            f"CPL designator mismatch: missing={sorted(fitted - cpl_refs)} "
            f"extra={sorted(cpl_refs - fitted)}"
        )
    if dnp & bom_refs or dnp & cpl_refs:
        raise ValueError("DNP designators leaked into BOM or CPL")
    if len(cpl_rows) != len(cpl_refs):
        raise ValueError("duplicate CPL designators")
    for row in cpl_rows:
        x = float(row["Mid X"].removesuffix("mm"))
        y = float(row["Mid Y"].removesuffix("mm"))
        if not (0 <= x <= BOARD_WIDTH and 0 <= y <= BOARD_HEIGHT):
            raise ValueError(f"CPL coordinate is outside the board: {row}")
        if row["Layer"] not in {"Top", "Bottom"}:
            raise ValueError(f"invalid CPL layer: {row}")
        if int(row["Rotation"]) not in {0, 90, 180, 270}:
            raise ValueError(f"invalid CPL rotation: {row}")

    expected_by_side = {
        side: {ref for ref in parts if geometry[ref]["layer"] == side}
        for side in ("Top", "Bottom")
    }
    for side in ("Top", "Bottom"):
        if drawing_refs[side] != expected_by_side[side]:
            raise ValueError(
                f"{side} drawing coverage mismatch: "
                f"missing={sorted(expected_by_side[side] - drawing_refs[side])}"
            )
        document = fitz.open(outputs[side.lower()])
        if document.page_count != 3:
            raise ValueError(f"{side} drawing has {document.page_count} pages, expected 3")
        text = "\n".join(page.get_text() for page in document)
        document.close()
        for ref in expected_by_side[side]:
            if re.search(rf"(?<![A-Za-z0-9$]){re.escape(ref)}(?![A-Za-z0-9])", text) is None:
                raise ValueError(f"{ref} is missing from {side} drawing text")

    if len(bom_rows) != len(read_csv(outputs["bom"])):
        raise ValueError("BOM row count changed during serialization")
    for path in outputs.values():
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise ValueError(f"missing or empty output: {path}")


def main():
    os.makedirs(ASSEMBLY, exist_ok=True)
    board_components, pads = read_board()
    board_refs = set(board_components) - ARTWORK_REFS
    parts = schematic_parts()
    if board_refs != set(parts):
        raise ValueError(
            f"schematic/PCB mismatch: missing PCB={sorted(set(parts) - board_refs)}, "
            f"extra PCB={sorted(board_refs - set(parts))}"
        )
    geometry = component_geometry(board_components, pads)
    bom_rows = make_bom(parts, geometry)

    outputs = {
        "bom": write_bom(bom_rows),
        "cpl": write_cpl(parts, geometry),
        "notes": write_notes(parts, geometry, bom_rows),
    }
    outputs["top"], top_refs = write_drawing("Top", parts, geometry)
    outputs["bottom"], bottom_refs = write_drawing("Bottom", parts, geometry)
    drawing_refs = {"Top": top_refs, "Bottom": bottom_refs}
    validate(outputs, parts, geometry, bom_rows, drawing_refs)

    fitted = sum(
        component["params"].get("DNS") != "Yes" for component in parts.values()
    )
    counts = assembly_counts(parts, geometry)
    unresolved = sum(not row["LCSC Part #"] for row in bom_rows)
    print("ASSEMBLY_RELEASE PASS")
    print(
        f"{len(bom_rows)} BOM lines, {fitted} fitted designators "
        f"({counts['Top']} top / {counts['Bottom']} bottom), "
        f"{unresolved} BOM lines need sourcing resolution"
    )
    for key in ("bom", "cpl", "notes", "top", "bottom"):
        path = outputs[key]
        print(
            f"{os.path.basename(path)} | {os.path.getsize(path)} bytes | "
            f"SHA256 {sha256(path)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
