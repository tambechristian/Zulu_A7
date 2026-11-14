import maze as M, numpy as np, json
from scipy.sparse.csgraph import dijkstra
B = M.Board()
import sys
sites = json.load(open('maze_candidates.json'))['sites']
for mode in 'AB':
    sc = M.side_copper(mode)
    trkU, landU = B.masks(sc['sd'])
    srcU = M.poly_cells(M.RUN_TOP, 0) + ([] if mode == 'A' else [(k,) + M.cell(*M.VIA) for k in range(4)])
    AU, _ = M.build_graph(trkU, landU, srcU)
    dU = dijkstra(AU, indices=[M.nid(*c) for c in srcU], min_only=True).reshape(4, M.NY, M.NX)
    trkS, landS = B.masks(sc['u1'])
    srcS = [(k,) + M.cell(*M.VIA) for k in range(4)] + M.poly_cells(M.RUN_L3, 1) if mode == 'A' else [c for c in M.poly_cells(M.RUN_L3, 1) if M.XS[c[2]] < 38.0]
    AS, _ = M.build_graph(trkS, landS, srcS)
    dS = dijkstra(AS, indices=[M.nid(*c) for c in srcS], min_only=True).reshape(4, M.NY, M.NX)
    np.savez_compressed('dbg_%s.npz' % mode, dU=dU, dS=dS)
    nu = ns = 0
    for s in sites:
        k = M.RL.index(s['side'])
        dx, dy = (0.3, 0) if s['rot'] == 0 else (0, 0.3)
        for p in ((s['x'] - dx, s['y'] - dy), (s['x'] + dx, s['y'] + dy)):
            j, i = M.cell(*p)
            nu += np.isfinite(dU[k, j, i]); ns += np.isfinite(dS[k, j, i])
    print(mode, 'pads reachable U1', nu, 'SD', ns)
    for k in range(4):
        print('  ', M.RL[k], 'U1 cells', np.isfinite(dU[k]).sum(), 'SD cells', np.isfinite(dS[k]).sum())
