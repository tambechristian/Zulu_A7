"""(a) U1 receiver GND/power clamp current during reads, from the saved die waveforms and U1's IBIS clamp tables
    (LVCMOS33_S_8_HR, the receiver model bus_sim.py used), R = 0/15/22/33 ohm, fab stack.
(b) Write-direction extremes per net group from si/spice/results_all.json + waveforms (R = 0), fab stack.
Planning only; reads files, writes nothing but stdout."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SP)
import ibis2spice as I

U1 = I.Ibis(os.path.join(os.path.dirname(HERE), 'vivado', 'zulu_a7_no_pmod_u1.ibs'))
m = U1.model('LVCMOS33_S_8_HR')
COL = {'typ': 1, 'min': 2, 'max': 3}
RAIL = {'typ': 3.3, 'max': 3.465}
print('(a) U1 die clamp current during reads (peak per line; sum of 16 peaks = all-lines-same-edge bound)')
for tag in ('', '_r15', '_r22', '_r33'):
    for c in ('typ', 'max'):
        gc, pc = m.tables['gnd clamp'], m.tables['power clamp']
        pk_g, pk_p = [], []
        for d in range(16):
            z = np.load(os.path.join(SP, 'wave', 'D%d_read_%s_fab%s.npz' % (d, c, tag)))
            v = z['rx_die']
            ig = np.interp(v, gc[:, 0], gc[:, COL[c]])           # current into the pin (negative = out of die)
            ip = np.interp(RAIL[c] - v, pc[:, 0], pc[:, COL[c]])
            pk_g.append(-ig.min()); pk_p.append(ip.max())
        print('  R %-3s %-3s GND clamp peak %5.1f mA worst line, %6.1f mA sum | power clamp peak %5.1f mA worst, %6.1f sum' % (
            tag[2:] or '0', c, 1e3 * max(pk_g), 1e3 * sum(pk_g), 1e3 * max(pk_p), 1e3 * sum(pk_p)))

print('\n(b) WRITE direction (U1 drives, U3 receives), R = 0, fab stack, from results_all.json + wave/*.npz')
R = [r for r in json.load(open(os.path.join(SP, 'results_all.json'))) if 'error' not in r and r['stack'] == 'fab' and r['scenario'] == 'write']
groups = {'data D0-D15': lambda n: n.startswith('D') and n[1:].isdigit(),
          'address A0-A12 BS0/1': lambda n: (n.startswith('A') and n[1:].isdigit()) or n.startswith('BS'),
          'control': lambda n: n in ('CAS#', 'RAS#', 'WE#', 'CKE', 'SDRAM-CS#', 'LDQM', 'UDQM'),
          'SDRAM-CLK': lambda n: n == 'SDRAM-CLK'}
for g, f in groups.items():
    for c in ('typ', 'max'):
        rr = [r for r in R if f(r['net']) and r['corner'] == c]
        die_max = max(r['vmax'] for r in rr); die_min = min(r['vmin'] for r in rr)
        pin_os = max(r['pin_overshoot'] for r in rr); pin_us = max(r['pin_undershoot'] for r in rr)
        t = [r['t10_90_ns'] for r in rr]; rb = max(r['ringback_into_band'] for r in rr)
        print('  %-22s %-3s n=%2d  die %.2f..%.2f V  pin over +%.2f under -%.2f V  t10-90 %.2f-%.2f ns  ringback %.2f V' % (
            g, c, len(rr), die_min, die_max, pin_os, pin_us, min(t), max(t), rb))
