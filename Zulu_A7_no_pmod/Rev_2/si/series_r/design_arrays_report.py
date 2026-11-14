# -*- coding: utf-8 -*-
"""Analysis + outputs for design_arrays.py (gap survey, depth, arrays evaluation, electrical position, north blockers,
JSON + PNG).  READ-ONLY on the board files; writes design_arrays.json / design_arrays.png in this folder only."""
import json
import math
import os

import plan_check as P
import plan_south as SOUTH
import design_arrays as DA

HERE = DA.HERE
B, D, U3, ESC = DA.B, DA.D, DA.U3, DA.ESC
LINES = json.load(open(os.path.join(os.path.dirname(HERE), 'spice', 'lines.json')))
PS_PER_MM_BOT = LINES['fab:Bottom Layer@0.1250']['td_ps_per_mm']      # field-solved, si/spice/lines.json
DESIGNATOR = {'D%d' % i: 'R%d' % (119 + i) for i in range(16)}       # schematic_plan.md: R119 = D0 ... R134 = D15


def gap_survey():
    """For every gap between two neighbouring U3 pads: other-net Bottom copper within 0.09 mm of a 0.0762 mm probe
    through the gap (toe to heel), and of 0.5 mm probes continuing outward / inward."""
    objs = [o for o in P.objects(B.tracks, B.vias, B.pads)['Bottom'] if not (o.kind == 'pad' and o.tag.startswith('U3-'))]
    grid = P.Grid(objs)
    out = {}
    for row, pins, o in (('south', range(1, 27), -1), ('north', range(28, 54), 1)):
        for n in pins:
            a, b = U3[str(n)], U3[str(n + 1)]
            g = (a['x'] + b['x']) / 2
            toe, heel = a['y'] + o * DA.PAD_HALF_L, a['y'] - o * DA.PAD_HALF_L
            res = {}
            for part, (y0, y1) in (('in_gap', (toe, heel)), ('outward', (toe, toe + o * 0.5)), ('inward', (heel, heel - o * 0.5))):
                pr = P.Obj('track', 'cap', ((g, y0), (g, y1)), 0.0381, '__probe__', 'Bottom', 'probe', None, None)
                hits = sorted({(round(P.dist(pr, q), 3), q.describe()) for q in grid.near(pr)
                               if P.dist(pr, q) < P.CL and not (q.net or '').startswith('D')})
                res[part] = ['%s (%.3f)' % (h[1], h[0]) for h in hits]
            out['%d|%d' % (n, n + 1)] = dict(row=row, x=round(g, 4), pads=[a['net'], b['net']], free=not (res['in_gap'] or res['outward']), **res)
    return out


def outward_depth():
    """Per DQ column (pin x +-0.75 mm): distance from U3's pad toe outward to the nearest pad of another part."""
    out = {}
    for net, pin in DA.DQ_PIN.items():
        xp, yp = DA.pin_xy(net)
        o = DA.row_sign(net)
        toe = yp + o * DA.PAD_HALF_L
        best = (99.0, None)
        for p in D['pads']:
            if p['ref'] in ('U3', 'X2') or p['layer'] not in ('Bottom', 'Multi'):
                continue
            if p['x'] + p['w'] / 2 < xp - 0.75 or p['x'] - p['w'] / 2 > xp + 0.75:
                continue
            edge = p['y'] - p['h'] / 2 if o > 0 else p['y'] + p['h'] / 2
            dd = (edge - toe) * o
            if 0 < dd < best[0]:
                best = (round(dd, 3), '%s-%s (%s)' % (p['ref'], p['pad'], p['net']))
        out[net] = dict(toe_y=round(toe, 4), nearest_part_pad=best[1], depth_mm=best[0])
    return out


# Land patterns: the two CTS 0.8 mm parts are MEASURED on this board (R1 = 742C043, R34 = 742C083); the 0201-element
# arrays use ASSUMED typical lands (vendor land drawings were not retrieved -- parts.md OPEN 3).
ARRAYS = [
    dict(part='CTS 742C083 (4 x R, 0.8 mm pitch)', n=4, pitch=0.80, pad_w=0.50, depth=2.70, width=2.90,
         land='measured: board R34, pads 0.50 x 0.90, rows 1.80 apart'),
    dict(part='CTS 742C043 (2 x R, 0.8 mm pitch)', n=2, pitch=0.80, pad_w=0.45, depth=2.60, width=1.25,
         land='measured: board R1, pads 0.45 x 0.90, rows 1.70 apart'),
    dict(part='Panasonic EXB-18V / Yageo YC104 (4 x 0201, 0.4 mm pitch)', n=4, pitch=0.40, pad_w=0.20, depth=0.90, width=1.40,
         land='ASSUMED: pads 0.20 x 0.30, rows 0.60 apart (not from a vendor drawing)'),
    dict(part='Panasonic EXB-14V / Bourns CAY06 (2 x 0201, 0.5 mm pitch)', n=2, pitch=0.50, pad_w=0.25, depth=0.90, width=0.75,
         land='ASSUMED: pads 0.25 x 0.30, rows 0.60 apart (not from a vendor drawing)'),
]
DISCRETE = dict(part='Yageo RC0201FR-0722RL (discrete 0201)', n=1, pitch=None, pad_w=0.30, depth=0.30, width=0.90,
                land='measured: zulu_a7.PcbLib R0201, pads 0.30 x 0.30 at 0.60 mm')
MIN_PASS = P.CL * 2 + DA.W_RET      # a 0.10 mm Bottom D-net track between two foreign pads: 0.28 mm


def arrays_eval(gaps, depth, south_fixable):
    rows = {'south': ['D%d' % i for i in range(8)], 'north': ['D%d' % i for i in range(8, 16)]}
    avail = {r: min(depth[n]['depth_mm'] for n in rows[r]) for r in rows}
    pairs = [('D1', 'D2', '3|4', '5|6'), ('D3', 'D4', '6|7', '8|9'), ('D5', 'D6', '9|10', '11|12'),
             ('D9', 'D10', '43|44', '45|46'), ('D11', 'D12', '46|47', '48|49'), ('D13', 'D14', '49|50', '51|52')]
    res = []
    for fam in ARRAYS + [DISCRETE]:
        between = (fam['pitch'] - fam['pad_w']) if fam['pitch'] else None
        through_ok = fam['n'] == 1 or between >= MIN_PASS - 1e-9
        need = DA.TOE_GAP + fam['depth'] + 0.20     # toe web + land + 0.20 copper gap (0.10 web) to the next part's pad
        r = dict(part=fam['part'], land=fam['land'], elements=fam['n'],
                 element_pad_gap_mm=None if between is None else round(between, 3),
                 return_between_elements=('n/a' if fam['n'] == 1 else bool(through_ok)),
                 depth_needed_mm=round(need, 3),
                 nets_per_part_on_bottom=1 if fam['n'] == 1 else (fam['n'] if through_ok else min(2, fam['n'])))
        for row in rows:
            r['depth_available_%s_mm' % row] = avail[row]
            r['fits_depth_%s' % row] = need <= avail[row] + 1e-9
        if fam['n'] == 2 and not through_ok:
            pr = []
            for a, b2, g1, g2 in pairs:
                blk = [g for g in (g1, g2) if not (gaps[g]['free'] or g in south_fixable)]
                pr.append(dict(pair=a + '/' + b2, flank_gaps=[g1, g2],
                               blocked={g: (gaps[g]['in_gap'] + gaps[g]['outward'])[:2] for g in blk}))
            r['pairs'] = pr
        res.append(r)
    return res


def electrical(Rs):
    out, sim = {}, {}
    for Rv in ('22', '33'):
        f = HERE + '/design_arrays_sim_r%s.json' % Rv
        if os.path.exists(f):
            for x in json.load(open(f)):
                sim[(Rv, x['net'], x['corner'])] = x
    for net, R in Rs.items():
        L = lambda t: math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        feed = sum(L(t) for t in R['tracks'] if t['net'].startswith('SDRAM-'))
        ret = sum(L(t) for t in R['tracks'] if not t['net'].startswith('SDRAM-'))
        old = ESC[net]['bottom_stub_length']
        e = dict(feed_mm=round(feed, 3), feed_ps=round(feed * PS_PER_MM_BOT, 1),
                 r_body_centre_mm=round(feed + DA.R_PITCH / 2, 3), r_body_centre_ps=round((feed + DA.R_PITCH / 2) * PS_PER_MM_BOT, 1),
                 fold_back_return_mm=round(ret, 3), fold_back_return_ps=round(ret * PS_PER_MM_BOT, 1),
                 old_stub_mm=round(old, 3), added_bottom_length_mm=round(feed + ret - old, 3))
        for Rv in ('22', '33'):
            for c in ('typ', 'max'):
                x = sim.get((Rv, net, c))
                if x:
                    e['sim_r%s_%s' % (Rv, c)] = dict(ball_vmin=round(x['ball_vmin'], 3), ball_vmax=round(x['ball_vmax'], 3),
                                                     ball_budget_pct=round(100 * x['ball_budget'], 1), die_vmin=round(x['die_vmin'], 3),
                                                     die_budget_pct=round(100 * x['die_budget'], 1), t10_90_ns=round(x['t10_90_ns'], 2))
        out[net] = e
    return out


def north_blockers():
    f = {}
    toe = U3['53']['y'] + DA.PAD_HALF_L
    f['led_resistor_row'] = [dict(ref=p['ref'], pad=p['pad'], net=p['net'], x=p['x'], y=p['y'], pad_edge_from_toe_mm=round(p['y'] - p['h'] / 2 - toe, 3))
                             for p in D['pads'] if p['ref'] in ('R80', 'R81', 'R82', 'R83')]
    f['row_needed'] = ('a 0201 row needs pads at y %.3f..%.3f (0.21 mm toe web) and >= 0.20 mm copper (0.10 mm mask web) to the next '
                       'part, so the next pads must start at y >= %.3f; R80-R83 start at y 18.600' %
                       (toe + DA.TOE_GAP, toe + DA.TOE_GAP + DA.R_PAD, toe + DA.TOE_GAP + DA.R_PAD + 0.2))
    f['vcc3v3_fingers_in_row'] = [t for t in D['tracks'] if t['net'] == 'VCC3V3' and t['layer'] == 'Bottom'
                                  and 18.2 < max(t['y1'], t['y2']) < 19.1 and 29.0 < min(t['x1'], t['x2']) < 35.0]
    f['l3_vcc1v0_bar_under_toes'] = [t for t in D['tracks'] if t['net'] == 'VCC1V0' and t['layer'] == 'L3-SIG'
                                     and min(t['y1'], t['y2']) < 18.0 and max(t['y1'], t['y2']) > 17.0]
    f['l4_lines_just_north'] = [t for t in D['tracks'] if t['net'] in ('SD-DAT0', 'SD-DAT2') and t['layer'] == 'L4-SIG'
                                and 18.5 < t['y1'] < 20 and min(t['x1'], t['x2']) < 36]
    f['led_microvias_in_row_band'] = [v for v in D['vias'] if v['net'] in ('N$LD0R', 'N$LD0G', 'N$LD1A', 'SD-DAT0', 'SD-DAT2', 'LED1')
                                      and 'Bottom' in v['span'] and 18.2 < v['y'] < 19.1 and 29 < v['x'] < 38]
    f['foreign_row_crossings'] = {
        '41|42': 'SD-DAT0: Bottom from its L4 stack (29.500,18.700) down the gap to under U3 (west)',
        '42|43': 'N$LD0B: Bottom from R80-2 down the gap to the Top..Bottom stack (29.300,15.600)',
        '51|52': 'SD-DAT2: Bottom between its L3 stacks (36.750,18.300) and (37.200,16.550); L3 is blocked by the '
                 'VCC1V0 bar, L4 by D14 (y 17.25)'}
    f['gap_exits_needing_local_edits'] = {
        '43|44': 'U3-43 VCC3V3 heel track to through via (30.300,16.400) (the via also feeds U2 on Top)',
        '48|49': 'UART_FT_RXD Bottom track + microvia (34.500,16.650)',
        '49|50': 'U3-49 VCC3V3 heel track to via (35.260,16.380) and UART_FT_TXD microvia (34.850,16.450)',
        '53|54': 'U3-54 GND toe track + GND via (38.350,18.400)'}
    r0 = HERE + '/r0_pernet.json'
    if os.path.exists(r0):
        f['ball_budget_pct_at_R0'] = {'%s %s' % (x['corner'], x['net']): round(100 * min(x['ball_budget'], 9.999), 1)
                                      for x in json.load(open(r0))}
    return f


def plot(Rs, plan, chk, gaps, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    tracks, vias, pads, rep = P.apply_plan(B, plan)
    fig, axs = plt.subplots(2, 1, figsize=(15, 15))
    wins = [(27.6, 39.6, 3.3, 9.6, 'SOUTH row D0-D7, Bottom, AFTER the plan, seen from above: red = added or changed copper, '
                                    'grey dashed = removed, orange = the eight new 22 ohm 0201s'),
            (27.6, 39.6, 15.4, 20.9, 'NORTH row D8-D15, Bottom, unchanged: why the same plan does not close here (magenta)')]
    for k, (ax, (x0, x1, y0, y1, title)) in enumerate(zip(axs, wins)):
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=10)
        ax.grid(True, lw=0.2); ax.set_xlabel('x mm (board origin bottom-left)'); ax.set_ylabel('y mm')
        use_t, use_v, use_p = (tracks, vias, pads) if k == 0 else (B.tracks, B.vias, B.pads)
        for t in use_t:
            if t['layer'] != 'Bottom' or max(t['x1'], t['x2']) < x0 or min(t['x1'], t['x2']) > x1 or \
                    max(t['y1'], t['y2']) < y0 or min(t['y1'], t['y2']) > y1:
                continue
            new = t.get('new')
            dn = (t['net'] or '').startswith('D') or (t['net'] or '').startswith('SDRAM-D')
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='red' if new else ('darkorange' if dn else 'steelblue'),
                    lw=max(t['w'], 0.05) * 30, alpha=0.8 if new else 0.45, solid_capstyle='round', zorder=3 if new else 2)
        if k == 0:
            for t in rep['removed_tracks']:
                if t['layer'] == 'Bottom':
                    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='grey', lw=0.9, ls='--', zorder=4)
        for p in use_p:
            if p['layer'] not in ('Bottom', 'Multi') or not (x0 - 1 < p['x'] < x1 + 1 and y0 - 1 < p['y'] < y1 + 1):
                continue
            c, a = ('orange', 0.95) if p.get('new') else (('gold', 0.6) if ('D' in (p['net'] or '') and p['ref'] == 'U3') else ('silver', 0.6))
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=c, alpha=a, zorder=5))
            if p['ref'] == 'U3' and 'D' in (p['net'] or ''):
                ax.text(p['x'], p['y'], p['net'].replace('SDRAM-', ''), fontsize=6, ha='center', va='center', rotation=90, zorder=6)
            elif p['ref'] != 'U3' and not p.get('new') and p['ref'][0] in 'RC':
                ax.text(p['x'], p['y'], p['ref'], fontsize=4.5, ha='center', va='center', zorder=6)
        for v in use_v:
            if 'Bottom' not in v['span'] or not (x0 < v['x'] < x1 and y0 < v['y'] < y1):
                continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=bool(v.get('new')),
                                color='red' if v.get('new') else ('darkorange' if (v['net'] or '').startswith('D') else 'k'),
                                lw=0.6, alpha=0.85, zorder=6))
        if k == 0:
            for net, R in Rs.items():
                ax.text(R['x'], R['y'] - 0.55, '%s %s' % (R['ref'], net), fontsize=6.5, ha='center', va='center', color='darkred', zorder=7)
            for g, info in gaps.items():
                if info['row'] == 'south' and x0 < info['x'] < x1:
                    ax.text(info['x'], 9.35, g, fontsize=5, ha='center', color='dimgray')
            for txt, xy in (('TMS moved to gap 7|8', (33.6, 7.6)), ('U3-6 GND heel straightened', (34.85, 8.3)),
                            ('U3-9 heel microvia to L5', (32.35, 7.35)), ('FT-VCORE trunk y 4.55 -> 4.28', (31.1, 4.05)),
                            ('U3-12 GND re-run', (30.05, 4.7)), ('C138-2 own microvia; TDO reshaped', (28.6, 4.15))):
                ax.annotate(txt, xy, fontsize=6, color='red', ha='center')
        else:
            for g, info in gaps.items():
                if info['row'] == 'north' and x0 < info['x'] < x1:
                    ax.text(info['x'], 15.55, g, fontsize=5, ha='center', color='dimgray')
                    if not info['free']:
                        ax.plot([info['x']], [17.53], marker='x', color='magenta', ms=7, mew=1.5, zorder=8)
            ax.add_patch(Rectangle((27.6, 18.13), 12.0, 0.47, color='magenta', alpha=0.12, zorder=1))
            ax.text(33.6, 18.37, 'only 0.47 mm between the U3 toes and the R80-R83 pads; a 0201 row needs 0.71 mm',
                    fontsize=7, ha='center', color='purple', zorder=9)
            ax.text(27.7, 20.6, 'x = gap already used by another net (SD-DAT0, N$LD0B, SD-DAT2) or blocked at its exit.  '
                                'L3 under these toes carries the VCC1V0 0.8 mm bar (y 17.1-17.9); L4 just north carries SD-DAT0 (y 19.2) '
                                'and SD-DAT2 (y 19.5-19.7)', fontsize=6.5, color='purple')
    fig.text(0.01, 0.003, 'si/series_r/design_arrays.py + plan_check.py on board_extract.json (PcbDoc md5 %s). '
             'South plan check: %d rule violations.' % (D['source']['pcbdoc_md5'][:8], len(chk['violations'])), fontsize=8)
    plt.tight_layout(rect=(0, 0.01, 1, 1))
    plt.savefig(path, dpi=130)
    plt.close(fig)


def main():
    gaps = gap_survey()
    depth = outward_depth()
    Rs, extra, notes = SOUTH.south(DA.tpl)
    for n, R in Rs.items():
        R['ref'] = DESIGNATOR[n]
    plan = DA.build(Rs, extra)
    chk = P.check_plan(B, plan, DA.touched(plan, Rs))
    south_fixable = {'6|7', '8|9', '9|10', '12|13'}     # made usable by the south plan's local edits (checked above)
    arr = arrays_eval(gaps, depth, south_fixable)
    ele = electrical(Rs)
    nb = north_blockers()
    placements = [dict(ref=R['ref'], nets='%s / SDRAM-%s' % (n, n), side='Bottom', x=R['x'], y=R['y'], rot=R['rot'],
                       pad1=R['pads'][0], pad2=R['pads'][1], dist_from_u3_pin_mm=ele[n]['feed_mm'],
                       footprint='R0201 (zulu_a7.PcbLib)', part='Yageo RC0201FR-0722RL') for n, R in Rs.items()]
    out = dict(source=D['source'],
               rules_used=dict(clearance=P.CL, sdram_inner=P.CL_SDRAM_INNER, hole_to_hole=P.HOLE_HOLE, mask_expansion=P.MASK,
                               sliver=P.SLIVER, component_clearance_advisory=P.COMP_CL, toe_web=DA.TOE_GAP),
               gap_survey=gaps, outward_depth=depth, arrays=arr,
               south_plan=dict(placements=placements, notes=notes,
                               copper=dict(remove_tracks=plan['remove_tracks'], add_tracks=plan['add_tracks'],
                                           remove_vias=plan['remove_vias'], add_vias=plan['add_vias'],
                                           renet_pads=plan['renet_pads'], add_pads=plan['add_pads']),
                               check=dict(violations=chk['violations'], worst=chk['worst'],
                                          component_advisory=chk['component_advisory'], connectivity=chk['connectivity'],
                                          missing_removals=chk['removal']['missing'])),
               electrical=ele, north=nb,
               arrays_verdict=(
                   'Arrays lose on every count measured here. (1) The 0.8 mm-pitch CTS 742C043/742C083 match the TSOP pitch but '
                   'their lands are 2.6/2.7 mm deep (measured on R1/R34): 3.0/3.1 mm needed vs 1.47 mm south (toe to the C135-C41 '
                   '0201 decoupling row) and 0.47 mm north (toe to R80-R83). (2) The 0201-element arrays fit the south depth '
                   '(1.31 mm needed, assumed lands) but their 0.20/0.25 mm element gaps are < 0.28 mm, so only the two END elements '
                   'can return on Bottom: a 4-element array serves 2 nets, and a 2-element array only a DQ pair whose BOTH flank '
                   'gaps are usable. (3) Of the six 0.8 mm DQ pairs only D3/D4 has both flank gaps usable (D1/D2: 5|6 is the '
                   'FT-VPHY neck; D5/D6: 11|12 is the FT-VCORE neck; north pairs: blocked as listed) and an array on D3/D4 would '
                   'cover gap 7|8, which the south pocket needs for TMS (7 gaps for 7 users). (4) Discrete 0201s use the board\'s '
                   'existing R0201 footprint and process, keep >= 0.3 mm between Rs (vs ~0.1 mm element spacing), and close '
                   'all eight south nets with 0 rule violations.'))
    json.dump(out, open(DA.OUT_JSON, 'w'), indent=1, default=str)
    plot(Rs, plan, chk, gaps, DA.OUT_PNG)
    print('south violations:', len(chk['violations']), '| worst margins:', {k: v[0] for k, v in chk['worst'].items()})
    print('connectivity ok:', all(v['ok'] for v in chk['connectivity'].values()), sorted(chk['connectivity']))
    for a in arr:
        print('ARRAY %-60s need %.2f  S %.2f N %.2f  between %-5s nets/part %s' % (
            a['part'], a['depth_needed_mm'], a['depth_available_south_mm'], a['depth_available_north_mm'],
            a['return_between_elements'], a['nets_per_part_on_bottom']), [(p['pair'], list(p['blocked'])) for p in a.get('pairs', [])])
    for n, e in ele.items():
        print(n, e['feed_mm'], e['feed_ps'], e['fold_back_return_mm'], e['old_stub_mm'], e.get('sim_r22_max', {}).get('ball_vmin'))
    for n in sorted(depth, key=lambda s: int(s[1:])):
        print('depth', n, depth[n])


if __name__ == '__main__':
    main()
