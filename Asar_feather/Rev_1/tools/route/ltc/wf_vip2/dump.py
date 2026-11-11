import json,sys
M=json.load(open(sys.argv[1]))
x0,y0,x1,y1=map(float,sys.argv[2:6])
refs=set(sys.argv[6].split(',')) if len(sys.argv)>6 else None
for p in M['pads']:
    if refs and p['ref'] in refs or (not refs and x0<p['x']<x1 and y0<p['y']<y1):
        print('PAD',p['ref'],p['pad'],p['net'],p['x'],p['y'],p['w'],p['h'],p['layers'][0][:6],p.get('drill'))
