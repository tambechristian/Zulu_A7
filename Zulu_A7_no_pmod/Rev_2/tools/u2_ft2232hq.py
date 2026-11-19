# -*- coding: utf-8 -*-
"""Convert Rev_2 sheet 4 from FT2232HL/LQFP-64 back to FT2232HQ/QFN-64.

Run only while the SchDoc is closed. The 64 signal pins keep their numbering and
connections; this restores the QFN identity, footprint model, grounded EP pin,
and EP ground stub removed by u2_ft2232hl.py.

    python tools/u2_ft2232hq.py "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import os
import random
import re
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_text_orientation import field, join, read_stream, set_field, split, write_stream


SPEC = (
    'USB 2.0 Hi-Speed dual-channel UART/FIFO/MPSSE bridge, QFN-64 9 x 9 mm body, '
    '0.5 mm pitch, 4.35 mm package exposed pad on a 4.20 mm PCB land; same die and '
    'pin numbering as FT2232HL; channel A MPSSE JTAG + PROG#/DONE, channel B UART; '
    '12 MHz CMOS oscillator into OSCI, internal 1.8 V regulator, 93LC46B EEPROM, REF 12 k'
)
NOTE = (
    'FT2232HQ-REEL. Use FTDI-authorized distribution because counterfeit FTDI devices exist. '
    'Pins 1-64 match FT2232HL. EP is a separate schematic pin tied to GND as required by '
    'DS_FT2232H section 8.1. Footprint FT2232HQ-QFN64 uses 0.75 x 0.28 mm perimeter lands '
    'and a 4.20 mm exposed-pad land.'
)
DESC = (
    'FTDI FT2232HQ Dual USB-UART/MPSSE Bridge, QFN-64. Channel A = MPSSE JTAG to the FPGA '
    '(ADBUS0-3 = TCK/TDI/TDO/TMS, ADBUS4/5 = PROG#/DONE). Channel B = UART '
    '(BDBUS0-4 = TXD/RXD/RTS#/CTS#/DTR#). Pins 1-64 match FT2232HL; EP is grounded.'
)

EP_PIN = (
    b'|RECORD=2|OwnerIndex=0|OwnerPartId=1|FormalType=1|Electrical=7|PinConglomerate=59|'
    b'PinLength=30|Location.X=532|Location.Y=592|Color=128|Name=EP|Designator=EP|'
    b'%UTF8%SwapIDPart=\xc2\xa6&\xc2\xa6|||SwapIDPart=\x8e&\x8e||'
    b'PinName_PositionConglomerate=17|Name_CustomPosition_Margin=7|'
    b'Name_CustomPosition_Margin_Frac=50000|Name_CustomFontID=3|Name_CustomColor=8421504|'
    b'PinDesignator_PositionConglomerate=17|Designator_CustomPosition_Margin=7|'
    b'Designator_CustomPosition_Margin_Frac=50000|Designator_CustomFontID=3|'
    b'Designator_CustomColor=8421504|PinPropagationDelay=0.000000E+000|UniqueID=PINUID\x00'
)
EP_HIDDEN_NET = (
    b'|RECORD=41|OwnerIndex=0|OwnerPartId=-1|Color=8388608|FontID=1|Text=GND|'
    b'Name=HiddenNetName|UniqueID=HIDDENID\x00'
)
EP_PIN_UID = (
    b'|RECORD=41|OwnerIndex=0|IndexInSheet=1|OwnerPartId=-1|Location.X=532|Location.Y=592|'
    b'Color=8388608|FontID=1|IsHidden=T|Text=PINUID|Name=PinUniqueId|UniqueID=PARAMUID\x00'
)
EP_STUB = (
    b'|RECORD=27|IndexInSheet=0|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID=STUBUID|'
    b'LocationCount=2|X1=532|Y1=552|X2=532|Y2=562\x00'
)
EP_BUS_EXT = (
    b'|RECORD=27|IndexInSheet=0|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID=EXTUID|'
    b'LocationCount=2|X1=512|Y1=552|X2=532|Y2=552\x00'
)


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def num(body, key):
    value = field(body, key)
    return int(value) if value is not None else None


def points(body):
    return [(num(body, 'X%d' % k), num(body, 'Y%d' % k))
            for k in range(1, num(body, 'LocationCount') + 1)]


def convert(path):
    records = split(read_stream(path, 'FileHeader'))
    header = records[0][1]
    assert int(field(header, 'Weight')) == len(records) - 1

    designators = {
        int(field(body, 'OwnerIndex')) + 1: field(body, 'Text')
        for _, body in records if field(body, 'RECORD') == '34'
    }
    component_indexes = [i for i, text in designators.items() if text == 'U2']
    if len(component_indexes) != 1:
        raise RuntimeError('Refusing: expected one U2, found %d' % len(component_indexes))
    ci = component_indexes[0]
    obj = ci - 1
    component = records[ci][1]
    if field(component, 'LibReference') != 'FT2232HL-LQFP64':
        raise RuntimeError('Refusing: U2 is not FT2232HL-LQFP64')

    direct = []
    parameters = {}
    pins = {}
    for i, (_, body) in enumerate(records):
        if field(body, 'OwnerIndex') != str(obj):
            continue
        direct.append(i)
        if field(body, 'RECORD') == '41':
            parameters[field(body, 'Name')] = i
        elif field(body, 'RECORD') == '2':
            pins[field(body, 'Designator')] = i
    if 'EP' in pins:
        raise RuntimeError('Refusing: U2 already has an EP pin')
    if len(pins) != 64:
        raise RuntimeError('Refusing: expected 64 U2 pins, found %d' % len(pins))

    component = set_field(component, 'LibReference', 'FT2232HQ-QFN64')
    component = set_field(component, 'DesignItemId', 'FT2232HQ-QFN64')
    component = set_field(component, 'ComponentDescription', DESC)
    records[ci][1] = component

    changes = {
        'MANF#': 'FT2232HQ-REEL',
        'Comment': 'FT2232HQ USB-UART/JTAG Bridge',
        'DeviceName': '-QFN64',
        'DeviceSetName': 'FT2232HQ',
        'SPEC': SPEC,
        'NOTE': NOTE,
    }
    for name, text in changes.items():
        if name not in parameters:
            raise RuntimeError('Refusing: U2 parameter %s is missing' % name)
        records[parameters[name]][1] = set_field(records[parameters[name]][1], 'Text', text)

    label = parameters.get('FT2232HL')
    if label is None:
        raise RuntimeError('Refusing: U2 visible FT2232HL label is missing')
    records[label][1] = set_field(set_field(records[label][1], 'Name', 'FT2232HQ'), 'Text', 'FT2232HQ')

    model_headers = [
        i for i, (_, body) in enumerate(records)
        if field(body, 'RECORD') == '44' and field(body, 'OwnerIndex') == str(obj)
    ]
    if len(model_headers) != 1:
        raise RuntimeError('Refusing: expected one U2 model header')
    model_records = [
        i for i, (_, body) in enumerate(records)
        if field(body, 'RECORD') == '45' and field(body, 'OwnerIndex') == str(model_headers[0] - 1)
    ]
    if len(model_records) != 1 or field(records[model_records[0]][1], 'ModelName') != 'FT2232HL-LQFP64':
        raise RuntimeError('Refusing: unexpected U2 footprint model')
    records[model_records[0]][1] = set_field(records[model_records[0]][1], 'ModelName', 'FT2232HQ-QFN64')
    # Altium reads the footprint from the library by this entity name: keep it equal to ModelName like every other part
    records[model_records[0]][1] = set_field(records[model_records[0]][1], 'ModelDatafileEntity0', 'FT2232HQ-QFN64')

    title_changes = 0
    for record in records:
        body = record[1]
        if field(body, 'RECORD') == '4' and field(body, 'Text') == 'FT2232HL, JTAG, CLOCK':
            record[1] = set_field(body, 'Text', 'FT2232HQ, JTAG, CLOCK')
            title_changes += 1
    if title_changes != 1:
        raise RuntimeError('Refusing: expected one FT2232HL sheet title')

    bus = None
    for i, (_, body) in enumerate(records):
        if field(body, 'RECORD') != '27':
            continue
        pts = points(body)
        if pts[0] == (342, 552) and (512, 552) in pts and (512, 562) in pts:
            bus = i
        if pts == [(532, 552), (532, 562)]:
            raise RuntimeError('Refusing: EP ground stub already exists')
        if pts in ([(512, 552), (532, 552)], [(532, 552), (512, 552)]):
            raise RuntimeError('Refusing: EP GND bus extension already exists')
    if bus is None:
        raise RuntimeError('Refusing: shortened U2 GND bus was not found')

    subtree = {ci}
    while True:
        found = {
            i for i, (_, body) in enumerate(records)
            if field(body, 'OwnerIndex') is not None and int(field(body, 'OwnerIndex')) + 1 in subtree
        }
        expanded = subtree | found
        if expanded == subtree:
            break
        subtree = expanded
    insert_at = max(subtree) + 1

    pin_uid, hidden_uid, param_uid, stub_uid, ext_uid = uid(), uid(), uid(), uid(), uid()
    max_sheet_index = max((num(body, 'IndexInSheet') or 0) for _, body in records)
    ep_pin = EP_PIN.replace(b'PINUID', pin_uid.encode())
    ep_hidden = EP_HIDDEN_NET.replace(b'HIDDENID', hidden_uid.encode())
    ep_pin_uid = EP_PIN_UID.replace(b'PINUID', pin_uid.encode()).replace(b'PARAMUID', param_uid.encode())
    ep_stub = EP_STUB.replace(b'STUBUID', stub_uid.encode())
    ep_stub = set_field(ep_stub, 'IndexInSheet', str(max_sheet_index + 1))
    ep_bus_ext = EP_BUS_EXT.replace(b'EXTUID', ext_uid.encode())
    ep_bus_ext = set_field(ep_bus_ext, 'IndexInSheet', str(max_sheet_index + 2))

    old_to_new = {}
    new_records = []
    ep_index = None
    for old_index, record in enumerate(records):
        if old_index == insert_at:
            ep_index = len(new_records)
            new_records.extend([
                [b'\x00\x00\x00\x00', ep_pin],
                [b'\x00\x00\x00\x00', ep_hidden],
                [b'\x00\x00\x00\x00', ep_pin_uid],
                [b'\x00\x00\x00\x00', ep_stub],
                [b'\x00\x00\x00\x00', ep_bus_ext],
            ])
        old_to_new[old_index] = len(new_records)
        new_records.append([record[0], record[1]])
    if ep_index is None:
        raise RuntimeError('Refusing: failed to choose an EP insertion point')

    for old_index, new_index in old_to_new.items():
        body = new_records[new_index][1]
        owner = field(body, 'OwnerIndex')
        if owner is not None:
            parent_old = int(owner) + 1
            new_records[new_index][1] = set_field(body, 'OwnerIndex', str(old_to_new[parent_old] - 1))

    component_new = old_to_new[ci]
    new_records[ep_index][1] = set_field(new_records[ep_index][1], 'OwnerIndex', str(component_new - 1))
    new_records[ep_index + 1][1] = set_field(new_records[ep_index + 1][1], 'OwnerIndex', str(ep_index - 1))
    new_records[ep_index + 2][1] = set_field(new_records[ep_index + 2][1], 'OwnerIndex', str(ep_index - 1))
    new_records[0][1] = set_field(new_records[0][1], 'Weight', str(len(new_records) - 1))

    output = join(new_records)
    write_stream(path, 'FileHeader', output)
    if read_stream(path, 'FileHeader') != output:
        raise RuntimeError('SchDoc write verification failed')

    check = split(output)
    ep = [
        body for _, body in check
        if field(body, 'RECORD') == '2' and field(body, 'Designator') == 'EP'
        and field(body, 'OwnerIndex') == str(component_new - 1)
    ]
    if len(ep) != 1:
        raise RuntimeError('SchDoc verification found %d EP pins' % len(ep))
    print('U2 -> FT2232HQ-QFN64; EP pin/stub restored; %d records written' % (len(check) - 1))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: python tools/u2_ft2232hq.py <zulu_a7_4.SchDoc>')
    convert(sys.argv[1])
