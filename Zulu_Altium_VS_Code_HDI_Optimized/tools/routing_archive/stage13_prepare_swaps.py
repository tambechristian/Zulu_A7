# -*- coding: utf-8 -*-
"""Apply the Stage 13 FPGA ball permutation to the XDC and schematic.

Both edits are all-old or all-new operations. Mixed state, unexpected text,
duplicate labels, or an XDC pin collision aborts before either file is written.

    python tools/stage13_prepare_swaps.py <zulu_a7_pins.xdc> <zulu_a7_5.SchDoc>
"""
import hashlib
import os
import re
import sys

from fix_text_orientation import field, join, read_stream, set_field, split, write_stream


XDC_EDITS = [
    (80, "JA3", "G17", "W18", "IO_L16P_T2_CSI_B_14"),
    (49, "CHAN7", "H19", "G17", "IO_L5N_T0_D07_14"),
    (28, "CHAN13", "W18", "H19", "IO_L4P_T0_D04_14"),
    (82, "JA7", "T17", "R19", "IO_L10N_T1_D15_14"),
    (44, "CHAN28", "R19", "T17", "IO_L17P_T2_A14_D30_14"),
    (83, "JA8", "E19", "W19", "IO_L16N_T2_A15_D31_14"),
    (27, "CHAN12", "W19", "E19", "IO_L3N_T0_DQS_EMCCLK_14"),
    (104, "UART_FT_TXD", "K18", "K17", "IO_L12N_T1_MRCC_14"),
    (26, "CHAN11", "K17", "K18", "IO_L8N_T1_D12_14"),
    (86, "LED0_B", "N19", "N17", "IO_L13P_T2_MRCC_14"),
    (21, "BTN", "N17", "N19", "IO_L9N_T1_DQS_D13_14"),
    (76, "FT_PWREN_N", "P17", "P19", "IO_L10P_T1_D14_14"),
    (88, "LED0_R", "P19", "P17", "IO_L13N_T2_MRCC_14"),
]

SCH_EDITS = [
    (255, 952, "CHAN7", "CHAN13"),
    (255, 912, "CHAN11", "UART_FT_TXD"),
    (255, 892, "CHAN12", "JA8"),
    (255, 882, "CHAN13", "JA3"),
    (935, 802, "UART_FT_TXD", "CHAN11"),
    (235, 1132, "FT-PWREN#", "LED0_R"),
    (935, 357, "JA8", "CHAN12"),
    (935, 367, "JA7", "CHAN28"),
    (935, 387, "JA3", "CHAN7"),
    (740, 262, "LED0_B", "BTN"),
    (740, 252, "LED0_R", "FT-PWREN#"),
    (740, 212, "BTN", "LED0_B"),
    (740, 202, "CHAN28", "JA7"),
]


def md5(path):
    with open(path, "rb") as src:
        return hashlib.md5(src.read()).hexdigest()


def prepare_xdc(path):
    with open(path, encoding="utf-8") as src:
        text = src.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    states = []
    for line_no, port, old_pin, new_pin, _ in XDC_EDITS:
        line = lines[line_no - 1]
        match = re.search(r"PACKAGE_PIN\s+(\S+).*get_ports\s+\{([^}]*)\}", line)
        if match is None or match.group(2) != port:
            raise SystemExit("XDC line %d does not name port %s: %r" % (line_no, port, line))
        if match.group(1) == old_pin:
            states.append("old")
        elif match.group(1) == new_pin:
            states.append("new")
        else:
            raise SystemExit(
                "XDC line %d has pin %s; expected %s or %s"
                % (line_no, match.group(1), old_pin, new_pin)
            )
    if len(set(states)) != 1:
        raise SystemExit("XDC is in a mixed Stage 13 state; nothing written")

    if states[0] == "old":
        for line_no, _, old_pin, new_pin, function in XDC_EDITS:
            line = lines[line_no - 1]
            line = line.replace("PACKAGE_PIN %s " % old_pin, "PACKAGE_PIN %s " % new_pin, 1)
            line, count = re.subn(
                r"(;#\s+.*?\s+bank\s+14\s+).*$", lambda match: match.group(1) + function, line
            )
            if count != 1:
                raise SystemExit("XDC line %d has an unexpected comment: %r" % (line_no, line))
            lines[line_no - 1] = line
        new_text = newline.join(lines) + (newline if text.endswith(("\r\n", "\n")) else "")
    else:
        new_text = text

    pins = []
    for line in new_text.splitlines():
        match = re.search(r"PACKAGE_PIN\s+(\S+)", line)
        if match:
            pins.append(match.group(1))
    duplicates = sorted(pin for pin in set(pins) if pins.count(pin) > 1)
    if duplicates:
        raise SystemExit("XDC would contain duplicate PACKAGE_PIN values: %s" % duplicates)
    for line_no, port, _, new_pin, function in XDC_EDITS:
        line = new_text.splitlines()[line_no - 1]
        if (
            "PACKAGE_PIN %s " % new_pin not in line
            or "get_ports {%s}" % port not in line
            or function not in line
        ):
            raise SystemExit("XDC verification failed at line %d: %r" % (line_no, line))
    return text, new_text


def prepare_schematic(path):
    original = read_stream(path, "FileHeader")
    records = split(original)
    found = {}
    for record in records:
        body = record[1]
        if not body.startswith(b"|RECORD=25|"):
            continue
        x = field(body, "Location.X")
        y = field(body, "Location.Y")
        if x is None or y is None:
            continue
        key = (int(x), int(y))
        if key in {(edit[0], edit[1]) for edit in SCH_EDITS}:
            if key in found:
                raise SystemExit("duplicate schematic label at %s" % (key,))
            found[key] = (field(body, "Text"), record)

    states = []
    for x, y, old_name, new_name in SCH_EDITS:
        if (x, y) not in found:
            raise SystemExit("schematic label at (%d,%d) was not found" % (x, y))
        value = found[(x, y)][0]
        if value == old_name:
            states.append("old")
        elif value == new_name:
            states.append("new")
        else:
            raise SystemExit(
                "schematic label at (%d,%d) is %r; expected %r or %r"
                % (x, y, value, old_name, new_name)
            )
    if len(set(states)) != 1:
        raise SystemExit("schematic is in a mixed Stage 13 state; nothing written")

    if states[0] == "old":
        for x, y, _, new_name in SCH_EDITS:
            record = found[(x, y)][1]
            record[1] = set_field(record[1], "Text", new_name)
    updated = join(records)
    if len(updated) != len(original):
        raise SystemExit(
            "schematic stream length changed from %d to %d; nothing written"
            % (len(original), len(updated))
        )
    return original, updated


def main(xdc_path, schematic_path):
    old_xdc, new_xdc = prepare_xdc(xdc_path)
    old_sch, new_sch = prepare_schematic(schematic_path)
    changed = old_xdc != new_xdc or old_sch != new_sch
    if not changed:
        print("Stage 13 XDC and schematic swaps are already applied")
        return

    with open(xdc_path, "w", encoding="utf-8", newline="") as dst:
        dst.write(new_xdc)
    write_stream(schematic_path, "FileHeader", new_sch)

    if prepare_xdc(xdc_path)[1] != new_xdc:
        raise SystemExit("XDC readback verification failed")
    if prepare_schematic(schematic_path)[1] != new_sch:
        raise SystemExit("schematic readback verification failed")
    print("Applied 13 Stage 13 ball swaps")
    print("XDC md5:", md5(xdc_path))
    print("SchDoc md5:", md5(schematic_path))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: stage13_prepare_swaps.py <zulu_a7_pins.xdc> <zulu_a7_5.SchDoc>")
    for argument in sys.argv[1:]:
        if not os.path.isfile(argument):
            raise SystemExit("not a file: " + argument)
    main(sys.argv[1], sys.argv[2])
