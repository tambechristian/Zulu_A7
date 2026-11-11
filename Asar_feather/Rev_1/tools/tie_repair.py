"""U3/U1 plane-tie repair on a finished signal plan (2026-10-29): adds the six power ties (GND E3/B7, VCC3V3 A7/A9/C7
and U1.R1) and locally re-plans the bus copper they displace, without rip-up. Recipe in docs/routing.md ("TIE
REPAIR COMPLETE").

    python tools/tie_repair.py <model.json> <signal_plan.json> <outdir> [--slack-a1 0.0]

model.json holds the stage-3 SDRAM bus as fixed copper (swapA/model.json style); the bus is moved into the seed
(bus_seed.py) so the passes may clip it. Writes <outdir>/model.json (bus-less model for route_check), dropped.json
(bus copper the board chain must not emit), remove_a8.json, the stage plans and final.json (deduped), and prints
the exact check of every stage. Every stage is a single-net or few-net router pass with --rip 0."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
BUS = os.path.join(HERE, 'route', 'stage3_sdram.json')

SITES_P = [
    {'net': 'VCC3V3', 'x': 31.725, 'y': 12.905, 'kind': 'stack_tie', 'cut': ['D4:0.4']},
    {'net': 'VCC3V3', 'x': 33.4, 'y': 12.83, 'kind': 'stack_tie', 'cut': ['A4:0.4', 'A6:0.4', 'D4:0.5', 'D0:0.6']},
    {'net': 'VCC3V3', 'x': 31.7, 'y': 14.5, 'kind': 'stack_tie', 'cut': ['A1:0.4', 'RAS#:2.5']},
    {'net': 'A3', 'x': 32.075, 'y': 14.7, 'kind': None, 'cut': ['A3:0.45']},
    {'net': 'VCC3V3', 'x': 30.4, 'y': 13.935, 'kind': 'stack_tie', 'cut': []},
    {'net': 'GND', 'x': 34.95, 'y': 9.8, 'kind': 'uvia_top', 'cut': []},
    {'net': 'GND', 'x': 32.65, 'y': 12.9, 'kind': 'uvia_top', 'cut': []},
]
SITES_S = [{'net': 'A0', 'x': 32.2, 'y': 15.2, 'kind': None, 'cut': ['A0:0.6']}]
STAGES = [('RAS#', 0.005), ('A1', 'a1'), ('A4,A6,D0,D4', 0.005)]      # after sites_p; then sites_s, A3, A0


def run(args, log=None):
    r = subprocess.run([PY] + args, capture_output=True, text=True)
    if log:
        open(log, 'w').write(r.stdout + r.stderr)
    if r.returncode:
        sys.exit('FAILED: %s\n%s%s' % (' '.join(args), r.stdout[-2000:], r.stderr[-2000:]))
    return r.stdout


def main():
    model, plan, out = sys.argv[1:4]
    slack_a1 = sys.argv[sys.argv.index('--slack-a1') + 1] if '--slack-a1' in sys.argv else '0.0'
    os.makedirs(out, exist_ok=True)
    print(run([os.path.join(HERE, 'bus_seed.py'), model, BUS, out]).strip())
    M0 = json.load(open(os.path.join(out, 'model.json')))
    P = json.load(open(plan))
    B = json.load(open(os.path.join(out, 'bus.json')))
    seed = {'vias': P['vias'] + B['vias'], 'tracks': P['tracks'] + B['tracks'], 'remove': P.get('remove', []),
            'log': P.get('log', []) + ['bus of stage3_sdram.json seeded (rippable) for the tie repair']}
    json.dump(seed, open(os.path.join(out, 'seed.json'), 'w'), indent=0)
    # A8's fixed L4 stub: its tail past the via at 30.875,13.425 is dead copper that walls D4 off the A7 column
    stub = [t for t in M0['tracks'] if t['net'] == 'A8' and t['layer'] == 'L4-SIG' and abs(t['x2'] - 31.4) < 1e-3
            and abs(t['y2'] - 13.367) < 1e-3]
    assert len(stub) == 1, stub
    rm = os.path.join(out, 'remove_a8.json')
    json.dump({'tracks': stub}, open(rm, 'w'))
    json.dump(SITES_P, open(os.path.join(out, 'sites_p.json'), 'w'))
    json.dump(SITES_S, open(os.path.join(out, 'sites_s.json'), 'w'))
    cut = os.path.join(out, 'cut_p.json')
    print(run([os.path.join(HERE, 'tie_cut.py'), os.path.join(out, 'model.json'), os.path.join(out, 'seed.json'),
               os.path.join(out, 'sites_p.json'), '0.6', cut]).strip())
    C = json.load(open(cut))
    C['tracks'].append(dict(stub[0], x2=30.875, y2=13.425))
    a2 = [t for t in C['tracks'] if t['net'] == 'A2' and t['layer'] == 'Top Layer' and abs(t['y1'] - 14.225) < 1e-3
          and abs(t['y2'] - 14.225) < 1e-3 and abs(t['x1'] - 31.4) < 1e-3]
    assert len(a2) == 1, a2
    a2[0]['y1'] = a2[0]['y2'] = 14.215
    C['log'] += ['A8 fixed L4 stub trimmed at its via (30.875,13.425)',
                 'A2 Top (31.4-32.075, 14.225) nudged to y 14.215 so the A9 column may sit at 14.500']
    json.dump(C, open(cut, 'w'), indent=0)

    def stage(seed_file, nets, slack, name):
        o = os.path.join(out, name + '.json')
        run([os.path.join(HERE, 'router.py'), '--model', os.path.join(out, 'model.json'), '--remove', rm, '--seed', seed_file,
             '--nets', nets, '--rip', '0', '--margin', '1.0', '--pops', '1500000', '--slack', str(slack), '--out', o],
            log=os.path.join(out, name + '.log'))
        chk = run([os.path.join(HERE, 'route_check.py'), o, os.path.join(out, 'model.json')]).strip().splitlines()
        print('%-6s %-14s slack %-5s -> %s | %s' % (name, nets, slack, chk[-2], chk[-1]))
        return o
    cur = cut
    for i, (nets, slack) in enumerate(STAGES):
        cur = stage(cur, nets, slack_a1 if slack == 'a1' else slack, 'st%d' % (i + 1))
    cut_s = os.path.join(out, 'cut_s.json')
    run([os.path.join(HERE, 'tie_cut.py'), os.path.join(out, 'model.json'), cur, os.path.join(out, 'sites_s.json'), '0.6', cut_s])
    cur = stage(cut_s, 'A3', 0.005, 'st4')
    cur = stage(cur, 'A0', 0.005, 'st5')
    final = os.path.join(out, 'final.json')
    print(run([os.path.join(HERE, 'plan_dedupe.py'), cur, final]).strip())
    print(run([os.path.join(HERE, 'route_check.py'), final, os.path.join(out, 'model.json')]).strip().splitlines()[-2])


if __name__ == '__main__':
    main()
