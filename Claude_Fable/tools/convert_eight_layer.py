# -*- coding: utf-8 -*-
"""Convert the synchronized Zulu A7 board pair to the eight-layer build."""

import io
import os
import re
import xml.etree.ElementTree as ET


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
SCH = os.path.join(ROOT, "zulu_a7.sch")

U2_X = 33.108
U2_Y = 12.208
THERMAL_OFFSETS = (-1.2, 0.0, 1.2)

PASTE_RECTS = "\n".join(
    '<rectangle x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" layer="31"/>'
    % (x - 0.625, y - 0.625, x + 0.625, y + 0.625)
    for y in (-1.5, 0.0, 1.5)
    for x in (-1.5, 0.0, 1.5)
)

THERMAL_VIAS = "\n".join(
    '<via x="%.3f" y="%.3f" extent="1-16" drill="0.2" diameter="0.3">\n</via>'
    % (U2_X + x, U2_Y + y)
    for y in THERMAL_OFFSETS
    for x in THERMAL_OFFSETS
)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise ValueError("%s: expected one occurrence, found %d" % (label, count))
    return text.replace(old, new, 1)


def improve_package(text):
    match = re.search(
        r'(<package name="FT2232HQ-QFN64">)(.*?)(</package>)', text, re.S)
    if not match:
        raise ValueError("FT2232HQ-QFN64 package not found")
    body = match.group(2)
    body = replace_once(
        body,
        '<description>&lt;b&gt;FTDI FT2232HQ, 64-pin 9x9mm QFN, 0.5mm pitch&lt;/b&gt;</description>',
        '<description>&lt;b&gt;FTDI FT2232HQ, 64-pin 9x9mm QFN, 0.5mm pitch&lt;/b&gt;'
        '&lt;p&gt;EP paste is a 3x3 window array: 9 x 1.25mm square apertures, '
        '57.4% nominal coverage. The board adds nine 0.20/0.30mm through vias; '
        'fabricate them as IPC-4761 Type VII resin-filled, copper-capped and '
        'planarized via-in-pad.</description>',
        "package description")
    body = replace_once(
        body,
        '<smd name="EP" x="0" y="0" dx="4.95" dy="4.95" layer="1"/>',
        '<smd name="EP" x="0" y="0" dx="4.95" dy="4.95" layer="1" cream="no"/>\n'
        + PASTE_RECTS,
        "EP paste definition")
    return text[:match.start()] + match.group(1) + body + match.group(3) + text[match.end():]


def update_default_pass(board):
    match = re.search(r'(<pass name="Default">)(.*?)(</pass>)', board, re.S)
    if not match:
        raise ValueError("Default autorouter pass not found")
    body = match.group(2)
    directions = {
        1: "*",
        2: "0",
        3: "-",
        4: "|",
        5: "0",
        6: "|",
        7: "-",
        16: "*",
    }
    for layer, direction in directions.items():
        body, count = re.subn(
            r'(<param name="PrefDir\.%d" value=")[^"]+("/>)' % layer,
            r'\g<1>%s\2' % direction, body)
        if count != 1:
            raise ValueError("PrefDir.%d: expected one occurrence, found %d"
                             % (layer, count))
    for layer in (2, 5):
        body, count = re.subn(
            r'(<param name="cfBase\.%d" value=")[^"]+("/>)' % layer,
            r'\g<1>99\2', body)
        if count != 1:
            raise ValueError("cfBase.%d: expected one occurrence, found %d"
                             % (layer, count))
    return (board[:match.start()] + match.group(1) + body + match.group(3)
            + board[match.end():])


def improve_board(board):
    board = improve_package(board)
    board = replace_once(
        board,
        '<layer number="6" name="Route6" color="25" fill="1" visible="no" active="no"/>',
        '<layer number="6" name="Route6" color="25" fill="1" visible="yes" active="yes"/>',
        "Route6 activation")
    board = replace_once(
        board,
        '<layer number="7" name="Route7" color="26" fill="1" visible="no" active="no"/>',
        '<layer number="7" name="Route7" color="26" fill="1" visible="yes" active="yes"/>',
        "Route7 activation")
    board = replace_once(
        board,
        '<designrules name="Zulu A7 6 layer PCBWay">',
        '<designrules name="Zulu A7 8 layer PCBWay">',
        "design-rule name")
    board = replace_once(
        board,
        '<param name="layerSetup" value="(1*2*3*4*5*16)"/>',
        '<param name="layerSetup" value="[5:(1+2+3+4+5*6+7+16):5]"/>',
        "layer setup")
    board, count = re.subn(
        r'<param name="mtCopper" value="[^"]+"/>',
        '<param name="mtCopper" value="0.035mm 0.018mm 0.018mm 0.018mm '
        '0.018mm 0.018mm 0.018mm 0.035mm 0.035mm 0.035mm 0.035mm '
        '0.035mm 0.035mm 0.035mm 0.035mm 0.035mm"/>',
        board, count=1)
    if count != 1:
        raise ValueError("mtCopper update failed")
    board, count = re.subn(
        r'<param name="mtIsolate" value="[^"]+"/>',
        '<param name="mtIsolate" value="0.12mm 0.20mm 0.25mm 0.282mm '
        '0.25mm 0.20mm 0.12mm 0.15mm 0.2mm 0.15mm 0.2mm 0.15mm '
        '0.2mm 0.15mm 0.2mm"/>',
        board, count=1)
    if count != 1:
        raise ValueError("mtIsolate update failed")

    dr = re.search(r'(<designrules name="Zulu A7 8 layer PCBWay">)(.*?)(</designrules>)',
                   board, re.S)
    if not dr:
        raise ValueError("eight-layer design-rules block not found")
    dr_body, count = re.subn(
        r'<description language="en">.*?</description>',
        '<description language="en">&lt;b&gt;Zulu A7 - 8-layer PCBWay build&lt;/b&gt;'
        '&lt;p&gt;Provisional symmetric 1.6mm stack for layout: L1 signal, L2 solid '
        'GND, L3 horizontal signal, L4 vertical signal, L5 VCC3V3 plane, '
        'L6 vertical signal, L7 horizontal signal, L8 bottom signal. Final dielectric '
        'and copper values require PCBWay pre-production stackup approval. '
        'U2 exposed-pad vias require IPC-4761 Type VII resin fill, copper cap and '
        'planarization; simple open or tented vias are not an approved substitute.'
        '</description>',
        dr.group(2), count=1, flags=re.S)
    if count != 1:
        raise ValueError("design-rule description update failed")
    board = (board[:dr.start()] + dr.group(1) + dr_body + dr.group(3)
             + board[dr.end():])

    vcc = re.search(r'(<signal name="VCC3V3">)(.*?)(</signal>)', board, re.S)
    if not vcc:
        raise ValueError("VCC3V3 signal not found")
    vcc_body, count = re.subn(
        r'(<polygon\b[^>]*\blayer=")5("[^>]*>)', r'\g<1>5\2',
        vcc.group(2), count=1)
    if count != 1:
        raise ValueError("expected one VCC3V3 plane on layer 5")
    board = (board[:vcc.start()] + vcc.group(1) + vcc_body + vcc.group(3)
             + board[vcc.end():])

    gnd = re.search(r'(<signal name="GND">)(.*?)(</signal>)', board, re.S)
    if not gnd:
        raise ValueError("GND signal not found")
    gnd_body = gnd.group(2)
    old_via = (r'<via x="32\.8019" y="11\.4689" extent="1-16" drill="0\.2" '
               r'diameter="0\.3">\s*</via>\s*')
    gnd_body, via_count = re.subn(old_via, "", gnd_body, count=1)
    old_wire = (r'<wire x1="33\.108" y1="12\.208" x2="32\.8019" y2="11\.4689" '
                r'width="0\.3" layer="1"/>\s*')
    gnd_body, wire_count = re.subn(old_wire, "", gnd_body, count=1)
    if (via_count, wire_count) != (1, 1):
        raise ValueError("legacy U2 EP via/wire not found exactly once")
    gnd_body = "\n" + THERMAL_VIAS + gnd_body
    board = (board[:gnd.start()] + gnd.group(1) + gnd_body + gnd.group(3)
             + board[gnd.end():])

    fab_note = (
        '<text x="0" y="59.0" size="0.6" layer="48" ratio="10">'
        'FAB NOTE: U2 EP - 9x 0.20mm FINISHED VIA-IN-PAD; IPC-4761 TYPE VII '
        'RESIN FILLED, COPPER CAPPED, PLANARIZED. DO NOT SUBSTITUTE TENTING.'
        '</text>\n')
    board = replace_once(board, "<plain>\n", "<plain>\n" + fab_note,
                         "fabrication note")
    return update_default_pass(board)


def write_checked(path, text):
    ET.fromstring(text)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    schematic = io.open(SCH, encoding="utf-8", errors="replace").read()
    improved_board = improve_board(board)
    improved_schematic = improve_package(schematic)
    write_checked(BRD, improved_board)
    write_checked(SCH, improved_schematic)
    print("converted synchronized board/schematic to eight layers")
    print("U2 EP paste coverage: %.1f%%" % (100.0 * 9 * 1.25 * 1.25 / (4.95 * 4.95)))
    print("U2 EP thermal vias: 9, 0.20mm drill / 0.30mm land, 1.20mm pitch")


if __name__ == "__main__":
    main()
