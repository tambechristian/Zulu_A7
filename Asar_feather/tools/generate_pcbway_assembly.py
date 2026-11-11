# -*- coding: utf-8 -*-
"""Generate and validate the Asar Feather PCBWay assembly release (PROVISIONAL, 2026-11-11).

The BOM is read from the Asar schematics (asar_a7_0..6.SchDoc). Component locations, rotations, layers and
pad geometry are read from asar_feather.PcbDoc. Via-in-pad counts come from tools/fab_facts.json (the
fabrication release's own census of the same PcbDoc), cross-checked here against the board's via totals.

    python tools/generate_pcbway_assembly.py

Writes into assembly/: Asar_Feather_PCBWay_BOM.csv (PCBWay BOM template columns), _CPL.csv (SMT parts
only, both sides), _Assembly_Notes.txt, _Assembly_Drawing_Top.pdf / _Bottom.pdf and
Asar_Feather_PCBWay_Assembly_2026-11-11_PROVISIONAL.zip, then validates them and prints every MPN problem.

ORIGIN: copied 2026-11-11 from Zulu_A7_Fab_B/tools/generate_jlcpcb_assembly.py (PCBWay mode only) and
retargeted to the Asar Feather. Changes from Fab B: the board constants; the Asar parts (USB-C X1 with plated
shell slots, FT2232HQ QFN-64, AS4C32M16SB-7BIN FBGA, W25Q128JVPIQ WSON, 93LC46BT-I/MNY TDFN, STEMMA QT X5,
RESET button, SMD test pads JP3/JP4); X2 (the Feather 1x16 + 1x12 headers) is bought by PCBWay and SHIPPED
LOOSE, not soldered (LOOSE_PARTS, user decision 2026-11-11: two BOM purchase lines, X2 not in the CPL, its
holes left empty); LED polarity per LED (LD1/LD2 and LD3/LD4 face opposite ways here);
the panel is left to PCBWay's proposal; MPN sanity checks (package vs footprint, value code vs Comment);
the PROVISIONAL banner tied to docs/pcbway_vip_enquiry.md. Fab B's JLCPCB/neutral modes and LCSC table are
not carried over. Helpers are in tools/pcbway_inputs.py (cut-down copies of Fab B's bom_audit.py,
route_inputs.py and fix_text_orientation.py).
"""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import sys
import textwrap
import zipfile
from collections import defaultdict

import olefile
import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbway_inputs as bom_audit                 # natkey, load_components (Asar sheets)
from pcbway_inputs import LAYER, U, kvs

# ---- Asar Feather board-specific constants (2026-11-11) ----
RELEASE_PREFIX = "Asar_Feather"
RELEASE_NAME = "Asar Feather"
RELEASE_DATE = "2026-11-11"
BOARD_WIDTH = 50.80            # Feather outline 2000 x 900 mil, 2.54 mm corner radius
BOARD_HEIGHT = 22.86
CORNER_RADIUS = 2.54
FAB_ARCHIVE = "Asar_Feather_PCBWay_Fabrication_2026-11-11_PROVISIONAL.zip"
FAB_NOTES = "Asar_Feather_PCBWay_FAB_NOTES.txt"
ASSEMBLY_ARCHIVE = "Asar_Feather_PCBWay_Assembly_2026-11-11_PROVISIONAL.zip"
FINISHED_THICKNESS = "1.60 +/- 0.16 mm"   # the stack PCBWay agreed for the earlier Zulu A7 HDI order
ENQUIRY = "docs/pcbway_vip_enquiry.md"

ROOT = os.path.dirname(HERE)
PROJECT = os.path.join(ROOT, "Asar_feather.PrjPcb")
PCB = os.path.join(PROJECT, "asar_feather.PcbDoc")
FAB_FACTS = os.path.join(HERE, "fab_facts.json")
ASSEMBLY = os.path.join(ROOT, "assembly")
BOM_FILENAME = f"{RELEASE_PREFIX}_PCBWay_BOM.csv"
CPL_FILENAME = f"{RELEASE_PREFIX}_PCBWay_CPL.csv"
NOTES_FILENAME = f"{RELEASE_PREFIX}_PCBWay_Assembly_Notes.txt"
DRAWING_FILENAME = f"{RELEASE_PREFIX}_PCBWay_Assembly_Drawing_{{side}}.pdf"
FORBIDDEN_TEXT = ("W1150632AS3P6", "JLCPCB", "LCSC")   # never in a deliverable

ARTWORK_REFS = {"U$2", "U$3", "U$4", "U$5"}
NON_PART_LIBS = {"DOCFIELD", "CC_BY", "CC_CC", "CC_SA", "CC_COPYRIGHT"}

# Parts PCBWay buys but does NOT solder: packed loose with each board (user decision 2026-11-11). Each entry is
# one BOM purchase line: (MPN, maker, qty per board, description). The designator is not placed, not in the
# CPL and not DNS; main() checks that the schematic's MANF# / MANF name exactly these parts.
LOOSE_PARTS = {
    "X2": [
        ("PRPC016SAAN-RC", "Sullins", 1,
         "Feather header 1x16: 0.1 in (2.54 mm) male single-row strip, straight (vertical), through-hole, "
         "0.64 mm square gold-flash pins"),
        ("PRPC012SAAN-RC", "Sullins", 1,
         "Feather header 1x12: 0.1 in (2.54 mm) male single-row strip, straight (vertical), through-hole, "
         "0.64 mm square gold-flash pins"),
    ],
}
LOOSE_TYPE = "Ship loose"          # BOM Type of a loose line: bought, not placed
LOOSE_NOTE = ("SHIP LOOSE - do not solder, pack with each board. Buy {qty} per board and pack {qty} with each "
              "finished board; X2's 28 plated holes stay EMPTY at assembly (we solder the headers ourselves). "
              "Not in the CPL.")

# The maker each MPN prefix belongs to (as Fab B). The LTC3556-block edit wrote MANF=Samsung on Murata GRM
# parts and MANF=Yageo on the Panasonic ERA part; the BOM takes the maker from the MPN and prints each fix.
MPN_MANUFACTURER = {
    "GRM": "Murata",
    "DFE": "Murata",
    "BLM": "Murata",
    "CL05": "Samsung",
    "CL10": "Samsung",
    "CL21": "Samsung",
    "RC0201": "Yageo",
    "RC0402": "Yageo",
    "ERA-": "Panasonic",
}
MANUFACTURER_FIXES = []        # (ref, schematic MANF, MPN, maker used), filled by make_bom
MPN_PROBLEMS = []              # (refs, text), filled by check_mpns / make_bom

# MPN prefixes that fit each footprint (a mismatch is reported as a doubtful MPN, not fixed).
FOOTPRINT_MPN_PREFIX = {
    "C0201": ("GRM033", "GRM0335"),
    "C0402": ("GRM155", "CL05", "MSASJ105"),
    "C0603": ("GRM188", "CL10"),
    "C0805": ("GRM21", "CL21"),
    "R0201": ("RC0201", "ERA-1A"),
    "R0402": ("RC0402",),
    "IND2520": ("DFE2520",),
    "IND0603": ("BLM18",),
}

# Zulu A7 parts that the Feather replaced or removed: validate() fails if one reaches the BOM.
STALE_MPNS = {
    "105017-0001", "PPTC062LFBN-RC", "FT2232HL-REEL", "AS4C32M16SB-7TCN", "W25Q128JVSIQ", "93LC46BT-I/SN",
    "BQ24232RGTR", "TPS63802DLAR", "SC189ZSKTRT", "SC189LSKTRT", "PRPC009SAAN-RC", "PRPC011SAAN-RC",
}
STALE_REFS = {"J1", "R29", "R30", "R31", "R32", "R33", "U5", "U6", "LD5", "R78", "C162"}

LD0_NUMBERING = {
    "19-337/R6GHBHC-A01/2T": [
        "  Its datasheet's pin numbers depend on the revision: Rev.4 (DSE-0002657)",
        "  numbers the cathodes 1-3 and the anodes 4-6, Rev.6 numbers them like the",
        "  footprint. Follow the cathode mark, not the pad numbers.",
    ],
}


def clean(value):
    return " ".join((value or "").split())


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def md5(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], check=True, capture_output=True, text=True).stdout.strip()


def source_line():
    dirty = subprocess.run(
        ["git", "-C", os.path.dirname(PCB), "status", "--porcelain", "--", os.path.basename(PCB)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    head = git("rev-parse", "HEAD")
    if dirty:
        return f"Source: working copy after commit {head[:7]} (the PCB SHA-256 below identifies it)"
    return f"Source commit: {head}"


def configure():
    global PCB, ASSEMBLY, FAB_FACTS
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pcb", default=PCB, help="PcbDoc used for placement data")
    parser.add_argument("--assembly-dir", default=ASSEMBLY, help="directory for generated outputs")
    parser.add_argument("--fab-facts", default=FAB_FACTS, help="fab_facts.json of the same PcbDoc")
    args = parser.parse_args()
    PCB = os.path.abspath(args.pcb)
    ASSEMBLY = os.path.abspath(args.assembly_dir)
    FAB_FACTS = os.path.abspath(args.fab_facts)
    if not os.path.isfile(PCB):
        parser.error(f"PCB does not exist: {PCB}")


# ------------------------------------------------------------------ board --
def read_board():
    board_file = olefile.OleFileIO(PCB)
    indexed_components = dict(kvs(board_file, "Components6/Data", "SOURCEDESIGNATOR=").items())
    components = {record["SOURCEDESIGNATOR"]: record for record in indexed_components.values()}

    data = board_file.openstream("Pads6/Data").read()
    pads = []
    offset = 0
    while offset + 5 <= len(data):
        record_type = data[offset]
        record_length = struct.unpack("<I", data[offset + 1: offset + 5])[0]
        if record_type != 2:
            break
        name = data[offset + 6: offset + 6 + data[offset + 5]].decode("latin-1")
        offset += 5 + record_length
        for _ in range(3):
            block_length = struct.unpack("<I", data[offset: offset + 4])[0]
            offset += 4 + block_length
        block_length = struct.unpack("<I", data[offset: offset + 4])[0]
        body = data[offset + 4: offset + 4 + block_length]
        offset += 4 + block_length
        block_length = struct.unpack("<I", data[offset: offset + 4])[0]
        offset += 4 + block_length
        if len(body) < 60:
            continue
        component_index = struct.unpack("<h", body[7:9])[0]
        ref = indexed_components.get(component_index, {}).get("SOURCEDESIGNATOR")
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
        pads.append({
            "ref": ref, "pad": name, "layer": LAYER.get(body[0], str(body[0])),
            "x": x, "y": y, "sx": size_x, "sy": size_y, "hole": hole,
            "round": body[49] == body[50] == body[51] == 1,
        })
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
        layer = "Bottom" if component.get("LAYER") == "BOTTOM" else "Top"
        geometry[ref] = {
            "ref": ref, "footprint": component.get("PATTERN", ""), "layer": layer,
            "rotation": int(round(float(component.get("ROTATION", "0")))) % 360,
            "x": (x0 + x1) / 2, "y": (y0 + y1) / 2, "bbox": (x0, y0, x1, y1), "pads": component_pads,
            "has_smd": any(pad["hole"] <= 1e-6 for pad in component_pads),
            "has_th": any(pad["hole"] > 1e-6 for pad in component_pads),
        }
    return geometry


def board_via_totals():
    """{(span, hole mm): count} straight from the PcbDoc, to check fab_facts.json against."""
    from altium_monkey import AltiumPcbDoc
    names = {1: "Top", 4: "L2", 2: "L3", 3: "L4", 5: "L5", 32: "Bot"}
    totals = defaultdict(int)
    for via in AltiumPcbDoc.from_file(PCB).vias:
        totals[(f"{names[via.layer_start]}-{names[via.layer_end]}", round(via.hole_size_mils * 0.0254, 2))] += 1
    return dict(totals)


def load_fab_facts():
    """fab_facts.json, refused if it is older than the PcbDoc or its via totals differ from the board's."""
    if not os.path.isfile(FAB_FACTS):
        raise ValueError(f"missing {FAB_FACTS}: run tools/fab_facts.py first")
    if os.path.getmtime(FAB_FACTS) < os.path.getmtime(PCB):
        raise ValueError("fab_facts.json is older than the PcbDoc: re-run tools/fab_facts.py")
    facts = json.load(open(FAB_FACTS, encoding="utf-8"))
    totals = board_via_totals()
    via_total = sum(totals.values())
    through = sum(n for (span, _), n in totals.items() if span == "Top-Bot")
    buried = sum(n for (span, _), n in totals.items() if span == "L3-L4")
    if (facts["via_total"], facts["through_total"], facts["buried_total"], facts["laser_total"]) != \
            (via_total, through, buried, via_total - through - buried):
        raise ValueError("fab_facts.json via totals differ from the PcbDoc")
    return facts, totals


# ------------------------------------------------------------- schematic --
def schematic_parts():
    return {ref: c for ref, c in bom_audit.load_components().items() if c["lib"] not in NON_PART_LIBS}


def is_fitted(ref, parts):
    """Placed (soldered) by the assembler: not DNS and not a ship-loose part."""
    return parts[ref]["params"].get("DNS") != "Yes" and ref not in LOOSE_PARTS


def fitted_refs(parts):
    return {ref for ref in parts if is_fitted(ref, parts)}


def loose_refs(parts):
    """Bought by the assembler and shipped loose: neither fitted nor DNS."""
    return {ref for ref in parts if ref in LOOSE_PARTS and parts[ref]["params"].get("DNS") != "Yes"}


def dns_refs_of(parts):
    return set(parts) - fitted_refs(parts) - loose_refs(parts)


def check_loose(parts):
    """The schematic must name exactly the loose lines' MPNs (joined by ' + ') and their maker."""
    for ref, lines in LOOSE_PARTS.items():
        if ref not in parts:
            raise ValueError(f"loose part {ref} is not in the schematic")
        params = parts[ref]["params"]
        want_mpn = " + ".join(mpn for mpn, _, _, _ in lines)
        if clean(params.get("MANF#")) != want_mpn:
            raise ValueError(f"{ref} schematic MANF# '{clean(params.get('MANF#'))}' != loose lines '{want_mpn}'")
        makers = {maker for _, maker, _, _ in lines}
        if makers != {clean(params.get("MANF"))}:
            raise ValueError(f"{ref} schematic MANF '{clean(params.get('MANF'))}' != loose makers {sorted(makers)}")


def value_in_ohms(text):
    """'4.7K' / '5.1k' / '845' / '12K 1%' / '104K' -> ohms."""
    m = re.match(r"\s*([\d.]+)\s*([kKmM]?)", text or "")
    if not m:
        return None
    return float(m.group(1)) * {"": 1, "k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6}[m.group(2)]


def value_in_farads(text):
    m = re.match(r"\s*([\d.]+)\s*([pnu])F", text or "")
    if not m:
        return None
    return float(m.group(1)) * {"p": 1e-12, "n": 1e-9, "u": 1e-6}[m.group(2)]


def code3(code, unit):
    """3-character EIA value code ('104', '4R7', '100') -> value, in pF for caps or ohms for resistors."""
    if "R" in code:
        return float(code.replace("R", "."))
    return float(code[:2]) * 10 ** int(code[2])


def mpn_value(mpn):
    """(kind, value) the MPN itself encodes, or None when the pattern is not one checked here."""
    m = re.match(r"RC0[24]0[12]FR-07(\d+)([RK])(\d*)L$", mpn)
    if m:
        return ("R", float(f"{m.group(1)}.{m.group(3) or 0}") * (1e3 if m.group(2) == "K" else 1))
    m = re.match(r"ERA-1AEB(\d{3})(\d)C$", mpn)
    if m:
        return ("R", float(m.group(1)) * 10 ** int(m.group(2)))
    m = re.match(r"742C\d{3}(\d{3})JP$", mpn)
    if m:
        return ("R", code3(m.group(1), "ohm"))
    m = re.match(r"GRM(?:03|15|18|21|31|32)\w\w\w\d\w(\d\d[\dR])", mpn)   # size, height, TC, voltage, value
    if m:
        return ("C", code3(m.group(1), "pF") * 1e-12)
    m = re.match(r"CL\d\d\w(\d\d\d)", mpn)
    if m:
        return ("C", code3(m.group(1), "pF") * 1e-12)
    m = re.match(r"MSASJ105\w{3}(\d{3})", mpn)
    if m:
        return ("C", code3(m.group(1), "pF") * 1e-12)
    m = re.match(r"DFE\d{6}\w-(\d)R(\d)M", mpn)
    if m:
        return ("L", float(f"{m.group(1)}.{m.group(2)}") * 1e-6)
    return None


def check_mpns(parts):
    """Doubtful MPNs: package prefix vs footprint, encoded value vs the schematic Comment."""
    for ref in sorted(fitted_refs(parts), key=bom_audit.natkey):
        params = parts[ref]["params"]
        mpn = clean(params.get("MANF#"))
        comment = clean(params.get("Comment"))
        fp = parts[ref]["fp"]
        if not mpn:
            MPN_PROBLEMS.append(([ref], "no MANF# (MPN) on the schematic part"))
            continue
        if not clean(params.get("MANF")):
            MPN_PROBLEMS.append(([ref], f"{mpn}: no MANF (manufacturer) on the schematic part"))
        prefixes = FOOTPRINT_MPN_PREFIX.get(fp)
        if prefixes and not mpn.startswith(prefixes):
            MPN_PROBLEMS.append(([ref], f"{mpn} does not look like a {fp} part"))
        encoded = mpn_value(mpn)
        if encoded is None:
            continue
        kind, value = encoded
        if kind == "R":
            stated = value_in_ohms(comment)
        elif kind == "C":
            stated = value_in_farads(comment)
        else:
            m = re.match(r"([\d.]+)uH", comment)
            stated = float(m.group(1)) * 1e-6 if m else None
        if stated is None or abs(stated - value) > 1e-3 * value:
            MPN_PROBLEMS.append(([ref], f"{mpn} encodes {value:g} but the Comment says '{comment}'"))


def make_bom(parts, geometry):
    groups = {}
    for ref in fitted_refs(parts):
        params = parts[ref]["params"]
        mpn = clean(params.get("MANF#")) or clean(params.get("Comment"))
        manufacturer = clean(params.get("MANF"))
        maker = next((m for prefix, m in MPN_MANUFACTURER.items() if mpn.startswith(prefix)), None)
        if maker and maker != manufacturer:
            MANUFACTURER_FIXES.append((ref, manufacturer, mpn, maker))
            manufacturer = maker
        footprint = parts[ref]["fp"] or geometry[ref]["footprint"]
        groups.setdefault((mpn, manufacturer, footprint), []).append(ref)

    rows = []
    for (mpn, manufacturer, footprint), refs in groups.items():
        refs = sorted(refs, key=bom_audit.natkey)
        comments = sorted({clean(parts[r]["params"].get("Comment")) for r in refs
                           if clean(parts[r]["params"].get("Comment"))})
        kinds = {"Mixed" if geometry[r]["has_smd"] and geometry[r]["has_th"]
                 else "THT" if geometry[r]["has_th"] else "SMT" for r in refs}
        if len(kinds) != 1:
            raise ValueError(f"mixed assembly types in BOM group {refs}")
        rows.append({"Comment": " / ".join(comments) or mpn, "Designator": ",".join(refs),
                     "Footprint": footprint, "Manufacturer": manufacturer, "Manufacturer Part Number": mpn,
                     "Qty per PCB": str(len(refs)), "Assembly Type": next(iter(kinds)), "_refs": refs})
    rows.sort(key=lambda row: bom_audit.natkey(row["_refs"][0]))
    return rows


PCBWAY_COLUMNS = ["Item #", "Designator", "Qty", "Manufacturer", "Mfg Part #", "Description / Value",
                  "Package/Footprint", "Type", "Your Instructions / Notes"]

PACKAGE_NAMES = {
    "742C043": "CTS 742C043: 2-element concave resistor array, 1.6 x 1.6 mm, 0.8 mm pitch",
    "742C083": "CTS 742C083: 4-element concave resistor array, 3.2 x 1.6 mm, 0.8 mm pitch",
    "742C163": "CTS 742C163: 8-element concave resistor array, 6.4 x 1.6 mm, 0.8 mm pitch",
    "32X25": "3.2 x 2.5 mm SMD oscillator",
    "IND2520": "2520 SMD inductor, 2.5 x 2.0 mm",
    "IND0603": "0603 SMD ferrite bead",
    "LED0603": "0603 SMD LED",
    "EVERLIGHT-19-337": "1.6 x 1.6 mm SMD RGB LED (Everlight 19-337 land)",
    "XC7A35T-CPG236": "CPG236 BGA, 10 x 10 mm, 0.5 mm pitch, 238 balls",
    "QFN-64-9X9-P0.5-EP4.35": "QFN-64 (VQFN), 9 x 9 mm, 0.5 mm pitch, 4.35 mm exposed pad",
    "FBGA-54-8X8-P0.8": "54-ball FBGA, 8 x 8 mm, 0.8 mm pitch",
    "WSON-8-6X5-P1.27": "WSON-8, 6 x 5 mm, 1.27 mm pitch, exposed pad",
    "TDFN-8-2X3-P0.5": "TDFN-8 (Microchip MN), 2 x 3 mm, 0.5 mm pitch, exposed pad",
    "QFN28-UFD-4X5": "QFN-28 (ADI UFD), 4 x 5 mm, 0.5 mm pitch, exposed pad (pin 29)",
    "SOT23-5": "SOT-23-5",
    "USB-C-HRO-TYPE-C-31-M-12": "USB Type-C receptacle, SMT contacts + 4 shell legs in plated slots + 2 pegs",
    "JST-B2B-PH-SM4-TB": "JST PH 2-pin top-entry SMT header",
    "JST-SM04B-SRSS-TB": "JST SH 1.0 mm 4-pin side-entry SMT header",
    "DM3D-SF": "Hirose DM3D microSD socket, SMT",
    "PTS810": "C&K PTS810 SMT tactile switch, 4.2 x 3.2 mm",
    "FEATHER-28": "Feather header holes, 1x16 + 1x12, 2.54 mm pitch, 1.0 mm plated",
    "TP-1X03-SMD": "three 1.0 mm round SMD test pads, 1.27 mm pitch",
}

PCBWAY_LINE_NOTES = {
    "XC7A35T-2CPG236I": (
        "Speed grade -2, industrial temperature: the approved substitute for XC7A35T-1CPG236C "
        "(same die, package and pinout). Buy only from an AMD-authorized distributor (e.g. Digi-Key, Mouser, "
        "Avnet); no local, broker or open-market stock. 0.5 mm BGA on 0.25 mm lands with filled, capped "
        "microvias in the lands: X-ray every board. Moisture sensitive: follow the MSL label."
    ),
    "FT2232HQ-REEL": (
        "QFN-64 9 x 9 mm (the HQ, not the LQFP HL). Buy only from an FTDI-authorized distributor (FTDI clones "
        "exist); no broker stock. Exposed pad: the land has no net (the datasheet says the pad is not "
        "internally grounded); solder it with reduced paste. Moisture sensitive: follow the MSL label."
    ),
    "AS4C32M16SB-7BIN": (
        "54-ball FBGA 8 x 8 mm, 0.8 mm pitch, 0.40 mm lands (the -7BIN, not the TSOP -7TCN). X-ray every "
        "board. Moisture sensitive: follow the MSL label."
    ),
    "W25Q128JVPIQ": ("WSON-8 6 x 5 mm (the JVPIQ, not the SOIC JVSIQ). Exposed pad land has no net: solder it "
                     "with reduced paste. Moisture sensitive: follow the MSL label."),
    "93LC46BT-I/MNY": "TDFN-8 2 x 3 mm, top side. Exposed pad land has no net: solder it with reduced paste.",
    "LTC3556EUFD#PBF": (
        "Bottom side. Exposed pad (pin 29) is GND: reduced, windowpane paste. The tape-and-reel "
        "ordering code LTC3556EUFD#TRPBF is the same part. Follow the MSL label."
    ),
    "SC189ASKTRT": "U7 = 1.0 V FPGA core (the only SOT-23-5 on the board).",
    "DFE252012F-2R2M=P2": (
        "L1, L2, L9 = 2.2 uH. Look-alike 2520 bodies: L3 is 1.5 uH (DFE252010P-1R5M=P2) and L8 "
        "3.3 uH (DFE252012F-3R3M=P2). Load each position from its own reel."
    ),
    "DFE252010P-1R5M=P2": "L3 = 1.5 uH (U7 buck). Look-alike of L1/L2/L8/L9: load from its own reel.",
    "DFE252012F-3R3M=P2": "L8 = 3.3 uH (U8 PowerPath). Look-alike of L1/L2/L3/L9: load from its own reel.",
    "ERA-1AEB1043C": "R116 = 104 kohm 0.1 % thin film (sets VCC3V3). No 1 % or other-value substitute.",
    "19-337/R6GHBHC-A01/2T": (
        "Water-clear lens. Polarity: cathodes = the cathode-mark column (board footprint pads 2, 4, 6; "
        "datasheet Rev.4 numbers them 1, 2, 3, Rev.6 like the footprint). The drawing's red dot marks "
        "footprint pad 1, an anode."
    ),
    "TYPE-C-31-M-12": (
        "Top side, mouth flush with the left (USB) board edge. Place in the LAST (top) reflow. Four shell legs "
        "in plated 0.6 mm slots (MP1-MP4) have no paste: hand/selective solder them after reflow to full "
        "barrel fill (see notes). Two 0.65 mm non-plated holes take the locating pegs."
    ),
    "SM04B-SRSS-TB(LF)(SN)": "STEMMA QT. Top side, mouth toward the right board edge. Pin 1 = GND.",
    "B2B-PH-SM4-TB(LF)(SN)": "Polarity: pin 1 is battery +, pin 2 is GND (see notes for its position).",
    "PTS810SJM250SMTR LFS": "BTN (user) and RESET (FPGA reload): same part, top side.",
    "DM3D-SF": "Bottom side; it sees the second (top-side) reflow upside down: support or glue if your process needs it.",
}

DESCRIPTION_OVERRIDES = {
    "ECS-3225SMV-120-FP-TR": "12 MHz HCMOS SMD oscillator, +-10 ppm, 1.62-3.63 V, 3.2 x 2.5 mm",
    "LTC3556EUFD#PBF": ("USB power manager with PowerPath, 4.2 V Li-ion charger, two 400 mA buck "
                        "regulators and a 1 A buck-boost, QFN-28 4 x 5 mm (UFD), exposed pad"),
    "SC189ASKTRT": "1.5 A synchronous buck regulator, fixed 1.0 V output, SOT-23-5",
    "LTST-C191KGKT": "green 0603 SMD indicator LED",
    "LTST-C191KRKT": "red 0603 SMD indicator LED",
    "742C163101JP": "8 x 100 ohm +-5% isolated concave resistor array, 6.4 x 1.6 mm, 0.8 mm pitch",
    "MSASJ105BB5475MFNA01": "4.7uF X5R 6.3V +-20% 0402 MLCC, 0.65 mm max",
    "TYPE-C-31-M-12": "USB Type-C receptacle, USB 2.0, SMT, 4 through-hole shell legs",
    "FT2232HQ-REEL": "FTDI FT2232HQ dual high-speed USB to UART/FIFO/JTAG bridge, QFN-64 9 x 9 mm",
    "AS4C32M16SB-7BIN": "512 Mbit SDRAM (32M x 16), 143 MHz, industrial, 54-ball FBGA 8 x 8 mm",
    "W25Q128JVPIQ": "128 Mbit SPI/QSPI NOR flash, industrial, WSON-8 6 x 5 mm",
    "93LC46BT-I/MNY": "1 Kbit Microwire serial EEPROM, industrial, TDFN-8 2 x 3 mm",
    "SM04B-SRSS-TB(LF)(SN)": "JST SH 1.0 mm 4-pin side-entry SMT header (STEMMA QT / Qwiic)",
    "XC7A35T-2CPG236I": "AMD Artix-7 FPGA XC7A35T, speed grade -2, industrial, CPG236 BGA 0.5 mm pitch",
}


def led_polarity_notes(geometry):
    """For the two-pad A/K LEDs: {ref: (side of pad K, X of K, X of A)}, from the PCB."""
    notes = {}
    for ref, item in geometry.items():
        names = {pad["pad"]: pad for pad in item["pads"]}
        if set(names) == {"A", "K"}:
            side = "EAST" if names["K"]["x"] > names["A"]["x"] else "WEST"
            notes[ref] = (side, names["K"]["x"], names["A"]["x"])
    return notes


def ld0_cathode_side(geometry):
    """'WEST' / 'EAST' / 'NORTH' / 'SOUTH': where LD0's cathode column (pads 2, 4, 6) lies from its anodes."""
    pads = {p["pad"]: p for p in geometry["LD0"]["pads"]}
    k = [pads[n] for n in ("2", "4", "6")]
    a = [pads[n] for n in ("1", "3", "5")]
    dx = sum(p["x"] for p in k) / 3 - sum(p["x"] for p in a) / 3
    dy = sum(p["y"] for p in k) / 3 - sum(p["y"] for p in a) / 3
    if abs(dx) > abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "NORTH" if dy > 0 else "SOUTH"


def buyer_spec(spec):
    spec = clean(spec).split(" -- ")[0]
    kept = []
    for clause in spec.split("; "):
        if re.search(r"replace|flagged|sheet p\d|section \d|DS_|same die|typo|alias|successor|"
                     r"obsolete|catalog|on 20\d\d-\d\d|LCSC|JLC", clause):
            continue
        if kept and len("; ".join(kept + [clause])) > 160:
            break
        kept.append(clause)
    return "; ".join(kept)


def pcbway_rows(rows, parts, geometry):
    leds = led_polarity_notes(geometry)
    out = []
    for row in rows:
        refs = row["_refs"]
        mpn = row["Manufacturer Part Number"]
        spec = buyer_spec(parts[refs[0]]["params"].get("SPEC"))
        comment = row["Comment"]
        description = DESCRIPTION_OVERRIDES.get(mpn) or (
            f"{comment}: {spec}" if spec and comment != mpn else (spec or comment))
        package = PACKAGE_NAMES.get(row["Footprint"], row["Footprint"])
        kind = {"SMT": "SMD", "THT": "thru-hole", "Mixed": "SMD"}[row["Assembly Type"]]
        note = PCBWAY_LINE_NOTES.get(mpn, "")
        led_refs = [ref for ref in refs if ref in leds]
        if led_refs:
            note = "Polarity: cathode = pad K; " + "; ".join(
                f"{ref} K on the {leds[ref][0]} side (X {leds[ref][1]:.2f} mm)" for ref in led_refs) + \
                ". Follow the drawings' red bar."
        out.append({
            "Designator": row["Designator"], "Qty": row["Qty per PCB"], "Manufacturer": row["Manufacturer"],
            "Mfg Part #": mpn, "Description / Value": description, "Package/Footprint": package, "Type": kind,
            "Your Instructions / Notes": note, "_refs": refs, "_qty": int(row["Qty per PCB"]),
        })
    for ref, component in sorted(parts.items(), key=lambda kv: bom_audit.natkey(kv[0])):
        if is_fitted(ref, parts):
            continue
        fp = component["fp"] or geometry[ref]["footprint"]
        if ref in loose_refs(parts):
            for mpn, maker, qty, desc in LOOSE_PARTS[ref]:
                out.append({
                    "Designator": ref, "Qty": str(qty), "Manufacturer": maker, "Mfg Part #": mpn,
                    "Description / Value": desc, "Package/Footprint": "through-hole pin header, 2.54 mm pitch "
                    "(not placed: shipped loose)", "Type": LOOSE_TYPE,
                    "Your Instructions / Notes": LOOSE_NOTE.format(qty=qty), "_refs": [ref], "_qty": qty,
                })
            continue
        note = ("DNS - do not populate, do not buy. Bare SMD test pads (JTAG): leave empty; please remove "
                "their apertures from the bottom stencil (tinned pads are acceptable if you cannot).")
        desc = buyer_spec(component["params"].get("SPEC")) or clean(component["params"].get("Comment"))
        out.append({
            "Designator": ref, "Qty": "0", "Manufacturer": "", "Mfg Part #": "none (do not populate)",
            "Description / Value": desc, "Package/Footprint": PACKAGE_NAMES.get(fp, fp), "Type": "DNS",
            "Your Instructions / Notes": note, "_refs": [ref], "_qty": 0,
        })
    for item, row in enumerate(out, 1):
        row["Item #"] = str(item)
    return out


def write_bom(rows, parts, geometry):
    path = os.path.join(ASSEMBLY, BOM_FILENAME)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=PCBWAY_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(pcbway_rows(rows, parts, geometry))
    return path


def cpl_refs(parts, geometry):
    return {ref for ref in fitted_refs(parts) if geometry[ref]["has_smd"]}


def write_cpl(parts, geometry):
    path = os.path.join(ASSEMBLY, CPL_FILENAME)
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        writer.writeheader()
        for ref in sorted(cpl_refs(parts, geometry), key=bom_audit.natkey):
            item = geometry[ref]
            writer.writerow({"Designator": ref, "Mid X": f'{item["x"]:.4f}mm', "Mid Y": f'{item["y"]:.4f}mm',
                             "Layer": item["layer"], "Rotation": item["rotation"]})
    return path


def assembly_counts(parts, geometry):
    fitted = fitted_refs(parts)
    return {side: sum(geometry[ref]["layer"] == side for ref in fitted) for side in ("Top", "Bottom")}


def edge_parts(geometry, fitted, limit=1.0):
    """Fitted parts whose pad copper comes within `limit` mm of a straight board edge, nearest first."""
    best = {}
    for ref in fitted:
        for pad in geometry[ref]["pads"]:
            for edge, dist in (("left", pad["x"] - pad["sx"] / 2),
                               ("right", BOARD_WIDTH - pad["x"] - pad["sx"] / 2),
                               ("bottom", pad["y"] - pad["sy"] / 2),
                               ("top", BOARD_HEIGHT - pad["y"] - pad["sy"] / 2)):
                if dist < limit and dist < best.get((ref, edge), 99.0):
                    best[(ref, edge)] = dist
    return sorted(((r, e, d) for (r, e), d in best.items()), key=lambda t: t[2])


def pin_one_parts(fitted):
    return [ref for ref in sorted(fitted, key=bom_audit.natkey)
            if re.match(r"(U|Q)[0-9]", ref) or ref in ("X4", "X5")]


def counts_line(counter):
    return ", ".join(f"{n} {k}" for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))


def write_notes(parts, geometry, bom_rows, facts, totals):
    fitted = fitted_refs(parts)
    dnp = sorted(dns_refs_of(parts), key=bom_audit.natkey)
    counts = assembly_counts(parts, geometry)
    rows = pcbway_rows(bom_rows, parts, geometry)
    buy_rows = [row for row in rows if row["Type"] != "DNS"]
    placed_rows = [row for row in buy_rows if row["Type"] != LOOSE_TYPE]
    loose_rows = [row for row in buy_rows if row["Type"] == LOOSE_TYPE]
    loose_text = ", ".join(f"{row['Mfg Part #']} x{row['Qty']}" for row in loose_rows)
    smd = sorted(cpl_refs(parts, geometry), key=bom_audit.natkey)
    n0201 = sum(len(row["_refs"]) for row in bom_rows if row["Footprint"] in ("C0201", "R0201"))
    top0201 = sum(1 for row in bom_rows if row["Footprint"] in ("C0201", "R0201")
                  for ref in row["_refs"] if geometry[ref]["layer"] == "Top")
    u1 = geometry["U1"]["pads"]
    u1_land = max(pad["sx"] for pad in u1)
    u3 = geometry["U3"]["pads"]
    u3_land = max(pad["sx"] for pad in u3)
    mpn = {ref: clean(parts[ref]["params"].get("MANF#")) for ref in parts}
    leds = led_polarity_notes(geometry)
    led_lines = []
    for side in ("WEST", "EAST"):
        refs = sorted((r for r in leds if leds[r][0] == side), key=bom_audit.natkey)
        if refs:
            led_lines.append(f"{', '.join(refs)}: cathode (pad K) on the {side} side "
                             f"(X {', '.join(sorted({f'{leds[r][1]:.2f}' for r in refs}))} mm)")
    ld0_side = ld0_cathode_side(geometry)
    edges = edge_parts(geometry, fitted)
    edge_text = "; ".join(f"{ref} {dist:.2f} mm from the {edge} edge" for ref, edge, dist in edges) or "none"
    pin1 = pin_one_parts(fitted)
    pin1_text = ", ".join(pin1[:-1]) + " and " + pin1[-1]
    x4 = {p["pad"]: p for p in geometry["X4"]["pads"]}
    x4_pin1_side = "west" if x4["1"]["x"] < x4["2"]["x"] else "east"
    side_of = {ref: geometry[ref]["layer"].lower() for ref in parts}

    vip = facts["via_in_pad_summary"]
    thr = facts["through_vias_in_smd_pads_count"]
    thr_list = facts["through_vias_in_smd_pads"]
    thr_refs = sorted({e["ref"] for e in thr_list}, key=bom_audit.natkey)
    thr_ic = [f"{e['ref']}-{e['pad']}" for e in thr_list if re.match(r"U\d", e["ref"]) or e["ref"].startswith("X")]
    lasers_non_u1 = facts["lasers_in_non_u1_smd_pads"]
    u1c = facts["u1_centred_combos"]
    u1_lasers = facts["u1_centred_lasers"]
    off = facts["u1_off_centre_overlaps"]
    l010 = facts["lasers_010"]
    stacked = facts["stacked"]
    hole_gap = facts["min_hole_to_hole"]["gap"]
    hw = facts["hole_wall_to_other_net_track"]
    track_gap = facts["min_spacing_track_to_other_copper"]["gap"]
    by_type_non_u1 = vip["non_u1"]
    exposed_top = facts["tenting"]["Top"]["vias_with_land_in_opening"]
    exposed_bot = facts["tenting"]["Bottom"]["vias_with_land_in_opening"]

    lines = [
        f"{RELEASE_NAME.upper()} - PCBWAY ASSEMBLY NOTES",
        "*** PROVISIONAL RELEASE - NOT FOR PRODUCTION UNTIL CONFIRMED ***",
        f"Release date: {RELEASE_DATE}",
        source_line(),
        f"PCB SHA-256: {sha256(PCB)}",
        "",
        "PROVISIONAL STATUS",
        "This release is provisional. We are waiting for your answers to our enquiry",
        "about laser via-in-pad under a 0.5 mm BGA and 3/3 mil design rules. Please quote",
        "it and raise engineering queries, but do not start production until we have",
        "confirmed the points below in writing. The fabrication notes",
        f"({FAB_NOTES}) restate the full list; the counts below are",
        "this board's current counts (they supersede the counts in the enquiry).",
        f"A. Via-in-pad on U1 (0.5 mm BGA, {len(u1)} round lands of {u1_land:.2f} mm): "
        f"{facts['u1_centred_lasers_total']} laser microvias of 0.10 mm hole / 0.25 mm land centred in "
        f"ball lands ({counts_line(u1_lasers)}), {facts['u1_centred_buried']} buried L3-L4 vias stacked "
        f"under them; {u1c.get('Top-L2', 0)} balls Top-L2 only, {u1c.get('Top-L2 + L2-L3', 0)} Top-L2 + "
        f"L2-L3, {u1c.get('Top-L2 + L2-L3 + L3-L4', 0)} also on a buried via, "
        f"{u1c.get('Top-L2 + L2-L3 + L3-L4 + L4-L5', 0)} full columns to L5; {u1c.get('none', 0)} balls "
        f"have no centred via, and on {off['balls']} of them a via overlaps the land off-centre "
        f"({counts_line(off['by_type'])}). All filled with copper and capped flat.",
        f"B. 0.10 mm laser microvias (0.25 mm land), lasered at 0.10 mm through the 0.1016 mm outer "
        f"and 0.071 mm inner prepregs: {l010['total']} in all, {l010['not_on_ball']} not on a U1 ball "
        f"({l010['not_on_ball_under_u1']} of them under U1). Other lasers 0.15 / 0.30 mm: "
        f"{facts['lasers_015']}. Totals: {facts['laser_total']} lasers, {facts['buried_total']} buried "
        f"L3-L4, {facts['through_total']} through vias (0.20 / 0.35 mm).",
        f"C. 3/3 mil on all six layers: 0.0762 mm tracks; smallest track-to-copper gap {track_gap:.4f} mm; "
        f"one 0.0762 mm track passes between two U1 lands on Top, with the mask opening 1:1 on the lands.",
        f"D. Via-in-pad on other parts: {lasers_non_u1['total']} laser via-to-pad contacts on SMD pads of "
        f"other parts ({counts_line({k + ' mm': v for k, v in lasers_non_u1['by_hole'].items()})} hole), "
        f"filled and capped; {thr['vias']} through vias (0.20 / 0.35 mm) in or on the edge of SMD pads, "
        f"{thr['entries']} via-to-pad contacts ({thr['by_position']['hole in pad']} with the hole inside "
        f"the pad, {thr['by_position']['hole on pad edge']} with the hole on the pad edge, "
        f"{thr['by_position']['land only']} touching with the land only; {thr['by_side']['Top']} on the "
        f"top side, {thr['by_side']['Bottom']} on the bottom), to be resin-plugged and plated over (POFV). "
        f"This includes U1-W8 and U3 balls G9 and H2.",
        f"E. Stacking: {stacked['top_l2_on_l2_l3']} Top-L2 lasers stacked on L2-L3, "
        f"{stacked['l2_l3_on_buried']} L2-L3 and {stacked['l4_l5_on_buried']} L4-L5 lasers on buried "
        f"vias, {stacked['L2_L5_sites']} L2-to-L5 columns ({stacked['L2_L5_full_top_bottom']} running "
        "Top to Bottom); no mechanical L2-L5 drill.",
        f"F. Mechanical vias as drawn (buried 0.15 / 0.27 mm, through 0.20 / 0.35 mm), not enlarged; "
        f"smallest hole-to-hole edge gap {hole_gap:.3f} mm; hole wall to other-net copper "
        f"{hw['laser']['gap']:.3f} mm (laser), {hw['buried']['gap']:.3f} mm (buried), "
        f"{hw['through_via']['gap']:.3f} mm (through); non-plated hole to track "
        f"{facts['npth_to_track']['gap']:.3f} mm.",
        "G. Plane webs: the L2 ground plane keeps copper strips of about 0.09 mm between adjacent "
        "via-in-pad balls under U1 (measured for the enquiry, none under 0.0762 mm; not re-measured on "
        "this board). No connection depends on them: you may clear any strip below your minimum.",
        "If any of A-G changes, this assembly release is re-issued.",
        "",
        "UPLOAD SET",
        "PCBWay fabricates the HDI board and assembles it, Turnkey: PCBWay buys every part.",
        f"- PCB: {FAB_ARCHIVE}",
        f"  (Gerbers incl. the GTP/GBP paste layers, drill files and {FAB_NOTES}),",
        f"  ordered as \"HDI (Buried/blind vias)\" per {FAB_NOTES}.",
        f"- BOM: {BOM_FILENAME} (PCBWay's BOM template columns). Centroid:",
        f"  {CPL_FILENAME} (SMT parts only, both sides in one file).",
        f"- Drawings: {DRAWING_FILENAME.format(side='Top')},",
        f"  {DRAWING_FILENAME.format(side='Bottom')}. These notes.",
        "- Preferred: tick Assembly Service on the HDI quote, so it is one order.",
        "Copy every critical item below into \"Detailed information of assembly\" and",
        "email this file to Service@pcbway.com with the quote number.",
        "",
        "RECOMMENDED FORM SETTINGS (adjust if you decide otherwise)",
        "- Assembly: Service = Turnkey; Assembly side(s) = Both sides.",
        f"- Number of Unique Parts = {len({row['Mfg Part #'] for row in buy_rows})}; "
        f"Number of SMD Parts = {len(smd)};",
        "  Number of BGA/QFP Parts = 2 BGA (U1 CPG236, U3 FBGA-54); also 4 leadless",
        "  parts with exposed pads (U2 QFN-64, U8 QFN-28, U4 WSON-8, U10 TDFN-8);",
        "  Number of Through-Hole Parts = 0 (the X2 headers are shipped loose, not",
        "  soldered; X1's four shell legs in plated slots need hand/selective",
        "  soldering, see below).",
        f"- Loose parts (bought, NOT soldered, packed with each board): {len(loose_rows)} BOM lines, "
        f"X2 = {loose_text}. Put \"X2 headers {loose_text}: buy, do not solder, pack one set with each "
        "board\" in \"Detailed information of assembly\"; they are counted in Number of Unique Parts above.",
        "- Contains sensitive components/parts = Yes. Paste into its box:",
        f"  \"{mpn['U1']}, {mpn['U2']}, {mpn['U3']}, {mpn['U4']},",
        f"  {mpn['U8']}: moisture sensitive, follow the MSL label, bake if floor life",
        f"  is exceeded. {mpn['U1']} (0.5 mm BGA) and {mpn['U3']}",
        "  (0.8 mm FBGA): X-ray every board.\"",
        "- Do you accept alternatives/substitutes made in China = No.",
        "- Number of X-ray test = the number of boards ordered (U1 and U3 on every",
        "  board); please confirm what this field counts.",
        f"- PCB: surface finish ENIG ({u1_land:.2f} mm BGA lands, 0201 pads, filled via-in-pad).",
        f"- Panel (the board is only {BOARD_WIDTH:.2f} x {BOARD_HEIGHT:.2f} mm, corners rounded "
        f"{CORNER_RADIUS:.2f} mm): PCB Board type = Panel by Supplier; panel per PCBWay proposal, "
        "to be approved (see PANEL below). Assembly Board type = Panelized PCBs; Depanel the boards to "
        "delivery = Yes.",
        "",
        "ASSEMBLY SCOPE",
        f"Fitted PCB designators: {len(fitted)}",
        f"Top-side fitted designators: {counts['Top']}",
        f"Bottom-side fitted designators: {counts['Bottom']}",
        f"Physical parts placed per board: {sum(row['_qty'] for row in placed_rows)}; plus "
        f"{sum(row['_qty'] for row in loose_rows)} shipped loose (X2 headers)",
        f"BOM purchase lines: {len(buy_rows)} ({len(placed_rows)} placed + {len(loose_rows)} ship-loose); "
        f"DNS lines: {len(rows) - len(buy_rows)} ({', '.join(dnp)})",
        "Assembly is required on both sides: SMT bottom, SMT top, then hand soldering of X1's shell legs.",
        f"BGAs (top side): U1 {mpn['U1']}, 0.5 mm pitch, {len(u1)} round lands of {u1_land:.2f} mm; "
        f"U3 {mpn['U3']}, 0.8 mm pitch, {len(u3)} round lands of {u3_land:.2f} mm.",
        f"Other 0.5 mm pitch: U2 {mpn['U2']} QFN-64 (top), U8 {mpn['U8']} QFN-28 (bottom), "
        f"U10 {mpn['U10']} TDFN-8 (top).",
        f"Smallest package 0201: {n0201} parts ({top0201} on top).",
        f"Board: {BOARD_WIDTH:.2f} x {BOARD_HEIGHT:.2f} mm (Adafruit Feather outline), six-layer two-step "
        f"sequential HDI, finished {FINISHED_THICKNESS} on the stack you agreed for the earlier Zulu A7 HDI "
        f"order ({FAB_NOTES}).",
        "",
        "VIA-IN-PAD AND ASSEMBLY",
        "Via-in-pad is used throughout this board, by design (see PROVISIONAL STATUS A and D):",
        f"- Mask openings on pads expose {exposed_top} via lands on the top side and {exposed_bot} on the "
        f"bottom (fabrication census). Every laser microvia in a pad must be copper-filled and capped flat, "
        "and every through via in a pad resin-plugged and plated over, so that no via wicks solder or traps "
        "flux. Please confirm the dimple/planarity you guarantee on the capped lands.",
        f"- {len(set(vip['by_ref']))} parts carry a via in or on a pad; through vias in pads touch "
        f"{len(thr_refs)} parts, among them {', '.join(sorted(set(thr_ic), key=bom_audit.natkey))}.",
        "- If you cannot plug and cap a via in a pad, send an engineering query before",
        "  building; do not tent, mask or leave it open.",
        "",
        "PANEL",
        "Panel per PCBWay proposal, to be approved: please send the panel drawing for",
        "approval before production. Constraints for your proposal:",
        f"- The outline has {CORNER_RADIUS:.2f} mm corner radii and four 2.50 mm non-plated holes (X2's corner",
        "  holes), so the board edge needs routing; tabs or V-cut where you advise.",
        "- X1 (USB-C) is flush with the left short edge and X5 (STEMMA QT) faces the",
        "  right short edge: keep both connector mouths clear of rails, tabs and",
        "  break-off residue.",
        f"- Parts whose pad copper is within 1.0 mm of a straight edge: {edge_text}. Confirm the "
        "depanelizer and support fixture cannot touch them.",
        "- X2's 28 header holes run along both long edges: no tab residue over them.",
        "- Depanel with a supported cutter, not by hand-snapping.",
        "- The board has no fiducials. Please put global fiducials on the rails (top",
        "  and bottom) and confirm that they suffice for U1, U3 and the 0201s, or",
        "  propose another alignment method.",
        "",
        "CPL AND ORIENTATION",
        f"{CPL_FILENAME}: Designator, Mid X, Mid Y, Layer (Top/Bottom), Rotation.",
        "It lists every fitted part with SMD pads (X1 included); X2 (shipped loose) and the DNS test pads "
        "are not in it.",
        "If your line needs one file per side, please split it by the Layer column.",
        "- Units are millimetres (\"mm\" suffix). Origin: the board's lower-left",
        f"  corner; the outline runs from 0,0 to {BOARD_WIDTH:.2f},{BOARD_HEIGHT:.2f}.",
        "- Coordinates on both sides are as viewed from the top. Bottom-side X",
        "  values are NOT mirrored.",
        "- Mid X/Y is the centre of each part's pad extents, not the footprint",
        "  origin. For connectors (X1, X3, X4, X5) align the part to its pads in CAM.",
        "- Rotations are the values stored in the final Altium PCB, in degrees",
        "  (0/90/180/270), not converted for bottom-side parts. Please confirm your",
        "  bottom-side convention against the bottom drawing before programming.",
        "- The top drawing is viewed from the top; the bottom drawing is mirrored,",
        "  viewed from the bottom. Red dot = pin 1/A1; red bar = LED cathode (K);",
        "  dashed red label = DNP. Most designators are hidden on the silkscreen and",
        "  U10 and the 0603 LEDs have no silkscreen polarity mark, so the drawings",
        "  and this file are the orientation reference.",
        "If the CPL and a drawing disagree, please send an engineering query.",
        "",
        "SPECIAL COMPONENT INSTRUCTIONS",
        "- Reflow order: bottom side FIRST, top side LAST, so U1, U3 and X1 (all on top)",
        "  see one reflow. The bottom side then rides the second reflow upside down:",
        f"  its heaviest parts are X3 (microSD socket), U8 and the 2520 inductors; support",
        "  or glue them if your process needs it.",
        f"- X1 ({parts['X1']['params'].get('MANF')} {mpn['X1']}, USB-C receptacle, top side): the mouth",
        "  is flush with the left (USB) board edge. We have no HRO datasheet on file",
        "  and give no reflow-cycle limit: please apply HRO's published profile and",
        "  tell us if it limits the number of reflows. The four shell legs go into",
        "  plated 0.60 mm slots MP1-MP4 (two 1.70 mm and two 1.20 mm long); the top",
        "  stencil has no paste on them, so hand- or selective-solder them after",
        "  reflow to full barrel fill (paste-in-hole is acceptable if you prefer).",
        "  The two locating pegs go into 0.65 mm non-plated holes and are not",
        "  soldered.",
        f"- X2 (Feather headers, 1x16 + 1x12, 2.54 mm): SHIPPED LOOSE. Buy {loose_text} (Sullins, "
        "straight male, gold) per the BOM, do NOT solder them, and pack one set with each finished board. "
        "Leave X2's 28 plated holes empty (no paste, no solder, no masking residue in the holes): we solder "
        "the headers ourselves.",
        f"- X5 ({mpn['X5']}, STEMMA QT, top side): the mouth faces the right board",
        "  edge. Pin 1 (GND) is the south contact; check against the top drawing.",
        f"- X4 (JST {mpn['X4']}, top side): pin 1 (the {x4_pin1_side} contact) is battery",
        "  positive, pin 2 is GND.",
        f"- X3 (Hirose {mpn['X3']} microSD, {side_of['X3']} side): per our placement record the card "
        "opening faces the right board edge; please check it against the bottom drawing.",
        f"- U2 ({mpn['U2']}, QFN-64), U4 ({mpn['U4']}, WSON-8) and U10",
        f"  ({mpn['U10']}, TDFN-8): their exposed-pad lands have no net; the paste",
        "  layer prints them 1:1. Please apply your windowpane reduction.",
        f"- U8 ({mpn['U8']}, Analog Devices, bottom side): QFN-28 4 x 5 mm, 0.5 mm",
        "  pitch, exposed pad (pin 29) to GND. Pin 1 per the drawing's red dot.",
        f"- U7 (Semtech {mpn['U7']}, SOT-23-5, bottom side): 1.0 V FPGA core buck.",
        "- Inductors L1, L2, L3, L8, L9 (bottom side) share one 2.5 x 2.0 mm body and",
        "  are usually unmarked: L1, L2, L9 = DFE252012F-2R2M=P2 (2.2 uH), L3 =",
        "  DFE252010P-1R5M=P2 (1.5 uH), L8 = DFE252012F-3R3M=P2 (3.3 uH). Load each",
        "  position from its own reel and check the reels on the first article.",
        "- R116 (Panasonic ERA-1AEB1043C, 0201) is a 104 kohm 0.1 % thin-film part;",
        "  do not substitute a 1 % resistor.",
        "- 0603 LEDs: " + "; ".join(led_lines) + ". The two pairs face opposite ways; the drawings mark "
        "each cathode with a red bar.",
        f"- LD0 ({parts['LD0']['params'].get('MANF')} {mpn['LD0']}, 1.6 x 1.6 mm): cathodes are on the "
        f"{ld0_side} side, the cathode-mark column (board footprint pads 2, 4, 6), anodes opposite "
        "(pads 1, 3, 5). The drawing's red dot marks footprint pad 1, an anode. The land is symmetric, so "
        "a part turned 180 degrees fits but stays dark.",
        *LD0_NUMBERING.get(mpn["LD0"], []),
        f"- BTN and RESET ({mpn['BTN']}, top side): same part twice.",
        "- JP3 and JP4 are intentional DNS JTAG test-pad positions (three 1.0 mm SMD",
        "  pads each, bottom side): no part. Please remove their six apertures from",
        "  the bottom stencil (tinned pads are acceptable if you cannot).",
        f"- Verify pin 1/A1 against the drawings on {pin1_text}.",
        "- Stencil from the GTP/GBP layers, whose apertures are 1:1 with copper.",
        "  Please apply your house reductions, in particular: U1 0.25 mm round",
        "  apertures (0.08 mm or thinner stencil suggested, paste that releases",
        "  them reliably); U3 0.40 mm lands; the exposed pads of U2, U4, U8 and U10.",
        "",
        "SOURCING",
        "Please buy by the Manufacturer and Mfg Part # columns; every purchase line",
        "carries an exact manufacturer part number. Nothing is consigned.",
        "- Make no substitution without our written approval. Report any line with",
        "  no stock, a lifecycle problem or an ambiguous MPN as an engineering query.",
        f"- U1 {mpn['U1']}: AMD-authorized distributors only (e.g. Digi-Key,",
        "  Mouser, Avnet); no local, broker or open-market stock. Ask us first if",
        "  none can supply it.",
        f"- U2 {mpn['U2']}: FTDI-authorized distributors only (FTDI clones exist).",
        f"  It and U3 {mpn['U3']} have had thin stock: please report availability",
        "  with the quote.",
        "- The BOM's last column carries per-line instructions; please follow them.",
        "",
        "QUALITY AND TEST",
        "- Lead-free (SAC) solder process.",
        "- Moisture-sensitive parts: U1, U2, U3, U4 and U8 (and any reel with an MSL",
        "  label). Follow their MSL labels for storage, floor life and bake.",
        "- X-ray U1 and U3 on every board and include it in the quotation.",
        "- AOI on both sides; workmanship to IPC-A-610 Class 2.",
        "- No firmware programming or functional test is included unless separately",
        "  quoted and supplied with a test procedure and programming image.",
        "- First article: please send photos of BOTH sides and the U1 and U3 X-ray",
        "  images, and wait for our approval before building the rest.",
        "",
        "REQUIRED ORDER REVIEW",
        "Before releasing the order, please confirm in writing:",
        "- the answers to the PROVISIONAL STATUS points A-G;",
        "- the HDI fabrication quote, with turnkey assembly on the same order;",
        "- filling/capping of every via in a pad (lasers) and plugging/plating over of",
        "  the through vias in pads;",
        "- the panel drawing and rail fiducials;",
        "- your bottom-side CPL rotation convention;",
        "- authorized sourcing for U1 and U2, and any lines with no stock;",
        "- hand soldering of X1's four shell legs; X2 holes left empty, X2 headers",
        "  bought and shipped loose with each board;",
        "- the stencil apertures for U1, U3 and the exposed pads, and X-ray of U1 and",
        "  U3 (and what the Number of X-ray test field counts);",
        "- polarity and pin 1 against both drawings, then first-article approval.",
    ]
    wrapped = []
    for line in lines:
        if len(line) <= 86:
            wrapped.append(line)
            continue
        lead = len(line) - len(line.lstrip(" "))
        stripped = line.lstrip()
        follow = " " * (lead + (2 if stripped.startswith("- ") else 3 if re.match(r"[A-G]\. ", stripped) else 0))
        wrapped += textwrap.wrap(line, 86, initial_indent="", subsequent_indent=follow, break_on_hyphens=False)
    path = os.path.join(ASSEMBLY, NOTES_FILENAME)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(wrapped) + "\n")
    return path


# --------------------------------------------------------------- drawings --
def board_to_page(x, y, region, plot, side):
    x0, y0, x1, y1 = region
    scale = min(plot.width / (x1 - x0), plot.height / (y1 - y0))
    left = plot.x0 + (plot.width - (x1 - x0) * scale) / 2
    top = plot.y0 + (plot.height - (y1 - y0) * scale) / 2
    source_x = x1 - (x - x0) if side == "Bottom" else x
    return left + (source_x - x0) * scale, top + (y1 - y) * scale, scale


def label(page, centre, text, font_size, colour, opacity=0.82):
    width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
    page.draw_rect(fitz.Rect(centre[0] - width / 2 - 1.2, centre[1] - font_size * 0.75,
                             centre[0] + width / 2 + 1.2, centre[1] + font_size * 0.55),
                   color=None, fill=(1, 1, 1), fill_opacity=opacity)
    page.insert_text((centre[0] - width / 2, centre[1] + font_size * 0.30), text, fontsize=font_size,
                     fontname="helv", color=colour)


def draw_assembly_page(doc, side, region, title, parts, geometry):
    page = doc.new_page(width=1190.55, height=841.89)
    page.insert_text((42, 37), f"{RELEASE_NAME} - {side} Assembly Drawing - {title} - PROVISIONAL",
                     fontsize=18, fontname="hebo", color=(0.08, 0.10, 0.14))
    view_note = "MIRRORED - viewed from bottom" if side == "Bottom" else "Viewed from top"
    page.insert_text((42, 57), f"{view_note}; dimensions and coordinate grid in millimetres; "
                     f"release {RELEASE_DATE}, provisional pending PCBWay's via-in-pad answers",
                     fontsize=9, color=(0.25, 0.28, 0.32))
    plot = fitz.Rect(52, 78, page.rect.width - 42, page.rect.height - 58)
    x0, y0, x1, y1 = region

    p0 = board_to_page(x0, y0, region, plot, side)
    p1 = board_to_page(x1, y1, region, plot, side)
    board_rect = fitz.Rect(min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1]))
    page.draw_rect(board_rect, color=(0.08, 0.10, 0.14), fill=(0.97, 0.98, 0.98), width=1.2)

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

    side_refs = [ref for ref in parts if geometry[ref]["layer"] == side
                 and x0 <= geometry[ref]["x"] <= x1 and y0 <= geometry[ref]["y"] <= y1]
    if side == geometry["X2"]["layer"] and "X2" not in side_refs:
        side_refs.append("X2")               # X2's centre is the board centre: show it on both detail pages
    side_ref_set = set(side_refs)

    for item in geometry.values():
        for pad in item["pads"]:
            through_hole = pad["hole"] > 1e-6
            if not through_hole and (item["ref"] not in side_ref_set or pad["layer"] != side):
                continue
            if not (x0 <= pad["x"] <= x1 and y0 <= pad["y"] <= y1):
                continue
            cx, cy, scale = board_to_page(pad["x"], pad["y"], region, plot, side)
            width = max(pad["sx"] * scale, 0.8)
            height = max(pad["sy"] * scale, 0.8)
            fill = (0.72, 0.77, 0.82) if through_hole else (0.42, 0.62, 0.78)
            if pad["round"] and abs(width - height) < 0.25:
                page.draw_circle((cx, cy), width / 2, color=(0.22, 0.30, 0.38), fill=fill, width=0.35)
            else:
                page.draw_rect(fitz.Rect(cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2),
                               color=(0.22, 0.30, 0.38), fill=fill, width=0.35)
            if through_hole:
                page.draw_circle((cx, cy), max(min(pad["hole"], pad["sx"], pad["sy"]) * scale / 2, 0.45),
                                 color=(0.2, 0.2, 0.2), fill=(1, 1, 1), width=0.3)

    detail = (x1 - x0) < BOARD_WIDTH - 1
    font_size = 7.0 if detail else 5.2
    for ref in sorted(side_refs, key=bom_audit.natkey):
        item = geometry[ref]
        dnp = not is_fitted(ref, parts)
        if ref == "X2":
            rows = sorted({round(p["y"], 2) for p in item["pads"] if p["hole"] > 1e-6 and p["pad"]})
            for row_y in rows:
                xs = [p["x"] for p in item["pads"] if p["pad"] and round(p["y"], 2) == row_y]
                n = len(xs)
                cx = min(max(sum(xs) / n, x0 + 6), x1 - 6)
                ly = row_y + (1.6 if row_y < BOARD_HEIGHT / 2 else -1.6)
                pos = board_to_page(cx, ly, region, plot, side)
                label(page, pos, f"X2 holes left empty - headers shipped loose ({n}-pin row)", font_size,
                      (0.55, 0.12, 0.10), 0.86)
            continue
        bx0, by0, bx1, by1 = item["bbox"]
        c0 = board_to_page(bx0, by0, region, plot, side)
        c1 = board_to_page(bx1, by1, region, plot, side)
        box = fitz.Rect(min(c0[0], c1[0]), min(c0[1], c1[1]), max(c0[0], c1[0]), max(c0[1], c1[1]))
        page.draw_rect(box, color=(0.60, 0.60, 0.60) if dnp else (0.10, 0.40, 0.24), width=0.55,
                       dashes="[2 2]" if dnp else None)
        label(page, ((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2), f"DNP {ref}" if dnp else ref,
              font_size, (0.55, 0.12, 0.10) if dnp else (0.05, 0.07, 0.09))
        pin_one = next((p for p in item["pads"] if p["pad"] == "1"),
                       next((p for p in item["pads"] if p["pad"] == "A1"), None))
        if pin_one is not None and not dnp:
            mx, my, _ = board_to_page(pin_one["x"], pin_one["y"], region, plot, side)
            page.draw_circle((mx, my), 2.1 if detail else 1.35, color=(0.78, 0.08, 0.08),
                             fill=(0.92, 0.15, 0.12), width=0.4)
        cathode = next((p for p in item["pads"] if p["pad"] == "K"), None)
        if pin_one is None and cathode is not None:
            mx, my, scale = board_to_page(cathode["x"], cathode["y"], region, plot, side)
            half_w = 1.0 if detail else 0.7
            half_h = max(cathode["sy"] * scale / 2, 2.0 if detail else 1.3)
            page.draw_rect(fitz.Rect(mx - half_w, my - half_h, mx + half_w, my + half_h),
                           color=(0.78, 0.08, 0.08), fill=(0.92, 0.15, 0.12), width=0.3)

    page.insert_text((52, page.rect.height - 28),
                     "Red dot = pin 1/A1. Red bar = LED cathode (pad K). Dashed red label = DNP. "
                     "Verify every rotation and polarity in PCBWay's engineering review.",
                     fontsize=8, color=(0.24, 0.27, 0.31))
    return set(side_refs)


def write_drawing(side, parts, geometry):
    output = os.path.join(ASSEMBLY, DRAWING_FILENAME.format(side=side))
    document = fitz.open()
    regions = [
        ((0.0, 0.0, BOARD_WIDTH, BOARD_HEIGHT), "Overview"),
        ((0.0, 0.0, 27.5, BOARD_HEIGHT), "West Detail"),
        ((23.3, 0.0, BOARD_WIDTH, BOARD_HEIGHT), "East Detail"),
    ]
    shown = set()
    for region, title in regions:
        shown.update(draw_assembly_page(document, side, region, title, parts, geometry))
    document.set_metadata({
        "title": f"{RELEASE_NAME} {side} Assembly Drawing (provisional)",
        "author": "Asar Feather project", "subject": "PCBWay assembly reference",
        "keywords": "Asar Feather, PCBWay, assembly, pick and place",
        "creator": "Asar Feather assembly generator", "producer": "PyMuPDF",
        "creationDate": f"D:{RELEASE_DATE.replace('-', '')}000000-07'00'",
    })
    document.save(output, garbage=4, deflate=True)
    document.close()
    return output, shown


# ------------------------------------------------------------- validation --
def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def validate(outputs, parts, geometry, bom_rows, drawing_refs):
    fitted = fitted_refs(parts)
    loose = loose_refs(parts)
    dnp = dns_refs_of(parts)
    if fitted & loose or dnp & loose or fitted | loose | dnp != set(parts):
        raise ValueError("fitted / loose / DNS sets overlap or miss a part")
    bom_all = read_csv(outputs["bom"])
    if list(bom_all[0].keys()) != PCBWAY_COLUMNS:
        raise ValueError(f"PCBWay BOM columns changed: {list(bom_all[0].keys())}")
    loose_rows = [row for row in bom_all if row["Type"] == LOOSE_TYPE]
    buy = [row for row in bom_all if row["Type"] not in ("DNS", LOOSE_TYPE)]
    dns_refs = {row["Designator"] for row in bom_all if row["Type"] == "DNS"}
    if dns_refs != dnp:
        raise ValueError(f"BOM DNS rows {sorted(dns_refs)} != DNP parts {sorted(dnp)}")
    want_loose = sorted((ref, mpn, maker, str(qty)) for ref, lines in LOOSE_PARTS.items() if ref in loose
                        for mpn, maker, qty, _ in lines)
    got_loose = sorted((row["Designator"], row["Mfg Part #"], row["Manufacturer"], row["Qty"]) for row in loose_rows)
    if got_loose != want_loose:
        raise ValueError(f"ship-loose BOM lines {got_loose} != LOOSE_PARTS {want_loose}")
    for row in loose_rows:
        if int(row["Qty"]) < 1 or "SHIP LOOSE - do not solder, pack with each board" not in \
                row["Your Instructions / Notes"]:
            raise ValueError(f"ship-loose line without quantity or instruction: {row}")
    for row in buy:
        refs = row["Designator"].split(",")
        if not row["Mfg Part #"] or not row["Manufacturer"]:
            raise ValueError(f"PCBWay BOM line without manufacturer or MPN: {row}")
        if row["Type"] not in ("SMD", "thru-hole"):
            raise ValueError(f"invalid PCBWay Type: {row}")
        if int(row["Qty"]) != len(refs) or len(set(refs)) != len(refs):
            raise ValueError(f"PCBWay BOM quantity != designator count: {row}")
    bom_refs = [ref for row in buy for ref in row["Designator"].split(",")]
    if len(bom_refs) != len(set(bom_refs)):
        raise ValueError("a designator is on two BOM lines")
    if set(bom_refs) != fitted:
        raise ValueError(f"BOM designator mismatch: missing={sorted(fitted - set(bom_refs))} "
                         f"extra={sorted(set(bom_refs) - fitted)}")

    cpl_rows = read_csv(outputs["cpl"])
    cpl_seen = [row["Designator"] for row in cpl_rows]
    expected = cpl_refs(parts, geometry)
    if len(cpl_seen) != len(set(cpl_seen)):
        raise ValueError("duplicate CPL designators")
    if set(cpl_seen) != expected:
        raise ValueError(f"CPL designator mismatch: missing={sorted(expected - set(cpl_seen))} "
                         f"extra={sorted(set(cpl_seen) - expected)}")
    smd_fitted = {ref for ref in fitted if geometry[ref]["has_smd"]}
    if smd_fitted - set(cpl_seen):
        raise ValueError(f"fitted SMD parts missing from the CPL: {sorted(smd_fitted - set(cpl_seen))}")
    if dnp & set(cpl_seen):
        raise ValueError("DNP designators leaked into the CPL")
    if loose & set(cpl_seen):
        raise ValueError("ship-loose designators leaked into the CPL")
    for row in cpl_rows:
        ref = row["Designator"]
        x = float(row["Mid X"].removesuffix("mm"))
        y = float(row["Mid Y"].removesuffix("mm"))
        if not (0 <= x <= BOARD_WIDTH and 0 <= y <= BOARD_HEIGHT):
            raise ValueError(f"CPL coordinate is outside the board: {row}")
        if abs(x - geometry[ref]["x"]) > 5e-5 or abs(y - geometry[ref]["y"]) > 5e-5:
            raise ValueError(f"CPL position differs from the PcbDoc: {row}")
        if row["Layer"] != geometry[ref]["layer"] or int(row["Rotation"]) != geometry[ref]["rotation"]:
            raise ValueError(f"CPL row differs from the PcbDoc: {row}")
        if int(row["Rotation"]) not in {0, 90, 180, 270}:
            raise ValueError(f"invalid CPL rotation: {row}")
    cpl_set = set(cpl_seen)
    for row in buy:
        refs = row["Designator"].split(",")
        if row["Type"] == "SMD" and not set(refs) <= cpl_set:
            raise ValueError(f"BOM line does not match its CPL rows: {row}")
        if row["Type"] == "thru-hole" and set(refs) & cpl_set:
            raise ValueError(f"through-hole part in the CPL: {row}")

    expected_by_side = {side: {ref for ref in parts if geometry[ref]["layer"] == side} for side in ("Top", "Bottom")}
    for side in ("Top", "Bottom"):
        if drawing_refs[side] != expected_by_side[side]:
            raise ValueError(f"{side} drawing coverage mismatch: "
                             f"missing={sorted(expected_by_side[side] - drawing_refs[side])}")
        document = fitz.open(outputs[side.lower()])
        if document.page_count != 3:
            raise ValueError(f"{side} drawing has {document.page_count} pages, expected 3")
        text = "\n".join(page.get_text() for page in document)
        document.close()
        for ref in expected_by_side[side]:
            if re.search(rf"(?<![A-Za-z0-9$]){re.escape(ref)}(?![A-Za-z0-9])", text) is None:
                raise ValueError(f"{ref} is missing from {side} drawing text")

    stale = {row["Mfg Part #"] for row in bom_all} & STALE_MPNS
    if stale or STALE_REFS & set(parts):
        raise ValueError(f"removed parts reached the release: {sorted(stale)} {sorted(STALE_REFS & set(parts))}")
    if len(pcbway_rows(bom_rows, parts, geometry)) != len(bom_all):
        raise ValueError("BOM row count changed during serialization")

    with open(outputs["notes"], encoding="utf-8") as handle:
        notes = handle.read()
    if max(map(len, notes.splitlines())) > 88:
        raise ValueError("a notes line is over 88 characters")
    if "PROVISIONAL" not in notes.splitlines()[1]:
        raise ValueError("the notes do not open with the PROVISIONAL banner")
    for path in outputs.values():
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise ValueError(f"missing or empty output: {path}")
        with open(path, "rb") as handle:
            blob = handle.read()
        if path.endswith(".pdf"):
            document = fitz.open(path)
            blob = "\n".join(page.get_text() for page in document).encode()
            document.close()
        for word in FORBIDDEN_TEXT:
            if word.encode() in blob:
                raise ValueError(f"{os.path.basename(path)} contains '{word}'")


def write_zip(outputs):
    path = os.path.join(ASSEMBLY, ASSEMBLY_ARCHIVE)
    stamp = tuple(int(v) for v in RELEASE_DATE.split("-")) + (0, 0, 0)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for key in ("bom", "cpl", "notes", "top", "bottom"):
            info = zipfile.ZipInfo(os.path.basename(outputs[key]), date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(outputs[key], "rb") as handle:
                archive.writestr(info, handle.read())
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if archive.testzip() is not None or len(names) != 5 or any(w in n for n in names for w in FORBIDDEN_TEXT):
            raise ValueError(f"bad assembly ZIP: {path}")
    return path


def main():
    configure()
    os.makedirs(ASSEMBLY, exist_ok=True)
    board_components, pads = read_board()
    board_refs = set(board_components) - ARTWORK_REFS
    parts = schematic_parts()
    if board_refs != set(parts):
        raise ValueError(f"schematic/PCB mismatch: missing PCB={sorted(set(parts) - board_refs)}, "
                         f"extra PCB={sorted(board_refs - set(parts))}")
    geometry = component_geometry(board_components, pads)
    facts, totals = load_fab_facts()
    check_mpns(parts)
    check_loose(parts)
    bom_rows = make_bom(parts, geometry)

    outputs = {
        "bom": write_bom(bom_rows, parts, geometry),
        "cpl": write_cpl(parts, geometry),
        "notes": write_notes(parts, geometry, bom_rows, facts, totals),
    }
    outputs["top"], top_refs = write_drawing("Top", parts, geometry)
    outputs["bottom"], bottom_refs = write_drawing("Bottom", parts, geometry)
    validate(outputs, parts, geometry, bom_rows, {"Top": top_refs, "Bottom": bottom_refs})
    outputs["zip"] = write_zip(outputs)

    fitted = fitted_refs(parts)
    counts = assembly_counts(parts, geometry)
    buy = [r for r in read_csv(outputs["bom"]) if r["Type"] != "DNS"]
    loose = [r for r in buy if r["Type"] == LOOSE_TYPE]
    dnp = sorted(dns_refs_of(parts), key=bom_audit.natkey)
    print("ASSEMBLY_RELEASE PASS (PROVISIONAL)")
    print(f"PCB md5 {md5(PCB)}")
    print(f"{len(buy)} BOM purchase lines ({len(buy) - len(loose)} placed + {len(loose)} ship-loose: "
          f"{', '.join(r['Designator'] + ' ' + r['Mfg Part #'] + ' x' + r['Qty'] for r in loose)}), "
          f"{len(dnp)} DNS ({', '.join(dnp)}), "
          f"{len(fitted)} fitted designators ({counts['Top']} top / {counts['Bottom']} bottom), "
          f"{len(read_csv(outputs['cpl']))} CPL rows")
    for ref, was, mpn, maker in sorted(MANUFACTURER_FIXES, key=lambda t: bom_audit.natkey(t[0])):
        print(f"MANF corrected from the MPN: {ref} {mpn}: schematic '{was}' -> '{maker}'")
    for refs, text in MPN_PROBLEMS:
        print(f"MPN PROBLEM: {','.join(refs)}: {text}")
    for key in ("bom", "cpl", "notes", "top", "bottom", "zip"):
        path = outputs[key]
        print(f"{os.path.basename(path)} | {os.path.getsize(path)} bytes | SHA256 {sha256(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
