"""Un-flip text in Altium SchDocs produced by the EAGLE importer.

EAGLE draws R180/R270 text readable (flipped in place); Altium draws
Orientation 2/3 literally, upside down.  For every text-like record with
Orientation 2 or 3 this sets Orientation 0 or 1 and mirrors the justification,
which keeps the text box, and the anchor, exactly where they were.  The font is
swapped for the same face/size at the matching rotation.  Optionally tidies the
N$ net labels: small font, centred on their wire, hanging below it.
"""
import re, sys, shutil, olefile, pythoncom
from win32com import storagecon
from collections import Counter

TEXT_RECORDS={4:'text',25:'netlabel',34:'designator',41:'parameter'}

def read_stream(path,name):
    return olefile.OleFileIO(path).openstream(name).read()

def write_stream(path,name,data):
    mode=storagecon.STGM_READWRITE|storagecon.STGM_SHARE_EXCLUSIVE
    stg=pythoncom.StgOpenStorage(path,None,mode,None,0)
    stm=stg.OpenStream(name,None,mode,0)
    stm.SetSize(0); stm.Seek(0,0); stm.Write(data); stm.Commit(0)
    stm=None; stg.Commit(0)

def split(data):
    recs=[]; i=0
    while i+4<=len(data):
        n=int.from_bytes(data[i:i+2],'little'); hdr=data[i:i+4]; i+=4
        recs.append([hdr,data[i:i+n]]); i+=n
    assert i==len(data)
    return recs

def join(recs):
    out=[]
    for hdr,body in recs:
        out.append(len(body).to_bytes(2,'little')+hdr[2:]+body)
    return b''.join(out)

def field(body,key):
    m=re.search(rb'\|(?:%UTF8%)?'+key.encode()+rb'=([^|\x00]*)',body,re.I)
    return m.group(1).decode('latin-1') if m else None

def set_field(body,key,value):
    """Replace key's value, or insert |key=value| right after |RECORD=n|."""
    pat=re.compile(rb'(\|(?:%UTF8%)?'+key.encode()+rb'=)[^|\x00]*',re.I)
    if pat.search(body):
        return pat.sub(lambda m: m.group(1)+value.encode(),body,count=1)
    m=re.match(rb'\|RECORD=\d+',body)
    return body[:m.end()]+b'|'+key.encode()+b'='+value.encode()+body[m.end():]

def fonts_of(body):
    ft={}
    for a,b,c,d,e,g in re.findall(rb'Size(\d+)=(\d+)|Rotation(\d+)=(\d+)|FontName(\d+)=([^|\x00]*)',body):
        if a: ft.setdefault(int(a),{'rot':0})['size']=int(b)
        if c: ft.setdefault(int(c),{'rot':0})['rot']=int(d)
        if e: ft.setdefault(int(e),{'rot':0})['name']=g.decode('latin-1')
    return ft

def mirror_just(j):
    h,v=j%3,j//3
    return (2-v)*3+(2-h)

def fix(path, tidy_nsets=False, verbose=True):
    data=read_stream(path,'FileHeader')
    recs=split(data)
    assert join(recs)==data
    fontrec=next(r for r in recs if r[1].startswith(b'|RECORD=31|'))
    fonts=fonts_of(fontrec[1])
    def font_for(fid,rot):
        f=fonts[fid]
        if f['rot']==rot: return fid
        for i,g in fonts.items():
            if g['name']==f['name'] and g['size']==f['size'] and g['rot']==rot: return i
        raise KeyError(f'no font {f["name"]} {f["size"]} rot {rot} in {path}')
    stats=Counter()
    for rec in recs[1:]:
        body=rec[1]
        m=re.match(rb'\|RECORD=(\d+)\|',body)
        if not m: continue
        t=int(m.group(1))
        if t not in TEXT_RECORDS: continue
        o=int(field(body,'Orientation') or 0)
        if o in (2,3):
            j=int(field(body,'Justification') or 0)
            body=set_field(body,'Orientation',str(o-2))
            body=set_field(body,'Justification',str(mirror_just(j)))
            fid=int(field(body,'FontID') or 1)
            body=set_field(body,'FontID',str(font_for(fid,0 if o==2 else 90)))
            stats[(TEXT_RECORDS[t],f'o{o}->o{o-2}',f'j{j}->j{mirror_just(j)}')]+=1
        if tidy_nsets and t==25 and (field(body,'Text') or '').startswith('N$'):
            o=int(field(body,'Orientation') or 0)
            fid=int(field(body,'FontID') or 1)
            small=[i for i,g in fonts.items() if g['name']==fonts[fid]['name'] and g['rot']==(90 if o==1 else 0) and g['size']<=7]
            if small:
                body=set_field(body,'FontID',str(max(small,key=lambda i:fonts[i]['size'])))
            body=set_field(body,'Justification','1' if o==1 else '7')
            stats[('N$ label tidied',f'o{o}','')]+=1
        rec[1]=body
    new=join(recs)
    write_stream(path,'FileHeader',new)
    back=read_stream(path,'FileHeader')
    assert back==new
    if verbose:
        for k,n in sorted(stats.items()): print('   ',n,*k)
    return stats

if __name__=='__main__':
    for p in sys.argv[1:]:
        print(p)
        fix(p, tidy_nsets=p.endswith('_2.SchDoc'))
