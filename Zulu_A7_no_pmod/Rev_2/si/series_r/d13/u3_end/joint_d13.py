import json, os, subprocess, sys
import planio
d14 = json.load(open('cands_14_XF-Top_gnd47.json'))['cands']
out = []
for i, c in enumerate(d14):
    P = planio.merge([c['rec']], note='D14 cand %d' % i)
    bp = os.path.abspath('joint/base_14_%02d.json' % i)
    planio.write(P, bp)
    env = dict(os.environ, U3END_BASE=bp, U3END_SUFFIX='_on14_%02d' % i)
    r = subprocess.run([sys.executable, 'search.py', '13', 'XF-Top', 'none', '38.0,15.5,40.2,17.2', '6'], env=env, capture_output=True, text=True)
    print(i, c['x'], c['y'], c['rot'], r.stdout.splitlines()[0] if r.stdout else r.stderr[-500:], flush=True)
