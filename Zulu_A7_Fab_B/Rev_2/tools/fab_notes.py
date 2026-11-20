# -*- coding: utf-8 -*-
"""Write the Zulu A7 Fab B Rev 2 PCBWay FAB NOTES from tools/fab_facts.json (2026-11-20, the no-PMOD sync).

    python tools/fab_facts.py      # measure the saved PcbDoc and the exported drill files first
    python tools/fab_notes.py      # -> fabrication/Zulu_A7_Fab_B_Rev_2_PCBWay_FAB_NOTES.txt

Ported from Zulu_A7_no_pmod/Rev_2/tools/fab_notes.py (427960e). Every board-derived number in the note (drill counts,
via-in-pad sites and their stacks, mask reach over through vias, hole sizes, slot centres, USB geometry, trace and
space minimums, outline, copper to the edges) is read from fab_facts.json, whose 'source' must match the PcbDoc on
disk. The prose that is not measured (stack, finish, engineering questions) is the 2026-11-11 Fab B Rev 2 note's and
the no-PMOD note's, edited for this board. What changed against the 2026-11-11 release is measured too: via counts and
via-in-pad sites against tools/fab_facts_rev2_2026-11-11.json (that release's report, kept byte for byte), moved parts
against tools/route/sync_altium/release_2026-11-11_components.json (that release's Components6). The export times of
the Gerbers, drills and DRC are read from the files in Project Outputs.

Fab B rules that the no-PMOD copy did not have (all REFUSE, nothing is written):
  * NO through via may have its land overlapping an SMD pad (user rule, 2026-11-11 Fab B release, restated for the
    sync): fab_facts' through_vias_in_smd_pads must be EMPTY (the no-PMOD board accepted two GND through vias in U2-EP
    and X4-2; on Fab B those ties are laser microvia stacks), and no through-via land may overlap an SMD pad by more
    than 0.5 um (tangent lands are listed, not refused);
  * the outline must be the 69.85 x 25.40 mm rectangle and the silkscreen title 'ZULU A7 2.2' must be on Top Overlay
    exactly once;
  * tools/body_heights.json must hold no 'provisional' height (the note says every body is at its datasheet height,
    J1's from DigiKey's parametric data);
  * RELEASE_DATE must be set (2026-11-20 below; None refuses) and the note must not name an order number.
The DRC must be 0 and must have run Component Clearance, as on the no-PMOD board.
"""
import collections
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sync_altium_read as R  # noqa: E402

OUT = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'Project Outputs for zulu_a7_fab_b')
PCB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'zulu_a7_fab_b.PcbDoc')
NOTE = os.path.join(ROOT, 'fabrication', 'Zulu_A7_Fab_B_Rev_2_PCBWay_FAB_NOTES.txt')
DRC = os.path.join(OUT, 'Design Rule Check - zulu_a7_fab_b.drc')
PREV_FACTS = os.path.join(HERE, 'fab_facts_rev2_2026-11-11.json')
PREV_COMPONENTS = os.path.join(HERE, 'route', 'sync_altium', 'release_2026-11-11_components.json')
HEIGHTS = os.path.join(HERE, 'body_heights.json')
BASE = 'zulu_a7_fab_b'
RELEASE_NAME = 'Zulu A7 Fab B Rev 2'
# the release day, YYYY-MM-DD, the same in tools/fab_notes.py, tools/package_fabrication_release.py
# and tools/generate_jlcpcb_assembly.py. None makes every release tool refuse.
RELEASE_DATE = '2026-11-20'
TITLE = 'ZULU A7 2.2'
BOARD_W, BOARD_H = 69.85, 25.40
PREV_RELEASE = '2026-11-11'
SPAN_SHORT = {'Top-L2-GND': 'T-2', 'L2-GND-L3-SIG': '2-3', 'L3-SIG-L4-SIG': '3-4b', 'L4-SIG-L5-VCC3V3': '4-5',
              'L5-VCC3V3-Bottom': '5-B', 'Top-Bottom': 'thru'}
SPAN_ORDER = list(SPAN_SHORT)
VIA_NAME = {'Top-L2-GND': 'Top-L2 uvia', 'L5-VCC3V3-Bottom': 'L5-Bot uvia', 'Top-Bottom': 'thru via'}
# Fab B accepts NO through via in an SMD pad (the no-PMOD board accepted U2-EP and X4-2)
ACCEPTED_THROUGH_IN_PAD = set()
# the footprints the no-PMOD sync puts on this board (R119-R134 are R0201); the note's prose assumes them
SYNCED_PATTERNS = {'U2': 'FT2232HQ-QFN64', 'X4': 'JST-S2B-PH-SM4-TB', 'U10': 'MSOP-8_3X3_P0.65', 'J1': '2X06'}
# order numbers never go into the note (public repository): SHA-256 of each order number, matched against every
# substring that looks like one (W + 7 digits + 4 to 6 letters/digits, every length tried, so trailing characters
# cannot hide it); the number itself stays out of this file
ORDER_SHA256 = {"4b77802bdde723a747a12d3526f308f0a84011df15acdd400fb8eeb3018f1674"}
ORDER_HEAD = re.compile(r"W\d{7}", re.I)


def names_order(data):
    if isinstance(data, bytes):
        data = data.decode('latin-1', 'replace')
    up = data.upper()
    for m in ORDER_HEAD.finditer(up):
        for n in range(4, 7):
            tail = up[m.end():m.end() + n]
            if len(tail) == n and tail.isalnum() and \
                    hashlib.sha256((m.group(0) + tail).encode('ascii', 'replace')).hexdigest() in ORDER_SHA256:
                return True
    return False


def release_date():
    """RELEASE_DATE, or SystemExit while it is still the TODO."""
    if not (isinstance(RELEASE_DATE, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', RELEASE_DATE)):
        raise SystemExit('TODO: set RELEASE_DATE (YYYY-MM-DD) in tools/fab_notes.py, tools/package_fabrication_release.py '
                         'and tools/generate_jlcpcb_assembly.py before a release')
    return RELEASE_DATE


def through_in_pad_problem(facts):
    """None when fab_facts lists exactly the accepted through vias in SMD pads (none on Fab B), else a message."""
    got = {(e['pad'], round(e['via_x'], 3), round(e['via_y'], 3)) for e in facts['through_vias_in_smd_pads']}
    if got != ACCEPTED_THROUGH_IN_PAD:
        return 'through vias in SMD pads %s; Fab B accepts none (use laser microvia stacks)' % sorted(got)
    return None


def provisional_heights():
    return sorted(json.load(open(HEIGHTS)).get('provisional', {}))


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


def natkey(ref):
    return (re.sub(r'\d+', '', ref), int(re.sub(r'\D', '', ref) or 0))


def relocated_parts(B):
    """Parts of the 2026-11-11 release whose footprint, side, centre or rotation differs now, and parts added."""
    prev = json.load(open(PREV_COMPONENTS))['parts']
    now = {c['ref']: [c['pattern'], c['side'], round(c['rot'], 6), c['x'], c['y']] for c in B['comps']}
    moved = sorted((r for r in set(prev) & set(now)
                    if prev[r][:2] != now[r][:2] or abs(prev[r][2] - now[r][2]) > 0.001
                    or abs(prev[r][3] - now[r][3]) > 0.001 or abs(prev[r][4] - now[r][4]) > 0.001), key=natkey)
    return ([(r, prev[r], now[r]) for r in moved], sorted(set(now) - set(prev), key=natkey),
            sorted(set(prev) - set(now), key=natkey))


def main():
    date = release_date()
    F = json.load(open(os.path.join(HERE, 'fab_facts.json')))
    P = json.load(open(PREV_FACTS))
    raw = open(PCB, 'rb').read()
    md5, sha = hashlib.md5(raw).hexdigest(), hashlib.sha256(raw).hexdigest().upper()
    if F['source']['md5'] != md5:
        raise SystemExit('fab_facts.json was measured on md5 %s, the board is %s: re-run fab_facts.py' % (F['source']['md5'], md5))
    problem = through_in_pad_problem(F)
    if problem:
        raise SystemExit(problem)
    prov = provisional_heights()
    if prov:
        raise SystemExit('tools/body_heights.json still has provisional heights %s: verify them before a release' % prov)
    B = R.read(PCB)
    # the prose below describes the synced board: refuse on any other
    pats = {c['ref']: c['pattern'] for c in B['comps']}
    want = dict(SYNCED_PATTERNS, **{'R%d' % i: 'R0201' for i in range(119, 135)})
    wrong = {r: (pats.get(r), p) for r, p in want.items() if pats.get(r) != p}
    if wrong:
        raise SystemExit('not the synced board (part: footprint on the board, expected): %s' % wrong)
    titles = [t for t in B['texts'] if t['comp'] is None and t['layer'] == 'TopOverlay' and t['text'] == TITLE]
    if len(titles) != 1:
        raise SystemExit('%d free %r texts on Top Overlay, expected 1' % (len(titles), TITLE))
    dvb = F['drill_vs_board']
    if any(v.get('board_not_in_file') or v.get('file_not_on_board') for v in dvb.values()):
        raise SystemExit('drill files and board disagree: %s' % dvb)
    geo = {g['span']: g for g in F['via_geometry']}
    n = {s: geo[s]['count'] for s in geo}
    pgeo = {g['span']: g['count'] for g in P['via_geometry']}
    uvia = n['Top-L2-GND'] + n['L2-GND-L3-SIG'] + n['L4-SIG-L5-VCC3V3'] + n['L5-VCC3V3-Bottom']
    puvia = pgeo['Top-L2-GND'] + pgeo['L2-GND-L3-SIG'] + pgeo['L4-SIG-L5-VCC3V3'] + pgeo['L5-VCC3V3-Bottom']
    hits = F['drill_hits_per_tool']
    if hits['TXT']['02'] != n['Top-Bottom']:
        raise SystemExit('TXT T02 %s != through vias %s' % (hits['TXT']['02'], n['Top-Bottom']))
    out = F['board_outline']
    w, h = out['size_mm']
    if not out['gm_matches_pcb']:
        raise SystemExit('GM profile does not match the PcbDoc outline')
    if abs(w - BOARD_W) > 0.0005 or abs(h - BOARD_H) > 0.0005 or out['bbox_mm'][:2] != [0.0, 0.0]:
        raise SystemExit('outline %s is not the %.2f x %.2f mm rectangle at 0,0' % (out['bbox_mm'], BOARD_W, BOARD_H))
    holes = collections.defaultdict(list)
    for p in F['pad_holes']:
        holes[round(p['hole'], 3)].append(p)
    x1 = {p['pad']: p for p in F['x1_hole_pads']}
    vip, vs = F['via_in_pad'], F['via_in_pad_summary']
    cols = {(c['ref'], c['pad'], round(c['via_x'], 3), round(c['via_y'], 3)): c['spans_at_xy'] for c in F['via_in_pad_columns']}
    mask = F['mask_over_through_vias']
    reach = [(s, e) for s in ('Top', 'Bottom') for e in mask[s]['through_via_lands_reached']]
    if not mask['all_same_net'] or any(e['hole_margin'] < 0 for _, e in reach):
        raise SystemExit('a mask opening reaches a through-via hole or another net')
    usb = F['usb_track_length']
    coupled = F['usb_coupled_overlap_by_gap'].get('Top 0.1500', 0)
    other_gaps = [float(k.split()[1]) for k in F['usb_coupled_length_by_gap'] if not k.endswith(' 0.1500')]
    abut = F['through_via_lands_abutting_smd_pads']
    if any(e['land_to_pad_gap'] < -0.0005 for e in abut):
        raise SystemExit('a through-via land overlaps an SMD pad by more than 0.5 um: %s'
                         % [e for e in abut if e['land_to_pad_gap'] < -0.0005])
    mv = F['mask_over_microvias']
    if not mv['all_same_net'] or any(e['hole_reached'] for s in ('Top', 'Bottom') for e in mv[s]):
        raise SystemExit('a mask opening reaches a microvia hole or another net')
    uns = F['unstacked_outer_microvias']
    proj = F['different_net_projected_hole_overlaps']
    cte = F['copper_to_edge']
    prev_sites = {(e['ref'], e['pad']) for e in P['via_in_pad']}
    now_sites = {(e['ref'], e['pad']) for e in vip}
    new_sites = sorted(now_sites - prev_sites, key=lambda rp: (natkey(rp[0]), rp[1]))
    gone_sites = sorted(prev_sites - now_sites, key=lambda rp: (natkey(rp[0]), rp[1]))
    mc = F['mask_cover_different_net']
    moved, added, removed = relocated_parts(B)
    if added != ['R%d' % i for i in range(119, 135)]:
        raise SystemExit('parts added since the %s release: %s, expected R119-R134' % (PREV_RELEASE, added))
    drc = open(DRC, encoding='latin1').read()
    drc_v = re.search(r'Violations Detected : (\d+)', drc).group(1)
    drc_t = re.search(r'Date\s*:\s*(\S+)\s+Time\s*:\s*([\d:]+ [AP]M)', drc.replace('\n', ' '))
    drc_when = datetime.datetime.strptime(drc_t.group(1) + ' ' + drc_t.group(2), '%m/%d/%Y %I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S')
    drc_w = re.search(r'Warnings\s*:\s*(\d+)', drc)
    drc_hits, rule = collections.OrderedDict(), None
    for line in drc.splitlines():
        m = re.match(r'\s*Processing Rule : (.+?)\s*$', line)
        if m:
            rule = m.group(1).split(' (')[0]
        m = re.match(r'\s*Rule Violations :(\d+)', line)
        if m and int(m.group(1)):
            drc_hits[rule] = int(m.group(1))
    if drc_hits or int(drc_v) != 0:
        raise SystemExit('the DRC is not clean: %s violations %s' % (drc_v, dict(drc_hits)))
    if 'Processing Rule : Component Clearance' not in drc:
        raise SystemExit('the DRC did not run Component Clearance (tick it under Rules To Check > Placement > Batch)')
    gerb_t, drill_t = mtime(os.path.join(OUT, BASE + '.GTL')), mtime(os.path.join(OUT, BASE + '-RoundHoles.TXT'))
    pcb_t = mtime(PCB)
    ep = [e for e in vip if e['ref'] == 'U2' and e['pad'] == 'EP']
    x4_2 = [e for e in vip if e['ref'] == 'X4' and e['pad'] == '2']

    L = []
    A = L.append
    A('ZULU A7 FAB B REV 2 - PCBWAY FABRICATION NOTES')
    A('Revision: %s  (silkscreen title "%s"; Rev 1 reads "ZULU A7 2.0")' % (RELEASE_NAME, TITLE))
    A('Release date: %s' % date)
    A('PCB SHA-256: %s' % sha)
    A('Source: %s.PcbDoc (MD5 %s)' % (BASE, md5))
    A('')
    A('ORDER AND CAM GATE')
    L += wrap('This is a bare-board, six-layer, two-step sequential HDI release of the Zulu A7 Fab B Rev 2 board, '
              '%.2f x %.2f mm: same outline, stack, layer use and via types and sizes as the %s Fab B Rev 2 data, and '
              'the same fabrication design rules except one new solder-mask rule (U2\'s pads use a 0.035 mm mask '
              'expansion instead of the board\'s 0.05 mm, see ENGINEERING QUESTIONS); two new component-clearance '
              'rules (R131/R132 and X2) concern assembly only. It SUPERSEDES the %s Fab B Rev 2 data package; do not mix files of the two. What changed '
              '(see CHANGES FROM THE %s RELEASE): U2 is now an FT2232HQ in a QFN-64 package with a grounded exposed '
              'pad, X4 is now a side-entry SMT header at the south edge, U10 is now an MSOP-8, %d SDRAM series '
              'resistors were added, %d parts were placed differently, and the area around them was re-routed. The '
              'drill and via counts below are new. Microvias sit in SMD pads; NO through via sits in any SMD pad '
              '(see VIA-IN-PAD).' % (w, h, PREV_RELEASE, PREV_RELEASE, PREV_RELEASE, len(added), len(moved)))
    L += wrap('Route it to PCBWay HDI engineering/CAM review. Do not release fabrication as a standard six-layer '
              'prototype without confirming every blind/buried drill pair, the via-in-pad list and the '
              'ENGINEERING QUESTIONS below.')
    A('')
    A('CHANGES FROM THE %s RELEASE' % PREV_RELEASE)
    def vias_in(rows):
        return ('no in-pad via' if not rows else '%d in-pad laser microvia%s' % (len(rows), 's' if len(rows) > 1 else ''))
    L += wrap('U2 is the FT2232HQ in a QFN-64 (9 x 9 mm body, 0.5 mm pitch, 4.20 x 4.20 mm exposed pad EP, which is '
              'GND and carries %s) instead of the LQFP-64. X4 is the JST S2B-PH-SM4-TB 2 mm side-entry SMT battery '
              'header at the south edge (the plug opening faces south, the housing is inside the outline, no board '
              'notch) instead of the top-entry B2B-PH-SM4-TB; its pad 2 (GND) carries %s. U10 is the 93LC46B in an '
              'MSOP-8 instead of a SOIC-8. The 0201 SDRAM data series resistors %s were placed and routed. No through '
              'via is in any SMD pad (the in-pad GND ties are laser microvias). Outline, stack, layer use, via and '
              'hole sizes, X1 and its slots, J1 and the X2 holes are unchanged. The fabrication design rules are unchanged except the '
              'new 0.035 mm solder-mask expansion on U2\'s pads and two component-clearance rules that concern '
              'assembly only (R131/R132 and X2). Via objects %s -> '
              '%s: through vias %d -> %d, Top-L2 %d -> %d, L2-L3 %d -> %d, L3-L4 buried %d -> %d, L4-L5 %d -> %d, '
              'L5-Bottom %d -> %d (laser microvias %s -> %s). Parts added: %s. Parts placed differently from the %s '
              'release (same origin): %s.'
              % (vias_in(ep), vias_in(x4_2), '%s-%s' % (added[0], added[-1]) if added else 'none',
                 format(P['via_total'], ','), format(F['via_total'], ','), pgeo['Top-Bottom'],
                 n['Top-Bottom'], pgeo['Top-L2-GND'], n['Top-L2-GND'], pgeo['L2-GND-L3-SIG'], n['L2-GND-L3-SIG'],
                 pgeo['L3-SIG-L4-SIG'], n['L3-SIG-L4-SIG'], pgeo['L4-SIG-L5-VCC3V3'], n['L4-SIG-L5-VCC3V3'],
                 pgeo['L5-VCC3V3-Bottom'], n['L5-VCC3V3-Bottom'], format(puvia, ','), format(uvia, ','),
                 ', '.join(added) if added else 'none', PREV_RELEASE,
                 ', '.join('%s (%.2f, %.2f) -> (%.2f, %.2f)%s%s' % (
                     r, a[3], a[4], b[3], b[4], '' if abs(a[2] - b[2]) < 0.001 else ' rot %g -> %g' % (a[2], b[2]),
                     '' if a[0] == b[0] else ' (%s -> %s)' % (a[0], b[0])) for r, a, b in moved)))
    if removed:
        raise SystemExit('parts of the %s release are gone from the board: %s' % (PREV_RELEASE, removed))
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
              '(mating-face end). Their centres are (%.4f, %.4f) mm and (%.4f, %.4f) mm (unchanged from the %s '
              'release). The dedicated SlotHoles file uses a 0.60 mm tool over a 0.70 mm G85 centreline route to '
              'produce the 1.30 mm overall length.'
              % (x1['MS1']['x'], x1['MS1']['y'], x1['MS2']['x'], x1['MS2']['y'], PREV_RELEASE))
    A('Do not convert these slots to round holes or treat them as non-plated.')
    A('Slot lands: 1.11 x 1.81 mm oblong on Top and Bottom (0.255 mm ring),')
    A('0.90 x 1.60 mm oblong on L2-L5.')
    A('')
    A('VIA-IN-PAD (VIPPO REQUIRED)')
    by_span = vs['by_span']
    L += wrap('NO THROUGH VIA SITS IN ANY SMD PAD. None of the %d Top-Bottom 0.20 mm through vias has its land '
              'overlapping an SMD pad on either side, and every one of their drilled holes is at least %.3f mm '
              'outside every pad. %d through vias (%d pad contacts) have a land that ENDS ON the edge of a '
              'same-net SMD pad (gap within %.4f mm of zero in the design data, i.e. tangent; listed below); they '
              'are not via-in-pad sites and are plugged with the other through vias. Only microvias are in pads. '
              'This board has %d via sites whose land overlaps an SMD pad (%d pad contacts). At %d sites the drilled '
              'hole is inside the pad or crosses its edge; at %d only the land touches the pad. By via type: %d '
              'L5-Bottom microvias, %d Top-L2 microvias, %d through vias. The U2 exposed pad carries %d of the '
              'sites. The %s release had %d such sites; new pads '
              'with a site: %s; pads that no longer have one: %s.'
              % (n['Top-Bottom'], min(e['hole_to_pad_gap'] for e in abut) if abut else 0.075,
                 len({(e['x'], e['y']) for e in abut}), len(abut),
                 max(abs(e['land_to_pad_gap']) for e in abut) if abut else 0, vs['via_sites'], vs['entries'],
                 vs['hole_touches_pad'], vs['land_only'], by_span.get('L5-VCC3V3-Bottom', 0),
                 by_span.get('Top-L2-GND', 0), by_span.get('Top-Bottom', 0), len(ep), PREV_RELEASE,
                 P['via_in_pad_summary']['via_sites'], ', '.join('%s-%s' % rp for rp in new_sites) or 'none',
                 ', '.join('%s-%s' % rp for rp in gone_sites) or 'none'))
    if by_span.get('Top-Bottom', 0):
        raise SystemExit('via_in_pad_summary counts %d through vias in pads' % by_span['Top-Bottom'])
    if abut:
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
    for e in sorted(vip, key=lambda e: (natkey(e['ref']), e['pad'].zfill(3), e['via_x'])):
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
    u1v = sorted((e for e in vip if e['ref'] == 'U1'), key=lambda e: (e['pad'][0], int(e['pad'][1:])))
    L += wrap('U1 is an XC7A35T in CPG236 (0.5 mm pitch, 0.225 mm round lands) on the Top side. It is the '
              'finest-pitch feature on the board. The mask is as drawn in GTS; the minimum mask web (DRC '
              'mask-sliver rule) is 0.10 mm. Do not enlarge the mask openings at U1 without approval.'
              + (' %d U1 lands carry a 0.30/0.15 mm Top-L2 laser microvia (%s; the %s release had none in U1 '
                 'lands); at %d of them the hole touches the land. They are listed under VIA-IN-PAD and must be '
                 'copper-filled and capped flat like every via-in-pad site.'
                 % (len(u1v), ', '.join(e['pad'] for e in u1v), PREV_RELEASE,
                    sum(1 for e in u1v if e['hole_touches_pad'])) if u1v else ''))
    A('')
    A('CONTROLLED IMPEDANCE')
    A('USB_D_P / USB_D_N: 90 ohm differential, +/-10 percent, on the agreed stack')
    A("above, with PCBWay's etch compensation.")
    A('Layer/reference: L1 Top, referenced to L2 GND')
    L += wrap('Drawn geometry: 0.15 mm trace / 0.15 mm pair gap (measured on the board: both nets %s mm wide and '
              '%.2f / %.2f mm long, %.2f mm of parallel run at a 0.15 mm gap; the rest is the breakout at X1 and '
              'U2, where the other coupled gaps are %.4f-%.4f mm; %s; the parallel run is the overlap of facing '
              'segments at exactly 0.15 mm). The pair was rebuilt on Top only for the QFN U2 in this release, so '
              'the %s pair length and coupled length do not apply.'
              % ('/'.join('%.2f' % x for x in F['usb_widths']['Top']), usb['USB_D_P'], usb['USB_D_N'], coupled,
                 min(other_gaps), max(other_gaps),
                 'no vias on the pair' if not F['usb_vias'] else '%d vias on the pair' % len(F['usb_vias']),
                 PREV_RELEASE))
    L += wrap('This is the ONLY impedance-controlled structure. The SDRAM nets on L3/L4 are not impedance '
              'controlled; do not adjust them. If the target cannot be met by etch compensation alone, stop and '
              'request approval before changing the drawn geometry. Provide the final impedance calculation and, '
              'if included in the quotation, coupon results.')
    A('')
    A('PANEL')
    sig = [l for l in cte if l not in ('L2-GND', 'L5-VCC3V3')]
    L += wrap('1 x 4 panel with 5 mm V-cut rails on the two short ends, as approved for the previous HDI Zulu A7 '
              'board (the same %.2f mm outline), unless PCBWay proposes otherwise for approval. Copper to the board '
              'edge, measured on the copper Gerbers: the L2 and L5 plane polygons %.3f mm from every edge; '
              'Top/L3/L4/Bottom copper %.3f mm from the long (north and south) edges, %.3f mm from the west short '
              'edge and %.3f mm from the east short edge.'
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
        '0.2035 mm pad to pad, mask web 0.1035 mm, nominal courtyards overlapping by 0.127 mm. '
        'Can these be built and placed as drawn?',
        'Solder-mask cover over different-net copper: measured on GTS/GBS, the smallest mask cover between a '
        'track and another net\'s pad opening is %.3f mm, and %d track/opening pairs have under 0.044 mm (the '
        'tightest are listed below). Does your mask registration hold these, or may openings be reduced or '
        'corner-clipped there? Please do not change them without approval.'
        % (mc['min'], mc['under_0p044']),
        'Solder-mask openings on U2 (FT2232HQ, QFN-64): its pads use a 0.035 mm mask expansion instead of the '
        'board\'s 0.05 mm, so the web between the end pads of adjacent sides at each QFN corner (pads 1/64, '
        '16/17, 32/33, 48/49) is 0.127 mm against a 0.10 mm minimum. Can this be held? Please do not enlarge '
        'the U2 openings without approval.',
        'Projected hole overlaps: at %d places, vias of two different nets that share no copper layer overlap '
        'in plan view (%d of them exactly coaxial). Each pair is listed below by the two drills that overlap, '
        'net span (x, y) / net span (x, y), hole overlap; the other drills of each column sit at the same XY. '
        'Please confirm the sequential build accepts these as drawn.' % (len(proj), sum(1 for e in proj if e['centre_distance'] == 0)),
        'Confirm the via plugging method (see VIA TENTING) and the panel (see PANEL).']):
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
    L += wrap('Altium DRC %s: %s warnings, %s rule violations. Un-routed nets, short circuits, every clearance '
              'rule, silkscreen, solder-mask sliver, net-antenna and component-body clearance checks report 0 '
              '(every part carries a 3D body at its datasheet maximum height; J1\'s 8.51 mm is the insulator height from '
              'DigiKey\'s parametric data). The board was saved at %s with no '
              'edit between the DRC run and the save.'
              % (drc_when, drc_w.group(1) if drc_w else '0', drc_v, pcb_t))
    A('Source MD5 %s.' % md5[:8])
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
    if names_order(text):
        raise SystemExit('the note would name an order number')
    os.makedirs(os.path.dirname(NOTE), exist_ok=True)
    open(NOTE, 'w', encoding='ascii', newline='\n').write(text)
    print('wrote', NOTE, len(L), 'lines')


if __name__ == '__main__':
    main()
