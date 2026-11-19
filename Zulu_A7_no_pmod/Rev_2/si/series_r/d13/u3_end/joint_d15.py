import json, os, subprocess, sys
d14 = json.load(open('cands_14_XF-Top_gnd47.json'))['cands']
for i, c in enumerate(d14):
    bp = os.path.abspath('joint/base_14_%02d.json' % i)
    env = dict(os.environ, U3END_BASE=bp, U3END_SUFFIX='_on14_%02d' % i)
    r = subprocess.run([sys.executable, 'search.py', '15', 'XF-Top', 'none', '38.2,15.8,40.6,17.6', '6'], env=env, capture_output=True, text=True)
    print(i, c['x'], c['y'], c['rot'], r.stdout.splitlines()[0] if r.stdout else r.stderr[-800:], flush=True)
