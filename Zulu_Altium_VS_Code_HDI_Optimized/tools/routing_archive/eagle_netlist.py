"""EAGLE .sch -> {net: sorted list of 'PART-PAD'} (JSON). Same-named nets on
different sheets are one net, as EAGLE treats them. Supply symbols and frames
have no pads and are skipped."""
import sys, json
import xml.etree.ElementTree as ET
from collections import defaultdict
src,dst=sys.argv[1],sys.argv[2]
sch=ET.parse(src).getroot().find('drawing/schematic')
parts={p.get('name'):p for p in sch.findall('parts/part')}
libs={l.get('name'):l for l in sch.findall('libraries/library')}
connects={}
def pads(partname,gate,pin):
    p=parts[partname]; key=(p.get('library'),p.get('deviceset'),p.get('device'))
    if key not in connects:
        ds=next(d for d in libs[key[0]].findall('devicesets/deviceset') if d.get('name')==key[1])
        dev=next(d for d in ds.findall('devices/device') if d.get('name')==key[2])
        m=defaultdict(list)
        for c in dev.findall('connects/connect'):
            for pad in c.get('pad').split(): m[(c.get('gate'),c.get('pin'))].append(pad)
        connects[key]=m
    return connects[key].get((gate,pin),[])
net_pads=defaultdict(set); skipped=set(); nopad=set()
for s in sch.findall('sheets/sheet'):
    for net in s.findall('nets/net'):
        for pr in net.iter('pinref'):
            part=pr.get('part'); p=parts[part]
            if p.get('library') in ('supply1','supply2') or p.get('deviceset') in ('GND','VCC','SUPPLY','FRAME','DOCFIELD') or part.startswith(('SUPPLY','GND','FRAME')):
                skipped.add(part); continue
            pl=pads(part,pr.get('gate'),pr.get('pin'))
            if not pl: nopad.add((part,pr.get('gate'),pr.get('pin')))
            for pad in pl: net_pads[net.get('name')].add(f'{part}-{pad}')
out={n:sorted(v) for n,v in net_pads.items() if v}
json.dump(out,open(dst,'w'),indent=0)
seen=defaultdict(list)
for n,ps in out.items():
    for p in ps: seen[p].append(n)
multi={p:n for p,n in seen.items() if len(n)>1}
print('EAGLE nets:',len(out),'pads:',sum(len(v) for v in out.values()),'skipped supply/frame parts:',len(skipped),'pins without pad:',len(nopad),'pads in >1 net:',len(multi))
if nopad: print('  no-pad examples:', sorted(nopad)[:10])
if multi: print('  multi examples:', list(multi.items())[:10])
