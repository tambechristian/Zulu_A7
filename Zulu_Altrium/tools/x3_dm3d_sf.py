# -*- coding: utf-8 -*-
"""Turn X3 (sheet 3, Memory) from the Hirose DM3AT-SF-PEJM5 push-push microSD
socket into the DM3D-SF push-pull one (HRS 609-0025-8), 2026-09-06.

Source: Datasheet/DM3AT-SF-PEJM5.pdf is the whole DM3 catalog; page 9 is the
DM3D-SF page (drawing, pin names, PCB pattern).  Both parts carry the same
eight microSD contacts (#1 DAT2 .. #8 DAT1, leftmost pad #8 seen from the top
with the card entering from the bottom), four solder points on the metal
cover, and a card-detection switch whose two terminals (A) and (B) are open
without a card and closed with one.

What changes on the sheet:
  * part identity: LibReference/DesignItemId MICROSD_CONDM3D-SF, description,
    Comment, DeviceName, MANF# = DM3D-SF, new hidden HRS# and SPEC parameters,
    footprint model name DM3D-SF (the footprint itself is drawn at the PCB
    stage from the catalog pattern; the DM3AT one does not fit)
  * the two multi-pad shell pins 'G1,3' and 'G2,4' (an EAGLE import artefact,
    one pin owning two pads) become four pins G1..G4, all GND, all on the
    existing GND bus above the body
  * two new pins A and B for the card-detection switch on the bottom edge,
    left unconnected with No-ERC markers; wire B to a pull-up and an FPGA pin
    if hardware card detect is ever wanted
  * a dated note under the part

Pins 1-8 and their nets are untouched.  New pin records are inserted right
after X3's own records, every later OwnerIndex is shifted, and the loose
wires, junction, markers and note go at the end of the record list.

Run with the project closed in Altium:
    python tools/x3_dm3d_sf.py tools "Imported zulu_a7.PrjPcb/zulu_a7_3.SchDoc"
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))

def rec(body):
    body = body if isinstance(body, bytes) else body.encode()
    return [bytes(4), body + bytes(1)]          # every record ends with a NUL

def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    # ---- find X3 ---------------------------------------------------------
    x3 = [int(field(b, 'OwnerIndex')) + 1 for h, b in recs
          if b.startswith(b'|RECORD=34|') and field(b, 'Text') == 'X3']
    if len(x3) != 1:
        raise SystemExit(f'expected one X3, found {x3}')
    ci = x3[0]
    comp = recs[ci][1]
    if field(comp, 'LibReference') != 'MICROSD_CONDM3AT-SF-PEJM5':
        raise SystemExit(f"X3 is {field(comp, 'LibReference')}, not the DM3AT part; nothing done")
    own = str(ci - 1)
    kids = [i for i, (h, b) in enumerate(recs) if field(b, 'OwnerIndex') == own]
    # nested implementation records (44 -> 45 -> 46/48)
    lvl = kids
    tree = set(kids)
    while lvl:
        nxt = [i for i, (h, b) in enumerate(recs) if field(b, 'OwnerIndex') in {str(j - 1) for j in lvl}]
        nxt = [i for i in nxt if i not in tree]
        tree |= set(nxt)
        lvl = nxt
    last = max(tree)
    done = []
    # ---- component record --------------------------------------------------
    c = comp
    for k in ('LibReference', 'DesignItemId'):
        c = set_field(c, k, 'MICROSD_CONDM3D-SF')
    c = set_field(c, 'ComponentDescription', 'microSD socket, push-pull, Hirose DM3D-SF')
    if field(c, 'AllPinCount'):
        c = set_field(c, 'AllPinCount', str(int(field(c, 'AllPinCount')) + 4))
    recs[ci][1] = c
    done.append('component identity')
    # ---- children: pins, parameters, footprint -----------------------------
    pin_tpl = None
    for i in sorted(tree):
        b = recs[i][1]
        if b.startswith(b'|RECORD=2|'):
            d = field(b, 'Designator')
            if d == 'G1,3':
                recs[i][1] = set_field(b, 'Designator', 'G1'); done.append('pin G1,3 -> G1'); pin_tpl = recs[i][1]
            elif d == 'G2,4':
                recs[i][1] = set_field(b, 'Designator', 'G2'); done.append('pin G2,4 -> G2')
        elif b.startswith(b'|RECORD=41|'):
            n = field(b, 'Name')
            if n in ('DeviceName', 'MANF#'):
                recs[i][1] = set_field(b, 'Text', 'DM3D-SF'); done.append(f'{n} -> DM3D-SF')
            elif n == 'Comment':
                b = set_field(b, 'Text', 'DM3D-SF')
                b = set_field(b, 'Location.X', '290')          # right-aligned, clear of the new pins
                recs[i][1] = b; done.append('Comment -> DM3D-SF at (290,802)')
        elif b.startswith(b'|RECORD=45|') and field(b, 'ModelName') == 'DM3AT-SF-PEJM5':
            recs[i][1] = set_field(b, 'ModelName', 'DM3D-SF'); done.append('footprint -> DM3D-SF')
    if pin_tpl is None:
        raise SystemExit('shell pin G1,3 not found')
    # ---- new child records, inserted after X3's tree -----------------------
    def pin(des, name, x, y, cong):
        b = pin_tpl
        b = set_field(b, 'Designator', des); b = set_field(b, 'Name', name)
        b = set_field(b, 'Location.X', str(x)); b = set_field(b, 'Location.Y', str(y))
        b = set_field(b, 'PinConglomerate', str(cong)); b = set_field(b, 'Electrical', '4')
        b = set_field(b, 'UniqueID', uid())
        return rec(b)
    new_kids = [
        pin('G3', 'GND', 355, 897, 57),      # up, hot end (355,917)
        pin('G4', 'GND', 365, 897, 57),      # up, hot end (365,917)
        pin('A', 'SW_A', 345, 807, 59),      # down, hot end (345,787)
        pin('B', 'SW_B', 355, 807, 59),      # down, hot end (355,787)
        rec(f'|RECORD=41|OwnerIndex={own}|IndexInSheet=-1|OwnerPartId=1|Color=8421504|FontID=3|IsHidden=T|Text=609-0025-8|Name=HRS#|UniqueID={uid()}'),
        rec(f'|RECORD=41|OwnerIndex={own}|IndexInSheet=-1|OwnerPartId=1|Color=8421504|FontID=3|IsHidden=T|Text=microSD push-pull (no eject), top mount, 0.5 A; 8 contacts + 4 shell pads G1-G4 + card-detect switch A/B (open without card); DM3 catalog p9|Name=SPEC|UniqueID={uid()}'),
    ]
    n = len(new_kids)
    p = last + 1                                   # list position of the first inserted record
    for i, (h, b) in enumerate(recs):
        o = field(b, 'OwnerIndex')
        if o is not None and int(o) + 1 >= p:
            recs[i][1] = set_field(b, 'OwnerIndex', str(int(o) + n))
    recs[p:p] = new_kids
    done.append(f'{n} records inserted at {p}')
    # ---- loose records at the end ------------------------------------------
    def wire(x1, y1, x2, y2):
        return rec(f'|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID={uid()}|LocationCount=2|X1={x1}|Y1={y1}|X2={x2}|Y2={y2}')
    loose = [
        wire(355, 917, 355, 927), wire(365, 917, 365, 927), wire(355, 927, 375, 927),
        rec(f'|RECORD=29|OwnerPartId=-1|Location.X=365|Location.Y=927|Color=128|Locked=T|UniqueID={uid()}'),
        rec(f'|RECORD=22|OwnerPartId=-1|Location.X=345|Location.Y=787|Color=255|Symbol=Thin Cross|IsActive=T|SuppressAll=T|UniqueID={uid()}'),
        rec(f'|RECORD=22|OwnerPartId=-1|Location.X=355|Location.Y=787|Color=255|Symbol=Thin Cross|IsActive=T|SuppressAll=T|UniqueID={uid()}'),
        rec(f'|RECORD=4|OwnerPartId=-1|Location.X=70|Location.Y=722|Orientation=0|Color=8421504|FontID=3|Text=2026-09-06: X3 is now the Hirose DM3D-SF push-pull socket (HRS 609-0025-8), DM3 catalog p9. Same 8-contact pinout;|UniqueID={uid()}'),
        rec(f'|RECORD=4|OwnerPartId=-1|Location.X=70|Location.Y=712|Orientation=0|Color=8421504|FontID=3|Text=shell pads G1-G4 to GND; card-detect switch A/B (closed with card) left open. Needs its own footprint on the PCB.|UniqueID={uid()}'),
    ]
    recs.extend(loose)
    done.append(f'{len(loose)} loose records appended')
    hdr = recs[0][1]
    recs[0][1] = set_field(hdr, 'Weight', str(int(field(hdr, 'Weight')) + n + len(loose)))
    out = join(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'{len(recs)} records; ' + '; '.join(done))

if __name__ == '__main__':
    main(sys.argv[2])
