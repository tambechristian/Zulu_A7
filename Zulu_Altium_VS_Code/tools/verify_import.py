import re, sys, olefile
import xml.etree.ElementTree as ET
from collections import Counter
sch_path=sys.argv[1]; outdir=sys.argv[2]
def records(path):
    ole=olefile.OleFileIO(path); data=ole.openstream('FileHeader').read()
    recs=[]; i=0
    while i+4<=len(data):
        n=int.from_bytes(data[i:i+2],'little'); i+=4
        recs.append(data[i:i+n].rstrip(b'\x00').decode('utf-8','replace')); i+=n
    return recs
def field(rec,k):
    m=re.search(r'\|(?:%UTF8%)?'+k+r'=([^|]*)',rec,re.I); return m.group(1) if m else None
r=ET.parse(sch_path).getroot(); sch=r.find('drawing/schematic')
parts={p.get('name'):p for p in sch.findall('parts/part')}
def is_supply(n):
    return parts[n].get('deviceset') in ('GND','VCC','SUPPLY') or parts[n].get('library') in ('supply1','supply2') or n.startswith('SUPPLY') or n.startswith('GND')
allok=True
for k,sheet in enumerate(sch.findall('sheets/sheet')):
    recs=records(f'{outdir}/zulu_a7_{k}.SchDoc')
    comps=[rec for rec in recs if rec.startswith('|RECORD=1|')]
    des=Counter(field(rec,'Text') for rec in recs if rec.startswith('|RECORD=34|'))
    labels=Counter(field(rec,'Text') for rec in recs if rec.startswith('|RECORD=25|'))
    pwr=Counter(field(rec,'Text') for rec in recs if rec.startswith('|RECORD=17|'))
    pins=sum(1 for rec in recs if rec.startswith('|RECORD=2|'))
    wires=sum(1 for rec in recs if rec.startswith('|RECORD=27|'))
    inst=Counter(i.get('part') for i in sheet.findall('instances/instance'))
    ereal={n:c for n,c in inst.items() if not is_supply(n)}
    esup={n:c for n,c in inst.items() if is_supply(n)}
    enets={n.get('name'):n for n in sheet.findall('nets/net')}
    named=[n for n,e in enets.items() if not n.startswith('N$') and (e.findall('.//pinref') or e.findall('.//wire'))]
    missing=sorted(set(ereal)-set(des)); extra=sorted(set(des)-set(inst))
    bad=[(n,ereal[n],des[n]) for n in ereal if n in des and des[n]!=ereal[n]]
    nl_missing=sorted(n for n in named if n not in labels and n not in pwr)
    print(f"sheet {k} [{sheet.find('description').text}]: Altium parts={len(comps)} pins={pins} wires={wires} netlabels={sum(labels.values())} powerports={sum(pwr.values())} | EAGLE parts={len(ereal)} gates={sum(ereal.values())} supply symbols={sum(esup.values())} nets={len(enets)} named(non-empty)={len(named)}")
    if missing: print('     MISSING designators in Altium:', missing); allok=False
    if extra: print('     EXTRA designators in Altium:', extra)
    if bad: print('     gate-count mismatch (name, eagle, altium):', bad); allok=False
    if nl_missing: print('     EAGLE named nets with no Altium label/power port:', nl_missing); allok=False
    if sum(esup.values())!=sum(pwr.values()): print(f'     supply-symbol count {sum(esup.values())} != Altium power ports {sum(pwr.values())}'); allok=False
print('ALL SHEETS MATCH' if allok else 'DIFFERENCES FOUND')
