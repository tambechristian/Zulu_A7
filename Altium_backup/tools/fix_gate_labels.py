"""Show the >GATE labels of one-pin-per-gate EAGLE parts (X2, U3, U4, U1).

The importer turns each symbol's >GATE text into a parameter named GATE on
the placed gate, but gives every one of them OwnerPartId=1.  Altium only
draws a parameter whose OwnerPartId matches the component's CurrentPartId,
so only the gate that happens to be part 1 shows its name (CHAN-CLK on X2).
Set each GATE parameter's OwnerPartId to its owner's CurrentPartId.
"""
import sys, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
for path in sys.argv[2:]:
    data=read_stream(path,'FileHeader'); recs=split(data)
    fixed=0; already=0
    for rec in recs:
        b=rec[1]
        if b.startswith(b'|RECORD=41|') and field(b,'Name')=='GATE' and field(b,'IsHidden')!='T':
            owner=recs[int(field(b,'OwnerIndex'))+1][1]        # OwnerIndex counts from the record after the file header
            assert owner.startswith(b'|RECORD=1|'), path
            cur=field(owner,'CurrentPartId') or '1'
            if field(b,'OwnerPartId')==cur: already+=1; continue
            rec[1]=set_field(b,'OwnerPartId',cur); fixed+=1
    if fixed:
        new=join(recs); write_stream(path,'FileHeader',new)
        assert read_stream(path,'FileHeader')==new
    print(f'{path}: {fixed} GATE labels re-owned, {already} already right')
