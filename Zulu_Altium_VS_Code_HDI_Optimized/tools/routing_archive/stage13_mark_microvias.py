"""Mark scripted adjacent-layer laser vias as Altium microvias.

Altium's DelphiScript IPCB_Via interface exposes the start/end layers but not
the drill-pair type. A via created through PCBObjectFactory therefore defaults
to a regular blind/buried via even when its span matches a microvia type in the
layer stack. Stage 13 converts the former L2/L5 internal planes to signal
layers, whose saved layer IDs are 4 and 5. In the Vias6 record, byte 312 is
TDrillLayerPairType:
0 = regular, 1 = microvia. This offset was verified by changing one probe via
from "Blind 1:2" to "uVia 1:2" in Altium and comparing the saved records.
"""

import argparse
import collections
import os
import shutil
import struct
import sys

import olefile

from fix_text_orientation import read_stream


UNIT_MM = 2.54e-6
VIA_RECORD_TYPE = 3
DRILL_PAIR_TYPE_OFFSET = 312
REGULAR_DRILL = 0
MICROVIA_DRILL = 1

LAYER_NAMES = {
    1: "Top",
    2: "L3-SIG",
    3: "L4-SIG",
    4: "L2-GND",
    5: "L5-VCC3V3",
    32: "Bottom",
}

MICROVIA_PAIRS = {
    (1, 4),
    (4, 2),
    (3, 5),
    (5, 32),
}


def is_mm(value, expected):
    return abs(value * UNIT_MM - expected) < 0.00001


def mark_stream(data):
    out = bytearray(data)
    counts = collections.Counter()
    changed = 0
    candidates = 0
    offset = 0

    while offset + 5 <= len(data):
        record_type = data[offset]
        length = struct.unpack("<I", data[offset + 1 : offset + 5])[0]
        body_start = offset + 5
        body_end = body_start + length
        if body_end > len(data):
            raise ValueError("Vias6 record extends beyond the stream")

        if record_type == VIA_RECORD_TYPE:
            if length <= DRILL_PAIR_TYPE_OFFSET:
                raise ValueError("Vias6 via record is too short for drill-pair type")
            body = data[body_start:body_end]
            pair = (body[29], body[30])
            size = struct.unpack("<i", body[21:25])[0]
            hole = struct.unpack("<i", body[25:29])[0]
            marker = body[DRILL_PAIR_TYPE_OFFSET]

            if pair in MICROVIA_PAIRS and is_mm(size, 0.30) and is_mm(hole, 0.15):
                candidates += 1
                counts[pair] += 1
                if marker not in (REGULAR_DRILL, MICROVIA_DRILL):
                    raise ValueError(
                        "unexpected drill-pair type %d for candidate at record offset %d"
                        % (marker, offset)
                    )
                if marker == REGULAR_DRILL:
                    out[body_start + DRILL_PAIR_TYPE_OFFSET] = MICROVIA_DRILL
                    changed += 1

        offset = body_end

    if offset != len(data):
        raise ValueError("trailing bytes in Vias6 stream")
    return bytes(out), candidates, changed, counts


def pair_label(pair):
    return "%s -> %s" % (LAYER_NAMES[pair[0]], LAYER_NAMES[pair[1]])


def write_vias_stream(path, data):
    with olefile.OleFileIO(path, write_mode=True) as pcb:
        pcb.write_stream("Vias6/Data", data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pcbdoc")
    parser.add_argument("--expect", type=int, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    path = os.path.abspath(args.pcbdoc)
    data = read_stream(path, "Vias6/Data")
    marked, candidates, changed, counts = mark_stream(data)

    if candidates != args.expect:
        print(
            "REFUSED: found %d laser-via candidates, expected %d"
            % (candidates, args.expect)
        )
        return 1

    for pair in sorted(counts):
        print("%-22s %d" % (pair_label(pair), counts[pair]))

    if args.verify:
        if changed:
            print("VERIFY FAILED: %d candidate via(s) are still regular" % changed)
            return 1
        print("verified %d Altium microvia record(s)" % candidates)
        return 0

    if not changed:
        print("already marked: %d Altium microvia record(s)" % candidates)
        return 0

    if not args.no_backup:
        backup = path + ".pre-microvia"
        if os.path.exists(backup):
            print("REFUSED: backup already exists: %s" % backup)
            return 1
        shutil.copy2(path, backup)
        print("backup: %s" % backup)

    write_vias_stream(path, marked)
    reread = read_stream(path, "Vias6/Data")
    if reread != marked:
        print("WRITE FAILED: saved Vias6 stream did not read back byte-for-byte")
        return 1
    _, reread_candidates, reread_changed, _ = mark_stream(reread)
    if reread_candidates != candidates or reread_changed:
        print("WRITE FAILED: microvia records did not verify after save")
        return 1

    print("marked %d of %d Altium via record(s) as microvias" % (changed, candidates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
