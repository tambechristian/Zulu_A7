"""Plan the pin-1 / LED-cathode silkscreen dots of Asar Feather Rev 1 (2026-11-20).

Copy of Zulu_A7_no_pmod/Rev_2/tools/route/pin1_dots/plan_marks.py (see Zulu_A7_no_pmod/Rev_2/docs/pin1_silk_dots.md for
the rules) with a per-project CONFIG: the board, the release Gerbers from before the dots (read out of git history),
the parts that get no dot, and the part reader. Part bodies come from tools/body_check.py with each part's side,
rotation and pattern read from the board; the outline is the GM profile, filled, so the edge check follows any shape.

    python tools/route/pin1_dots/plan_marks.py [--images DIR]
writes marks.json beside this script; tools/pin1_dots_emit.py turns it into the Altium script.

Asar additions (2026-11-20): the silk check also keeps clear of each text's box (tools/board_pictures.py read_texts),
as Altium's Silk to Silk rule measures to the box, not the strokes; RESET is marked with BTN (same PTS810 part).
"""

import json
import re
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

CONFIG = {'reader': 'generate_pcbway_assembly', 'pcb': 'Asar_feather.PrjPcb/asar_feather.PcbDoc', 'git': ('257867d', 'Asar_feather/Rev_1/fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-20_PROVISIONAL.zip'), 'gbr': 'asar_feather', 'keyed': ['X1', 'X2', 'X3'], 'skip': {'U10': 'keeps its pin-1 tick west of pad 1 (2026-11-16), as U10 does on the Zulu boards'}}

HERE = os.path.dirname(os.path.abspath(__file__))
REV = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
REPO = os.path.abspath(os.path.join(REV, '..', '..'))
IMAGES = sys.argv[sys.argv.index('--images') + 1] if '--images' in sys.argv else None
import io, subprocess, tempfile, zipfile  # noqa: E402
_TMP = tempfile.mkdtemp(prefix='pin1_gbr_')
# the release Gerbers from before the dots, out of git history (the release ZIP of the same date is replaced)
_zip = subprocess.run(['git', 'show', '%s:%s' % CONFIG['git']], cwd=REPO, capture_output=True, check=True).stdout
zipfile.ZipFile(io.BytesIO(_zip)).extractall(_TMP)
GBR = os.path.join(_TMP, CONFIG['gbr'])
sys.argv = ['x']
sys.path.insert(0, REV + '/tools')
G = __import__(CONFIG['reader'])
import body_check as B  # noqa: E402

G.PCB = os.path.join(REV, CONFIG['pcb'])
DOT_R = 0.20            # Ø0.40 mm dot = arc radius 0.10, line width 0.20
SILK_MASK = 0.254       # board rule Silk To Solder Mask (IsPad),(All); applied to every opening
SILK_SILK = 0.254       # board rule Silk to Silk
BODY_GAP = 0.05
MASK_EXP = 0.05        # largest solder-mask expansion on the board (rule default; U2 has 0.035)
EDGE = 0.30
PPMM = 40               # raster resolution

comps, pads = G.read_board()
# silk texts as Altium's Silk to Silk rule measures them: to the text's box, not its strokes. The Gerber raster below
# sees only the strokes, which let the first X4 and X5 dots sit 0.22 mm from the "U2" and "BTN" boxes (DRC, 2026-11-20).
import hashlib  # noqa: E402
import board_pictures as BP  # noqa: E402
TEXT_BOXES = {'Top': [], 'Bottom': []}
for _t in BP.read_texts(G.PCB, hashlib.md5(open(G.PCB, 'rb').read()).hexdigest()):
    TEXT_BOXES['Top' if _t['side'] == 'top' else 'Bottom'].append(_t['box'])    # [x0, x1, y0, y1]


def text_gap(side, x, y):
    return min([math.hypot(max(b[0] - x, x - b[1], 0), max(b[2] - y, y - b[3], 0)) for b in TEXT_BOXES[side]] + [9.9])
geo = G.component_geometry(comps, pads)
BW = max(p['x'] + p['sx'] / 2 for p in pads)  # refined below from the outline Gerber

# ---- rasters from the release Gerbers (rendered by render.py at 30 px/mm; re-render here at PPMM)
from pygerber.gerberx3.api.v2 import ColorScheme, GerberFile, PixelFormatEnum  # noqa: E402
from pygerber.common.rgba import RGBA  # noqa: E402
SCHEME = ColorScheme(background_color=RGBA.from_rgba(0, 0, 0, 0), clear_color=RGBA.from_rgba(0, 0, 0, 0),
                     solid_color=RGBA.from_rgba(255, 255, 255, 255), clear_region_color=RGBA.from_rgba(0, 0, 0, 0),
                     solid_region_color=RGBA.from_rgba(255, 255, 255, 255))


def raster(code):
    f = GerberFile.from_file('%s.%s' % (GBR, code)).parse()
    out = os.path.join(_TMP, 'r_%s.png' % code)
    f.render_raster(out, dpmm=PPMM, color_scheme=SCHEME, pixel_format=PixelFormatEnum.RGBA)
    info = f.get_info()
    a = np.asarray(Image.open(out))[..., 3] > 0
    return a, float(info.min_x_mm), float(info.max_y_mm)


def dist_map(code, X0, Y1, shape):
    """Distance (mm) from every board-raster pixel to the nearest feature of a layer."""
    a, mx, my = raster(code)
    full = np.zeros(shape, bool)
    ox, oy = int(round((mx - X0) * PPMM)), int(round((Y1 - my) * PPMM))
    h, w = a.shape
    full[oy:oy + h, ox:ox + w] = a[:shape[0] - oy, :shape[1] - ox]
    return ndimage.distance_transform_edt(~full) / PPMM, full


out_a, ox_mm, oy_mm = raster('GM')
X0, Y1 = ox_mm, oy_mm            # board raster spans X0.., ..Y1
shape = out_a.shape
board_x1, board_y1 = X0 + shape[1] / PPMM, Y1
INSIDE = ndimage.binary_fill_holes(out_a) & ~out_a          # inside the outline stroke
EDGE_D = ndimage.distance_transform_edt(~out_a) / PPMM        # distance to the outline


def px(x, y):
    return (Y1 - y) * PPMM, (x - X0) * PPMM        # (row, col)


def register(mfull, side):
    # pygerber's reported layer extents and its raster can disagree by a few hundredths of a mm; measure the mask
    # layer's offset from the board's own SMD pads (each isolated opening's centre against its pad's centre)
    lab, _ = ndimage.label(mfull)
    dr, dc = [], []
    for p in pads:
        if p['hole'] > 1e-6 or p['layer'] != side:
            continue
        r, c = [int(round(v)) for v in px(p['x'], p['y'])]
        k = lab[r, c]
        if not k:
            continue
        rows, cols = np.where(lab[max(r - 80, 0):r + 80, max(c - 80, 0):c + 80] == k)
        if rows.size == 0 or rows.min() == 0 or cols.min() == 0:
            continue
        rows = rows + max(r - 80, 0); cols = cols + max(c - 80, 0)
        w, h = (cols.max() - cols.min() + 1) / PPMM, (rows.max() - rows.min() + 1) / PPMM
        if w > p['sx'] + 0.2 or h > p['sy'] + 0.2:
            continue                                       # opening shared with a neighbour or a via
        cr, cc = px(p['x'], p['y'])
        dr.append((rows.min() + rows.max() + 1) / 2 - cr); dc.append((cols.min() + cols.max() + 1) / 2 - cc)
    sr, sc = int(round(np.median(dr))), int(round(np.median(dc)))
    print('%s mask raster offset from the pads: %+.3f mm x, %+.3f mm y (%d pads); corrected' % (
        side, sc / PPMM, -sr / PPMM, len(dr)))
    return np.roll(np.roll(mfull, -sr, axis=0), -sc, axis=1)


side_maps = {}
for side, (ms, ss) in {'Top': ('GTS', 'GTO'), 'Bottom': ('GBS', 'GBO')}.items():
    _, mfull = dist_map(ms, X0, Y1, shape)
    mfull = register(mfull, side)
    dm = ndimage.distance_transform_edt(~mfull) / PPMM
    ds, sfull = dist_map(ss, X0, Y1, shape)
    side_maps[side] = (dm, ds, mfull, sfull)

# sanity: every SMD pad centre of each side must sit inside a mask opening on that side
for side in ('Top', 'Bottom'):
    dm, ds, mfull, sfull = side_maps[side]
    smd = [p for p in pads if p['hole'] <= 1e-6 and p['layer'] == side]
    inside = sum(mfull[int(round(px(p['x'], p['y'])[0])), int(round(px(p['x'], p['y'])[1]))] for p in smd)
    print('%s: %d of %d SMD pad centres inside a %s opening' % (side, inside, len(smd), 'GTS' if side == 'Top' else 'GBS'))

# ---- body model
Mpads = []
for p in pads:
    L = None if p['hole'] > 1e-6 else [('Top Layer' if p['layer'] == 'Top' else 'Bottom Layer')]
    Mpads.append({'ref': p['ref'], 'pad': p['pad'], 'x': p['x'], 'y': p['y'], 'w': p['sx'], 'h': p['sy'], 'layers': L})
_mech = json.load(open(B.COMPS)).get('mech', {})
_comps = [{'ref': r, 'layer': 'BOTTOM' if c.get('LAYER') == 'BOTTOM' else 'TOP',
           'rot': float(c.get('ROTATION', '0')), 'pattern': c.get('PATTERN', ''), 'height': 0.0}
          for r, c in comps.items()]
bodies = B.build({'pads': Mpads}, {'comps': _comps, 'mech': _mech})

TARGETS = {}
for ref, g in geo.items():
    names = {q['pad'] for q in g['pads']}
    if ref.startswith('LD'):
        TARGETS[ref] = ('cathode', {'K'} if 'K' in names else {'2', '4', '6'})
    elif ref in CONFIG['keyed']:
        continue                  # keyed connectors: the footprint only fits one way
    elif ref in CONFIG['skip']:
        continue                  # an existing mark already fills the only free spot (see CONFIG)
    # RESET is the same PTS810 switch as BTN: marked too, so both read the same way and the library keeps one PTS810
    elif re.match(r'(U|Q|X)\d|BTN$|RESET$', ref):
        TARGETS[ref] = ('pin1', {'A1'} if 'A1' in names else {'1'})
print('targets:', ' '.join(sorted(TARGETS, key=G.bom_audit.natkey)))


def pad_gap(q, x, y, grow=0.0):
    """Distance from (x, y) to pad q's rectangle grown by `grow` on each axis. A solder-mask opening is the pad grown
    by the mask expansion on each axis, so its corners stay square; subtracting the expansion from the copper gap
    (the first version) overstated the clearance near a corner by up to 0.41 x the expansion (0.02 mm)."""
    dx = max(abs(x - q['x']) - q['sx'] / 2 - grow, 0); dy = max(abs(y - q['y']) - q['sy'] / 2 - grow, 0)
    return math.hypot(dx, dy)


def box_gap(b, x, y):
    dx = max(b[0] - x, x - b[2], 0); dy = max(b[1] - y, y - b[3], 0)
    return math.hypot(dx, dy)


def context(ref):
    kind, tgt = TARGETS[ref]
    g = geo[ref]
    side = g['layer']
    own = [q for q in g['pads'] if q['pad'] in tgt]
    others = [q for q in g['pads'] if q['pad'] not in tgt]
    body = bodies[side][ref]['body'][0] if bodies[side].get(ref, {}).get('body') else B.ext([(q['x'] - q['sx'] / 2, q['y'] - q['sy'] / 2, q['x'] + q['sx'] / 2, q['y'] + q['sy'] / 2) for q in g['pads']])
    corners = [(body[0], body[1]), (body[0], body[3]), (body[2], body[1]), (body[2], body[3])]
    tx = np.mean([q['x'] for q in own]); ty = np.mean([q['y'] for q in own])
    use_corner = kind == 'pin1' and len(g['pads']) >= 4 and ref != 'X4'
    cx, cy = min(corners, key=lambda c: math.hypot(c[0] - tx, c[1] - ty)) if use_corner else (tx, ty)
    return dict(ref=ref, kind=kind, tgt=tgt, g=g, side=side, own=own, others=others, body=body, corners=corners,
                ax=(cx if SINGLE.get(ref, True) else g['x']), ay=(cy if SINGLE.get(ref, True) else g['y']),
                use_corner=use_corner, cx=cx, cy=cy, maps=side_maps[side],
                bx=[b_ for r_, v in bodies[side].items() for b_ in v['bodyt']],
                # exact pad openings near the target, grown by the largest mask expansion on the board, for the
                # Silk To Solder Mask rule; the raster still screens via openings
                near_pads=[q for q in pads if (q['hole'] > 1e-6 or q['layer'] == side) and
                           abs(q['x'] - cx) < 4.5 and abs(q['y'] - cy) < 4.5],
                oth=[(r_, v) for r_, v in bodies[side].items() if r_.split('[')[0] != ref and r_.split('[')[0] in TARGETS])


def evaluate(k, x, y, R):
    """None if a dot of radius R at (x, y) breaks a rule for this part, else (score, metrics)."""
    dm, ds, _, _ = k['maps']
    r_, c_ = [int(round(v)) for v in px(x, y)]
    if not (0 <= r_ < shape[0] and 0 <= c_ < shape[1]) or not INSIDE[r_, c_] or EDGE_D[r_, c_] < EDGE + R:
        return None
    if dm[r_, c_] < SILK_MASK + R - 0.02 or ds[r_, c_] < SILK_SILK + R + 0.02:
        return None
    gt = text_gap(k['side'].capitalize(), x, y) - R
    if gt < SILK_SILK + 0.01:     # the box comes from a stroke-font width table: keep 0.01 mm in hand
        return None
    gm_exact = min([pad_gap(q, x, y, MASK_EXP) for q in k['near_pads']] + [9.9]) - R
    # exact geometry (grown rectangles, see pad_gap), so the rule itself is the limit; the DRC rule measures to
    # exposed copper (CLEARANCETOEXPOSEDCOPPER), which is MASK_EXP further away
    if gm_exact < SILK_MASK:
        return None
    if any(B.gap((x - R, y - R, x + R, y + R), b_) < BODY_GAP for b_ in k['bx']):
        return None
    d_own = min(pad_gap(q, x, y) for q in k['own'])
    d_oth = min(pad_gap(q, x, y) for q in k['others']) if k['others'] else 9.9
    pad_ok = d_own + 0.15 <= d_oth and d_own <= 1.0
    corner_ok = False
    if k['use_corner']:
        d_c = math.hypot(x - k['cx'], y - k['cy'])
        corner_ok = d_c <= 1.3 and all(math.hypot(x - c[0], y - c[1]) >= d_c + 0.5 for c in k['corners'] if c != (k['cx'], k['cy']))
    if not (pad_ok or corner_ok):
        return None
    # the dot must read as this part's: nearer its own pads/body than any other marked part's
    d_body = min([box_gap(k['body'], x, y)] + [pad_gap(q, x, y) for q in k['g']['pads']])
    d_near = min([box_gap(b_, x, y) for r2, v in k['oth'] for b_ in v['body']] +
                 [box_gap(pb, x, y) for r2, v in k['oth'] for pb, _ in v['pads']] + [9.9])
    if d_near < d_body + 0.15:
        return None
    score = d_own - 0.3 * min(d_oth - d_own, 1.5) + (0 if R == 0.20 else 0.3)   # prefer spots away from neighbours
    return score, dict(d_own=d_own, gm=gm_exact, gs=min(ds[r_, c_] - R, gt), d_body=d_body, d_near=d_near)


# parts that share a footprint (same pattern, side and rotation) get the dot at the same footprint-relative spot, so
# Design > Make PCB Library sees one footprint, not variants
groups = {}
for ref in sorted(TARGETS, key=G.bom_audit.natkey):
    g = geo[ref]
    # Asar: one spot per footprint, side AND rotation (LD1/LD2 and LD3/LD4 have no common spot); the LED0603 dots stay
    # board-only (see docs/pin1_silk_dots.md)
    groups.setdefault((g['footprint'], g['layer'], g['rotation']), []).append(ref)

SINGLE = {r: len(refs) == 1 for refs in groups.values() for r in refs}
for key_, refs in groups.items():
    rots = {geo[r]['rotation'] for r in refs}
    if key_[1] == 'Bottom' and len(rots) > 1:
        raise SystemExit('%s: bottom-side parts of one footprint at different rotations, not handled' % refs)
plan = {}
for key_, refs in groups.items():
    ks = [context(r) for r in refs]
    best = None
    for R in (0.20, 0.15, 0.125):
        span = 2.5 if len(ks) == 1 else 3.5
        for dx in np.arange(-span, span + 0.0001, 0.025):
            for dy in np.arange(-span, span + 0.0001, 0.025):
                # the offset is taken in the first part's frame and turned with each part's rotation (same side)
                res = []
                for k in ks:
                    th = math.radians(k['g']['rotation'] - ks[0]['g']['rotation'])
                    ox = dx * math.cos(th) - dy * math.sin(th); oy = dx * math.sin(th) + dy * math.cos(th)
                    res.append(evaluate(k, k['ax'] + ox, k['ay'] + oy, R))
                if any(r_ is None for r_ in res):
                    continue
                score = max(r_[0] for r_ in res)
                if best is None or score < best[0]:
                    best = (score, dx, dy, R, res)
        if best is not None:
            break
    if best is None:
        for k in ks:
            print('%-5s %-6s NO LEGAL SPOT' % (k['ref'], k['side']))
            plan[k['ref']] = None
        continue
    s, dx, dy, R, res = best
    for k, (sc, mt) in zip(ks, res):
        th = math.radians(k['g']['rotation'] - ks[0]['g']['rotation'])
        ref, g = k['ref'], k['g']
        x = k['ax'] + dx * math.cos(th) - dy * math.sin(th); y = k['ay'] + dx * math.sin(th) + dy * math.cos(th)
        cp = sorted(k['own'], key=lambda q: (q['pad'] != '2', q['pad']))[0]
        plan[ref] = {'check_pad': {'name': cp['pad'], 'x': round(cp['x'], 4), 'y': round(cp['y'], 4)},
                     'side': k['side'], 'kind': k['kind'], 'pads': sorted(k['tgt']), 'x': round(x, 3), 'y': round(y, 3),
                     'diameter': 2 * R, 'gap_to_target_pad': round(mt['d_own'], 3),
                     'dot_centre_to_own_body': round(mt['d_body'], 3), 'dot_centre_to_other_parts': round(mt['d_near'], 3),
                     'dot_edge_to_mask': round(mt['gm'], 3), 'dot_edge_to_silk': round(mt['gs'], 3),
                     'shared_footprint_with': [r for r in refs if r != ref],
                     'footprint': g['footprint'], 'rotation': g['rotation']}
        print('%-5s %-6s %-20s dot (%7.3f, %7.3f) d%.2f  to %s %.3f, own body %.3f, others %.3f, mask %.3f, silk %.3f%s' % (
            ref, k['side'], g['footprint'][:20], x, y, 2 * R, '/'.join(sorted(k['tgt'])), mt['d_own'], mt['d_body'],
            mt['d_near'], mt['gm'], mt['gs'], '  (same spot as %s)' % ','.join(r for r in refs if r != ref) if len(refs) > 1 else ''))
plan = {r: plan[r] for r in sorted(plan, key=G.bom_audit.natkey)}

json.dump({'dot_diameter': 'per mark', 'rules': {'silk_mask': SILK_MASK, 'silk_silk': SILK_SILK, 'body_gap': BODY_GAP,
           'edge': EDGE}, 'board_mm': [board_x1, board_y1], 'marks': plan}, open(os.path.join(HERE, 'marks.json'), 'w'), indent=1)

# check images: silk (black) + openings (blue-gray) + bodies (outline) + the planned dots (red)
for side in (('Top', 'Bottom') if IMAGES else ()):
    dm, ds, mfull, sfull = side_maps[side]
    img = np.full(shape + (3,), 255, np.uint8)
    img[mfull] = (176, 196, 214)
    img[sfull] = (0, 0, 0)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    for r_, v in bodies[side].items():
        for b in v['bodyt']:
            a0 = px(b[0], b[3]); a1 = px(b[2], b[1])
            d.rectangle((a0[1], a0[0], a1[1], a1[0]), outline=(0, 150, 0))
    for ref, m in plan.items():
        if m and m['side'] == side:
            r_, c_ = px(m['x'], m['y'])
            rr = m['diameter'] / 2 * PPMM
            d.ellipse((c_ - rr, r_ - rr, c_ + rr, r_ + rr), fill=(220, 0, 0))
            d.text((c_ + 10, r_ - 6), ref, fill=(220, 0, 0))
    if side == 'Bottom':
        from PIL import ImageOps
        im = ImageOps.mirror(im)
    im.save(os.path.join(IMAGES, 'plan_%s.png' % side.lower()))
