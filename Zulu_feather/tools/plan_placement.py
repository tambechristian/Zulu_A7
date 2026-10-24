"""First-pass placement for the Feather board (2026-10-23): the floor plan as data, plus a packer.

Board: 0..50.80 x 0..22.86 mm (Altium axes, USB end at x = 0). Header rows at y = 1.27 (16-pin, x 6.35..44.45)
and y = 21.59 (12-pin, x 16.51..44.45); corner holes 2.5 mm at 2.54 mm in from each corner.

Connectors and ICs get fixed spots (FIXED). Every other part is packed by tools/plan_placement.py into the
zones of its group, in order, on a 0.1 mm scan, keeping a margin from everything already placed on the same
side and from through-hole pads and holes on either side. Parts that fit nowhere are parked off the board
(x > 56) and listed. Positions are pad-bounding-box centres; FeatherPlace.pas re-centres each part from its
real pads after setting side and rotation, so the bottom-side mirror needs no maths here.

    python tools/plan_placement.py     -> tools/placement.json, tools/FeatherPlace.pas, docs/placement_v1.png
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DUMP = json.load(open(os.path.join(HERE, 'board_dump.json')))
DUMP.pop('_board', None)            # board-edge box, not a part
W, H = 50.8, 22.86
GRID = 0.1

# ref: (side, rotation, bbox centre x, y, body w, body h at rotation 0) -- body sizes from the datasheets
FIXED = {
    'X2': ('top', 0, 25.4, 11.43, None, None),          # Feather headers + holes (footprint origin = board centre)
    'X1': ('top', 270, 5.085, 11.43, 8.94, 7.3),        # USB-C, mouth flush with x = 0 (body 0..7.30)
    'X4': ('top', 0, 10.8, 18.25, None, None),          # LiPo JST, 0.425 in from the USB end; tabs y 18.5..21.5
    'U2': ('top', 0, 13.7, 7.4, 9.0, 9.0),              # FT2232HQ
    'Q1': ('top', 0, 15.0, 14.3, None, None),             # 12 MHz XO beside the JST contact stem
    'U1': ('top', 0, 24.4, 11.43, 10.0, 10.0),          # XC7A35T CPG236
    'U3': ('top', 0, 35.0, 11.43, 8.0, 8.0),            # SDRAM FBGA-54
    'U4': ('top', 0, 44.3, 15.6, 6.0, 5.0),             # SPI flash WSON-8
    'BTN': ('top', 0, 43.6, 5.2, 4.2, 3.2),
    'LD0': ('top', 0, 44.5, 9.0, 1.6, 1.6),
    'X3': ('bottom', 90, 43.8, 11.43, None, None),      # microSD at the far end, card slot at the right edge
    # (43.8 here = 43.85 pad-centre box, as placed and verified; the dump now holds X3 flipped, which moves its
    #  pad-extent offset by 0.1 mm compared with the first plan made from the unflipped part)
    # bottom buck cells: input cap | SC189 | inductor, one row per rail (3V3, 1V8, 1V0)
    'C147': ('bottom', 90, 9.6, 18.6, None, None), 'U5': ('bottom', 0, 11.8, 18.6, None, None),
    'L1': ('bottom', 90, 14.6, 18.6, None, None),
    'C148': ('bottom', 90, 9.6, 14.6, None, None), 'U6': ('bottom', 0, 11.8, 14.6, None, None),
    'L2': ('bottom', 90, 14.6, 14.6, None, None),
    'C149': ('bottom', 90, 9.6, 10.6, None, None), 'U7': ('bottom', 0, 11.8, 10.6, None, None),
    'L3': ('bottom', 90, 14.6, 10.6, None, None),
}

# zones: (side, x0, y0, x1, y1)
Z = {
    'T_left_low':  ('top', 0.4, 2.3, 8.7, 7.0),
    'T_ft_top':    ('top', 8.9, 12.3, 16.2, 15.8),
    'T_band_low':  ('top', 18.6, 2.3, 41.6, 6.3),
    'T_band_high': ('top', 17.4, 16.6, 40.6, 20.2),
    'T_gap_u1u3':  ('top', 29.5, 6.5, 30.9, 16.4),
    'T_right':     ('top', 39.4, 6.6, 48.6, 13.2),
    'B_left':      ('bottom', 0.4, 2.3, 8.6, 20.6),
    'B_u2':        ('bottom', 8.6, 2.3, 19.2, 20.6),
    'B_u1':        ('bottom', 19.2, 2.3, 30.0, 20.6),
    'B_u3':        ('bottom', 30.0, 2.3, 37.9, 20.6),
    'B_right':     ('bottom', 37.9, 2.3, 50.5, 20.6),
}

GROUPS = [
    # (zones in order of preference, parts in order of importance)
    (['T_right', 'T_band_low'], ['LD5', 'LD1', 'LD2', 'R80', 'R81', 'R82', 'R78', 'R83', 'R84', 'R85', 'R86']),
    (['T_left_low', 'T_ft_top', 'B_left'], ['LD3', 'LD4', 'R27', 'R28']),
    (['T_band_high', 'T_band_low', 'T_gap_u1u3'], ['R2', 'R6', 'R7', 'R35', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15',
                                                   'R16', 'R17', 'C36', 'C37', 'R20', 'R21', 'R22', 'R23', 'R5',
                                                   'R25', 'L6', 'L7', 'C123', 'C124']),
    (['B_u2', 'B_left', 'T_ft_top'], ['C40', 'C41', 'C139', 'C152', 'C153', 'C154', 'L4', 'L5', 'R18', 'R19', 'R24',
                                       'R90', 'R91', 'R92', 'R93', 'R94', 'R99', 'R101', 'R97', 'R4', 'JP3', 'JP4']),
    (['B_left', 'B_u2'], ['U8', 'C150', 'C151', 'R102', 'R103', 'R104', 'R105', 'R106', 'R107', 'R108', 'C78',
                          'R26']),
    (['B_u1', 'B_u2', 'B_u3'], ['R1', 'R34', 'C89', 'C90', 'C91', 'C92', 'C95', 'C96', 'C107', 'C108', 'C109', 'C110',
                                'C111', 'C112', 'C113', 'C114', 'C115', 'C116', 'C117', 'C118', 'C119', 'C120', 'C121',
                                'C122', 'C133', 'C134', 'C135', 'C136', 'C137', 'C138', 'C155', 'C156', 'C157', 'C158',
                                'C159', 'C38', 'C84', 'C87', 'C88', 'C82', 'C94', 'C99', 'C100', 'C101', 'C102',
                                'C103', 'C104', 'C105', 'C106']),
    (['B_u3', 'B_u1', 'B_right'], ['C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C11', 'C12', 'C13']),
    (['B_u2', 'B_u1', 'B_u3', 'B_left', 'B_right'], ['C85', 'C86', 'C140', 'C141', 'C142', 'C143', 'C93', 'C144',
                                                     'C80', 'C97', 'C98', 'C145', 'C146']),
    # restored 2026-10-23: the FT2232H config EEPROM and its two pull-ups, last so nothing above moves
    # placed at the free bottom spot nearest U2's EEPROM pins 61-63 (top row, around x 12.7, y 12.0)
    (['B_left', 'B_u2', 'B_u1'], ['U10', 'R96', 'R98'], (12.7, 12.0)),
    # hardware reset button (added 2026-10-23), top side, nearest free spot to the USB end like a Feather's reset
    (['T_left_low', 'T_band_low', 'T_ft_top', 'T_right'], ['RESET'], (4.0, 4.5)),
]
PARK = ['U$2', 'U$3', 'U$4', 'U$5']     # Creative Commons silk art: kept off the board as on the production copy


def local_bbox(ref):
    ps = DUMP[ref]['pads']
    if not ps:
        return (0, 0, 0, 0)
    return (min(p['x'] - p['dx'] / 2 for p in ps), min(p['y'] - p['dy'] / 2 for p in ps),
            max(p['x'] + p['dx'] / 2 for p in ps), max(p['y'] + p['dy'] / 2 for p in ps))


def size(ref, rot):
    x0, y0, x1, y1 = local_bbox(ref)
    w, h = x1 - x0, y1 - y0
    return (h, w) if rot in (90, 270) else (w, h)


def centre_shift(ref, rot, bottom):
    """Board offset from a part's pad-extent centre to its pad-centre box centre (what the script aligns).
    Bottom parts are mirrored in x before rotating (assumed Altium convention; only X3 is affected)."""
    ps = DUMP[ref]['pads']
    if not ps:
        return 0.0, 0.0
    ex0, ey0, ex1, ey1 = local_bbox(ref)
    cx = (min(p['x'] for p in ps) + max(p['x'] for p in ps)) / 2 - (ex0 + ex1) / 2
    cy = (min(p['y'] for p in ps) + max(p['y'] for p in ps)) / 2 - (ey0 + ey1) / 2
    if bottom:
        cx = -cx
    c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot]
    return cx * c - cy * s, cx * s + cy * c


def margin(ref):
    fp = DUMP[ref]['footprint']
    return 0.12 if fp.endswith('0201') else 0.18 if fp.endswith(('0402', '0603')) else 0.25


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def obstacles():
    """Through-hole pads and holes, which block both sides."""
    out = []
    x2 = FIXED['X2']
    for p in DUMP['X2']['pads']:
        r = max(p['dx'], p['dy']) / 2 + 0.25
        out.append((x2[2] + p['x'] - r, x2[3] + p['y'] - r, x2[2] + p['x'] + r, x2[3] + p['y'] + r))
    # USB-C shell pads and pegs (rotation 270: local (x, y) -> (y, -x) about the footprint origin)
    ox, oy = 3.65, 11.43
    for p in DUMP['X1']['pads']:
        if not p['tht']:
            continue
        cx, cy = ox + p['y'], oy - p['x']
        hw, hh = p['dy'] / 2 + 0.25, p['dx'] / 2 + 0.25
        out.append((cx - hw, cy - hh, cx + hw, cy + hh))
    out.append((0, 0, 0.3, H)); out.append((W - 0.3, 0, W, H))
    out.append((0, 0, W, 0.3)); out.append((0, H - 0.3, W, H))
    return out


def main():
    placed = {}       # ref -> (side, rot, cx, cy, rect)
    side_rects = {'top': [], 'bottom': []}
    obs = obstacles()
    for ref, (side, rot, cx, cy, bw, bh) in FIXED.items():
        w, h = size(ref, rot)
        if bw:
            w, h = (bh, bw) if rot in (90, 270) else (bw, bh)
            w, h = max(w, size(ref, rot)[0]), max(h, size(ref, rot)[1])
        rect = (cx - w / 2 - 0.2, cy - h / 2 - 0.2, cx + w / 2 + 0.2, cy + h / 2 + 0.2)
        placed[ref] = (side, rot, cx, cy, rect)
        if ref != 'X2':
            side_rects[side].append(rect)
    # the USB-C rear SMD pads and the microSD body are real extents, not just their centres
    unplaced = []
    for group in GROUPS:
        zones, refs = group[0], group[1]
        target = group[2] if len(group) > 2 else None
        for ref in refs:
            done = False
            m = margin(ref)
            if target:                      # free spot nearest the target point, any listed zone, either rotation
                best = None
                for zn in zones:
                    side, x0, y0, x1, y1 = Z[zn]
                    for rot in (0, 90):
                        w, h = size(ref, rot)
                        y = y0 + h / 2 + m
                        while y + h / 2 + m <= y1 + 1e-9:
                            x = x0 + w / 2 + m
                            while x + w / 2 + m <= x1 + 1e-9:
                                r = (x - w / 2 - m, y - h / 2 - m, x + w / 2 + m, y + h / 2 + m)
                                d = (x - target[0]) ** 2 + (y - target[1]) ** 2
                                if (best is None or d < best[0]) and not any(overlap(r, o) for o in obs)                                         and not any(overlap(r, o) for o in side_rects[side]):
                                    best = (d, side, rot, round(x, 2), round(y, 2), r)
                                x += GRID
                            y += GRID
                if best:
                    placed[ref] = best[1:]
                    side_rects[best[1]].append(best[5])
                    done = True
            for zn in ([] if target else zones):
                side, x0, y0, x1, y1 = Z[zn]
                for rot in (0, 90):
                    w, h = size(ref, rot)
                    y = y0 + h / 2 + m
                    while not done and y + h / 2 + m <= y1 + 1e-9:
                        x = x0 + w / 2 + m
                        while x + w / 2 + m <= x1 + 1e-9:
                            r = (x - w / 2 - m, y - h / 2 - m, x + w / 2 + m, y + h / 2 + m)
                            if not any(overlap(r, o) for o in obs) and not any(overlap(r, o) for o in side_rects[side]):
                                placed[ref] = (side, rot, round(x, 2), round(y, 2), r)
                                side_rects[side].append(r)
                                done = True
                                break
                            x += GRID
                        y += GRID
                    if done:
                        break
                if done:
                    break
            if not done:
                unplaced.append(ref)
    missing = sorted(set(DUMP) - set(placed) - set(PARK) - set(unplaced))
    park_x = 57.0
    for i, ref in enumerate(unplaced + missing + PARK):
        w, h = size(ref, 0)
        placed[ref] = ('top', 0, park_x + (i % 8) * 4.0, -4.0 - (i // 8) * 4.0, None)
    plan = {}
    for r, v in placed.items():
        dx, dy = centre_shift(r, v[1], v[0] == 'bottom')
        plan[r] = {'side': v[0], 'rot': v[1], 'x': round(v[2] + dx, 3), 'y': round(v[3] + dy, 3)}
    json.dump({'placed': plan, 'unplaced': unplaced, 'not_grouped': missing}, open(os.path.join(HERE, 'placement.json'), 'w'), indent=1)
    emit_pas(plan)
    render(placed, obs)
    on_board = sum(1 for r, v in placed.items() if v[4] is not None)
    print('on board %d, parked %d (unplaced %s, not grouped %s, art %s)' % (on_board, len(unplaced) + len(missing) + len(PARK),
          unplaced, missing, PARK))


def emit_pas(plan):
    lines = ["""{ FeatherPlace.pas -- GENERATED by tools/plan_placement.py; do not edit by hand.
  First-pass placement of zulu_feather.PcbDoc. Each part goes to its side and rotation, then is shifted so the
  centre of its pads' bounding box lands on the planned point (padless parts: the origin does). }

Var
    Brd : IPCB_Board;
    NDone : Integer;
    Missing : String;

Procedure PlaceAt(D : String; Lay : Integer; Rot : Double; PX, PY : Double);
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    X0, Y0, X1, Y1 : TCoord;
    Got : Boolean;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then Begin Missing := Missing + D + ' '; Exit; End;
    C.BeginModify;
    If (Lay = 1) And (C.Layer <> eBottomLayer) Then C.Layer := eBottomLayer;
    If (Lay = 0) And (C.Layer <> eTopLayer) Then C.Layer := eTopLayer;
    C.Rotation := Rot;
    C.EndModify;
    Got := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If Not Got Then Begin X0 := P.X; X1 := P.X; Y0 := P.Y; Y1 := P.Y; Got := True; End;
        If P.X < X0 Then X0 := P.X;
        If P.X > X1 Then X1 := P.X;
        If P.Y < Y0 Then Y0 := P.Y;
        If P.Y > Y1 Then Y1 := P.Y;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    C.BeginModify;
    If Got Then
    Begin
        C.X := C.X + (MMsToCoord(PX) - (X0 + X1) Div 2);
        C.Y := C.Y + (MMsToCoord(PY) - (Y0 + Y1) Div 2);
    End
    Else
    Begin
        C.X := MMsToCoord(PX);
        C.Y := MMsToCoord(PY);
    End;
    C.EndModify;
    NDone := NDone + 1;
End;

Procedure FeatherPlaceV1;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\\Zulu_feather\\Zulu_feather.PrjPcb\\zulu_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_feather\\Zulu_feather.PrjPcb\\zulu_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    NDone := 0;
    Missing := '';
    PCBServer.PreProcess;
"""]
    for ref, v in sorted(plan.items()):
        lines.append("    PlaceAt('%s', %d, %d, %.3f, %.3f);" % (ref, 1 if v['side'] == 'bottom' else 0, v['rot'], v['x'], v['y']))
    lines.append("""    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Placed ' + IntToStr(NDone) + ' parts. Missing: ' + Missing);
End;
""")
    # NOTE: pad bbox here is of pad CENTRES; the planner used pad-extent centres -- identical for symmetric parts,
    # and FIXED asymmetric parts (X1, X4, Q1, U1, X3) are given as pad-extent centres too, see centre_shift().
    open(os.path.join(HERE, 'FeatherPlace.pas'), 'w', newline='\r\n').write('\n'.join(lines))
    open(os.path.join(HERE, 'FeatherPlace.PrjScr'), 'w', newline='\r\n').write(
        '[Design]\nVersion=1.0\n\n[Document1]\nDocumentPath=FeatherPlace.pas\n')


def render(placed, obs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(2, 1, figsize=(14, 13))
    for ax, side in zip(axes, ('top', 'bottom')):
        ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
        for o in obs:
            ax.add_patch(Rectangle((o[0], o[1]), o[2] - o[0], o[3] - o[1], color='#bbbbbb', lw=0))
        for ref, (s, rot, cx, cy, r) in placed.items():
            if s != side or r is None or ref == 'X2':
                continue
            big = DUMP[ref]['footprint'] not in ('C0201', 'R0201', 'C0402', 'R0402', 'C0603', 'C0805', 'LED0603', 'IND0603')
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=True, alpha=0.35,
                                   color='#d55' if big else '#58c', lw=0.5))
            ax.text(cx, cy, ref, fontsize=8 if big else 4.5, ha='center', va='center')
        ax.set_xlim(-1, W + 1); ax.set_ylim(-1, H + 1); ax.set_aspect('equal')
        ax.set_title('%s side (seen from the top)' % side)
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, 'docs', 'placement_v1.png'), dpi=130)


if __name__ == '__main__':
    main()
