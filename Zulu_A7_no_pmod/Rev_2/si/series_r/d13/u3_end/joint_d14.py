import json, os, subprocess, sys
import planio
d13 = json.load(open('cands_13_XF-Top_gnd47.json'))['cands']
for i, c in enumerate(d13):
    P = planio.merge([c['rec']], note='D13 cand %d' % i)
    bp = os.path.abspath('joint/base_13_%02d.json' % i)
    planio.write(P, bp)
    env = dict(os.environ, U3END_BASE=bp, U3END_SUFFIX='_on13_%02d' % i)
    r = subprocess.run([sys.executable, 'search.py', '14', 'XF-Top', 'none', '38.8,16.3,40.6,17.8', '6'], env=env, capture_output=True, text=True)
    print(i, c['x'], c['y'], c['rot'], r.stdout if r.stdout else r.stderr[-800:], flush=True)
