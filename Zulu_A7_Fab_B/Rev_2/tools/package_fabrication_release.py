# -*- coding: utf-8 -*-
"""Build and validate the Zulu A7 Fab B Rev 2 PCBWay fabrication ZIP.

    python tools/package_fabrication_release.py

Adapted from Zulu_Altium_VS_Code_HDI_Optimized/tools/package_fabrication_release.py,
then from Fab B Rev 1's copy (Rev_1/tools, export of 2026-11-11 08:46), then Fab B Rev 2's
2026-11-11 release. The script never regenerates outputs; it fails if any input is missing,
empty, older than the PcbDoc, or does not match.

FAB B REV 2 SYNC (2026-11-20): the no-PMOD Rev 2 version of this script
(Zulu_A7_no_pmod/Rev_2/tools/package_fabrication_release.py at 427960e) brought back to Fab B for
the release of the board synced from no-PMOD Rev 2 (FT2232HQ QFN-64 U2, S2B-PH-SM4-TB X4,
MSOP-8 U10, DQ series resistors R119-R134, body moves, 3D bodies; the Pmod J1 + R26-R33 and the
69.85 x 25.40 mm outline stay). Kept from the no-PMOD copy: the release body gate
(tools/release_body_gate.py) before anything is written, the order-number check on file names,
on the note and on every archived file, and the note written by tools/fab_notes.py. Fab B values:
names (zulu_a7_fab_b, Zulu_A7_Fab_B_Rev_2_PCBWay_*), the outline, the X1 slot centres (X1 does
not move) and the component-hole tools TXT T04 = 2 (X1 MH1/MH2) and T05 = 58 (J1 12, JP3 3, JP4 3,
X2 40; the no-PMOD board has 46). The order-number guard: the 2026-11-11 copy listed the number
itself in ORDER_DENYLIST; this copy keeps the same case-insensitive substring test without the
number in the (public) file -- every 'W' + 7 digits is tried with every 4-6 character tail against
the SHA-256 set, so trailing characters cannot hide it (the no-PMOD copy matched whole tokens only).

Release constants, filled 2026-11-20 from the synced board (md5 5fea1304), its export and
tools/fab_facts.json: EXPECTED_PCB_SHA256, EXPECTED_PCB_MD5, the through-via count TXT T02 and
TX3/TX6/TX7/TX9/TX10 in EXPECTED_ROUND_DRILLS, EXPECTED_MICROVIA_TOTAL and RELEASE_DATE (also in
tools/fab_notes.py and tools/generate_jlcpcb_assembly.py). The script refuses if any is set back to None.

The 2026-11-11 Fab B Rev 2 release (board saved 2026-11-12 00:16:55, MD5 33023787, SHA-256
D77DE904...B472): TXT T02 354 / T04 2 / T05 58, TX3 403, TX6 321, TX7 307, TX9 281, TX10 295,
1,204 microvias.
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
RELEASE_PREFIX = "Zulu_A7_Fab_B_Rev_2"
RELEASE_NAME = "Zulu A7 Fab B Rev 2"
RELEASE_DATE = "2026-11-20"   # as in tools/fab_notes.py and tools/generate_jlcpcb_assembly.py
DEFAULT_NOTE = os.path.join(FABRICATION, f"{RELEASE_PREFIX}_PCBWay_FAB_NOTES.txt")
DEFAULT_ARCHIVE = os.path.join(
    FABRICATION, f"{RELEASE_PREFIX}_PCBWay_Fabrication_{RELEASE_DATE}.zip"
)
# order/quote numbers never go into a packaged file name, the note or an archived file (public repo).
# ORDER_DENYLIST of the 2026-11-11 copy, kept as SHA-256 so the number stays out of this public file:
# a case-insensitive substring test, every 'W' + 7 digits tried with every 4-6 character tail.
ORDER_DENYLIST_SHA256 = {"4b77802bdde723a747a12d3526f308f0a84011df15acdd400fb8eeb3018f1674"}
ORDER_HEAD = re.compile(rb"W[0-9]{7}", re.I)


def names_order(data):
    if isinstance(data, str):
        data = data.encode("latin-1", "replace")
    up = data.upper()
    for m in ORDER_HEAD.finditer(up):
        for n in range(4, 7):
            tail = up[m.end():m.end() + n]
            if len(tail) == n and tail.isalnum() and \
                    hashlib.sha256(m.group(0) + tail).hexdigest() in ORDER_DENYLIST_SHA256:
                return True
    return False


# the 2026-11-20 synced zulu_a7_fab_b.PcbDoc (2026-11-11 release board: SHA-256
# D77DE904DF044841C4E7B6727630BF219601B3013EDB0ED3DE31465C5D03B472, MD5 330237878e325c882fca3f689b55ec0c)
EXPECTED_PCB_SHA256 = "0E5D64CE9B6596E442BBEAF72FC2C6AA30F55D9187B764ED43418729873FA074"
EXPECTED_PCB_MD5 = "5fea13046ef71090519f5d357c1d96e5"
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
# hits per tool, to be read from the release's zulu_a7_fab_b.DRR and checked equal to fab_facts.json
# drill_hits_per_tool and to the PcbDoc via counts per span. T04 (X1 MH1/MH2) and T05 (J1, JP3, JP4, X2) are fixed
# by parts the sync does not touch. 2026-11-20 values from the synced board's DRR and tools/fab_facts.json.
# (2026-11-11 release: TXT T02 354 / T04 2 / T05 58, TX3 403, TX6 321, TX7 307, TX9 281, TX10 295)
EXPECTED_ROUND_DRILLS = {
    "TXT": {"02": 329, "04": 2, "05": 58},
    "TX3": {"01": 403},
    "TX6": {"01": 344},
    "TX7": {"01": 307},
    "TX9": {"01": 312},
    "TX10": {"01": 330},
}
EXPECTED_TOOL_SIZES = {
    "TXT": {"02": 0.20, "04": 0.85, "05": 1.016},
    "TX3": {"01": 0.15},
    "TX6": {"01": 0.15},
    "TX7": {"01": 0.15},
    "TX9": {"01": 0.15},
    "TX10": {"01": 0.15},
}
# TX6 + TX7 + TX9 + TX10; the DRR's "MicroVia Totals" must agree (2026-11-20: 344 + 307 + 312 + 330).
# (2026-11-11 release: 321 + 307 + 281 + 295 = 1204; Rev 1: 1161)
EXPECTED_MICROVIA_TOTAL = 1293
# The .LDP maps the same seven drill files to the same layers on every Fab B and no-PMOD export,
# so do EXPECTED_ENTRIES and the extensions.
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
# X1-MS1 / X1-MS2 from Rev 2's -SlotHoles.TXT (2026-11-11 23:35:44), equal to the PcbDoc pad
# records (fab_facts.json x1_hole_pads): Rev 1's (29.5199, 23.9585) and
# (36.5201, 23.9585) moved 2.54 mm west with X1.  Tool, route and length unchanged; the sync
# does not move X1.
EXPECTED_SLOT_CENTERS = [(26.9799, 23.9585), (33.9801, 23.9585)]
EXPECTED_ENTRIES = 23


def require_release_constants():
    """TODO(release) guard: refuse while any board-dependent constant is still None."""
    todo = [name for name, value in (("RELEASE_DATE", RELEASE_DATE), ("EXPECTED_PCB_SHA256", EXPECTED_PCB_SHA256),
                                     ("EXPECTED_PCB_MD5", EXPECTED_PCB_MD5),
                                     ("EXPECTED_MICROVIA_TOTAL", EXPECTED_MICROVIA_TOTAL)) if value is None]
    todo += [f"EXPECTED_ROUND_DRILLS[{ext!r}][{tool!r}]" for ext, tools in EXPECTED_ROUND_DRILLS.items()
             for tool, count in tools.items() if count is None]
    if todo:
        raise ValueError("TODO(release): fill " + ", ".join(todo) + " from the final board's export and tools/fab_facts.json")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", RELEASE_DATE):
        raise ValueError(f"RELEASE_DATE {RELEASE_DATE!r} is not YYYY-MM-DD")
    if names_order(DEFAULT_ARCHIVE) or names_order(DEFAULT_NOTE):
        raise ValueError("a default file name names an order number")


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
    if names_order(text):
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
    if any(names_order(os.path.basename(path)) for path in sources):
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
            if names_order(archived):
                raise ValueError(f"archive entry names an order number: {os.path.basename(source)}")
            with open(source, "rb") as handle:
                if archived != handle.read():
                    raise ValueError(
                        f"archive entry differs from source: {os.path.basename(source)}"
                    )


def main():
    require_release_constants()
    args = parse_args()
    # release gate (2026-11-19): no component body may sit on another part or its pads; the DRC does not check this
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import release_body_gate
    try:
        release_body_gate.gate(PCB)
    except RuntimeError as exc:
        raise ValueError(str(exc)) from None
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
