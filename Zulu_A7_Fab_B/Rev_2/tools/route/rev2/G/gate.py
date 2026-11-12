"""gate.py <tag> [router plans ...]
rip_total = rip_min.json + hand.json removals; route_total = hand copper + router copper (+ extra.json if present)
-> B/augment.py connectors -> smart_prune.py (pad-aware trim) -> compose_plan -> final_<tag>.json, then every gate: route_check on prep/base_moved.json,
widthcheck, prune_stubs on the applied board, via-in-pad audit, USB metrics, counts (B/analyze.py)."""
import contextlib
import io
import json
import os
import runpy
import sys

G = os.path.dirname(os.path.abspath(__file__))
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
R2 = T + '/route/rev2'
BASE = R2 + '/prep/base_moved.json'
PCB = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc'
WC = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/widthcheck.py'
sys.path.insert(0, T)
import compose_plan as CP  # noqa: E402

tag = sys.argv[1]
rip = json.load(open(G + '/rip_min.json'))
hand = json.load(open(G + '/hand.json'))
extra = json.load(open(G + '/extra.json')) if os.path.exists(G + '/extra.json') else {}
plans = [json.load(open(p)) for p in sys.argv[2:]]
rip_total = {'remove': rip['remove'] + hand['remove'] + extra.get('remove', []),
             'remove_vias': rip['remove_vias'] + hand['remove_vias'] + extra.get('remove_vias', [])}
route_total = {'tracks': hand['tracks'] + extra.get('tracks', []) + sum((p['tracks'] for p in plans), []),
               'vias': hand['vias'] + extra.get('vias', []) + sum((p['vias'] for p in plans), []), 'remove': [], 'remove_vias': []}
json.dump(rip_total, open(G + '/rip_total.json', 'w'))
json.dump(route_total, open(G + '/route_total_%s.json' % tag, 'w'))


def run(*a):
    """run a tool script in this process (one python process for the whole gate)"""
    buf = io.StringIO()
    old = sys.argv[:]
    sys.argv[:] = list(a)
    cwd = os.getcwd()
    os.chdir(T)
    try:
        with contextlib.redirect_stdout(buf):
            runpy.run_path(a[0], run_name='__main__')
    except SystemExit:
        pass
    finally:
        sys.argv[:] = old
        os.chdir(cwd)
    return buf.getvalue().strip()


print(run(R2 + '/B/augment.py', BASE, G + '/rip_total.json', G + '/route_total_%s.json' % tag, G + '/route_aug_%s.json' % tag).split('\n')[0])
print(run(G + '/smart_prune.py', BASE, G + '/rip_total.json', G + '/route_aug_%s.json' % tag, G + '/rip_sp_%s.json' % tag,
          G + '/route_sp_%s.json' % tag))
print(run(T + '/compose_plan.py', BASE, G + '/rip_sp_%s.json' % tag, G + '/route_sp_%s.json' % tag, G + '/final_%s.json' % tag).split('\n')[-1])
F = json.load(open(G + '/final_%s.json' % tag))           # drop items removed and re-added unchanged (USB U2 end etc.)
same_t = {CP.tkey(t) for t in F['remove']} & {CP.tkey(t) for t in F['tracks']}
same_v = {CP.vkey(v) for v in F['remove_vias']} & {CP.vkey(v) for v in F['vias']}
for k, key, s in (('remove', CP.tkey, same_t), ('tracks', CP.tkey, same_t), ('remove_vias', CP.vkey, same_v), ('vias', CP.vkey, same_v)):
    F[k] = [o for o in F[k] if key(o) not in s]
json.dump(F, open(G + '/final_%s.json' % tag, 'w'), indent=1)
print('dedupe: %d tracks, %d vias removed-and-re-added dropped' % (len(same_t), len(same_v)))
print('\n'.join(run(T + '/route_check.py', G + '/final_%s.json' % tag, BASE).split('\n')[1:]))
print('\n'.join(run(WC, PCB, G + '/final_%s.json' % tag).split('\n')[-3:]))
M = CP.apply(json.load(open(BASE)), json.load(open(G + '/final_%s.json' % tag)))
json.dump(M, open(G + '/board_%s.json' % tag, 'w'))
print('prune_stubs:', run(T + '/prune_stubs.py', G + '/board_%s.json' % tag).split('\n')[-1])
print(run(R2 + '/D/via_pad.py', BASE, G + '/final_%s.json' % tag))
print(run(R2 + '/B/analyze.py', BASE, G + '/final_%s.json' % tag))
print(run(R2 + '/D/usb_metrics.py', G + '/final_%s.json' % tag))
