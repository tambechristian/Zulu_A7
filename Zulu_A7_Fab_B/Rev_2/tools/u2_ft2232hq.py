# -*- coding: utf-8 -*-
"""Fab B Rev 2 sync (2026-11-20), sheet 4: U2 FT2232HL/LQFP-64 -> FT2232HQ/QFN-64 with a grounded EP pin.

    python tools/u2_ft2232hq.py            dry run
    python tools/u2_ft2232hq.py apply      writes Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc

Port of Zulu_A7_no_pmod/Rev_2/tools/u2_ft2232hq.py (3b1817d, incl. the ModelDatafileEntity0 fix that
u2_model_entity.py had to repair there).  Same edits, same texts: the 64 signal pins keep their numbering and
connections; U2's LibReference / DesignItemId / description / MANF# / Comment / DeviceName / DeviceSetName / SPEC /
NOTE, the visible FT2232HL label parameter, the footprint model (FT2232HQ-QFN64) and the sheet title label
"FT2232HQ, JTAG, CLOCK" change; an EP pin (Electrical=7 power, HiddenNetName GND) is added at (532, 592), pointing down
(PinLength 30, hot spot at (532, 562)), with a 10-unit stub to (532, 552) and a 20-unit wire west to the U2 GND bus at
(512, 552).  The new records reuse the no-PMOD sheet's UniqueIDs (checked free here) so the U2 subtree matches it.
Netlist effect: GND gains U2-EP, nothing else.  Needs backups/zulu_a7_4.SchDoc.pre-sync.
"""
import sys

from sync_sch_common import (NEW_HDR, component, field, insert, load, num, require_backup, save, set_field, sheet,
                             subtree, by_uid)

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
# UniqueIDs of the same records on Zulu_A7_no_pmod Rev_2 sheet 4 (HEAD 427960e)
PIN_UID, HIDDEN_UID, PARAM_UID, STUB_UID, EXT_UID = 'HUPPXYES', 'JHUYYWUI', 'JBKVRJDH', 'KQEFGZYO', 'ZNXNPEEP'

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


def points(body):
    return [(num(body, 'X%d' % k), num(body, 'Y%d' % k)) for k in range(1, num(body, 'LocationCount') + 1)]


def convert(R):
    ci = component(R, 'U2')
    if field(R[ci][1], 'LibReference') != 'FT2232HL-LQFP64':
        raise RuntimeError('Refusing: U2 is not FT2232HL-LQFP64')
    uids = by_uid(R)
    for u in (PIN_UID, HIDDEN_UID, PARAM_UID, STUB_UID, EXT_UID):
        if u in uids:
            raise RuntimeError('Refusing: UniqueID %s already used on this sheet' % u)
    parameters, pins = {}, {}
    for i, (h, b) in enumerate(R):
        if field(b, 'OwnerIndex') != str(ci - 1):
            continue
        if field(b, 'RECORD') == '41':
            parameters[field(b, 'Name')] = i
        elif field(b, 'RECORD') == '2':
            pins[field(b, 'Designator')] = i
    if 'EP' in pins or len(pins) != 64:
        raise RuntimeError('Refusing: U2 has %d pins%s' % (len(pins), ' incl. EP' if 'EP' in pins else ''))

    c = R[ci][1]
    for k, v in (('LibReference', 'FT2232HQ-QFN64'), ('DesignItemId', 'FT2232HQ-QFN64'), ('ComponentDescription', DESC)):
        c = set_field(c, k, v)
    R[ci][1] = c
    for name, text in (('MANF#', 'FT2232HQ-REEL'), ('Comment', 'FT2232HQ USB-UART/JTAG Bridge'),
                       ('DeviceName', '-QFN64'), ('DeviceSetName', 'FT2232HQ'), ('SPEC', SPEC), ('NOTE', NOTE)):
        if name not in parameters:
            raise RuntimeError('Refusing: U2 parameter %s is missing' % name)
        R[parameters[name]][1] = set_field(R[parameters[name]][1], 'Text', text)
    label = parameters.get('FT2232HL')
    if label is None:
        raise RuntimeError('Refusing: U2 visible FT2232HL label is missing')
    R[label][1] = set_field(set_field(R[label][1], 'Name', 'FT2232HQ'), 'Text', 'FT2232HQ')

    heads = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '44' and field(b, 'OwnerIndex') == str(ci - 1)]
    if len(heads) != 1:
        raise RuntimeError('Refusing: expected one U2 model list')
    models = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '45' and field(b, 'OwnerIndex') == str(heads[0] - 1)]
    if len(models) != 1 or field(R[models[0]][1], 'ModelName') != 'FT2232HL-LQFP64':
        raise RuntimeError('Refusing: unexpected U2 footprint model')
    m = set_field(R[models[0]][1], 'ModelName', 'FT2232HQ-QFN64')
    R[models[0]][1] = set_field(m, 'ModelDatafileEntity0', 'FT2232HQ-QFN64')

    titles = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '4' and field(b, 'Text') == 'FT2232HL, JTAG, CLOCK']
    if len(titles) != 1:
        raise RuntimeError('Refusing: expected one FT2232HL sheet title')
    R[titles[0]][1] = set_field(R[titles[0]][1], 'Text', 'FT2232HQ, JTAG, CLOCK')

    bus = None
    for i, (h, b) in enumerate(R):
        if field(b, 'RECORD') != '27':
            continue
        p = points(b)
        if p[0] == (342, 552) and (512, 552) in p and (512, 562) in p:
            bus = i
        if p in ([(532, 552), (532, 562)], [(512, 552), (532, 552)], [(532, 552), (512, 552)]):
            raise RuntimeError('Refusing: an EP stub already exists')
    if bus is None:
        raise RuntimeError('Refusing: the U2 GND bus ending at (512, 552) was not found')

    at = max(subtree(R, ci)) + 1
    top = max((num(b, 'IndexInSheet') or 0) for h, b in R)
    pin = EP_PIN.replace(b'PINUID', PIN_UID.encode())
    hid = EP_HIDDEN_NET.replace(b'HIDDENID', HIDDEN_UID.encode())
    puid = EP_PIN_UID.replace(b'PINUID', PIN_UID.encode()).replace(b'PARAMUID', PARAM_UID.encode())
    stub = set_field(EP_STUB.replace(b'STUBUID', STUB_UID.encode()), 'IndexInSheet', str(top + 1))
    ext = set_field(EP_BUS_EXT.replace(b'EXTUID', EXT_UID.encode()), 'IndexInSheet', str(top + 2))
    out, new_old, new_ins = insert(R, [(at, NEW_HDR, pin, ('old', ci)), (at, NEW_HDR, hid, ('new', 0)),
                                       (at, NEW_HDR, puid, ('new', 0)), (at, NEW_HDR, stub, None),
                                       (at, NEW_HDR, ext, None)])
    # the two wires are sheet-level: insert() kept their bodies, which carry no OwnerIndex
    assert field(out[new_ins[3]][1], 'OwnerIndex') is None and field(out[new_ins[4]][1], 'OwnerIndex') is None
    return out


def main():
    apply = 'apply' in sys.argv[1:]
    path = sheet(4)
    R = load(path)
    out = convert(R)
    print('U2 -> FT2232HQ-QFN64; EP pin + 2 wires added: records %d -> %d' % (len(R), len(out)))
    if not apply:
        print('dry run (add "apply" to write)')
        return
    require_backup(path)
    print('written zulu_a7_4.SchDoc md5 %s' % save(path, out))


if __name__ == '__main__':
    main()
