"""Plan the pin-1 / LED-cathode silkscreen dots of Zulu_a7_no_pmod Rev 2 (2026-11-20).

PCBWay asked, on the HDI order, for pin 1 / cathode marks because the silkscreen had none. This board had one (U2's
tick; U10 has a tick below pad 1). The plan puts a dot beside every other polarized part, measured from the board and
its release Gerbers:
  * mask openings (GTS/GBS, every opening, vias too): dot edge >= 0.254 mm (rule Silk To Solder Mask)
  * existing silkscreen (GTO/GBO): dot edge >= 0.254 mm (rule Silk to Silk)
  * part bodies (tools/body_check.py, maximum-tolerance boxes) on the dot's side: dot edge >= 0.05 mm outside
  * board outline: dot edge >= 0.30 mm
  * it must point at pin 1: either pin 1 (A1; the LED cathode pads) is the part's nearest pad to the dot by
    >= 0.15 mm, or (multi-pin parts) the dot sits within 1.3 mm of the body corner nearest pin 1 and >= 0.5 mm closer
    to that corner than to any other; and no other marked part's pads or body are as close as its own (+0.15 mm)
  * diameter 0.40 mm where it fits, else 0.30 / 0.25 mm; the spot is the nearest legal one to pin 1, favouring spots
    away from pin 1's neighbours.
X1 and X3 are keyed (their footprints fit one way only) and get no dot; U10 keeps its existing tick.

    python tools/route/pin1_dots/plan_marks.py [--images DIR]
Reads the 2026-11-19 release Gerbers (that ZIP out of git commit 427960e: the board before the dots) and writes marks.json
beside this script; tools/pin1_dots_emit.py turns that into tools/NoPmodPin1Dots.pas.

marks.json is the record of the dots on the board. They were planned with the first pad check (copper gap minus the
expansion, limit 0.264 mm); the corner-exact check below (grown rectangles, limit 0.254 mm) came later and re-ranks a
few spots, so a re-run differs (BTN, Q1, U3, U4). Restore marks.json from git after a re-run; see docs/pin1_silk_dots.md.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REV2 = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
IMAGES = sys.argv[sys.argv.index('--images') + 1] if '--images' in sys.argv else None
REPO = os.path.abspath(os.path.join(REV2, '..', '..'))
import io, subprocess, tempfile, zipfile  # noqa: E402
_TMP = tempfile.mkdtemp(prefix='pin1_gbr_')
# the 2026-11-19 release Gerbers (the board before the dots), out of git history: the 2026-11-20 release replaced that ZIP
_zip = subprocess.run(['git', 'show', '427960e:Zulu_A7_no_pmod/Rev_3/fabrication/'
                       'Zulu_A7_no_pmod_Rev_2_PCBWay_Fabrication_2026-11-19.zip'],
                      cwd=REPO, capture_output=True, check=True).stdout
zipfile.ZipFile(io.BytesIO(_zip)).extractall(_TMP)
GBR = os.path.join(_TMP, 'Zulu_a7_no_pmod')
sys.argv = ['x']
sys.path.insert(0, REV2 + '/tools')
import generate_jlcpcb_assembly as G  # noqa: E402
import body_check as B  # noqa: E402

G.PCB = REV2 + '/Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc'
DOT_R = 0.20            # Ø0.40 mm dot = arc radius 0.10, line width 0.20
SILK_MASK = 0.254       # board rule Silk To Solder Mask (IsPad),(All); applied to every opening
SILK_SILK = 0.254       # board rule Silk to Silk
BODY_GAP = 0.05
MASK_EXP = 0.05        # largest solder-mask expansion on the board (rule default; U2 has 0.035)
EDGE = 0.30
PPMM = 40               # raster resolution

comps, pads = G.read_board()
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
oinfo = (ox_mm, oy_mm)
W_MM = out_a.shape[1] / PPMM
H_MM = out_a.shape[0] / PPMM
X0, Y1 = ox_mm, oy_mm            # board raster spans X0..X0+W_MM, Y1-H_MM..Y1
shape = out_a.shape
board_x0, board_y0 = 0.0, 0.0
board_x1, board_y1 = X0 + W_MM - 0.0127 * 2 + 0.0127, Y1 - 0.0127   # outline drawn with a 0.0254 line


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
bodies = B.build({'pads': Mpads}, json.load(open(B.COMPS)))

TARGETS = {}
for ref, g in geo.items():
    names = {q['pad'] for q in g['pads']}
    if ref.startswith('LD'):
        TARGETS[ref] = ('cathode', {'K'} if 'K' in names else {'2', '4', '6'})
    elif ref in ('X1', 'X3', 'X2'):
        continue                  # keyed connectors: the footprint only fits one way
    elif ref == 'U10':
        continue                  # already has a pin-1 tick below pad 1 (the only free spot)
    elif ref.startswith(('U', 'Q', 'X', 'BTN')):
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
    if not (EDGE + R <= x <= board_x1 - EDGE - R and EDGE + R <= y <= board_y1 - EDGE - R):
        return None
    r_, c_ = [int(round(v)) for v in px(x, y)]
    if dm[r_, c_] < SILK_MASK + R - 0.02 or ds[r_, c_] < SILK_SILK + R + 0.02:
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
    return score, dict(d_own=d_own, gm=gm_exact, gs=ds[r_, c_] - R, d_body=d_body, d_near=d_near)


# parts that share a footprint (same pattern, side and rotation) get the dot at the same footprint-relative spot, so
# Design > Make PCB Library sees one footprint, not variants
groups = {}
for ref in sorted(TARGETS, key=G.bom_audit.natkey):
    g = geo[ref]
    groups.setdefault((g['footprint'], g['layer'], g['rotation']), []).append(ref)

plan = {}
for key_, refs in groups.items():
    ks = [context(r) for r in refs]
    best = None
    for R in (0.20, 0.15, 0.125):
        for dx in np.arange(-2.5, 2.5001, 0.025):
            for dy in np.arange(-2.5, 2.5001, 0.025):
                res = [evaluate(k, k['cx'] + dx, k['cy'] + dy, R) for k in ks]
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
        ref, g, x, y = k['ref'], k['g'], k['cx'] + dx, k['cy'] + dy
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
