"""rb.py model plan|- x0 y0 x1 y1 out.png layer[,layer]  : big single-layer render with net labels"""
import json,sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
M=json.load(open(sys.argv[1])); P=json.load(open(sys.argv[2])) if sys.argv[2]!='-' else {'tracks':[],'vias':[]}
x0,y0,x1,y1=map(float,sys.argv[3:7]); out=sys.argv[7]; LAYS=sys.argv[8].split(',')
C={'GND':'#888','VU':'orange','USB5V0':'magenta','VBATT':'green','PWR_SW':'blue','EN':'cyan','PWR_PROG':'brown'}
fig,axs=plt.subplots(1,len(LAYS),figsize=(12*len(LAYS),12*(y1-y0)/(x1-x0)))
if len(LAYS)==1: axs=[axs]
for ax,L in zip(axs,LAYS):
    ax.set_title(L); ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.grid(True,lw=.3)
    ax.set_xticks([x0+0.5*i for i in range(int((x1-x0)*2)+1)])
    ax.set_yticks([y0+0.5*i for i in range(int((y1-y0)*2)+1)])
    k=72*12/(x1-x0)
    for p in M['pads']:
        if (L in p['layers'] or p.get('drill')) and x0-2<p['x']<x1+2 and y0-2<p['y']<y1+2:
            ax.add_patch(Rectangle((p['x']-p['w']/2,p['y']-p['h']/2),p['w'],p['h'],fc=C.get(p['net'],'#4a8'),alpha=.45,ec='k',lw=.5))
            ax.text(p['x'],p['y'],'%s-%s\n%s'%(p['ref'],p['pad'],p['net'][:10]),fontsize=6,ha='center',va='center')
    for src,ls in ((M,'-'),(P,'--')):
        for t in src['tracks']:
            if t['layer']==L:
                ax.plot([t['x1'],t['x2']],[t['y1'],t['y2']],ls,color=C.get(t['net'],'#4a8'),lw=t['w']*k,alpha=.6,solid_capstyle='round')
                if x0<t['x1']<x1 and y0<t['y1']<y1: ax.text((t['x1']+t['x2'])/2,(t['y1']+t['y2'])/2,t['net'][:8],fontsize=5,color='k')
        for v in src['vias']:
            sp=v.get('span') or [v['from'],v['to']]
            if x0<v['x']<x1 and y0<v['y']<y1 and (L in sp):
                ax.add_patch(Circle((v['x'],v['y']),v['size']/2,fc=C.get(v['net'],'#4a8'),ec='k',lw=.6))
                ax.text(v['x'],v['y']+0.2,v['net'][:8]+' %.2f'%v['size'],fontsize=5)
plt.tight_layout(); plt.savefig(out,dpi=100)
