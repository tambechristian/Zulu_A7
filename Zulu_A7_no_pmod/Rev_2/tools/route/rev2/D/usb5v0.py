"""hand USB5V0: Rev1 geometry with X1 pad 1 now at x 31.78 (the y 22.5 run starts 2.54 mm further west)"""
import json
STACK=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
R=json.load(open('prep/rip.json'))
t=[x for x in R['remove'] if x['net']=='USB5V0']
v=[x for x in R['remove_vias'] if x['net']=='USB5V0']
out=[]
for x in t:
    if (x['x1'],x['y1'],x['x2'],x['y2'])==(34.32,21.259,34.32,22.5): x=dict(x,x1=31.78,x2=31.78)
    if (x['x1'],x['y1'],x['x2'],x['y2'])==(34.32,22.5,36.68,22.5): x=dict(x,x1=31.78)
    out.append(x)
json.dump({'tracks':out,'vias':v},open('D/usb5v0.json','w'),indent=1)
print(out)
