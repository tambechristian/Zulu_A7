# -*- coding: utf-8 -*-
"""Write the Zulu A7 no-PMOD Rev 2 PCBWay FAB NOTES from tools/fab_facts.json (2026-11-13).

    python tools/fab_facts.py      # measure the saved PcbDoc and the exported drill files first
    python tools/fab_notes.py      # -> fabrication/Zulu_A7_no_pmod_Rev_2_PCBWay_FAB_NOTES.txt

Every board-derived number in the note (drill counts, via-in-pad sites and their stacks, mask reach over
through vias, hole sizes, slot centres, USB geometry, trace and space minimums, outline) is read from
fab_facts.json, whose 'source' must match the PcbDoc on disk. The prose that is not measured (stack, finish,
engineering questions) is the Fab B Rev 2 note's, edited for this board; the engineering questions come from
docs/dq_series_resistors.md (decisions 9, 12, 14, 15 and the CHAN7 / SDRAM-D14 advisory).
The export times of the Gerbers, drills and DRC are read from the files in Project Outputs.
"""
import collections
import datetime
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'Project Outputs for Zulu_a7_no_pmod')
PCB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc')
NOTE = os.path.join(ROOT, 'fabrication', 'Zulu_A7_no_pmod_Rev_2_PCBWay_FAB_NOTES.txt')
DRC = os.path.join(ROOT, 'docs', 'drc_r108_move.drc')
FABB_PCB = os.path.join(ROOT, '..', '..', 'Zulu_A7_Fab_B', 'Rev_2', 'Imported zulu_a7.PrjPcb', 'zulu_a7_fab_b.PcbDoc')
MOVES = os.path.join(HERE, 'route', 'vip2', 'plan1b.json')
FABB_FACTS = os.path.join(HERE, 'fab_facts_fabb_rev2.json')
BASE = 'Zulu_a7_no_pmod'
RELEASE_NAME = 'Zulu A7 no-PMOD Rev 2'
RELEASE_DATE = '2026-11-13'
SPAN_SHORT = {'Top-L2-GND': 'T-2', 'L2-GND-L3-SIG': '2-3', 'L3-SIG-L4-SIG': '3-4b', 'L4-SIG-L5-VCC3V3': '4-5',
              'L5-VCC3V3-Bottom': '5-B', 'Top-Bottom': 'thru'}
SPAN_ORDER = list(SPAN_SHORT)
VIA_NAME = {'Top-L2-GND': 'Top-L2 uvia', 'L5-VCC3V3-Bottom': 'L5-Bot uvia'}


def mtime(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')


def wrap(text, width=76):
    out, line = [], ''
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = word if not line else line + ' ' + word
    if line:
        out.append(line)
    return out


def relocated_parts():
    """Parts present on both boards whose centre or rotation differs from Fab B Rev 2 (Components6 records)."""
    import olefile

    def comps(path):
        d = olefile.OleFileIO(path).openstream('Components6/Data').read()
        out = {}
        for r in d.split(b'\x00'):
            kv = dict(x.split('=', 1) for x in r.decode('latin1').split('|') if '=' in x)
            if 'SOURCEDESIGNATOR' in kv and 'X' in kv:
                out[kv['SOURCEDESIGNATOR']] = (float(kv['X'].replace('mil', '')) * 0.0254, float(kv['Y'].replace('mil', '')) * 0.0254,
                                               round(float(kv.get('ROTATION', '0')), 1), kv.get('LAYER'))
        return out
    a, b = comps(FABB_PCB), comps(PCB)
    # the no-PMOD board is the Fab B board cut at its east end: same origin, so positions compare directly
    return sorted((r, a[r], b[r]) for r in set(a) & set(b)
                  if abs(a[r][0] - b[r][0]) > 0.001 or abs(a[r][1] - b[r][1]) > 0.001 or a[r][2] != b[r][2] or a[r][3] != b[r][3])


def main():
    F = json.load(open(os.path.join(HERE, 'fab_facts.json')))
    raw = open(PCB, 'rb').read()
    md5, sha = hashlib.md5(raw).hexdigest(), hashlib.sha256(raw).hexdigest().upper()
    if F['source']['md5'] != md5:
        raise SystemExit('fab_facts.json was measured on md5 %s, the board is %s: re-run fab_facts.py' % (F['source']['md5'], md5))
    if F['through_vias_in_smd_pads']:
        raise SystemExit('through vias in SMD pads: %s' % F['through_vias_in_smd_pads'])
    dvb = F['drill_vs_board']
    if any(v.get('board_not_in_file') or v.get('file_not_on_board') for v in dvb.values()):
        raise SystemExit('drill files and board disagree: %s' % dvb)
    geo = {g['span']: g for g in F['via_geometry']}
    n = {s: geo[s]['count'] for s in geo}
    uvia = n['Top-L2-GND'] + n['L2-GND-L3-SIG'] + n['L4-SIG-L5-VCC3V3'] + n['L5-VCC3V3-Bottom']
    hits = F['drill_hits_per_tool']
    if hits['TXT']['02'] != n['Top-Bottom']:
        raise SystemExit('TXT T02 %s != through vias %s' % (hits['TXT']['02'], n['Top-Bottom']))
    out = F['board_outline']
    w, h = out['size_mm']
    if not out['gm_matches_pcb']:
        raise SystemExit('GM profile does not match the PcbDoc outline')
    holes = collections.defaultdict(list)
    for p in F['pad_holes']:
        holes[round(p['hole'], 3)].append(p)
    x1 = {p['pad']: p for p in F['x1_hole_pads']}
    vip, vs = F['via_in_pad'], F['via_in_pad_summary']
    cols = {(c['ref'], c['pad'], round(c['via_x'], 3), round(c['via_y'], 3)): c['spans_at_xy'] for c in F['via_in_pad_columns']}
    mask = F['mask_over_through_vias']
    reach = [(s, e) for s in ('Top', 'Bottom') for e in mask[s]['through_via_lands_reached']]
    if not mask['all_same_net'] or any(mask[s]['through_via_holes_reached'] for s in ('Top', 'Bottom')):
        raise SystemExit('a mask opening reaches a through-via hole or another net')
    usb = F['usb_track_length']
    coupled = F['usb_coupled_overlap_by_gap'].get('Top 0.1500', 0)
    abut = F['through_via_lands_abutting_smd_pads']
    mv = F['mask_over_microvias']
    if not mv['all_same_net'] or any(e['hole_reached'] for s in ('Top', 'Bottom') for e in mv[s]):
        raise SystemExit('a mask opening reaches a microvia hole or another net')
    uns = F['unstacked_outer_microvias']
    proj = F['different_net_projected_hole_overlaps']
    cte = F['copper_to_edge']
    # the via-clearance pass moved four vias; the two on R108's pads went when R108 moved, so two remain
    moved_rep = [r for r in json.load(open(MOVES))['report'] if tuple(r['from']) != (4.8, 16.6) and r['net'] not in ('VU', 'LD4_A')]
    moves = [r['moved'] for r in moved_rep]
    if len(moves) != 2:
        raise SystemExit('expected 2 surviving moved vias in %s' % MOVES)
    fabb_sites = {(e['ref'], e['pad']) for e in json.load(open(FABB_FACTS))['via_in_pad']}
    new_sites = sorted({(e['ref'], e['pad']) for e in vip} - fabb_sites,
                       key=lambda rp: (re.sub(r'\d+', '', rp[0]), int(re.sub(r'\D', '', rp[0]) or 0), rp[1]))
    mc = F['mask_cover_different_net']
    moved = relocated_parts()
    if any(e['land_to_pad_gap'] < -0.0005 for e in abut):
        raise SystemExit('a through-via land overlaps an SMD pad by more than 0.5 um: %s' % abut)
    drc = open(DRC, encoding='latin1').read()
    drc_v = re.search(r'Violations Detected : (\d+)', drc).group(1)
    drc_t = re.search(r'Date\s*:\s*(\S+)\s+Time\s*:\s*([\d:]+ [AP]M)', drc.replace('\n', ' '))
    drc_when = datetime.datetime.strptime(drc_t.group(1) + ' ' + drc_t.group(2), '%m/%d/%Y %I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S')
    drc_w = re.search(r'Warnings\s*:\s*(\d+)', drc)
    gerb_t, drill_t = mtime(os.path.join(OUT, BASE + '.GTL')), mtime(os.path.join(OUT, BASE + '-RoundHoles.TXT'))
    pcb_t = mtime(PCB)

    L = []
    A = L.append
    A('ZULU A7 NO-PMOD REV 2 - PCBWAY FABRICATION NOTES')
    A('Revision: %s  (silkscreen title "ZULU A7 2.3"; Fab B Rev 2 reads "ZULU A7 2.2")' % RELEASE_NAME)
    A('Release date: %s' % RELEASE_DATE)
    A('PCB SHA-256: %s' % sha)
    A('Source: %s.PcbDoc (MD5 %s)' % (BASE, md5))
    A('')
    A('ORDER AND CAM GATE')
    L += wrap('This is a bare-board, six-layer, two-step sequential HDI release. It is a smaller derivative of '
              'the Zulu A7 Fab B Rev 2 board: same stack, same layer use, same via types and sizes, same design '
              'rules. What changed: the Pmod header and its parts were removed, the board was cut to %.2f x %.2f '
              'mm, the JTAG holes moved, 16 SDRAM series resistors were added, and the title is ZULU A7 2.3 (see '
              'CHANGES FROM FAB B REV 2). The drill and via counts below are new. Only microvias sit in SMD '
              'pads; no through via sits in any SMD pad (see VIA-IN-PAD).' % (w, h))
    L += wrap('Route it to PCBWay HDI engineering/CAM review. Do not release fabrication as a standard six-layer '
              'prototype without confirming every blind/buried drill pair, the via-in-pad list and the '
              'ENGINEERING QUESTIONS below.')
    A('')
    A('CHANGES FROM FAB B REV 2')
    L += wrap('Outline: 69.85 x 25.40 mm -> %.2f x %.2f mm (2.4 x 1.0 in). The Pmod header J1 (12 plated holes) '
              'and its series resistors R26-R33 left the design. The JTAG header holes JP3/JP4 (3 + 3, not '
              'fitted) now sit in one column at the west short edge. Sixteen 0201 SDRAM data series resistors '
              'R119-R134 were placed and routed (7 of their pads carry an in-pad microvia, listed below). Five '
              'through vias that the resize and the JTAG move had left in SMD pads were taken out: two (%s) moved %.2f-%.2f mm '
              'with a jumper, each land now at least 0.025 mm from every SMD pad; the TCK via in R4-6 was replaced by '
              'an in-pad Top-L2 + L2-L3 + L3-L4 microvia stack; the two on the R108 pads went when R108 moved. The '
              'JTAG-column move had put R108 (0402, Bottom) at (6.00, 13.48), under the L9 body; it now sits at '
              '(3.40, 17.80), turned 180 degrees, with an in-pad L5-Bottom + L4-L5 microvia stack on pad 2. '
              'Via objects 1,961 -> %s: through vias 354 -> %d, Top-L2 321 -> %d, L2-L3 307 -> %d, '
              'L3-L4 buried 403 -> %d, L4-L5 281 -> %d, L5-Bottom 295 -> %d. Stack, finish, layer use, via and '
              'hole sizes, X1 and its slots, and every design rule are unchanged. Parts placed differently from '
              'Fab B Rev 2 (same origin): %s.'
              % (w, h, ', '.join(r['pads'][0] for r in moved_rep), min(moves), max(moves), format(F['via_total'], ','), n['Top-Bottom'], n['Top-L2-GND'], n['L2-GND-L3-SIG'],
                 n['L3-SIG-L4-SIG'], n['L4-SIG-L5-VCC3V3'], n['L5-VCC3V3-Bottom'],
                 ', '.join('%s (%.2f, %.2f) -> (%.2f, %.2f)%s' % (r, a[0], a[1], b[0], b[1],
                           '' if a[2] == b[2] else ' rot %g -> %g' % (a[2], b[2])) for r, a, b in moved)))
    A('')
    A('BOARD')
    A('Finished outline: %.2f mm x %.2f mm (rectangle, from the GM profile)' % (w, h))
    A('Finished thickness: 1.60 mm +/-0.16 mm')
    A('Material: Shengyi S1000-2M, Tg 180')
    A('Surface finish: ENIG')
    A('Solder mask: green')
    A('Silkscreen: white')
    A('Layer order (PcbDoc layer names):')
    for i, (nm, use) in enumerate(zip(F['layer_order'], ['signal/components', 'GND plane polygon', 'signal', 'signal',
                                                         'VCC3V3 plane polygon', 'signal/components'])):
        A('  L%d  %-13s %s' % (i + 1, nm, use))
    A('')
    tw = F['track_min_width_by_layer']
    L += wrap('The L2 and L5 Gerbers are positive signal-layer polygon plots, not negative plane files. Minimum '
              'designed trace width is %.4f mm (3 mil), used on %s. Minimum designed copper spacing is 0.09 mm '
              '(global clearance rule; the measured minimum on the board is %.2f mm). Rule-specific clearances: '
              'SDRAM nets on L3/L4 0.10 mm, SDRAM-CLK on L3/L4 0.20 mm, L2/L5 planes to through vias 0.175 mm, '
              'X1 to the L5 plane 0.10 mm. Do not globally resize copper without approval.'
              % (F['track_min_width_routed'], ', '.join(k for k, v in tw.items() if v and abs(v - F['track_min_width_routed']) < 1e-4),
                 F['min_spacing_track_to_other_copper']['gap']))
    A('')
    A('STACK (AS AGREED WITH PCBWAY ENGINEERING FOR THE PREVIOUS HDI ZULU A7 BOARD)')
    A('Please build the same construction:')
    A('')
    for row in [('Layer/material', 'Thickness'), ('L1 copper', 'per PCBWay stack (outer foil + plating)'),
                ('3313 prepreg, L1-L2', '0.1015 mm'), ('L2 copper', '0.5 oz base, plated to 0.018 mm'),
                ('1080 prepreg, L2-L3', '0.0713 mm'), ('L3 copper', '0.5 oz'), ('Core, L3-L4', '1.065 mm'),
                ('L4 copper', '0.5 oz'), ('1080 prepreg, L4-L5', '0.0711 mm'),
                ('L5 copper', '0.5 oz base, plated to 0.018 mm'), ('3313 prepreg, L5-L6', '0.1015 mm'),
                ('L6 copper', 'per PCBWay stack (outer foil + plating)')]:
        A('  %-34s %s' % row)
    A('')
    L += wrap('Inner copper is 0.5 oz; do not substitute 1 oz without confirming that every 0.0762 mm trace and '
              '0.09 mm space remains manufacturable. If anything in the construction must change, return it for '
              'written approval first.')
    A('')
    A('HDI CONSTRUCTION')
    A('The drill data requires a symmetric two-step sequential buildup:')
    A('  Top -> L2       0.15 mm laser microvia')
    A('  L2 -> L3        0.15 mm laser microvia')
    A('  L3 -> L4        0.15 mm mechanically drilled buried via')
    A('  L4 -> L5        0.15 mm laser microvia')
    A('  L5 -> Bottom    0.15 mm laser microvia')
    A('  Top -> Bottom   0.20 mm plated through via')
    A('')
    L += wrap('Adjacent-layer laser microvias are stacked at common XY locations. Fill and planarize the receiving '
              'microvias and buried vias before the next buildup step. Confirm the complete lamination and '
              'fill/cap process in the CAM response.')
    A('')
    L += wrap('There is NO L2-L5 drill in this data. At %d XY sites an L2-L3 microvia, an L3-L4 buried via and an '
              'L4-L5 microvia coincide (%d of them also carry Top-L2 and L5-Bottom microvias, i.e. full '
              'Top-to-Bottom stacks). These are three separate drills (TX7, TX3, TX9) stacked on filled vias, '
              'exactly as drawn. Please keep them as separate drills; do not merge them into an L2-L5 drill.'
              % (F['stacked_L2_L5_sites'], F['stacked_L2_L5_full_top_bottom']))
    A('')
    A('VIA GEOMETRY AND DRILL COUNTS (PcbDoc and drill files agree)')
    A('All hole sizes in this note and in the drill files are FINISHED (plated) sizes.')
    A('Laser microvias: 0.15 mm hole / 0.30 mm land')
    A('L3-L4 buried vias: 0.15 mm hole / 0.27 mm land')
    A('Signal through vias: 0.20 mm hole / 0.35 mm land')
    A('')
    A('  Top -> Bottom signal through vias:   %d   (RoundHoles.TXT, T02)' % n['Top-Bottom'])
    A('  Top -> L2 microvias:                 %d   (RoundHoles.TX6)' % n['Top-L2-GND'])
    A('  L2 -> L3 microvias:                  %d   (RoundHoles.TX7)' % n['L2-GND-L3-SIG'])
    A('  L3 -> L4 buried vias:                %d   (RoundHoles.TX3)' % n['L3-SIG-L4-SIG'])
    A('  L4 -> L5 microvias:                  %d   (RoundHoles.TX9)' % n['L4-SIG-L5-VCC3V3'])
    A('  L5 -> Bottom microvias:              %d   (RoundHoles.TX10)' % n['L5-VCC3V3-Bottom'])
    A('  Total laser-microvia records:      %s' % format(uvia, ','))
    A('  Total via objects:                 %s' % format(F['via_total'], ','))
    A('  Physical blind/buried XY sites:      %d' % F['physical_hdi_sites'])
    A('')
    A('Plated component holes, all in RoundHoles.TXT (Top-Bottom):')
    for hole in sorted(holes):
        if abs(hole - 0.6) < 1e-3:
            continue
        ps = holes[hole]
        tot = sum(p['count'] for p in ps)
        what = ', '.join('%s (%d)' % (p['ref'], p['count']) for p in ps)
        if all(p['ref'] == 'X1' for p in ps):
            land = float(x1['MH1']['top'].split(' x ')[0])
            what = 'X1 MH1/MH2 (USB connector shell pegs, %.2f mm round lands)' % land
        A('  %-6s mm x%-3d %s' % (('%.3f' % hole).rstrip('0').rstrip('.'), tot, what))
    A('There are no non-plated holes.')
    A('')
    A('X1 MOLEX 105017-0001 PLATED SLOTS')
    L += wrap('X1-MS1 and X1-MS2 are two plated, vertical 0.60 mm x 1.30 mm full-radius front shell slots '
              '(mating-face end). Their centres are (%.4f, %.4f) mm and (%.4f, %.4f) mm (unchanged from Fab B Rev 2). '
              'The dedicated SlotHoles file uses a 0.60 mm tool over a 0.70 mm G85 centreline route to produce the '
              '1.30 mm overall length.' % (x1['MS1']['x'], x1['MS1']['y'], x1['MS2']['x'], x1['MS2']['y']))
    A('Do not convert these slots to round holes or treat them as non-plated.')
    A('Slot lands: 1.11 x 1.81 mm oblong on Top and Bottom (0.255 mm ring),')
    A('0.90 x 1.60 mm oblong on L2-L5.')
    A('')
    A('VIA-IN-PAD (VIPPO REQUIRED)')
    by_span = vs['by_span']
    L += wrap('NO THROUGH VIA SITS IN ANY SMD PAD. None of the %d Top-Bottom 0.20 mm through vias has its land '
              'overlapping an SMD pad on either side, and every drilled hole is at least %.3f mm outside every pad. '
              '%d through vias (%d pad contacts) have a land that ENDS ON the edge of a same-net SMD pad (gap within %.4f mm of zero '
              'in the design data, i.e. tangent; listed below and under VIA TENTING); they are the same vias and '
              'positions as on Fab B Rev 2, are not via-in-pad sites and are plugged with the other through vias. '
              'Only microvias are in pads. This board has %d via sites whose land overlaps an SMD pad '
              '(%d pad contacts; no via touches two pads). At %d sites the drilled hole is inside the pad or '
              'crosses its edge; at %d only the land touches the pad. By via type: %d L5-Bottom microvias, %d '
              'Top-L2 microvias, 0 through vias. Fab B Rev 2 had 68 such sites; the %d new pads are %s.'
              % (n['Top-Bottom'], min(e['hole_to_pad_gap'] for e in abut) if abut else 0.075,
                 len({(e['x'], e['y']) for e in abut}), len(abut),
                 max(abs(e['land_to_pad_gap']) for e in abut) if abut else 0, vs['via_sites'], vs['entries'], vs['hole_touches_pad'], vs['land_only'],
                 by_span.get('L5-VCC3V3-Bottom', 0), by_span.get('Top-L2-GND', 0), len(new_sites),
                 ', '.join('%s-%s' % rp for rp in new_sites)))
    A('Through-via lands tangent to a same-net SMD pad (not in the pad):')
    for e in sorted(abut, key=lambda e: (e['side'], e['pad'])):
        A('  %-6s %-7s %-8s via (%7.3f, %7.3f), hole %.3f mm outside the pad'
          % (e['side'], e['pad'], e['via_net'], e['x'], e['y'], e['hole_to_pad_gap']))
    multi = [c for c in F['via_in_pad_columns'] if len(c['spans_at_xy']) > 1]
    L += wrap('%d of these pad sites sit on a STACKED COLUMN: separate drills at one XY, exactly as drawn (the '
              '"Stack at XY" column below lists every drill at the site; %d of them are L2-L5 columns, %d full '
              'Top-to-Bottom stacks). Every microvia and buried via of these columns must be copper-filled and the '
              'in-pad microvia capped flat; do not replace a column with a through via.'
              % (len(multi), F['via_in_pad_columns_summary']['l2_l5_column_sites'],
                 F['via_in_pad_columns_summary']['full_top_bottom_sites']))
    L += wrap('Every one of the %d sites must be copper-filled and capped flat by plating (VIPPO / POFV), so the '
              'pads take paste normally and no solder wicks into a hole. Please confirm in the CAM response that '
              'all %d sites are filled and capped.' % (vs['via_sites'], vs['via_sites']))
    A('Stack key: T-2 Top-L2, 2-3 L2-L3, 3-4b L3-L4 buried, 4-5 L4-L5, 5-B L5-Bottom.')
    A('')
    A('  %-5s %-4s %-6s %-12s %-14s %-12s %-17s %s' % ('Ref', 'Pad', 'Side', 'Via', 'Net', 'Hole vs pad', 'Via centre (mm)', 'Stack at XY'))
    for e in sorted(vip, key=lambda e: (re.sub(r'\d+', '', e['ref']), int(re.sub(r'\D', '', e['ref']) or 0), e['pad'].zfill(3), e['via_x'])):
        rel = 'hole in pad' if e['hole_inside_pad'] else ('hole on edge' if e['hole_touches_pad'] else 'land only')
        spans = cols.get((e['ref'], e['pad'], round(e['via_x'], 3), round(e['via_y'], 3)), [e['span']])
        st = '+'.join(SPAN_SHORT[s] for s in sorted(spans, key=SPAN_ORDER.index))
        A('  %-5s %-4s %-6s %-12s %-14s %-12s (%7.3f, %7.3f) %s' % (e['ref'], e['pad'], e['layer'], VIA_NAME[e['span']],
                                                                  e['via_net'], rel, e['via_x'], e['via_y'], st))
    A('')
    A('VIA TENTING, RINGS AND SPACING')
    vias_reached = sorted({(round(e['x'], 3), round(e['y'], 3)) for s, e in reach})
    L += wrap('Every via that is not listed under VIA-IN-PAD is tented on both sides: no GTS/GBS opening is centred '
              'on a via and no mask opening reaches any via hole. However, the mask opening of a neighbouring '
              'same-net SMD pad overlaps or touches part of the land of %d through vias (%d via/opening contacts) '
              'and of %d microvias not in pads, so those lands are partly bare:'
              % (len(vias_reached), len(reach), len({(e['x'], e['y'], s) for s in ('Top', 'Bottom') for e in mv[s]})))
    A('Through vias:')
    for s, e in sorted(reach, key=lambda r: (r[1]['hole_margin'], r[0], r[1]['x'])):
        A('  %-6s via (%7.3f, %7.3f) %-15s opening %-7s hole margin %.3f mm, copper gap to it %.3f mm%s'
          % (s, e['x'], e['y'], e['via_net'], e['opening_pad'], e['hole_margin'], e['copper_gap'],
             '' if e['contact'] == 'overlap' else ' (%s)' % e['contact']))
    A('Microvias (not in a pad; "stacked" = an adjacent drill sits under it):')
    for s in ('Top', 'Bottom'):
        for e in mv[s]:
            A('  %-6s %-11s (%7.3f, %7.3f) %-9s opening %-7s hole margin %.3f mm, copper gap to it %.3f mm%s'
              % (s, VIA_NAME[e['span']], e['x'], e['y'], e['via_net'], e['opening_pad'], e['hole_margin'],
                 e['copper_gap'], ', stacked' if e['stacked'] else ''))
    L += wrap('PLEASE PLUG ALL %d THROUGH VIAS (resin- or copper-filled, IPC-4761 type VI or VII), so that mask '
              'registration cannot expose an open hole beside a pad, and state the method in the CAM response. '
              'PLEASE FILL AND CAP ALL %s MICROVIAS AND ALL %d BURIED VIAS. That includes the %d microvias that '
              'carry no stack (%d Top-L2, %d L5-Bottom, %d L2-L3, %d L4-L5; %d of them are not in a pad), which the '
              'stacking alone would not require to be filled.'
              % (n['Top-Bottom'], format(uvia, ','), n['L3-SIG-L4-SIG'],
                 uns['top_l2'] + uns['l5_bottom'] + uns['l2_l3'] + uns['l4_l5'], uns['top_l2'], uns['l5_bottom'],
                 uns['l2_l3'], uns['l4_l5'], uns['not_in_pads']))
    A('Annular rings as drawn: laser microvias 0.075 mm (0.15/0.30), L3-L4 buried')
    A('vias 0.06 mm (0.15/0.27), through vias 0.075 mm (0.20/0.35).')
    A('Minimum hole-to-hole spacing (DRC rule): 0.24 mm.')
    L += wrap('The L3-L4 buried via is a 0.15 mm mechanical drill through the 1.065 mm core, aspect ratio about '
              '7.1:1. Please confirm this is acceptable, as on the previous HDI Zulu A7 board.')
    vst = F['via_stacks']
    L += wrap('Stacks on buried vias: %d L2-L3 microvias sit directly on L3-L4 buried vias and %d buried vias carry '
              'an L4-L5 microvia, so the buried vias must be filled and capped before the L2/L5 lamination.'
              % (vst['l2_l3_on_l3_l4_buried'], vst['l3_l4_buried_with_l4_l5']))
    A('')
    A('BGA')
    L += wrap('U1 is an XC7A35T in CPG236 (0.5 mm pitch, 0.225 mm round lands) on the Top side. It is the '
              'finest-pitch feature on the board. The mask is as drawn in GTS; the minimum mask web (DRC '
              'mask-sliver rule) is 0.10 mm. Do not enlarge the mask openings at U1 without approval.')
    A('')
    A('CONTROLLED IMPEDANCE')
    A('USB_D_P / USB_D_N: 90 ohm differential, +/-10 percent, on the agreed stack')
    A("above, with PCBWay's etch compensation.")
    A('Layer/reference: L1 Top, referenced to L2 GND')
    L += wrap('Drawn geometry: 0.15 mm trace / 0.15 mm pair gap (measured on the board: both nets %s mm wide and '
              '%.2f / %.2f mm long, %.2f mm of parallel run at a 0.15 mm gap; the rest is the breakout at X1 and '
              'U2 and a small length-matching jog on USB_D_P; no vias on the pair; the parallel run is the overlap of '
              'facing segments at exactly 0.15 mm; the Fab B Rev 2 note gave 11.79 mm for the same, unchanged pair using '
              'a sum of whole segment lengths).'
              % ('/'.join('%.2f' % x for x in F['usb_widths']['Top']), usb['USB_D_P'], usb['USB_D_N'], coupled))
    L += wrap('This is the ONLY impedance-controlled structure. The SDRAM nets on L3/L4 are not impedance '
              'controlled; do not adjust them. If the target cannot be met by etch compensation alone, stop and '
              'request approval before changing the drawn geometry. Provide the final impedance calculation and, '
              'if included in the quotation, coupon results.')
    A('')
    A('PANEL (PROPOSAL)')
    sig = [l for l in cte if l not in ('L2-GND', 'L5-VCC3V3')]
    L += wrap('Proposed: 1 x 4 panel with 5 mm V-cut rails on the two short ends, as approved for the previous HDI '
              'Zulu A7 board (69.85 mm long). This %.2f mm board has not had a panel agreed: please confirm it or '
              'propose one for approval. Copper to the board edge, measured on the copper Gerbers: the L2 and L5 '
              'plane polygons %.3f mm from every edge; Top/L3/L4/Bottom copper %.3f mm from the long (north and '
              'south) edges, %.3f mm from the west short edge (JP3/JP4 lands) and %.3f mm from the east short edge '
              '(Bottom pads of R92, R93, R99). In a 1 x 4 array the long edges are V-cut or routed too, so please '
              'confirm the V-cut keep-out, or propose a routed/tab panel, before CAM.'
              % (w, min(min(cte[l].values()) for l in ('L2-GND', 'L5-VCC3V3')),
                 min(min(cte[l]['north'], cte[l]['south']) for l in sig), min(cte[l]['west'] for l in sig),
                 min(cte[l]['east'] for l in sig)))
    A('')
    A('ENGINEERING QUESTIONS (PLEASE ANSWER IN THE EQ)')
    for i, q in enumerate([
        'Component spacing below the 0.254 mm design target, all 0201 22 ohm resistors next to the TSOP-II-54 '
        'SDRAM U3 and the FPGA U1: (a) the south resistors R119-R126 sit 0.195-0.25 mm from U3\'s leads and '
        'overlap its IPC-7351B nominal courtyard by about 0.19 mm; (b) R129 and R130 (Top) are 0.26 mm pad to '
        'pad, mask web 0.16 mm, nominal courtyards overlapping by 0.04-0.07 mm; (c) R131 and R132 (Top) are '
        '0.2035 mm pad to pad, mask web 0.1035 mm, nominal courtyards overlapping by 0.127 mm, and R132\'s '
        'courtyard overlaps U2\'s by about 0.05 mm. Can these be built and placed as drawn?',
        'Solder-mask cover over different-net copper: measured on GTS/GBS, the smallest mask cover between a '
        'track and another net\'s pad opening is %.3f mm, and %d track/opening pairs have under 0.044 mm (the '
        'tightest are listed below). Among them, new in this revision and SI-critical: a 0.0762 mm SDRAM-D13 Top trace '
        'under U2\'s body corner, %.3f mm from U2-48\'s opening (U2-48 has no net). Does your mask registration hold '
        'these, or may openings be reduced or corner-clipped there? Please do not change them without approval.'
        % (mc['min'], mc['under_0p044'], min(c['cover'] for c in mc['u2_48']) if mc['u2_48'] else float('nan')),
        'Projected hole overlaps: at %d places, vias of two different nets that share no copper layer overlap '
        'in plan view (%d of them exactly coaxial). Each pair is listed below by the two drills that overlap, '
        'net span (x, y) / net span (x, y), hole overlap; the other drills of each column sit at the same XY. '
        'Please confirm the sequential build accepts these as drawn.' % (len(proj), sum(1 for e in proj if e['centre_distance'] == 0)),
        'Confirm the panel (see PANEL) and the via plugging method (see VIA TENTING).']):
        first = wrap('%d. %s' % (i + 1, q), 73)
        L += [first[0]] + ['   ' + x for x in first[1:]]
        if q.startswith('Solder-mask cover'):
            for c in mc['worst']:
                A('     %-6s %-14s track vs %-7s (%s) opening: %.3f mm' % (c['side'], c['track_net'], c['opening_pad'],
                                                                         c['opening_net'] or 'no net', c['cover']))
        if q.startswith('Projected hole overlaps'):
            for e in proj:
                A('     %s %s (%.3f, %.3f) / %s %s (%.3f, %.3f), %.3f mm'
                  % (e['a_net'], SPAN_SHORT[e['a_span']], e['a_xy'][0], e['a_xy'][1],
                     e['b_net'], SPAN_SHORT[e['b_span']], e['b_xy'][0], e['b_xy'][1], e['hole_overlap']))
    A('')
    A('FILE MAP')
    for ext, what in [('GTL', 'L1 Top copper'), ('G1', 'L2 GND'), ('G2', 'L3 signal'), ('G3', 'L4 signal'),
                      ('G4', 'L5 VCC3V3'), ('GBL', 'L6 Bottom copper'), ('GTS', 'Top solder mask'),
                      ('GBS', 'Bottom solder mask'), ('GTO', 'Top silkscreen'), ('GBO', 'Bottom silkscreen'),
                      ('GTP', 'Top paste'), ('GBP', 'Bottom paste'), ('GM', 'Board profile')]:
        A('  %-34s %s' % ('%s.%s' % (BASE, ext), what))
    for f, what in [('-RoundHoles.TXT', 'Top-Bottom plated round holes'), ('-SlotHoles.TXT', 'Top-Bottom plated X1 slots'),
                    ('-RoundHoles.TX3', 'L3-L4 buried vias'), ('-RoundHoles.TX6', 'Top-L2 microvias'),
                    ('-RoundHoles.TX7', 'L2-L3 microvias'), ('-RoundHoles.TX9', 'L4-L5 microvias'),
                    ('-RoundHoles.TX10', 'L5-Bottom microvias'), ('.LDP', 'Drill-pair layer map'),
                    ('.DRR', 'Drill sizes and counts')]:
        A('  %-34s %s' % (BASE + f, what))
    A('')
    A('FINAL VERIFICATION')
    A('Altium DRC %s (after the final via moves, repour and ratsnest rebuild): %s warnings,' % (drc_when, drc_w.group(1) if drc_w else '0'))
    A('%s rule violations.' % drc_v)
    A('The board was saved at %s (MD5 %s) with no further edit.' % (pcb_t, md5[:8]))
    A('Gerbers (exported %s): metric RS-274X, 0.0001 mm coordinate resolution' % gerb_t)
    A('NC Drill (exported %s): metric Excellon 4:4, separate round/slot files,' % drill_t)
    A('G85 plated slots')
    A('Every drill hit was matched one-to-one against the PcbDoc via and pad')
    A('positions (0 missing, 0 extra in every drill file).')
    A('')
    A('This ZIP intentionally contains fabrication data only. Assembly BOM, CPL,')
    A('drawings and assembly instructions are supplied separately if assembly is')
    A('quoted.')
    text = '\n'.join(L) + '\n'
    text.encode('ascii')
    os.makedirs(os.path.dirname(NOTE), exist_ok=True)
    open(NOTE, 'w', encoding='ascii', newline='\n').write(text)
    print('wrote', NOTE, len(L), 'lines')


if __name__ == '__main__':
    main()
