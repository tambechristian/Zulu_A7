# -*- coding: utf-8 -*-
"""Build and validate the Zulu A7 2.0 (Fab B) PCBWay fabrication ZIP.

    python tools/package_fabrication_release.py

Adapted from Zulu_Altium_VS_Code_HDI_Optimized/tools/package_fabrication_release.py.
Every expected number below was taken from the Altium export of 2026-11-11
08:46 (zulu_a7_fab_b.DRR / .LDP / -SlotHoles.TXT) and cross-checked against the
PcbDoc by tools/fab_facts.py.  The script never regenerates outputs; it fails
if any input is missing, empty, older than the PcbDoc, or does not match.
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
OUTPUTS = os.path.join(PROJECT, "Project Outputs for zulu_a7_fab_b")
FABRICATION = os.path.join(ROOT, "fabrication")
PCB = os.path.join(PROJECT, "zulu_a7_fab_b.PcbDoc")
DEFAULT_NOTE = os.path.join(FABRICATION, "Zulu_A7_Fab_B_PCBWay_FAB_NOTES.txt")
DEFAULT_ARCHIVE = os.path.join(
    FABRICATION, "Zulu_A7_Fab_B_PCBWay_Fabrication_2026-11-11.zip"
)
EXPECTED_PCB_SHA256 = (
    "C439E0F5F8D0B9E3C57B88EC823261C75979AD4AE88FF39305AB19B80D180382"
)
BASE = "zulu_a7_fab_b"
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
# hits per tool, from zulu_a7_fab_b.DRR (2026-11-11 08:46:54, after the
# through-via-out-of-pad change: 15 through vias became stacked microvia columns)
EXPECTED_ROUND_DRILLS = {
    "TXT": {"02": 369, "04": 2, "05": 58},
    "TX3": {"01": 391},
    "TX6": {"01": 313},
    "TX7": {"01": 301},
    "TX9": {"01": 269},
    "TX10": {"01": 278},
}
EXPECTED_TOOL_SIZES = {
    "TXT": {"02": 0.20, "04": 0.85, "05": 1.016},
    "TX3": {"01": 0.15},
    "TX6": {"01": 0.15},
    "TX7": {"01": 0.15},
    "TX9": {"01": 0.15},
    "TX10": {"01": 0.15},
}
EXPECTED_MICROVIA_TOTAL = 1161
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
EXPECTED_SLOT_CENTERS = [(29.5199, 23.9585), (36.5201, 23.9585)]
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
    if "Zulu A7 2.0 (Fab B)" not in text:
        raise ValueError("fab note does not name the revision")


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
        default="FAB_B_PCBWAY_FABRICATION_RELEASE",
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
    if any("W1150632AS3P6" in os.path.basename(path).upper() for path in sources):
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
