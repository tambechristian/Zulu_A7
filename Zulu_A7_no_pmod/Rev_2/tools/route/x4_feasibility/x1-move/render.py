from common import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
def render(M,D,fn,xr=(0,W),yr=(0,H),hl=()):
    parts=BC.build(M,D)
    fig,axs=plt.subplots(3,2,figsize=(22,15))
    LAY=['Top Layer','L3-SIG','L4-SIG','Bottom Layer']
    for ax,lay in zip(axs.flat,LAY+['vias','Top-parts']):
        ax.set_xlim(*xr); ax.set_ylim(*yr); ax.set_aspect('equal'); ax.set_title(lay)
        ax.add_patch(Rectangle((0,0),W,H,fill=False,ec='k'))
        if lay in LAY:
            for t in M['tracks']:
                if t['layer']==lay: ax.plot([t['x1'],t['x2']],[t['y1'],t['y2']],lw=max(0.5,t['w']*8),color='r' if t['net'] in hl else ('g' if t['net'] in ('GND','VCC3V3') else 'b'),alpha=.6,solid_capstyle='round')
            side='Top' if lay=='Top Layer' else ('Bottom' if lay=='Bottom Layer' else None)
            for p in M['pads']:
                L=p['layers'] or STACK
                if lay in L: ax.add_patch(Rectangle((p['x']-p['w']/2,p['y']-p['h']/2),p['w'],p['h'],color='orange',alpha=.7))
            if side:
                for r,P in parts[side].items():
                    for b in P['body']: ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec='m',lw=.8))
                    if P['body']: ax.text((P['body'][0][0]+P['body'][0][2])/2,(P['body'][0][1]+P['body'][0][3])/2,r,fontsize=6,ha='center')
            for v in M['vias']:
                if lay in v['span']: ax.add_patch(Circle((v['x'],v['y']),v['size']/2,color='k',alpha=.5))
        elif lay=='vias':
            for v in M['vias']:
                c={'Top Layer':'r','L2-GND':'g','L3-SIG':'b','L4-SIG':'c','L5-VCC3V3':'y'}[v['span'][0]]
                ax.add_patch(Circle((v['x'],v['y']),v['size']/2,color=c,alpha=.6))
        else:
            for r,P in parts['Top'].items():
                for b in P['body']: ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec='m'))
            for r,P in parts['Bottom'].items():
                for b in P['body']: ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec='c',ls='--'))
    plt.tight_layout(); plt.savefig(fn,dpi=110); plt.close()
if __name__=='__main__':
    render(M0,D0,'base_east.png',(36,61),(0,25.4),hl=('USB_D_P','USB_D_N','USB5V0'))
    render(M0,D0,'base_mid.png',(15,42),(0,25.4),hl=('USB_D_P','USB_D_N','USB5V0','VBATT'))
