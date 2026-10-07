# -*- coding: utf-8 -*-
"""Build and validate an optimized Zulu A7 fabrication ZIP."""

import argparse
import hashlib
import os
import re
import sys
import zipfile


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.join(ROOT, "Imported zulu_a7.PrjPcb")
OUTPUTS = os.path.join(PROJECT, "Project Outputs for zulu_a7_hdi_optimized")
FABRICATION = os.path.join(ROOT, "fabrication")
PCB = os.path.join(PROJECT, "zulu_a7_hdi_optimized.PcbDoc")
DEFAULT_NOTE = os.path.join(FABRICATION, "Zulu_A7_HDI_Optimized_FAB_NOTES.txt")
DEFAULT_ARCHIVE = os.path.join(
    FABRICATION, "Zulu_A7_HDI_Optimized_JLCPCB_Fabrication_2026-10-07.zip"
)
EXPECTED_PCB_SHA256 = (
    "A3436176F03BD3E7195F777322BC68DA107D3A8AB82A80259D8F1A6A5AAC6A4E"
)
BASE = "zulu_a7_hdi_optimized"
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
EXPECTED_ROUND_DRILLS = {
    "TXT": {"02": 393, "04": 2, "05": 58},
    "TX3": {"01": 362},
    "TX6": {"01": 291},
    "TX7": {"01": 278},
    "TX9": {"01": 222},
    "TX10": {"01": 222},
}
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


def drill_counts(path):
    counts = {}
    active_tool = None
    with open(path, encoding="ascii") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            selected = re.fullmatch(r"T(\d{2})", line)
            if selected:
                active_tool = selected.group(1)
                counts.setdefault(active_tool, 0)
            elif active_tool and re.match(r"^[XY]", line):
                counts[active_tool] += 1
    return counts


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
            r"X(\d{8})Y(\d{8})G85(?:X(\d{8}))?Y(\d{8})", line
        )
        if command:
            if active_tool not in tools:
                raise ValueError(f"slot command has no defined tool: {line}")
            start_x = int(command.group(1)) / 10000
            start_y = int(command.group(2)) / 10000
            end_x = (
                int(command.group(3)) / 10000
                if command.group(3) is not None
                else start_x
            )
            end_y = int(command.group(4)) / 10000
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
        default="FABRICATION_RELEASE",
        help="label printed after successful validation",
    )
    return parser.parse_args()


def validate_sources(note):
    actual_hash = sha256(PCB)
    if actual_hash != EXPECTED_PCB_SHA256:
        raise ValueError(
            f"optimized PCB hash changed: {actual_hash} != {EXPECTED_PCB_SHA256}"
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

    for extension, expected in EXPECTED_ROUND_DRILLS.items():
        actual = drill_counts(output_path(round_drill_filename(extension)))
        if actual != expected:
            raise ValueError(
                f"RoundHoles.{extension} drill counts changed: "
                f"{actual} != {expected}"
            )
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
    return sources


def build_archive(sources, archive_path):
    os.makedirs(FABRICATION, exist_ok=True)
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
        if len(archive.infolist()) != 23:
            raise ValueError(
                f"archive has {len(archive.infolist())} entries, expected 23"
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
