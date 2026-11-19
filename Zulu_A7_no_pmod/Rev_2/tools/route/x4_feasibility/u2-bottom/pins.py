import json,sys,math
sys.path.insert(0,'.')
from scan import *
for rot in (0,90):
    rs,_,_=u2geom(54.025,12.275,rot)
    d={pad:((r[0]+r[2])/2,(r[1]+r[3])/2) for r,pad,net in rs}
    print('rot',rot,{k:tuple(round(v,2) for v in d[k]) for k in ('1','7','8','16','17','24','38','43','49','61','64')})
print([ (p['pad'],p['net'],p['x'],p['y'],p['layers']) for p in M['pads'] if p['ref']=='X1'])
print([ (p['ref'],p['pad'],p['net'],p['x'],p['y']) for p in M['pads'] if p['ref'] in('JP3','JP4','R4','U10','R24','Q1')])
# S2B cx scan vs Top copper of nets other than U2 nets (those are ripped anyway)
import s2b
