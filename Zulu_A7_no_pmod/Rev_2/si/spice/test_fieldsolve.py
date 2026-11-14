"""Self-checks of fieldsolve against closed forms: Cohn's exact zero-thickness centred stripline, and Hammerstad-Jensen
microstrip (zero-thickness, ~0.2 % accurate)."""
import numpy as np, time
from scipy.special import ellipk
import fieldsolve as F

def cohn(w, b, er):
    k = 1/np.cosh(np.pi*w/(2*b)); kp = np.sqrt(1-k*k)
    return 30*np.pi/np.sqrt(er)*ellipk(k**2)/ellipk(kp**2)

def hj(w, h, er):
    u = w/h
    f = 6+(2*np.pi-6)*np.exp(-(30.666/u)**0.7528)
    z01 = 60*np.log(f/u+np.sqrt(1+(2/u)**2))
    a = 1+np.log((u**4+(u/52)**2)/(u**4+0.432))/49+np.log(1+(u/18.1)**3)/18.7
    b = 0.564*((er-0.9)/(er+3))**0.053
    ee = (er+1)/2+(er-1)/2*(1+10/u)**(-a*b)
    return z01/np.sqrt(ee), ee

for w,b,er in [(0.125,0.4,4.3),(0.2,0.5,4.3)]:
    t0=time.time()
    tiny=1e-4
    r=F.line_params([(b/2-tiny/2,er),(tiny,er),(b/2-tiny/2,er)],(b/2-tiny/2,tiny,w),True,True,fine=w/40)
    print('stripline w=%.3f b=%.2f: solver %.2f  Cohn %.2f  (%.1fs)'%(w,b,r['Z0'],cohn(w,b,er),time.time()-t0))
for w,h,er in [(0.2,0.1,4.1),(0.0762,0.1,4.1)]:
    t0=time.time(); tiny=1e-4
    r=F.line_params([(h,er),(tiny,1.0),(3.0,1.0)],(h,tiny,w),True,False,fine=w/40)
    z,ee=hj(w,h,er)
    print('microstrip w=%.4f h=%.2f: solver Z0 %.2f eeff %.3f | HJ %.2f %.3f (%.1fs)'%(w,h,r['Z0'],r['eps_eff'],z,ee,time.time()-t0))
