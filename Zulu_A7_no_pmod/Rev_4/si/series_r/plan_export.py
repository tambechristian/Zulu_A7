"""Export the CHOSEN series-R plan with the DFM fixes folded in (dfm_check.py variant FIXED: F1 D12 column at
(39.49,15.81), F2 R119/R120/R122/R123 0.04 mm south) as ONE implementation plan, and draw it.

    python plan_export.py        writes dq_series_r_plan.json + dq_series_r_plan.png (this folder only)

The copper edit comes from dfm_check.py's own plan reader (load_plan + apply_fixes + apply), so it is exactly the
copper that dfm_check_fixed.log proved (0 violations, 0 shorts, 0 opens). Existing U3-side copper of D8/D9/D11/D12
that must change net to SDRAM-Dn is DERIVED from physical connectivity (the island holding the U3 pad), the same
way dfm_check step 1 does it, and is written as remove-on-Dn + re-add-on-SDRAM-Dn so that tools/emit_copper.py can
apply it unchanged (it cannot re-net objects in place).

JSON layout (tools/emit_copper.py plan format plus implementation extras):
  remove        tracks to delete (old net, layer, width, ends)        -- emit_copper 'remove'
  remove_vias   vias to delete (old net, hole, x, y, span)             -- emit_copper 'remove_vias'
  tracks, vias  copper to add (vias use from/to)                        -- emit_copper 'tracks' / 'vias'
  parts         R119.. absolute placement (side, centre, rotation, pad nets) -- for a placement script, NOT emit_copper
  renet_pads    pads whose net the ECO changes (U3 DQ pads -> SDRAM-Dn); check only
  net_class_add nets to add to SDRAM_DATA
  microvias     added vias that tools/mark_microvias.py must mark (0.15 mm hole)
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0]]          # dfm_check reads --variant at import; keep it at its default
import dfm_check as D  # noqa: E402

EMIT_LAYER = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG',
              'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}


def main():
    E = D.apply_fixes(D.load_plan())
    pads, tracks, vias, newflags, errors = D.apply(E)
    assert not errors, errors
    n_old_t = len([t for t in D.board_records()[1]])
    n_old_v = len(D.board_records()[2])
    objs = D.build_objs(pads, tracks, vias, newflags)

    renames_t, renames_v, problems = {}, {}, []
    for n in sorted(E['parts']):
        fam = {'D%d' % n, 'SDRAM-D%d' % n}
        sub = [o for o in objs if o.net in fam]
        uf = D.phys_islands(sub, net_aware=False)
        isl = collections.defaultdict(list)
        for k, o in enumerate(sub):
            isl[uf.f(k)].append(o)
        u3 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U3' for o in os_)]
        u1 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U1' for o in os_)]
        if len(isl) != 2 or len(u3) != 1 or len(u1) != 1 or u3[0] == u1[0]:
            problems.append('D%d: %d islands' % (n, len(isl)))
            continue
        for o in isl[u3[0]]:
            kind, i = o.uid
            if o.net == 'SDRAM-D%d' % n:
                continue
            if kind == 't':
                if i < n_old_t:
                    renames_t[i] = 'SDRAM-D%d' % n
                else:
                    tracks[i]['net'] = 'SDRAM-D%d' % n
            elif kind == 'v':
                if i < n_old_v:
                    renames_v[i] = 'SDRAM-D%d' % n
                else:
                    vias[i]['net'] = 'SDRAM-D%d' % n
        for o in isl[u1[0]]:
            if o.net != 'D%d' % n:
                problems.append('D%d: U1-side object on %s: %s' % (n, o.net, o.tag))
    assert not problems, problems

    P = dict(source=dict(pcbdoc_md5=D.B['source']['pcbdoc_md5'], plan='dfm_check.py variant FIXED (F1 at %s, F2 dy -0.04)' % (D.F1XY,),
                         generated_by='si/series_r/plan_export.py'),
             remove=[], remove_vias=[], tracks=[], vias=[], parts=[], renet_pads=E['renet'],
             net_class_add=dict(SDRAM_DATA=sorted({'SDRAM-D%d' % n for n in E['parts']}, key=lambda s: int(s[7:]))),
             microvias=[], renamed_existing=dict(tracks=0, vias=0))
    base_all = D.board_records()[1]
    for t in E['rm_t']:
        m = [b for b in base_all if b['layer'] == t['layer'] and (not t.get('net') or b['net'] == t['net']) and (
            (D.same((t['x1'], t['y1']), (b['x1'], b['y1'])) and D.same((t['x2'], t['y2']), (b['x2'], b['y2']))) or
            (D.same((t['x1'], t['y1']), (b['x2'], b['y2'])) and D.same((t['x2'], t['y2']), (b['x1'], b['y1']))))]
        assert m, t
        b = m[0]
        P['remove'].append(dict(net=b['net'], layer=EMIT_LAYER[b['layer']], w=b['w'], x1=b['x1'], y1=b['y1'], x2=b['x2'], y2=b['y2']))
    for v in E['rm_v']:
        m = [b for b in D.board_records()[2] if D.same((b['x'], b['y']), (v['x'], v['y'])) and b['span'] == v['span']]
        assert len(m) == 1, (v, m)
        b = m[0]
        P['remove_vias'].append(dict(net=b['net'], x=b['x'], y=b['y'], hole=b['hole'], span=[b['span'][0], b['span'][-1]]))
    base_t = D.board_records()[1]
    base_v = D.board_records()[2]
    for i, new in sorted(renames_t.items()):
        t = base_t[i]
        P['remove'].append(dict(net=t['net'], layer=EMIT_LAYER[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
        P['tracks'].append(dict(net=new, layer=EMIT_LAYER[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
        P['renamed_existing']['tracks'] += 1
    for i, new in sorted(renames_v.items()):
        v = base_v[i]
        P['remove_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], hole=v['hole'], span=[v['span'][0], v['span'][-1]], why='rename'))
        P['vias'].append(dict(net=new, x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], **{'from': EMIT_LAYER[v['span'][0]], 'to': EMIT_LAYER[v['span'][-1]]}, why='rename'))
        P['renamed_existing']['vias'] += 1
    for i in range(n_old_t, len(tracks)):
        t = tracks[i]
        P['tracks'].append(dict(net=t['net'], layer=EMIT_LAYER[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for i in range(n_old_v, len(vias)):
        v = vias[i]
        rec = dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], **{'from': EMIT_LAYER[v['span'][0]], 'to': EMIT_LAYER[v['span'][-1]]})
        P['vias'].append(rec)
        P['microvias'].append(dict(rec, type='buried 0.27/0.15' if v['size'] < 0.29 else 'microvia 0.30/0.15'))
    byref = collections.defaultdict(dict)
    for p in E['add_p']:
        byref[p['ref']][p['pad']] = p
    for n in sorted(E['parts']):
        pr = E['parts'][n]
        p1, p2 = byref[pr['ref']]['1'], byref[pr['ref']]['2']
        P['parts'].append(dict(ref=pr['ref'], net_bit=n, side=pr['side'], footprint='R0201', comment='22',
                               x=round((p1['x'] + p2['x']) / 2, 5), y=round((p1['y'] + p2['y']) / 2, 5), rot=pr['rot'],
                               pad1=dict(net=p1['net'], x=p1['x'], y=p1['y']), pad2=dict(net=p2['net'], x=p2['x'], y=p2['y']),
                               designator_hidden=True))
    json.dump(P, open(os.path.join(HERE, 'dq_series_r_plan.json'), 'w'), indent=1)
    print('remove %d tracks (%d renames), remove %d vias (%d renames), add %d tracks, add %d vias (%d new), %d parts' % (
        len(P['remove']), P['renamed_existing']['tracks'], len(P['remove_vias']), P['renamed_existing']['vias'],
        len(P['tracks']), len(P['vias']), len(P['microvias']), len(P['parts'])))
    draw(P, base_t, base_v)


def draw(P, base_t, base_v):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    col = {'Top Layer': '#c0392b', 'Bottom Layer': '#2471a3', 'L3-SIG': '#d68910', 'L4-SIG': '#7d3c98',
           'L2-GND': '#1e8449', 'L5-VCC3V3': '#a04000'}
    views = [('South row (Bottom-side view, not mirrored): R119-R126', (27.6, 39.6, 3.2, 9.6)),
             ('North / U1 side: R127, R130, R131 (Top), R128 (Bottom)', (37.6, 44.0, 11.6, 17.2))]
    fig, axes = plt.subplots(2, 1, figsize=(12, 13))
    rmkey = {(r['layer'], round(r['x1'], 3), round(r['y1'], 3), round(r['x2'], 3), round(r['y2'], 3)) for r in P['remove']}
    for ax, (title, (x0, x1, y0, y1)) in zip(axes, views):
        for p in D.B['pads']:
            if not (x0 - 1 < p['x'] < x1 + 1 and y0 - 1 < p['y'] < y1 + 1) or p['layer'] not in ('Top', 'Bottom', 'Multi'):
                continue
            ax.add_patch(Rectangle((p['x'] - p['size_x'] / 2 if p['rot'] in (0, 180) else p['x'] - p['size_y'] / 2,
                                    p['y'] - p['size_y'] / 2 if p['rot'] in (0, 180) else p['y'] - p['size_x'] / 2),
                                   p['size_x'] if p['rot'] in (0, 180) else p['size_y'],
                                   p['size_y'] if p['rot'] in (0, 180) else p['size_x'],
                                   fc='#bbbbbb' if p['layer'] == 'Bottom' else '#e8c0c0', ec='none', alpha=0.6, zorder=1))
            if p['ref'] == 'U3' and p['net']:
                ax.text(p['x'], p['y'], '%s\n%s' % (p['pad'], p['net'][:7]), fontsize=5, ha='center', va='center', zorder=6, clip_on=True)
        for t in base_t:
            if t['layer'] not in D.CU or not (min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0):
                continue
            k = (EMIT_LAYER[t['layer']], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
            if k in rmkey:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=0.8, ls=':', zorder=3)
            else:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[EMIT_LAYER[t['layer']]], lw=max(0.6, t['w'] * 12), alpha=0.18, zorder=2)
        for v in base_v:
            if x0 < v['x'] < x1 and y0 < v['y'] < y1:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#888888', lw=0.5, zorder=2))
        for t in P['tracks']:
            if t.get('why') == 'rename':
                continue
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[t['layer']], lw=max(1.0, t['w'] * 14), zorder=4,
                    solid_capstyle='round')
        for v in P['vias']:
            if v.get('why') == 'rename':
                continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#000000', lw=1.2, zorder=5))
        for pr in P['parts']:
            for pd in (pr['pad1'], pr['pad2']):
                ax.add_patch(Rectangle((pd['x'] - 0.15, pd['y'] - 0.15), 0.3, 0.3, fc='#f1c40f', ec='k', lw=0.6, zorder=5))
            if x0 < pr['x'] < x1 and y0 < pr['y'] < y1:
                ax.text(pr['x'], pr['y'] - 0.32 if pr['side'] == 'Bottom' and pr['y'] < 9 else pr['y'] + 0.22,
                        '%s D%d (%s)' % (pr['ref'], pr['net_bit'], pr['side'][0]), fontsize=7, ha='center', zorder=7,
                        fontweight='bold')
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.2)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=c, lw=2, label='new ' + k) for k, c in col.items()]
    h += [Line2D([], [], color='k', ls=':', label='removed'), Line2D([], [], marker='s', color='#f1c40f', ls='', label='new R pad'),
          Line2D([], [], marker='o', mfc='none', color='k', ls='', label='new via / microvia')]
    axes[0].legend(handles=h, fontsize=7, loc='upper left', ncol=3)
    fig.suptitle('DQ series resistors, implementation plan (judge FINAL + DFM fixes F1/F2); faint = existing copper; board coords mm, y up',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, 'dq_series_r_plan.png'), dpi=150)


if __name__ == '__main__':
    main()
