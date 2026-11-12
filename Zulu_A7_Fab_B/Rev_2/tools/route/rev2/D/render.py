"""render.py <model> <rip|-> <plan|-> <out.png> x0 x1 y0 y1 [layers comma]"""
import json,sys,math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
M=json.load(open(sys.argv[1]))
rip=json.load(open(sys.argv[2])) if sys.argv[2]!='-' else {'remove':[],'remove_vias':[]}
plan=json.load(open(sys.argv[3])) if sys.argv[3]!='-' else {'tracks':[],'vias':[],'remove':[],'remove_vias':[]}
x0,x1,y0,y1=map(float,sys.argv[5:9])
layers=sys.argv[9].split(',') if len(sys.argv)>9 else ['Top Layer']
def key(t): return (t['net'],t['layer'],frozenset([(round(t['x1'],3),round(t['y1'],3)),(round(t['x2'],3),round(t['y2'],3))]))
rk={key(t) for t in rip['remove']+plan.get('remove',[])}
rv={(v['net'],round(v['x'],3),round(v['y'],3)) for v in rip['remove_vias']+plan.get('remove_vias',[])}
col={'Top Layer':'red','L3-SIG':'orange','L4-SIG':'green','Bottom Layer':'blue'}
fig,ax=plt.subplots(figsize=(18,18*(y1-y0)/(x1-x0)))
def seg(t,c,a=0.6):
    dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L=math.hypot(dx,dy) or 1e-9
    nx,ny=-dy/L*t['w']/2,dx/L*t['w']/2
    ax.add_patch(Polygon([(t['x1']+nx,t['y1']+ny),(t['x2']+nx,t['y2']+ny),(t['x2']-nx,t['y2']-ny),(t['x1']-nx,t['y1']-ny)],color=c,alpha=a,lw=0))
    for x,y in ((t['x1'],t['y1']),(t['x2'],t['y2'])): ax.add_patch(Circle((x,y),t['w']/2,color=c,alpha=a,lw=0))
for p in M['pads']:
    if not (x0-2<p['x']<x1+2 and y0-2<p['y']<y1+2): continue
    if not p['drill'] and not set(p['layers'])&set(layers): continue
    c='gray' if p['drill'] else ('salmon' if 'Top Layer' in p['layers'] else 'lightblue')
    if p['shape']=='circle': ax.add_patch(Circle((p['x'],p['y']),p['w']/2,color=c,alpha=.5))
    else: ax.add_patch(Rectangle((p['x']-p['w']/2,p['y']-p['h']/2),p['w'],p['h'],color=c,alpha=.5))
    ax.text(p['x'],p['y'],'%s-%s\n%s'%(p['ref'],p['pad'],p['net']),fontsize=6,ha='center',va='center')
for t in M['tracks']:
    if key(t) in rk or t['layer'] not in layers: continue
    if max(t['x1'],t['x2'])<x0 or min(t['x1'],t['x2'])>x1 or max(t['y1'],t['y2'])<y0 or min(t['y1'],t['y2'])>y1: continue
    seg(t,col.get(t['layer'],'k'),.4); ax.text((t['x1']+t['x2'])/2,(t['y1']+t['y2'])/2,t['net'],fontsize=5)
for t in plan['tracks']:
    if t['layer'] in layers: seg(t,'magenta',.8)
for v in M['vias']+plan['vias']:
    if (v['net'],round(v['x'],3),round(v['y'],3)) in rv: continue
    if x0<v['x']<x1 and y0<v['y']<y1:
        sp=v.get('span') or []
        ax.add_patch(Circle((v['x'],v['y']),v['size']/2,color='k' if len(sp)==6 else 'purple',alpha=.5))
        ax.text(v['x'],v['y'],v['net']+'\n'+'>'.join(s[:2] for s in sp),fontsize=5)
ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.grid(True,lw=.3)
ax.set_xticks([x0+i*0.5 for i in range(int((x1-x0)/0.5)+1)]);ax.tick_params(labelsize=6)
plt.savefig(sys.argv[4],dpi=110,bbox_inches='tight')
