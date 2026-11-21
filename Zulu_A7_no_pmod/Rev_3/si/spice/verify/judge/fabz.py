import sys; sys.path.insert(0, '../..')
import fieldsolve as F
CU = 0.0152
for dk_pp in (3.9, 4.1, 4.4):
    for dk_core in (4.5, 4.6):
        for cu in (0.0152, 0.0178):
            # L3 trace sits on the core top, embedded in 1080 resin (0.0713 to L2); L4/1080/L5 below the core
            slabs = [(0.0711, dk_pp), (cu, dk_pp), (1.065, dk_core), (cu, dk_pp), (0.0713, dk_pp)]
            r = F.line_params(slabs, (0.0711 + cu + 1.065, cu, 0.125), True, True)
            print('PP Dk %.1f core Dk %.1f Cu %.4f: Z0 %.2f td %.3f L %.4f C %.4f' % (dk_pp, dk_core, cu, r['Z0'], r['td_ps_per_mm'], r['L_nH_per_mm'], r['C_pF_per_mm']))
