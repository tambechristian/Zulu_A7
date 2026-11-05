"""Generic local knot repair (2026-10-31, after tie_repair.py): move the copper of a few routed nets into a rippable
seed, cut it around the sealed ball(s), then re-route the sealed net(s) and the cut nets in a fixed order with
--rip 0 passes, exact-checking every stage.

    python tools/knot.py <model.json> <cut_nets> <sites.json> <radius> <stages> <outdir>
                         [--seed plan.json] [--remove remove.json] [--slack 0.005] [--pops 1500000] [--margin 2.5] [--order name|short|y]
                         [--reuse <earlier outdir>]   (same model/seed/cut, other stages; model, cut_nets, sites, radius ignored)

cut_nets   comma list of routed nets whose copper may move (net_seed.py moves it into the seed)
sites.json tie_cut.py sites: [{"net": "LDQM", "x": 27.4, "y": 15.93, "kind": null, "cut": ["WE#:0.7", "D6:0.7"]}]
stages     ';'-separated router passes, each a comma list of nets, e.g. "LDQM;WE#,D6" (slack per stage after a
           colon: "LDQM:0.005;WE#,D6:0.0")
--seed     a plan already on top of the model (e.g. the stage-6 corner plan) that stays rippable copper too
--remove   model tracks deleted before routing (dead stubs); carried into every plan's 'remove'

Writes <outdir>/model.json, seed.json, dropped.json, cut.json, st1.json.., final.json (deduped) and prints the
exact check of every stage; the last line is the final check."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(args, log=None):
    r = subprocess.run([PY] + args, capture_output=True, text=True)
    if log:
        open(log, 'w').write(r.stdout + r.stderr)
    if r.returncode:
        sys.exit('FAILED: %s\n%s%s' % (' '.join(args), r.stdout[-2000:], r.stderr[-2000:]))
    return r.stdout


def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    model, cut_nets, sites, radius, stages, out = sys.argv[1:7]
    seed0, remove = opt('--seed', ''), opt('--remove', '')
    slack, pops, margin = opt('--slack', '0.005'), opt('--pops', '1500000'), opt('--margin', '2.5')
    order = opt('--order', 'name')
    os.makedirs(out, exist_ok=True)
    reuse = opt('--reuse', '')
    M0 = os.path.join(out, 'model.json')
    cut = os.path.join(out, 'cut.json')
    if reuse:                                     # an earlier knot dir: same model, seed and cut, other stages
        import shutil
        for f in ('model.json', 'seed.json', 'dropped.json', 'cut.json'):
            shutil.copy(os.path.join(reuse, f), os.path.join(out, f))
        print('reused model/seed/cut of %s' % reuse)
    else:
        print(run([os.path.join(HERE, 'net_seed.py'), model, cut_nets, out]).strip())
    seed = json.load(open(os.path.join(out, 'seed.json')))
    if seed0 and not reuse:
        P = json.load(open(seed0))
        seed = {'vias': P['vias'] + seed['vias'], 'tracks': P['tracks'] + seed['tracks'],
                'remove': P.get('remove', []), 'log': P.get('log', []) + seed['log']}
        json.dump(seed, open(os.path.join(out, 'seed.json'), 'w'), indent=0)
    if not reuse:
        print(run([os.path.join(HERE, 'tie_cut.py'), M0, os.path.join(out, 'seed.json'), sites, radius, cut]).strip())
    rm = ['--remove', remove] if remove else []

    def stage(seed_file, nets, sl, name):
        o = os.path.join(out, name + '.json')
        run([os.path.join(HERE, 'router.py'), '--model', M0, '--seed', seed_file, '--nets', nets, '--rip', '0',
             '--margin', margin, '--pops', pops, '--slack', str(sl), '--order', order, '--out', o] + rm, log=os.path.join(out, name + '.log'))
        chk = run([os.path.join(HERE, 'route_check.py'), o, M0]).strip().splitlines()
        print('%-5s %-20s slack %-5s -> %s | %s' % (name, nets, sl, chk[-2], chk[-1]), flush=True)
        return o
    cur = cut
    for i, st in enumerate(stages.split(';')):
        nets, sl = (st.rsplit(':', 1) + [slack])[:2] if st.count(':') else (st, slack)
        cur = stage(cur, nets, sl, 'st%d' % (i + 1))
    final = os.path.join(out, 'final.json')
    print(run([os.path.join(HERE, 'plan_dedupe.py'), cur, final]).strip())
    print(run([os.path.join(HERE, 'route_check.py'), final, M0]).strip().splitlines()[-2])


if __name__ == '__main__':
    main()
