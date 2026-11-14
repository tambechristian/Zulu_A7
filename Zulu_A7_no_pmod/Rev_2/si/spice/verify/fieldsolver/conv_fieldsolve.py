"""Grid / domain convergence of fieldsolve on the actual Zulu geometries (import only, no writes to the parent dir)."""
import sys, os, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import fieldsolve as F

cases = [('L3-SIG', 0.125), ('L4-SIG', 0.125), ('Top Layer', 0.0762), ('Bottom Layer', 0.125)]

def run(tag, **kw):
    for layer, w in cases:
        t0 = time.time()
        slabs, tr, pb, pt = F.layer_geometry(layer, w)
        if 'air' in kw and layer in ('Top Layer', 'Bottom Layer'):
            slabs = slabs[:-1] + [(kw['air'], 1.0)]
        kk = {k: v for k, v in kw.items() if k in ('fine', 'half_width')}
        if 'finefac' in kw:
            kk['fine'] = min(tr[1] / 4.0, w / 160.0) * kw['finefac']
        r = F.line_params(slabs, tr, pb, pt, **kk)
        print('%-22s %-12s w=%.4f Z0=%8.4f td=%7.4f eeff=%.4f  (%.1fs)' % (tag, layer, w, r['Z0'], r['td_ps_per_mm'], r['eps_eff'], time.time() - t0), flush=True)

run('default')
F.GROW, F.COARSE_DIV = 1.05, 40.0
run('grow1.05 div40')
F.GROW, F.COARSE_DIV = 1.10, 16.0
run('fine x4', finefac=4.0)
run('fine x0.5', finefac=0.5)
run('halfwidth 2x', half_width=None) if False else None
for hw in (3.0, 30.0):
    run('half_width=%g' % hw, half_width=hw)
run('air 10 mm', air=10.0)
run('air 1 mm', air=1.0)
