"""Place No-ERC markers on pins that are open on purpose.

The EAGLE sheet documents them: the eight GTP transceiver balls of U1
("GTP - float (UG482 T5-4)") and the micro-USB ID pin X1-4.  Their EAGLE
direction is "in", so Altium's compiler reports "floating input pin" errors
and "unconnected pin" warnings.  A No-ERC directive at the pin's hot end
(the coordinates Altium prints in the Messages panel) records the intent
and suppresses both.  Record layout copied from Altium's own example
projects (RECORD=22).
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

MARKERS={  # sheet index -> [(x, y, why)]
 5:[(985,427,'U1-A2 MGTPTXN1'),(985,457,'U1-A8 MGTREFCLK0N'),(985,437,'U1-A10 MGTREFCLK1N'),(985,477,'U1-B2 MGTPTXP1'),
    (985,467,'U1-B8 MGTREFCLK0P'),(985,447,'U1-B10 MGTREFCLK1P'),(985,487,'U1-D1 MGTPTXN0'),(985,497,'U1-D2 MGTPTXP0')],
 1:[(185,1102,'X1-4 USB ID')],
}
def uid(): return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
folder=sys.argv[2]
for k,marks in MARKERS.items():
    path=f'{folder}/zulu_a7_{k}.SchDoc'
    data=read_stream(path,'FileHeader'); recs=split(data)
    existing={(field(b,'Location.X'),field(b,'Location.Y')) for _,b in recs if b.startswith(b'|RECORD=22|')}
    added=0
    for x,y,why in marks:
        if (str(x),str(y)) in existing: continue
        body=f'|RECORD=22|OwnerPartId=-1|Location.X={x}|Location.Y={y}|Color=255|Symbol=Thin Cross|IsActive=T|SuppressAll=T|UniqueID={uid()}'.encode()
        recs.append([b'\x00\x00\x00\x00', body+b'\x00']); added+=1
    # the file header's Weight is the record count after the header
    hdr=recs[0][1]; w=int(field(hdr,'Weight')); recs[0][1]=set_field(hdr,'Weight',str(w+added))
    new=join(recs); write_stream(path,'FileHeader',new)
    assert read_stream(path,'FileHeader')==new
    print(f'sheet {k}: {added} No-ERC markers added, Weight {w}->{w+added}')
