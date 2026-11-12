"""region.py <model.json> <plan.json|-> x0,y0,x1,y1 [layer]: copper items touching a box (src B=model, P=plan)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
M = E.load(sys.argv[1]); P = E.load(sys.argv[2]) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
lay = sys.argv[4] if len(sys.argv) > 4 else None
inb = lambda x, y, r=0: x0 - r <= x <= x1 + r and y0 - r <= y <= y1 + r
for src, ts in (('B', M['tracks']), ('P', P['tracks'])):
    for t in ts:
        if lay and t['layer'] != lay: continue
        if inb(t['x1'], t['y1']) or inb(t['x2'], t['y2']) or inb((t['x1']+t['x2'])/2, (t['y1']+t['y2'])/2):
            print(src, 'T', t['net'], t['layer'][:3], '%.3f,%.3f-%.3f,%.3f w%.3f' % (t['x1'], t['y1'], t['x2'], t['y2'], t['w']))
for src, vs in (('B', M['vias']), ('P', P['vias'])):
    for v in vs:
        sp = E.span(v)
        if lay and lay not in sp: continue
        if inb(v['x'], v['y']):
            print(src, 'V', v['net'], '%.3f,%.3f %s>%s %.2f' % (v['x'], v['y'], sp[0][:3], sp[-1][:3], v['size']))
for p in M['pads']:
    if lay and lay not in (p['layers'] or []) and not p['drill']: continue
    if inb(p['x'], p['y'], max(p['w'], p['h'])/2):
        print('pad', p['ref'], p['pad'], p['net'], '%.3f,%.3f %.2fx%.2f %s' % (p['x'], p['y'], p['w'], p['h'], 'TH' if p['drill'] else (p['layers'] or [''])[0][:3]))
