# -*- coding: utf-8 -*-
"""Build and validate the Zulu A7 Fab B Rev 2 PCBWay fabrication ZIP.

    python tools/package_fabrication_release.py

Adapted from Zulu_Altium_VS_Code_HDI_Optimized/tools/package_fabrication_release.py,
then from Fab B Rev 1's copy (Rev_1/tools, export of 2026-11-11 08:46).
Every expected number below was taken from the Rev 2 Altium export of
2026-11-11 (Gerbers 23:34, NC drill 23:35:44: Zulu_a7_no_pmod.DRR / .LDP /
-SlotHoles.TXT), re-exported 2026-11-12 00:17 after the silkscreen title became
ZULU A7 2.2 (only GTO changed), of the board saved 2026-11-12 00:16:55
(MD5 33023787), and cross-checked
against the PcbDoc by tools/fab_facts.py (tools/fab_facts.json: drill_vs_board
0 missing / 0 extra in every drill file).  The script never regenerates outputs;
it fails if any input is missing, empty, older than the PcbDoc, or does not match.
"""

import argparse
import hashlib
import os
import re
import sys
import zipfile


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.join(ROOT, "Imported zulu_a7.PrjPcb")
OUTPUTS = os.path.join(PROJECT, "Project Outputs for Zulu_a7_no_pmod")
FABRICATION = os.path.join(ROOT, "fabrication")
PCB = os.path.join(PROJECT, "Zulu_a7_no_pmod.PcbDoc")
RELEASE_PREFIX = "Zulu_A7_no_pmod_Rev_2"
RELEASE_NAME = "Zulu A7 Fab B Rev 2"
RELEASE_DATE = "2026-11-11"
DEFAULT_NOTE = os.path.join(FABRICATION, f"{RELEASE_PREFIX}_PCBWay_FAB_NOTES.txt")
DEFAULT_ARCHIVE = os.path.join(
    FABRICATION, f"{RELEASE_PREFIX}_PCBWay_Fabrication_{RELEASE_DATE}.zip"
)
# order/quote numbers never go into a packaged file name or the note (public repo)
ORDER_DENYLIST = ("W1150632AS3P6",)
# Rev 2's final Zulu_a7_no_pmod.PcbDoc, saved 2026-11-12 00:16:55 (title ZULU A7 2.2;
# the 2026-11-11 23:27:22 save with title 2.0 was SHA-256 A319195B..., MD5 e8715917)
# (Rev 1: SHA-256 C439E0F5...0382, MD5 830b1744)
EXPECTED_PCB_SHA256 = (
    "D77DE904DF044841C4E7B6727630BF219601B3013EDB0ED3DE31465C5D03B472"
)
EXPECTED_PCB_MD5 = "330237878e325c882fca3f689b55ec0c"
BASE = "Zulu_a7_no_pmod"
OUTLINE = (0.0, 0.0, 69.85, 25.40)  # GM profile, mm
GERBER_EXTENSIONS = [
    "GTL",
    "G1",
    "G2",
    "G3",
    "G4",
    "GBL",
    "GTS",
    "GBS",
    "GTO",
    "GBO",
    "GTP",
    "GBP",
    "GM",
]
ROUND_DRILL_EXTENSIONS = ["TXT", "TX3", "TX6", "TX7", "TX9", "TX10"]
# hits per tool, from Rev 2's Zulu_a7_no_pmod.DRR (2026-11-11 23:35:44), equal to
# fab_facts.json drill_hits_per_tool and to the PcbDoc via counts per span
# (Rev 1, DRR 08:46: TXT T02 369, TX3 391, TX6 313, TX7 301, TX9 269, TX10 278;
# T04 2 and T05 58 are unchanged)
EXPECTED_ROUND_DRILLS = {
    "TXT": {"02": 354, "04": 2, "05": 58},
    "TX3": {"01": 403},
    "TX6": {"01": 321},
    "TX7": {"01": 307},
    "TX9": {"01": 281},
    "TX10": {"01": 295},
}
EXPECTED_TOOL_SIZES = {
    "TXT": {"02": 0.20, "04": 0.85, "05": 1.016},
    "TX3": {"01": 0.15},
    "TX6": {"01": 0.15},
    "TX7": {"01": 0.15},
    "TX9": {"01": 0.15},
    "TX10": {"01": 0.15},
}
# TX6 + TX7 + TX9 + TX10 = 321 + 307 + 281 + 295; the DRR's "MicroVia Totals" and
# docs/rev2_layout.md (mark_microvias.py --expect 1204) agree.  Rev 1: 1161.
EXPECTED_MICROVIA_TOTAL = 1204
# Rev 2's .LDP (23:35:44) maps the same seven drill files to the same layers as
# Rev 1's; only its header path changed.  So do EXPECTED_ENTRIES and the extensions.
EXPECTED_LAYER_MAP = {
    f"{BASE}-RoundHoles.TXT": "gtl,g1,g2,g3,g4,gbl",
    f"{BASE}-SlotHoles.TXT": "gtl,g1,g2,g3,g4,gbl",
    f"{BASE}-RoundHoles.TX3": "g2,g3",
    f"{BASE}-RoundHoles.TX6": "gtl,g1",
    f"{BASE}-RoundHoles.TX7": "g1,g2",
    f"{BASE}-RoundHoles.TX9": "g3,g4",
    f"{BASE}-RoundHoles.TX10": "g4,gbl",
}
SLOT_DRILL_FILENAME = f"{BASE}-SlotHoles.TXT"
# X1-MS1 / X1-MS2 from Rev 2's -SlotHoles.TXT (23:35:44), equal to the PcbDoc pad
# records (fab_facts.json x1_hole_pads): Rev 1's (29.5199, 23.9585) and
# (36.5201, 23.9585) moved 2.54 mm west with X1.  Tool, route and length unchanged.
EXPECTED_SLOT_CENTERS = [(26.9799, 23.9585), (33.9801, 23.9585)]
EXPECTED_ENTRIES = 23


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def output_path(filename):
    return os.path.join(OUTPUTS, filename)


def gerber_filename(extension):
    return f"{BASE}.{extension}"


def round_drill_filename(extension):
    return f"{BASE}-RoundHoles.{extension}"


def excellon_coord(text):
    """METRIC,LZ 4:4: leading zeros kept, trailing zeros suppressed."""
    negative = text.startswith("-")
    digits = text.lstrip("+-")
    if len(digits) > 8:
        raise ValueError(f"Excellon coordinate too long for 4:4: {text}")
    value = int(digits.ljust(8, "0")) / 10000
    return -value if negative else value


def read_excellon(path):
    """Return ({tool: diameter}, {tool: [(x, y), ...]}) with modal X/Y kept."""
    with open(path, encoding="ascii") as handle:
        lines = [line.strip() for line in handle]
    for header in (";FILE_FORMAT=4:4", "METRIC,LZ", ";TYPE=PLATED"):
        if header not in lines:
            raise ValueError(f"{os.path.basename(path)} lacks header {header}")
    tools, hits = {}, {}
    tool = None
    x = y = None
    in_header = True
    for line in lines:
        if in_header:
            definition = re.fullmatch(r"T(\d{2})F\d+S\d+C(\d+\.\d+)", line)
            if definition:
                tools[definition.group(1)] = float(definition.group(2))
            elif line == "%":
                in_header = False
            continue
        selected = re.fullmatch(r"T(\d{2})", line)
        if selected:
            tool = selected.group(1)
            if tool not in tools:
                raise ValueError(f"{os.path.basename(path)} selects undefined tool T{tool}")
            hits.setdefault(tool, [])
            continue
        hit = re.fullmatch(r"(?:X([-+]?\d+))?(?:Y([-+]?\d+))?", line)
        if hit and (hit.group(1) or hit.group(2)):
            if tool is None:
                raise ValueError(f"{os.path.basename(path)} has a hit before a tool: {line}")
            if hit.group(1):
                x = excellon_coord(hit.group(1))
            if hit.group(2):
                y = excellon_coord(hit.group(2))
            if x is None or y is None:
                raise ValueError(f"{os.path.basename(path)} modal coordinate unset: {line}")
            hits[tool].append((x, y))
            continue
        if line in ("G90", "G05", "M30", "") or line.startswith(";"):
            continue
        raise ValueError(f"{os.path.basename(path)}: unexpected line {line!r}")
    return tools, hits


def inside_outline(x, y):
    x0, y0, x1, y1 = OUTLINE
    return x0 < x < x1 and y0 < y < y1


def validate_round_drills():
    microvias = 0
    for extension, expected in EXPECTED_ROUND_DRILLS.items():
        path = output_path(round_drill_filename(extension))
        tools, hits = read_excellon(path)
        actual = {tool: len(points) for tool, points in hits.items()}
        if actual != expected:
            raise ValueError(
                f"RoundHoles.{extension} drill counts changed: {actual} != {expected}"
            )
        for tool, size in EXPECTED_TOOL_SIZES[extension].items():
            if abs(tools[tool] - size) > 0.0015:
                raise ValueError(
                    f"RoundHoles.{extension} T{tool} is {tools[tool]} mm, expected {size}"
                )
        outside = [p for points in hits.values() for p in points if not inside_outline(*p)]
        if outside:
            raise ValueError(f"RoundHoles.{extension} hits outside the outline: {outside[:5]}")
        if extension in ("TX6", "TX7", "TX9", "TX10"):
            microvias += sum(actual.values())
    if microvias != EXPECTED_MICROVIA_TOTAL:
        raise ValueError(f"microvia total {microvias} != {EXPECTED_MICROVIA_TOTAL}")


def validate_drr():
    """The DRR must report the same per-file tool counts the drill files hold."""
    with open(output_path(f"{BASE}.DRR"), encoding="ascii") as handle:
        text = handle.read()
    report = {}
    current = None
    for line in text.splitlines():
        named = re.match(r"ASCII RoundHoles File : (\S+)", line)
        if named:
            current = named.group(1)
            continue
        row = re.match(r"T(\d+)\s+(\d+(?:\.\d+)?)mm.*?\s(Round|Slot)\s+(\d+)\s+PTH", line)
        if row and row.group(3) == "Round" and current:
            report.setdefault(current, {})[row.group(1).zfill(2)] = int(row.group(4))
    expected = {
        round_drill_filename(ext): counts for ext, counts in EXPECTED_ROUND_DRILLS.items()
    }
    if report != expected:
        raise ValueError(f"DRR counts differ from expected: {report} != {expected}")
    total = re.search(r"MicroVia Totals\s+(\d+)", text)
    if not total or int(total.group(1)) != EXPECTED_MICROVIA_TOTAL:
        raise ValueError("DRR microvia total changed")


def validate_slots(path):
    with open(path, encoding="ascii") as handle:
        lines = [line.strip() for line in handle]
    required_headers = {";FILE_FORMAT=4:4", "METRIC,LZ", ";TYPE=PLATED"}
    missing_headers = required_headers - set(lines)
    if missing_headers:
        raise ValueError(
            f"slot drill headers missing from {os.path.basename(path)}: "
            f"{sorted(missing_headers)}"
        )

    tools = {}
    active_tool = None
    slots = []
    for line in lines:
        definition = re.fullmatch(r"T(\d{2})F\d+S\d+C(\d+\.\d+)", line)
        if definition:
            tools[definition.group(1)] = float(definition.group(2))
            continue
        selected = re.fullmatch(r"T(\d{2})", line)
        if selected:
            active_tool = selected.group(1)
            continue
        command = re.fullmatch(
            r"X(\d+)Y(\d+)G85(?:X(\d+))?(?:Y(\d+))?", line
        )
        if command:
            if active_tool not in tools:
                raise ValueError(f"slot command has no defined tool: {line}")
            start_x = excellon_coord(command.group(1))
            start_y = excellon_coord(command.group(2))
            end_x = excellon_coord(command.group(3)) if command.group(3) else start_x
            end_y = excellon_coord(command.group(4)) if command.group(4) else start_y
            slots.append((start_x, start_y, end_x, end_y, tools[active_tool]))

    if len(slots) != 2:
        raise ValueError(f"plated slot count changed: {len(slots)} != 2")

    actual_centers = []
    for start_x, start_y, end_x, end_y, tool_diameter in slots:
        route_length = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        overall_length = route_length + tool_diameter
        if abs(tool_diameter - 0.60) > 0.0001:
            raise ValueError(f"slot tool diameter changed: {tool_diameter} != 0.60")
        if abs(start_x - end_x) > 0.0001:
            raise ValueError("X1 slot orientation changed from vertical")
        if abs(route_length - 0.70) > 0.0001:
            raise ValueError(f"slot route length changed: {route_length} != 0.70")
        if abs(overall_length - 1.30) > 0.0001:
            raise ValueError(f"slot overall length changed: {overall_length} != 1.30")
        actual_centers.append(
            (round((start_x + end_x) / 2, 4), round((start_y + end_y) / 2, 4))
        )
    if actual_centers != EXPECTED_SLOT_CENTERS:
        raise ValueError(
            f"slot centers changed: {actual_centers} != {EXPECTED_SLOT_CENTERS}"
        )


def validate_outline():
    with open(output_path(gerber_filename("GM")), encoding="ascii") as handle:
        text = handle.read()
    if "%MOMM*%" not in text or "%FSLAX44Y44*%" not in text:
        raise ValueError("GM is not metric 4.4 RS-274X")
    x = y = 0
    points = []
    for x_text, y_text in re.findall(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0[12]\*", text):
        if x_text:
            x = int(x_text)
        if y_text:
            y = int(y_text)
        points.append((x / 10000, y / 10000))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    box = (min(xs), min(ys), max(xs), max(ys))
    if box != OUTLINE:
        raise ValueError(f"board outline changed: {box} != {OUTLINE}")


def validate_note(note):
    with open(note, encoding="ascii") as handle:
        text = handle.read()
    recorded = re.search(r"PCB SHA-256: ([0-9A-F]{64})", text)
    if not recorded:
        raise ValueError("fab note does not record the PCB SHA-256")
    if recorded.group(1) != EXPECTED_PCB_SHA256:
        raise ValueError(
            f"fab note records {recorded.group(1)}, board is {EXPECTED_PCB_SHA256}"
        )
    if f"Source: {BASE}.PcbDoc (MD5 {EXPECTED_PCB_MD5})" not in text:
        raise ValueError("fab note does not record the board MD5")
    if f"Revision: {RELEASE_NAME} " not in text:
        raise ValueError("fab note does not name the revision")
    if f"Release date: {RELEASE_DATE}" not in text:
        raise ValueError("fab note does not carry the release date")
    if any(order.upper() in text.upper() for order in ORDER_DENYLIST):
        raise ValueError("fab note names an order number")
    # the note's drill table, plug request and slot centres must match the files
    stated = {
        "TXT": r"Top -> Bottom signal through vias:\s+(\d+)\s+\(RoundHoles\.TXT, T02\)",
        "TX6": r"Top -> L2 microvias:\s+(\d+)\s+\(RoundHoles\.TX6\)",
        "TX7": r"L2 -> L3 microvias:\s+(\d+)\s+\(RoundHoles\.TX7\)",
        "TX3": r"L3 -> L4 buried vias:\s+(\d+)\s+\(RoundHoles\.TX3\)",
        "TX9": r"L4 -> L5 microvias:\s+(\d+)\s+\(RoundHoles\.TX9\)",
        "TX10": r"L5 -> Bottom microvias:\s+(\d+)\s+\(RoundHoles\.TX10\)",
    }
    for extension, pattern in stated.items():
        found = re.search(pattern, text)
        (expected,) = [
            count
            for tool, count in EXPECTED_ROUND_DRILLS[extension].items()
            if extension != "TXT" or tool == "02"
        ]
        if not found or int(found.group(1)) != expected:
            raise ValueError(f"fab note's {extension} count is not {expected}")
    total = re.search(r"Total laser-microvia records:\s+([\d,]+)", text)
    if not total or int(total.group(1).replace(",", "")) != EXPECTED_MICROVIA_TOTAL:
        raise ValueError(f"fab note's microvia total is not {EXPECTED_MICROVIA_TOTAL}")
    plug = re.search(r"PLEASE PLUG ALL (\d+) THROUGH VIAS", text)
    if not plug or int(plug.group(1)) != EXPECTED_ROUND_DRILLS["TXT"]["02"]:
        raise ValueError("fab note asks to plug a different number of through vias")
    for x, y in EXPECTED_SLOT_CENTERS:
        if f"({x:.4f}, {y:.4f}) mm" not in text:
            raise ValueError(f"fab note does not state the slot centre ({x}, {y})")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--note",
        default=DEFAULT_NOTE,
        help="fabricator-specific note included in the archive",
    )
    parser.add_argument(
        "--archive",
        default=DEFAULT_ARCHIVE,
        help="output ZIP path",
    )
    parser.add_argument(
        "--pass-label",
        default="FAB_B_REV_2_PCBWAY_FABRICATION_RELEASE",
        help="label printed after successful validation",
    )
    return parser.parse_args()


def validate_sources(note):
    actual_hash = sha256(PCB)
    if actual_hash != EXPECTED_PCB_SHA256:
        raise ValueError(
            f"Fab B PCB hash changed: {actual_hash} != {EXPECTED_PCB_SHA256}"
        )

    filenames = (
        [gerber_filename(extension) for extension in GERBER_EXTENSIONS]
        + [
            round_drill_filename(extension)
            for extension in ROUND_DRILL_EXTENSIONS
        ]
        + [SLOT_DRILL_FILENAME, f"{BASE}.LDP", f"{BASE}.DRR"]
    )
    sources = [output_path(filename) for filename in filenames] + [note]
    if any(
        order.upper() in os.path.basename(path).upper()
        for order in ORDER_DENYLIST
        for path in sources
    ):
        raise ValueError("an order file must never be packaged")
    missing = [path for path in sources if not os.path.isfile(path)]
    if missing:
        raise FileNotFoundError("missing release inputs: " + ", ".join(missing))
    empty = [path for path in sources if os.path.getsize(path) == 0]
    if empty:
        raise ValueError("empty release inputs: " + ", ".join(empty))

    pcb_mtime = os.path.getmtime(PCB)
    stale = [
        path
        for path in sources[:-1]
        if os.path.getmtime(path) < pcb_mtime
    ]
    if stale:
        raise ValueError(
            "fabrication outputs predate the PCB: " + ", ".join(stale)
        )

    validate_outline()
    validate_round_drills()
    validate_drr()
    validate_slots(output_path(SLOT_DRILL_FILENAME))

    with open(output_path(f"{BASE}.LDP"), encoding="ascii") as handle:
        layer_map = handle.read().lower()
    for filename, expected_layers in EXPECTED_LAYER_MAP.items():
        pattern = (
            rf"drillfile={re.escape(filename.lower())}"
            rf"\|drilllayers={re.escape(expected_layers)}(?:\r?\n|$)"
        )
        if re.search(pattern, layer_map) is None:
            raise ValueError(
                f"{filename} is missing the expected LDP map {expected_layers}"
            )
    if layer_map.count("drillfile=") != len(EXPECTED_LAYER_MAP):
        raise ValueError("LDP lists an unexpected drill file")
    validate_note(note)
    return sources


def build_archive(sources, archive_path):
    os.makedirs(os.path.dirname(archive_path), exist_ok=True)
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for source in sources:
            archive.write(source, arcname=os.path.basename(source))


def validate_archive(sources, archive_path):
    expected_names = [os.path.basename(path) for path in sources]
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("fabrication archive contains a corrupt entry")
        if archive.namelist() != expected_names:
            raise ValueError(
                f"archive entries changed: {archive.namelist()} != {expected_names}"
            )
        if len(archive.infolist()) != EXPECTED_ENTRIES:
            raise ValueError(
                f"archive has {len(archive.infolist())} entries, expected {EXPECTED_ENTRIES}"
            )
        for source in sources:
            archived = archive.read(os.path.basename(source))
            with open(source, "rb") as handle:
                if archived != handle.read():
                    raise ValueError(
                        f"archive entry differs from source: {os.path.basename(source)}"
                    )


def main():
    args = parse_args()
    note = os.path.abspath(args.note)
    archive_path = os.path.abspath(args.archive)
    sources = validate_sources(note)
    build_archive(sources, archive_path)
    validate_archive(sources, archive_path)
    print(f"{args.pass_label} PASS")
    print(f"{len(sources)} flat entries")
    print(
        f"{os.path.basename(archive_path)} | {os.path.getsize(archive_path)} bytes | "
        f"SHA256 {sha256(archive_path)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
