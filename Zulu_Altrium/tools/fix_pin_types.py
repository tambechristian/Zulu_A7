"""Give supply pins and connector pins the electrical type they really have.

The EAGLE library marks the supply/ground pins of U2 (FT2232HQ), U3 (SDRAM),
U4 (flash) and U10 (EEPROM) as "io", and every pin of the X2 header as "io".
Altium's ERC then reports "IO pin and power pin" on GND, VCC1V0, VCC1V8 and
VCC3V3.  Supply pins become Power (7), including the regulator output VREGOUT
and the header's supply pins (GND, +3.3V, +1.8V, +1.0V, VU, +5V-INPUT); the
header's signal pins become Passive (4); U2's TEST pin, tied to ground, is
an Input (0).
Only the displayed pin of each placed gate is touched; the one-pin gates
are recognised by their >GATE label.
"""
import sys, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
INPUT, POWER, PASSIVE = '0', '7', '4'
RULES={  # sheet index: {designator: [(regex on pin name or gate name, electrical), ...] first match wins}
 2:{'X2':[(r'^(GND\d*|\+[0-9.]+V\d*|VU|\+5V-INPUT)$', POWER), (r'.*', PASSIVE)]},
 3:{'U3':[(r'^(VDD|VDDQ|VSS|VSSQ)(@\d+)?$', POWER)], 'U4':[(r'^(GND|VCC)$', POWER)]},
 4:{'U2':[(r'^(AGND|EP|GND|VCCIO|VREGIN|VREGOUT|VCORE|VPHY|VPLL)(@\d+)?$', POWER), (r'^TEST$', INPUT)], 'U10':[(r'^(VCC|VSS)$', POWER)]},
}
folder=sys.argv[2]
for k,rules in RULES.items():
    path=f'{folder}/zulu_a7_{k}.SchDoc'
    data=read_stream(path,'FileHeader'); recs=split(data)
    comps={i:b for i,(h,b) in enumerate(recs) if b.startswith(b'|RECORD=1|')}
    desig={}; gate={}
    for h,b in recs:
        if b.startswith(b'|RECORD=34|'): desig[int(field(b,'OwnerIndex'))+1]=field(b,'Text')
        if b.startswith(b'|RECORD=41|') and field(b,'Name')=='GATE' and field(b,'IsHidden')!='T': gate[int(field(b,'OwnerIndex'))+1]=field(b,'Text')
    changed={}
    for rec in recs:
        b=rec[1]
        if not b.startswith(b'|RECORD=2|'): continue
        oi=int(field(b,'OwnerIndex'))+1; comp=comps.get(oi)
        if not comp or field(b,'OwnerPartId')!=field(comp,'CurrentPartId'): continue
        d=desig.get(oi)
        if d not in rules: continue
        name=field(b,'Name') or ''
        label=gate.get(oi,'') if name in ('1','P$1') else name
        elec=next((e for pat,e in rules[d] if re.match(pat,label)), None)
        if elec is None or (field(b,'Electrical') or '0')==elec: continue
        rec[1]=set_field(b,'Electrical',elec)
        changed.setdefault(d,[]).append(f"{field(b,'Designator')}:{label}")
    if changed:
        new=join(recs); write_stream(path,'FileHeader',new)
        assert read_stream(path,'FileHeader')==new
    print(f'sheet {k}:', {d:len(v) for d,v in changed.items()})
    for d,v in changed.items(): print(f'   {d}: {v[:12]}{" ..." if len(v)>12 else ""}')
