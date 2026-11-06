# -*- coding: utf-8 -*-
"""U2: FT2232HQ (QFN-64, no authorized stock until April 2027) -> FT2232HL (LQFP-64), 2026-09-09.

DS_FT2232H v2.10 section 3.1: "The 64-pin LQFP and 64-pin QFN have the same pin numbering for
specific functions" and "Both the LQFP and the QFN packages have the same function on each pin",
so every wire stays where it is. What changes on sheet 4: the part number, comment, the visible
FT2232HQ label, device/deviceset names, component description and footprint model
(FT2232HL-LQFP64, to be drawn from Figure 8.2: 10 x 10 mm body, 12 x 12 mm over leads, 0.5 mm
pitch, JEDEC MS-026 BCD); SPEC and NOTE parameters are inserted after MANF#; and the QFN's
exposed-pad pin EP, which the LQFP does not have, is removed together with its ground stub (the
GND bus wire along y=552 is shortened to the last GND pin stub). Sheet 4's title text and the
block on sheet 0 are renamed. Every later OwnerIndex is renumbered and the header Weight set.
Refuses to run twice.

    python tools/u2_ft2232hl.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

SPEC = ('USB 2.0 Hi-Speed dual-channel UART/FIFO/MPSSE bridge, LQFP-64 10 x 10 mm body, 12 x 12 mm over leads, 0.5 mm pitch, '
        'JEDEC MS-026 BCD, no exposed pad; same die and pin numbering as the FT2232HQ (DS_FT2232H v2.10 section 3.1); channel A '
        'MPSSE JTAG + PROG#/DONE, channel B UART; 12 MHz CMOS oscillator into OSCI, internal 1.8 V regulator, 93LC46B EEPROM, '
        'REF 12 k; replaced the FT2232HQ (0 stock until April 2027) on 2026-09-09')
NOTE = ('FT2232HL-REEL: Digi-Key 0 with 1,000 expected 19-Feb-2027 ($5.30, 50-week lead); LCSC C27882 4,767 in stock at $11.45 '
        '(not an FTDI-authorized channel: name it explicitly or consign for a PCBWay build). Pin numbers unchanged from the '
        'FT2232HQ; the QFN exposed pad (pin EP, GND) has no LQFP counterpart, so that pin and its ground stub were removed. '
        'thetaJA 37.66 C/W for the LQFP vs 29.67 for the QFN (DS_FT2232H Table 5.7). Footprint FT2232HL-LQFP64 to be drawn from '
        'Figure 8.2 or FTDI TN_166. Alternates on the same pin numbers: FT2232HQ (QFN-64) and FT4232HL / FT4232HQ (UART lands '
        'on channel C, EEPROM re-templated, PID 0x6011); the FT2232H-56Q keeps every signal but renumbers every pin.')
DESC = ('FTDI FT2232HL Dual USB-UART/MPSSE Bridge, LQFP-64. Channel A = MPSSE JTAG to the FPGA (ADBUS0-3 = TCK/TDI/TDO/TMS, '
        'ADBUS4/5 = PROG#/DONE). Channel B = UART (BDBUS0-4 = TXD/RXD/RTS#/CTS#/DTR#). Same pin numbering as the FT2232HQ, '
        'no exposed pad. Replaced the FT2232HQ on 2026-09-09.')


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def num(b, k):
    v = field(b, k); return int(v) if v is not None else None


def parents(rs):
    out = {}
    for h, b in rs:
        u = field(b, 'UniqueID'); oi = field(b, 'OwnerIndex')
        if u and oi is not None:
            pb = rs[int(oi) + 1][1]
            out[u] = (b[:12], pb[:12], field(pb, 'UniqueID'))
    return out


def sheet4(path):
    recs = split(read_stream(path, 'FileHeader'))
    head = recs[0][1]
    assert int(field(head, 'Weight')) == len(recs) - 1
    des = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    comp = [i for i, d in des.items() if d == 'U2']
    assert len(comp) == 1, comp
    ci = comp[0]; obj = ci - 1
    c = recs[ci][1]
    assert field(c, 'LibReference') == 'FT2232HQ-QFN64', 'already applied'
    c = set_field(c, 'LibReference', 'FT2232HL-LQFP64')
    c = set_field(c, 'ComponentDescription', DESC)
    recs[ci][1] = c
    prm, pins = {}, {}
    for i, (h, b) in enumerate(recs):
        oi = field(b, 'OwnerIndex')
        if oi is None or int(oi) != obj: continue
        if b.startswith(b'|RECORD=41|'): prm[field(b, 'Name')] = i
        elif b.startswith(b'|RECORD=2|'): pins[field(b, 'Designator')] = i
    assert field(recs[prm['MANF#']][1], 'Text') == 'FT2232HQ-REEL'
    recs[prm['MANF#']][1] = set_field(recs[prm['MANF#']][1], 'Text', 'FT2232HL-REEL')
    recs[prm['Comment']][1] = set_field(recs[prm['Comment']][1], 'Text', 'FT2232HL USB-UART/JTAG Bridge')
    recs[prm['DeviceName']][1] = set_field(recs[prm['DeviceName']][1], 'Text', '-LQFP64')
    recs[prm['DeviceSetName']][1] = set_field(recs[prm['DeviceSetName']][1], 'Text', 'FT2232HL')
    lbl = prm['FT2232HQ']                       # the visible label on the symbol, a parameter named after the part
    recs[lbl][1] = set_field(set_field(recs[lbl][1], 'Text', 'FT2232HL'), 'Name', 'FT2232HL')
    # footprint model
    i44 = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=44|') and int(field(b, 'OwnerIndex')) == obj]
    i45 = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=45|') and int(field(b, 'OwnerIndex')) == i44[0] - 1]
    assert len(i44) == 1 and len(i45) == 1 and field(recs[i45[0]][1], 'ModelName') == 'FT2232HQ-QFN64'
    recs[i45[0]][1] = set_field(recs[i45[0]][1], 'ModelName', 'FT2232HL-LQFP64')
    # sheet title text
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=4|') and field(b, 'Text') == 'FT2232HQ, JTAG, CLOCK':
            recs[i][1] = set_field(b, 'Text', 'FT2232HL, JTAG, CLOCK')
    # the exposed-pad pin and its ground stub
    ep = pins['EP']; epb = recs[ep][1]
    ex, ey = num(epb, 'Location.X'), num(epb, 'Location.Y')
    assert (ex, ey) == (532, 592) and num(epb, 'PinLength') == 30
    delete = {ep}
    for i, (h, b) in enumerate(recs):                       # anything the pin owns
        if field(b, 'OwnerIndex') is not None and int(field(b, 'OwnerIndex')) == ep - 1: delete.add(i)
    stub = bus = None
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=27|'):
            pts = [(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, num(b, 'LocationCount') + 1)]
            if pts == [(532, 552), (532, 562)]: stub = i
            if pts[0] == (342, 552) and pts[-1] == (532, 552): bus = i
    assert stub is not None and bus is not None
    delete.add(stub)
    b = recs[bus][1]
    n = num(b, 'LocationCount')
    recs[bus][1] = set_field(b, 'X%d' % n, '512')          # bus now ends on the last GND pin stub (pin 51)
    # parent map before the structural edit, minus the deleted records
    before = {u: v for u, v in parents(recs).items() if all(field(recs[i][1], 'UniqueID') != u for i in delete)}
    old_owner, new_recs, old_to_new = {}, [], {}
    for i, (h, b) in enumerate(recs):
        if i in delete: continue
        old_to_new[i] = len(new_recs)
        new_recs.append([h, b])
        oi = field(b, 'OwnerIndex')
        if oi is not None: old_owner[id(new_recs[-1])] = int(oi) + 1
        if i == prm['MANF#']:
            for k, (name, text) in enumerate([('SPEC', SPEC), ('NOTE', NOTE)], 1):
                nb = set_field(set_field(set_field(set_field(b, 'Text', text), 'Name', name), 'UniqueID', uid()), 'IndexInSheet', str(900 + k))
                new_recs.append([h, nb])
                old_owner[id(new_recs[-1])] = ci
    for r in new_recs:
        if id(r) in old_owner:
            r[1] = set_field(r[1], 'OwnerIndex', str(old_to_new[old_owner[id(r)]] - 1))
    new_recs[0][1] = set_field(head, 'Weight', str(len(new_recs) - 1))
    after = parents(new_recs)
    changed = [u for u in before if before[u] != after.get(u)]
    assert not changed, changed[:5]
    assert len(new_recs) == len(recs) - len(delete) + 2
    out = join(new_recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'sheet 4: U2 -> FT2232HL-REEL, {len(delete)} records removed (EP pin and stub), SPEC/NOTE inserted, {len(new_recs) - 1} records')


def sheet0(path):
    recs = split(read_stream(path, 'FileHeader'))
    n = 0
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=4|') and field(b, 'Text') == 'FT2232HQ':
            recs[i][1] = set_field(b, 'Text', 'FT2232HL'); n += 1
    assert n == 1, n
    out = join(recs); write_stream(path, 'FileHeader', out); assert read_stream(path, 'FileHeader') == out
    print('sheet 0: block label FT2232HQ -> FT2232HL')


if __name__ == '__main__':
    prj = sys.argv[2]
    sheet4(os.path.join(prj, 'zulu_a7_4.SchDoc'))
    sheet0(os.path.join(prj, 'zulu_a7_0.SchDoc'))
