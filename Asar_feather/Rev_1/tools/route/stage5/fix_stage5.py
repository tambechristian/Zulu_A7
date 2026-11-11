"""Drop the two VCC3V3 microvias that sit under the VCC3V3 through via at (34.95, 12.425) from the stage-5 plan and
its chunk files, so the plans match the board after FeatherFixStage5.pas (2026-10-31). Idempotent."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
def gone(v):
    return v['net'] == 'VCC3V3' and abs(v['x'] - 34.95) < 1e-3 and abs(v['y'] - 12.425) < 1e-3 and abs(v['hole'] - 0.15) < 1e-3
for name in ('tie38_swapB.json', 'tie38_swapB_a.json', 'tie38_swapB_b.json'):
    p = os.path.join(HERE, name); P = json.load(open(p))
    n = len(P['vias']); P['vias'] = [v for v in P['vias'] if not gone(v)]
    if n != len(P['vias']):
        P['log'] = P.get('log', []) + ['FixStage5: 2 VCC3V3 microvias under the through via at (34.95,12.425) removed (hole-to-hole DRC)']
        json.dump(P, open(p, 'w'), indent=0)
    print('%s: %d -> %d vias' % (name, n, len(P['vias'])))
