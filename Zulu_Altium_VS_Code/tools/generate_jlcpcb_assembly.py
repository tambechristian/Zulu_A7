# -*- coding: utf-8 -*-
"""Generate and validate a Zulu A7 assembly release.

The BOM is read from the current Altium schematics. Component locations,
rotations, layers, and pad geometry are read from the current PcbDoc.

    python tools/generate_jlcpcb_assembly.py                      (PCBWay, the default since 2026-10-07)
    python tools/generate_jlcpcb_assembly.py --assembler jlcpcb   (the old JLCPCB release files)
    python tools/generate_jlcpcb_assembly.py --pcb <PcbDoc> \
        --assembly-dir <output-dir> --release-prefix <filename-prefix> \
        --release-name <drawing-title> --assembler-neutral

PCBWay mode writes Zulu_A7_PCBWay_BOM.csv in PCBWay's BOM template columns (MPN identities, DNS rows,
X2 split into its two strip part numbers, per-line instructions), Zulu_A7_PCBWay_CPL.csv with the SMT
parts only (PCBWay's centroid rule), and PCBWay-specific assembly notes.
"""

import argparse
import csv
import hashlib
import os
import re
import struct
import subprocess
import sys
import textwrap
from collections import defaultdict

import olefile
import pymupdf as fitz

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.join(ROOT, "Imported zulu_a7.PrjPcb")
PCB = os.path.join(PROJECT, "zulu_a7.PcbDoc")
ASSEMBLY = os.path.join(ROOT, "assembly")
BOM_FILENAME = "Zulu_A7_PCBWay_BOM.csv"
CPL_FILENAME = "Zulu_A7_PCBWay_CPL.csv"
NOTES_FILENAME = "Zulu_A7_Assembly_Notes.txt"
DRAWING_FILENAME = "Zulu_A7_Assembly_Drawing_{side}.pdf"
RELEASE_NAME = "Zulu A7"
ASSEMBLER = "pcbway"
ASSEMBLER_NEUTRAL = False
FAB_ARCHIVE = "Zulu_A7_PCBWay_Fabrication_2026-10-07.zip"

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


def source_line():
    """'Source commit: <HEAD>' when the PCB is committed as is, otherwise say it is a working copy after HEAD."""
    dirty = subprocess.run(
        ["git", "-C", os.path.dirname(PCB), "status", "--porcelain", "--", os.path.basename(PCB)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        return f"Source: working copy after commit {git_commit()[:7]} (the PCB SHA-256 below identifies it)"
    return f"Source commit: {git_commit()}"


def configure():
    global PCB
    global ASSEMBLY
    global BOM_FILENAME
    global CPL_FILENAME
    global NOTES_FILENAME
    global DRAWING_FILENAME
    global RELEASE_NAME
    global ASSEMBLER_NEUTRAL
    global ASSEMBLER
    global RELEASE_DATE

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcb", default=PCB, help="PcbDoc used for placement data")
    parser.add_argument(
        "--assembly-dir", default=ASSEMBLY, help="directory for generated outputs"
    )
    parser.add_argument(
        "--release-prefix",
        help="filename prefix; omitted to preserve the production release names",
    )
    parser.add_argument("--release-name", default=RELEASE_NAME)
    parser.add_argument("--release-date", default=RELEASE_DATE)
    parser.add_argument(
        "--assembler",
        choices=("pcbway", "jlcpcb", "neutral"),
        default="pcbway",
        help="assembler the release is written for (default pcbway)",
    )
    parser.add_argument(
        "--assembler-neutral",
        action="store_true",
        help="same as --assembler neutral: a separate HDI-capable assembler",
    )
    args = parser.parse_args()

    PCB = os.path.abspath(args.pcb)
    ASSEMBLY = os.path.abspath(args.assembly_dir)
    RELEASE_NAME = args.release_name
    RELEASE_DATE = args.release_date
    ASSEMBLER = "neutral" if args.assembler_neutral else args.assembler
    ASSEMBLER_NEUTRAL = ASSEMBLER == "neutral"
    if ASSEMBLER != "pcbway":
        BOM_FILENAME = "Zulu_A7_JLCPCB_BOM.csv"
        CPL_FILENAME = "Zulu_A7_JLCPCB_CPL.csv"
    if args.release_prefix:
        BOM_FILENAME = f"{args.release_prefix}_BOM.csv"
        CPL_FILENAME = f"{args.release_prefix}_CPL.csv"
        NOTES_FILENAME = f"{args.release_prefix}_Assembly_Notes.txt"
        DRAWING_FILENAME = f"{args.release_prefix}_Assembly_Drawing_{{side}}.pdf"
    if not os.path.isfile(PCB):
        parser.error(f"PCB does not exist: {PCB}")


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


PCBWAY_COLUMNS = [
    "Item #",
    "Designator",
    "Qty",
    "Manufacturer",
    "Mfg Part #",
    "Description / Value",
    "Package/Footprint",
    "Type",
    "Your Instructions / Notes",
]

# Footprint names that are not package names, spelled out for PCBWay's buyers.
PACKAGE_NAMES = {
    "742C043": "CTS 742C043: 2-element concave resistor array, 1.6 x 1.6 mm, 0.8 mm pitch",
    "742C083": "CTS 742C083: 4-element concave resistor array, 3.2 x 1.6 mm, 0.8 mm pitch",
    "742C163": "CTS 742C163: 8-element concave resistor array, 6.4 x 1.6 mm, 0.8 mm pitch",
    "32X25": "3.2 x 2.5 mm SMD oscillator",
    "IND2520": "2520 SMD inductor, 2.5 x 2.0 mm",
    "IND0603": "0603 SMD ferrite bead",
    "LED0603": "0603 SMD LED",
    "EVERLIGHT-19-337": "1.6 x 1.6 mm SMD RGB LED (Everlight 19-337 land)",
    "XC7A35T-CPG236": "CPG236 BGA, 10 x 10 mm, 0.5 mm pitch",
    "FT2232HL-LQFP64": "LQFP-64, 10 x 10 mm body, 0.5 mm pitch",
    "TSOPII-54": "TSOP-II-54, 400 mil, 0.8 mm pitch",
    "SOIC-8_208MIL": "SOIC-8, 208 mil (5.3 mm) body",
    "SPI-8_SOIC_150": "SOIC-8, 150 mil (3.9 mm) body",
    "VQFN16-3X3-RGT": "VQFN-16 (RGT), 3 x 3 mm, 0.5 mm pitch, exposed pad",
    "MOLEX-105017-0001": "Molex 105017 micro-USB-B, SMT with plated slots and holes",
    "JST-B2B-PH-SM4-TB": "JST PH 2-pin top-entry SMT header",
    "DM3D-SF": "Hirose DM3D microSD socket, SMT",
    "2X06": "2x6 2.54 mm female header, through-hole",
    "PTS810": "C&K PTS810 SMT tactile switch, 4.2 x 3.2 mm",
}

# Per-MPN instructions written into the BOM line itself, where PCBWay's buyer reads them.
PCBWAY_LINE_NOTES = {
    "XC7A35T-1CPG236C": (
        "Buy only from an AMD-authorized distributor (e.g. Digi-Key, Mouser, Avnet); "
        "no local, broker or open-market stock. 0.5 mm BGA: X-ray every board. "
        "Moisture sensitive: follow the MSL label."
    ),
    "FT2232HL-REEL": (
        "Buy only from an FTDI-authorized distributor (FTDI clones exist); no broker "
        "stock. Moisture sensitive: follow the MSL label."
    ),
    "AS4C32M16SB-7TCN": "Moisture sensitive: follow the MSL label.",
    "W25Q128JVSIQ": "Moisture sensitive: follow the MSL label.",
    "BQ24232RGTR": "Moisture sensitive: follow the MSL label.",
    "SC189ZSKTRT": (
        "U5 = 3.3 V. U5/U6/U7 are look-alike SOT23-5 bucks: check reel and marking at "
        "each position. A U5/U7 swap puts 3.3 V on the FPGA core."
    ),
    "SC189LSKTRT": "U6 = 1.8 V. Look-alike of U5/U7: check reel and marking.",
    "SC189ASKTRT": "U7 = 1.0 V FPGA core. Look-alike of U5/U6: check reel and marking.",
    "EAST1616RGBA8": (
        "Polarity: cathodes are pads 2, 4, 6 on the WEST side; anodes 1, 3, 5 on the "
        "east side (opposite to LD1-LD5). The drawing's red dot marks pad 1, an anode."
    ),
    "105017-0001": (
        "Rated for ONE reflow: place in the last (top) reflow. Shell stakes in plated "
        "slots MS1/MS2: hand-solder from the bottom after reflow (see notes)."
    ),
    "PPTC062LFBN-RC": "Top-side through-hole: hand or selective solder after both reflows. Pin 1 = square pad.",
    "B2B-PH-SM4-TB(LF)(SN)": "Polarity: pin 1 (west contact) is battery +, pin 2 is GND.",
}

# Buyer-facing descriptions where the schematic SPEC is mostly design commentary.
DESCRIPTION_OVERRIDES = {
    "ECS-3225SMV-120-FP-TR": "12 MHz HCMOS SMD oscillator, +-10 ppm, 1.62-3.63 V, 3.2 x 2.5 mm",
    "BQ24232RGTR": "Single-cell Li-ion/LiPo linear charger with power path, VQFN-16 3 x 3 mm (RGT)",
    "742C163101JP": "8 x 100 ohm +-5% isolated concave resistor array, 6.4 x 1.6 mm, 0.8 mm pitch",
    "MSASJ105BB5475MFNA01": "4.7uF X5R 6.3V +-20% 0402 MLCC, 0.65 mm max",
}

X2_STRIPS = [
    ("PRPC009SAAN-RC", "1x9 male breakaway header strip, 2.54 mm pitch, 0.64 mm square pins, gold flash",
     "1x9 through-hole strip", "X2 pins 1-9 and 21-29."),
    ("PRPC011SAAN-RC", "1x11 male breakaway header strip, 2.54 mm pitch, 0.64 mm square pins, gold flash",
     "1x11 through-hole strip", "X2 pins 10-20 and 30-40."),
]
X2_NOTE = (
    "Underside THT: housing on the BOTTOM side, the short post end (about 3 mm) up "
    "through the board, the long mating end pointing down. Hand-solder on top after "
    "both reflows and after depanel. 2 per board."
)


def led_polarity_notes(geometry):
    """For the two-pad A/K LEDs: (side of pad K, X of K, X of A), from the PCB."""
    notes = {}
    for ref, item in geometry.items():
        names = {pad["pad"]: pad for pad in item["pads"]}
        if set(names) == {"A", "K"}:
            side = "EAST" if names["K"]["x"] > names["A"]["x"] else "WEST"
            notes[ref] = (side, names["K"]["x"], names["A"]["x"])
    return notes


def buyer_spec(spec):
    """The schematic SPEC without the design commentary some parts carry (calculations after ' -- ',
    sourcing history, datasheet page references), capped near 160 characters at a clause boundary."""
    spec = clean(spec).split(" -- ")[0]
    kept = []
    for clause in spec.split("; "):
        if re.search(r"replace|flagged|sheet p\d|section \d|DS_|same die|typo|alias|successor|"
                     r"obsolete|catalog|on 20\d\d-\d\d", clause):
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
        if refs == ["X2"]:
            for strip, desc, pkg, pins in X2_STRIPS:
                out.append({
                    "Designator": "X2", "Qty": "2", "Manufacturer": "Sullins", "Mfg Part #": strip,
                    "Description / Value": desc, "Package/Footprint": pkg, "Type": "thru-hole",
                    "Your Instructions / Notes": f"{pins} {X2_NOTE}", "_refs": refs, "_qty": 2,
                })
            continue
        note = PCBWAY_LINE_NOTES.get(mpn, "")
        led = [leds[ref] for ref in refs if ref in leds]
        if led:
            sides = {side for side, _, _ in led}
            assert len(sides) == 1, refs
            side = sides.pop()
            note = (f"Polarity: cathode = pad K on the {side} side (X {led[0][1]:.2f} mm), "
                    f"anode = pad A (X {led[0][2]:.2f} mm). All face the same way.")
        out.append({
            "Designator": row["Designator"], "Qty": row["Qty per PCB"], "Manufacturer": row["Manufacturer"],
            "Mfg Part #": mpn, "Description / Value": description, "Package/Footprint": package, "Type": kind,
            "Your Instructions / Notes": note, "_refs": refs, "_qty": int(row["Qty per PCB"]),
        })
    for ref, component in sorted(parts.items(), key=lambda kv: bom_audit.natkey(kv[0])):
        if component["params"].get("DNS") != "Yes":
            continue
        out.append({
            "Designator": ref, "Qty": "0", "Manufacturer": "", "Mfg Part #": "none (do not populate)",
            "Description / Value": buyer_spec(component["params"].get("SPEC")) or clean(component["params"].get("Comment")),
            "Package/Footprint": component["fp"] or geometry[ref]["footprint"], "Type": "DNS",
            "Your Instructions / Notes": "DNS - do not populate, do not buy. Bare plated holes: no paste, no solder.",
            "_refs": [ref], "_qty": 0,
        })
    for item, row in enumerate(out, 1):
        row["Item #"] = str(item)
    return out


def write_bom(rows, parts=None, geometry=None):
    if ASSEMBLER == "pcbway":
        path = os.path.join(ASSEMBLY, BOM_FILENAME)
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=PCBWAY_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(pcbway_rows(rows, parts, geometry))
        return path
    path = os.path.join(ASSEMBLY, BOM_FILENAME)
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
    path = os.path.join(ASSEMBLY, CPL_FILENAME)
    columns = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    fitted = [
        ref
        for ref, component in parts.items()
        if component["params"].get("DNS") != "Yes"
        and (ASSEMBLER != "pcbway" or geometry[ref]["has_smd"])   # PCBWay: SMT parts only
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


def u1_via_census(geometry):
    """Top-side vias in U1's land field: (through at ball sites, through other, laser interstitial,
    laser at ball sites, laser other, vias in a land). Read with altium_monkey from the same PcbDoc."""
    import math
    from altium_monkey import AltiumPcbDoc
    lands = [(p["x"], p["y"]) for p in geometry["U1"]["pads"]]
    pitch = 0.5
    gx0 = min(x for x, _ in lands); gy0 = min(y for _, y in lands)
    x0 = gx0 - 0.3; x1 = max(x for x, _ in lands) + 0.3
    y0 = gy0 - 0.3; y1 = max(y for _, y in lands) + 0.3
    land_cells = {(round((x - gx0) / pitch), round((y - gy0) / pitch)) for x, y in lands}

    def frac(v):
        return v - math.floor(v)

    board = AltiumPcbDoc.from_file(PCB)
    census = defaultdict(int)
    for via in board.vias:
        x, y = via.x_mils * 0.0254, via.y_mils * 0.0254
        if via.layer_start != 1 or not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        fx, fy = (x - gx0) / pitch, (y - gy0) / pitch
        on_grid = min(frac(fx), 1 - frac(fx)) < 0.04 and min(frac(fy), 1 - frac(fy)) < 0.04
        half = abs(frac(fx) - 0.5) < 0.04 and abs(frac(fy) - 0.5) < 0.04
        kind = "through" if via.layer_end == 32 else "laser"
        if on_grid:   # a grid site: a land if U1 has a ball there, otherwise a depopulated ball site
            where = "land" if (round(fx), round(fy)) in land_cells else "ball site"
        else:
            where = "interstitial" if half else "other"
        census[(kind, where)] += 1
    return census


def via_phrase(census, kind, noun):
    """'59 plated 0.20 mm through vias (all at depopulated ball sites)' style text from u1_via_census."""
    total = sum(v for (k, _), v in census.items() if k == kind)
    parts = [(census[(kind, w)], label) for w, label in
             (("ball site", "at depopulated ball sites"), ("interstitial", "interstitial"),
              ("other", "elsewhere in the field"), ("land", "in lands")) if census[(kind, w)]]
    if len(parts) == 1:
        return f"{total} {noun} (all {parts[0][1]})"
    return f"{total} {noun} (" + ", ".join(f"{n} {label}" for n, label in parts) + ")"


def x2_housing_neighbours(geometry):
    """Bottom-side SMD pads under or within 0.1 mm of X2's 2.54 mm housings, as (ref, overlap mm)."""
    strips = defaultdict(list)
    for pad in geometry["X2"]["pads"]:
        strips[(round(pad["y"], 2), pad["x"] > 33.0)].append(pad["x"])
    bands = [(min(xs) - 1.27, y - 1.27, max(xs) + 1.27, y + 1.27) for (y, _), xs in strips.items()]
    near = {}
    for ref, item in geometry.items():
        if item["layer"] != "Bottom" or ref == "X2":
            continue
        for pad in item["pads"]:
            if pad["hole"] > 1e-6 or pad["layer"] != "Bottom":
                continue
            px0, py0 = pad["x"] - pad["sx"] / 2, pad["y"] - pad["sy"] / 2
            px1, py1 = pad["x"] + pad["sx"] / 2, pad["y"] + pad["sy"] / 2
            for bx0, by0, bx1, by1 in bands:
                if px1 < bx0 or px0 > bx1:
                    continue
                gap = max(by0 - py1, py0 - by1)
                if gap < 0.1:
                    near[ref] = min(near.get(ref, 9.0), gap)
    return near


def write_notes_pcbway(parts, geometry, bom_rows):
    fitted = {ref for ref, component in parts.items() if component["params"].get("DNS") != "Yes"}
    dnp = sorted(set(parts) - fitted, key=bom_audit.natkey)
    counts = assembly_counts(parts, geometry)
    rows = pcbway_rows(bom_rows, parts, geometry)
    buy_rows = [row for row in rows if row["Type"] != "DNS"]
    smd = sorted((ref for ref in fitted if geometry[ref]["has_smd"]), key=bom_audit.natkey)
    tht_parts = sum(row["_qty"] for row in buy_rows if row["Type"] == "thru-hole")
    tht_joints = sum(len(geometry[ref]["pads"]) for ref in fitted if not geometry[ref]["has_smd"])
    n0201 = sum(len(row["_refs"]) for row in bom_rows if row["Footprint"] in ("C0201", "R0201"))
    top0201 = sum(1 for row in bom_rows if row["Footprint"] in ("C0201", "R0201")
                  for ref in row["_refs"] if geometry[ref]["layer"] == "Top")
    u1 = geometry["U1"]["pads"]
    u1_land = max(pad["sx"] for pad in u1)
    vias = u1_via_census(geometry)
    leds = led_polarity_notes(geometry)
    led_refs = ", ".join(sorted(leds, key=bom_audit.natkey))
    led_side = {side for side, _, _ in leds.values()}
    assert len(led_side) == 1
    led_side = led_side.pop()
    led_kx = next(iter(leds.values()))[1]
    near = x2_housing_neighbours(geometry)
    overlapping = sorted((ref for ref, gap in near.items() if gap < 0), key=bom_audit.natkey)
    close = sorted((ref for ref, gap in near.items() if gap >= 0), key=bom_audit.natkey)
    worst = min(near.values()) if near else 0.0

    lines = [
        "ZULU A7 - PCBWAY ASSEMBLY NOTES",
        f"Release date: {RELEASE_DATE}",
        source_line(),
        f"PCB SHA-256: {sha256(PCB)}",
        "",
        "UPLOAD SET",
        "PCBWay fabricates the HDI board and assembles it, Turnkey: PCBWay buys every part.",
        f"- PCB: {FAB_ARCHIVE} (Gerbers incl. the GTP/GBP paste",
        "  layers, drill files, PCBWAY_FAB_NOTES.txt), ordered as \"HDI (Buried/blind",
        "  vias)\" per PCBWAY_FAB_NOTES.txt.",
        f"- BOM: {BOM_FILENAME} (PCBWay's BOM template columns). Centroid:",
        f"  {CPL_FILENAME} (SMT parts only, both sides in one file).",
        f"- Drawings: {DRAWING_FILENAME.format(side='Top')},",
        f"  {DRAWING_FILENAME.format(side='Bottom')}. These notes.",
        "- Preferred: tick Assembly Service on the HDI quote, so it is one order.",
        "  Alternative: once the HDI PCB order exists and before it ships, open a",
        "  separate assembly quote and link it with \"Select PCBWay's PCB Order#\".",
        "Copy every critical item below into \"Detailed information of assembly\" and",
        "email this file to Service@pcbway.com with the order number.",
        "",
        "RECOMMENDED FORM SETTINGS (adjust if you decide otherwise)",
        "- Assembly: Service = Turnkey; Assembly side(s) = Both sides.",
        f"- Number of Unique Parts = {len({row['Mfg Part #'] for row in buy_rows})}; "
        f"Number of SMD Parts = {len(smd)};",
        f"  Number of BGA/QFP Parts = 2 (U1 BGA, U2 LQFP); Number of Through-Hole",
        f"  Parts = {tht_parts} (J1 and four X2 strips, {tht_joints} joints).",
        "- Contains sensitive components/parts = Yes. Paste into its box:",
        "  \"XC7A35T-1CPG236C, FT2232HL-REEL, AS4C32M16SB-7TCN, W25Q128JVSIQ,",
        "  BQ24232RGTR: moisture sensitive, follow the MSL label, bake if floor life",
        "  is exceeded. XC7A35T-1CPG236C: 0.5 mm BGA, X-ray every board. 105017-0001:",
        "  one reflow cycle maximum.\"",
        "- Do you accept alternatives/substitutes made in China = No.",
        "- Number of X-ray test = the number of boards ordered (one X-ray of U1 per",
        "  board); please confirm what this field counts.",
        "- PCB: surface finish ENIG recommended (0.225 mm BGA lands, 0201 pads).",
        "- Panel (the board is only 69.85 x 25.40 mm): PCB Board type = Panel by",
        "  Supplier; Break-away rail = Yes; Route Process = Panel as Tab Route;",
        "  X-out Allowance = Not Accept. Assembly Board type = Panelized PCBs;",
        "  Depanel the boards to delivery = Yes.",
        "",
        "ASSEMBLY SCOPE",
        f"Fitted PCB designators: {len(fitted)}",
        f"Top-side fitted designators: {counts['Top']}",
        f"Bottom-side fitted designators: {counts['Bottom']}",
        f"Physical parts per board: {sum(row['_qty'] for row in buy_rows)} "
        f"(X2 is four strips under one designator)",
        f"BOM purchase lines: {len(buy_rows)}; DNS lines: {len(rows) - len(buy_rows)} "
        f"({', '.join(dnp)})",
        "Assembly is required on both sides: SMT bottom, SMT top, then hand soldering.",
        f"BGA: U1 only, XC7A35T-1CPG236C, 0.5 mm pitch, {len(u1)} round lands of",
        f"{u1_land:.3f} mm. Other 0.5 mm pitch: U2 LQFP-64 (top), U8 VQFN-16 with",
        f"exposed pad (bottom). Smallest package 0201: {n0201} parts ({top0201} on top).",
        "Board: 69.85 x 25.40 mm, six-layer two-step sequential HDI, about 1.63 mm",
        "thick with solder mask.",
        "",
        "HDI AND U1 ORDER GATE",
        "The bare board is a 1+1+N+1+1 HDI build with stacked, copper-filled laser",
        "microvias and an L3-L4 buried-via stage, quoted manually after engineering",
        "review (PCBWAY_FAB_NOTES.txt). Before payment, please confirm in writing:",
        "- turnkey assembly is accepted on this HDI build within the same order;",
        f"- U1's {u1_land:.3f} mm round lands (0.5 mm pitch) are within your fabrication",
        "  line and the assembly process you quote;",
        "- U1's top-side land field holds "
        + via_phrase(vias, "through", "plated 0.20 mm through vias")
        + " and " + via_phrase(vias, "laser", "Top-L2 laser microvias") + ". "
        + ("No via is in a land." if vias[('through', 'land')] + vias[('laser', 'land')] == 0
           else f"{vias[('through', 'land')] + vias[('laser', 'land')]} vias are in lands."),
        "  The through vias are tented but not filled. Per your BGA rule (tent and",
        "  fill vias near BGA pads), please plug or fill them and quote the method.",
        "PANEL: please send the panel drawing for approval before production.",
        "- Copper reaches about 0.3 mm from the board edge: rails on the long edges",
        "  and tab routing, not V-score.",
        "- Keep tabs clear of X1 (top edge, X about 29-37 mm) and X4 (bottom edge,",
        "  X about 28-37 mm). X2's housings seat along both long edges: no tab",
        "  residue where a housing seats.",
        "- MLCCs sit about 3 mm from the long edges: depanel with a router or",
        "  cutter, not by hand-snapping. Depanel before fitting X2.",
        "- The board has no fiducials. Please put global fiducials on the rails",
        "  (top and bottom) and confirm that they suffice for U1 and the 0201s,",
        "  or propose another alignment method.",
        "",
        "CPL AND ORIENTATION",
        f"{CPL_FILENAME}: Designator, Mid X, Mid Y, Layer (Top/Bottom), Rotation.",
        "It lists the SMT parts only; J1 and X2 are hand-soldered and are not in it.",
        "If your line needs one file per side, please split it by the Layer column.",
        "- Units are millimetres (\"mm\" suffix). Origin: the board's lower-left",
        "  corner; the outline runs from 0,0 to 69.85,25.40.",
        "- Coordinates on both sides are as viewed from the top. Bottom-side X",
        "  values are NOT mirrored.",
        "- Mid X/Y is the centre of each part's pad extents, not the footprint",
        "  origin. For connectors (X1, X3, X4) align the part to its pads in CAM.",
        "- Rotations are the values stored in the final Altium PCB, in degrees",
        "  (0/90/180/270), not converted for bottom-side parts. Please confirm your",
        "  bottom-side convention against the bottom drawing before programming.",
        "- The top drawing is viewed from the top; the bottom drawing is mirrored,",
        "  viewed from the bottom. Red dot = pin 1/A1; red bar = LED cathode (K);",
        "  dashed red label = DNP. The silkscreen has no polarity marks, so the",
        "  drawings and this file are the orientation reference.",
        "If the CPL and a drawing disagree, please send an engineering query.",
        "",
        "SPECIAL COMPONENT INSTRUCTIONS",
        "- Reflow order: bottom side FIRST, top side LAST. X1 is rated for one",
        "  reflow cycle and U1 should see only one. Then hand-solder J1, X2 and",
        "  X1's shell stakes.",
        "- X2 is not one 40-pin part: four single-row 2.54 mm THT strips mounted on",
        "  the underside, 2 x Sullins PRPC009SAAN-RC (X2 pins 1-9, 21-29) and",
        "  2 x PRPC011SAAN-RC (pins 10-20, 30-40). The BOM has one line per strip",
        "  part number with designator X2 on both. Housings on the BOTTOM side;",
        "  insert the SHORT post end (about 3 mm) up through the board so about",
        "  1.4 mm stands on top for soldering; the LONG mating end points down.",
        "  Solder on top by hand or selectively, after both reflows and depanel.",
    ]
    if overlapping or close:
        lines += textwrap.wrap(
            f"Fit check: in plan view the housings overlap the pads of "
            f"{', '.join(overlapping) or 'none'} (worst {abs(min(worst, 0.0)):.2f} mm) and come "
            f"within 0.1 mm of {', '.join(close) or 'none'}. Seat each strip without force, "
            "check that it sits flush on the first article, and report any interference "
            "rather than forcing it.",
            78, initial_indent="  ", subsequent_indent="  ")
    lines += [
        "  If you cannot quote X2, leave it unpopulated, do not buy the strips,",
        "  and say so in the quotation.",
        "- J1 (Sullins PPTC062LFBN-RC): vertical 2x6 female Pmod header, top side.",
        "  Pin 1 is the square pad. Hand or selective solder after both reflows.",
        "- JP3 and JP4 are intentional DNS flying-lead/pogo positions (DNS rows in",
        "  the BOM): bare plated holes, no paste, leave empty.",
        "- X1 (Molex 105017-0001 micro-USB-B, top side) opens toward the upper",
        "  board edge. Its shell stakes go into the plated 0.60 x 1.30 mm slots",
        "  MS1/MS2 at the mating-face end, beside the board edge. The MP1/MP4",
        "  paste only tacks them: please hand-solder MS1/MS2 from the bottom side",
        "  after reflow to",
        "  full barrel fill. Please confirm from the Molex drawing whether the",
        "  MH1/MH2 locating pegs are to be soldered.",
        "- X3 (Hirose DM3D-SF microSD, top side): the card opening faces the left",
        "  board edge.",
        "- X4 (JST B2B-PH-SM4-TB, top side): pin 1 (the west contact) is battery",
        "  positive, pin 2 is GND.",
        "- U5, U6 and U7 are look-alike Semtech SC189 bucks (SOT23-5, bottom side):",
        "  U5 = SC189ZSKTRT (3.3 V), U6 = SC189LSKTRT (1.8 V), U7 = SC189ASKTRT",
        "  (1.0 V, FPGA core). A U5/U7 swap puts 3.3 V on U1's core. Check reel and",
        "  marking at each position on the first article.",
        f"- {led_refs} (0603): cathode = pad K on the {led_side} side (X {led_kx:.2f} mm);",
        "  all face the same way. The drawings mark it with a red bar.",
        "- LD0 (Everlight EAST1616RGBA8, 1.6 x 1.6 mm): cathodes are pads 2, 4, 6",
        "  on the WEST side, anodes 1, 3, 5 on the east side, opposite to the",
        "  0603 LEDs. The drawing's red dot marks pad 1, an anode. The land is",
        "  symmetric, so a part turned 180 degrees fits but stays dark.",
        "- Verify pin 1/A1 against the drawings on U1, U2, U3, U4, U5, U6, U7, U8,",
        "  U10, Q1 and X4.",
        "- Stencil from the GTP/GBP layers, whose apertures are 1:1 with copper.",
        "  Please apply your house reductions, in particular: U2 LQFP-64 0.5 mm",
        "  pitch; U8 exposed pad (about 85 % area, windowpane); U1 0.225 mm round",
        "  apertures need a thin stencil (0.08 mm or thinner suggested) and a",
        "  paste that releases them reliably.",
        "",
        "SOURCING",
        "Please buy by the Manufacturer and Mfg Part # columns; every purchase line",
        "carries an exact manufacturer part number. Nothing is consigned.",
        "- Make no substitution without our written approval. Report any line with",
        "  no stock, a lifecycle problem or an ambiguous MPN as an engineering query.",
        "- U1 XC7A35T-1CPG236C: AMD-authorized distributors only (e.g. Digi-Key,",
        "  Mouser, Avnet); no local, broker or open-market stock. Ask us first if",
        "  none can supply it.",
        "- U2 FT2232HL-REEL: FTDI-authorized distributors only (FTDI clones exist).",
        "- The BOM's last column carries per-line instructions; please follow them.",
        "",
        "QUALITY AND TEST",
        "- Lead-free (SAC) solder process.",
        "- Moisture-sensitive parts: U1, U2, U3, U4 and U8. Follow their MSL labels",
        "  for storage, floor life and bake.",
        "- X-ray U1 on every board and include it in the quotation.",
        "- AOI on both sides; workmanship to IPC-A-610 Class 2.",
        "- No firmware programming or functional test is included unless separately",
        "  quoted and supplied with a test procedure and programming image.",
        "- First article: please send photos of BOTH sides and the U1 X-ray images,",
        "  and wait for our approval before building the rest.",
        "",
        "REQUIRED ORDER REVIEW",
        "Before releasing the order, please confirm in writing:",
        "- the HDI fabrication quote, with turnkey assembly on the same order;",
        "- U1 land acceptance, and the plugging or filling of the vias near U1;",
        "- the panel drawing, tab positions and rail fiducials (and that rail",
        "  fiducials alone suffice);",
        "- your bottom-side CPL rotation convention;",
        "- authorized sourcing for U1 and U2, and any lines with no stock;",
        "- hand soldering of X2's four strips and X1's stakes, or X2 left",
        "  unpopulated;",
        "- the stencil apertures for U1, U2 and U8, and X-ray of U1 (and what the",
        "  Number of X-ray test field counts);",
        "- polarity and pin 1 against both drawings, then first-article approval.",
    ]
    wrapped = []
    for line in lines:                       # computed lines can run long: wrap them, keeping the indent
        if len(line) <= 86:
            wrapped.append(line)
            continue
        lead = len(line) - len(line.lstrip(" "))
        follow = " " * (lead + 2 if line.lstrip().startswith("- ") else lead)
        wrapped += textwrap.wrap(line, 86, initial_indent="", subsequent_indent=follow,
                                 break_on_hyphens=False)
    lines = wrapped
    path = os.path.join(ASSEMBLY, NOTES_FILENAME)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def write_notes(parts, geometry, bom_rows):
    if ASSEMBLER == "pcbway":
        return write_notes_pcbway(parts, geometry, bom_rows)
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
    if ASSEMBLER_NEUTRAL:
        title = f"{RELEASE_NAME.upper()} - ASSEMBLY NOTES"
        upload_lines = [
            "Provide the fabrication ZIP to the PCB fabricator and provide this BOM,",
            "CPL, both drawings, and these notes separately to the assembly provider.",
            "Copy all critical instructions into the quotation/order remarks.",
        ]
        gate_lines = [
            "ASSEMBLER QUALIFICATION",
            "JLCPCB does not support assembly of this HDI board. Use a separate",
            "assembler qualified for six-layer two-step sequential HDI, stacked",
            "laser microvias, an L3-L4 buried-via stage, 0201 parts, two-sided SMT,",
            "mixed SMT/THT assembly, and X-ray inspection of the CPG236 BGA.",
        ]
        placement_preview = "the assembly provider's placement preview"
        x2_provider = "the assembler"
        sourcing_lines = [
            "manufacturer, MPN, package, lifecycle, authenticity, and stock using",
            "the selected supplier's live parts system. Do not make substitutions",
            "without written approval.",
        ]
        review_lines = [
            "Confirm HDI-capable two-sided SMT/THT assembly, BGA X-ray inspection,",
            "X2's four-piece manual installation, unresolved/consigned parts,",
            "polarity, and placement preview before releasing the order.",
        ]
    else:
        title = "ZULU A7 - JLCPCB ASSEMBLY NOTES"
        upload_lines = [
            "Upload the fabrication ZIP, BOM CSV, and CPL CSV in their separate",
            "JLCPCB order fields. Copy all critical instructions from this file into",
            "the online order remarks; do not rely on this file being read automatically.",
        ]
        gate_lines = [
            "HDI ORDER GATE",
            "This is a six-layer, two-step sequential HDI board with stacked laser",
            "microvias and an L3-L4 buried-via stage. Obtain written confirmation that",
            "JLCPCB PCBA can be attached to the manually reviewed HDI fabrication quote",
            "before relying on turnkey assembly.",
        ]
        placement_preview = "JLCPCB's placement preview"
        x2_provider = "JLCPCB"
        sourcing_lines = [
            "manufacturer, MPN, package, lifecycle, authenticity, and stock in the live",
            "JLCPCB parts selector. Do not make substitutions without written approval.",
        ]
        review_lines = [
            "Confirm HDI fabrication plus two-sided SMT/THT assembly, X2's four-piece",
            "manual installation, unresolved/consigned parts, polarity, and placement",
            "preview before releasing the order.",
        ]
    lines = [
        title,
        f"Release date: {RELEASE_DATE}",
        source_line(),
        f"PCB SHA-256: {sha256(PCB)}",
        "",
        "UPLOAD SET",
        *upload_lines,
        "",
        "ASSEMBLY SCOPE",
        f"Fitted PCB designators: {len(fitted)}",
        f"Top-side fitted designators: {counts['Top']}",
        f"Bottom-side fitted designators: {counts['Bottom']}",
        f"Do not populate: {', '.join(dnp)}",
        "Assembly is required on both sides.",
        "",
        *gate_lines,
        "",
        "CPL AND ORIENTATION",
        "CPL units are millimetres from the board lower-left origin. The top drawing",
        "is viewed from the top; the bottom drawing is mirrored and viewed from the",
        "bottom. CPL rotations are the rotations stored in the final Altium PCB.",
        f"Review every polarized part and all rotations in {placement_preview}.",
        "Do not approve the order if the preview disagrees with either assembly drawing.",
        "",
        "SPECIAL COMPONENT INSTRUCTIONS",
        "- X2 is not one 40-pin component. It is four underside-mounted THT strips:",
        "  2 x PRPC009SAAN-RC (9-pin) and 2 x PRPC011SAAN-RC (11-pin). The BOM",
        "  therefore reports physical quantity 4 for the single PCB designator X2.",
        f"  Quote this as manual THT work. If {x2_provider} cannot process that exception,",
        "  leave X2 unpopulated for post-assembly installation.",
        "- J1 is a vertical 2x6 female through-hole Pmod header on the top side.",
        "- JP3 and JP4 are intentional DNP flying-lead/pogo positions.",
        "- X4 pin 1 is battery positive.",
        "- X3's microSD card opening faces the left board edge.",
        "- X1's micro-USB opening faces the upper board edge.",
        "- X1-MS1/MS2 are plated 0.60 x 1.30 mm front shell-stake slots. Confirm",
        "  that both connector shell stakes seat fully before soldering.",
        "- Verify pin 1/A1 on U1, U2, U3, U4, U8, U10, Q1, and every polarized LED.",
        "- LD0 cathodes are pads 2, 4, and 6; its anodes are pads 1, 3, and 5.",
        "",
        "SOURCING",
        "The LCSC codes in the BOM are exact identities captured by the project's",
        "September 2026 sourcing audit, not a claim of current stock. Revalidate",
        *sourcing_lines,
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
            *review_lines,
        ]
    )
    path = os.path.join(ASSEMBLY, NOTES_FILENAME)
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
        f"{RELEASE_NAME} - {side} Assembly Drawing - {label}",
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
        cathode = next((pad for pad in item["pads"] if pad["pad"] == "K"), None)
        if pin_one is None and cathode is not None:
            # two-pad LEDs (pads A/K): a red bar across the cathode pad
            marker = board_to_page(cathode["x"], cathode["y"], region, plot, side)
            half_w = (1.0 if detail else 0.7)
            half_h = max(cathode["sy"] * marker[2] / 2, 2.0 if detail else 1.3)
            page.draw_rect(
                fitz.Rect(marker[0] - half_w, marker[1] - half_h, marker[0] + half_w, marker[1] + half_h),
                color=(0.78, 0.08, 0.08),
                fill=(0.92, 0.15, 0.12),
                width=0.3,
            )

    preview_text = {
        "neutral": "the assembler's placement preview",
        "pcbway": "PCBWay's engineering review",
    }.get(ASSEMBLER, "JLCPCB's placement preview")
    page.insert_text(
        (52, page.rect.height - 28),
        "Red dot = pin 1/A1. Red bar = LED cathode (pad K). Dashed red label = DNP. "
        f"Verify every rotation and polarity in {preview_text}.",
        fontsize=8,
        color=(0.24, 0.27, 0.31),
    )
    return set(side_refs)


def write_drawing(side, parts, geometry):
    output = os.path.join(ASSEMBLY, DRAWING_FILENAME.format(side=side))
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
            "title": f"{RELEASE_NAME} {side} Assembly Drawing",
            "author": "Zulu A7 project",
            "subject": {
                "neutral": "assembly reference",
                "pcbway": "PCBWay assembly reference",
            }.get(ASSEMBLER, "JLCPCB assembly reference"),
            "keywords": {
                "neutral": "Zulu A7, assembly, pick and place",
                "pcbway": "Zulu A7, PCBWay, assembly, pick and place",
            }.get(ASSEMBLER, "Zulu A7, JLCPCB, assembly, pick and place"),
            "creator": ("tools/generate_jlcpcb_assembly.py" if ASSEMBLER == "jlcpcb"
                        else "Zulu A7 assembly generator"),
            "producer": "PyMuPDF",
            "creationDate": f"D:{RELEASE_DATE.replace('-', '')}000000-07'00'",
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
    bom_csv = read_csv(outputs["bom"])
    if ASSEMBLER == "pcbway":
        if list(bom_csv[0].keys()) != PCBWAY_COLUMNS:
            raise ValueError(f"PCBWay BOM columns changed: {list(bom_csv[0].keys())}")
        buy = [row for row in bom_csv if row["Type"] != "DNS"]
        dns_refs = {row["Designator"] for row in bom_csv if row["Type"] == "DNS"}
        if dns_refs != dnp:
            raise ValueError(f"BOM DNS rows {sorted(dns_refs)} != DNP parts {sorted(dnp)}")
        for row in buy:
            refs = row["Designator"].split(",")
            if not row["Mfg Part #"] or not row["Manufacturer"]:
                raise ValueError(f"PCBWay BOM line without manufacturer or MPN: {row}")
            if row["Type"] not in ("SMD", "thru-hole"):
                raise ValueError(f"invalid PCBWay Type: {row}")
            if refs != ["X2"] and int(row["Qty"]) != len(refs):
                raise ValueError(f"PCBWay BOM quantity != designator count: {row}")
        if sum(int(row["Qty"]) for row in buy if row["Designator"] == "X2") != 4:
            raise ValueError("X2 must be four strips in the PCBWay BOM")
        bom_csv = buy
        cpl_expected = {ref for ref in fitted if geometry[ref]["has_smd"]}
    else:
        cpl_expected = fitted
    bom_refs = {
        ref
        for row in bom_csv
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
    if cpl_refs != cpl_expected:
        raise ValueError(
            f"CPL designator mismatch: missing={sorted(cpl_expected - cpl_refs)} "
            f"extra={sorted(cpl_refs - cpl_expected)}"
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

    expected_rows = len(pcbway_rows(bom_rows, parts, geometry)) if ASSEMBLER == "pcbway" else len(bom_rows)
    if expected_rows != len(read_csv(outputs["bom"])):
        raise ValueError("BOM row count changed during serialization")
    with open(outputs["notes"], encoding="utf-8") as handle:
        notes = handle.read()
    if ASSEMBLER == "pcbway" and ("JLCPCB" in notes or "LCSC" in notes or max(map(len, notes.splitlines())) > 88):
        raise ValueError("PCBWay notes mention JLCPCB/LCSC or have a line over 88 characters")
    for path in outputs.values():
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise ValueError(f"missing or empty output: {path}")


def main():
    configure()
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
        "bom": write_bom(bom_rows, parts, geometry),
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
