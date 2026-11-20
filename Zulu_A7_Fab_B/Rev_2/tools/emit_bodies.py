"""3D component bodies for Fab B Rev 2 (2026-11-20): one extruded box per part, so Altium's Component Clearance rule
checks real bodies instead of each part's bounding rectangle (ported from Zulu_A7_no_pmod/Rev_2/tools/emit_bodies.py,
427960e, which wrote NoPmodBodies3D.pas).

    python tools/emit_bodies.py                 -> tools/FabB_SyncBodies.pas / .PrjScr + tools/route/sync_altium/bodies.json
                                                   for the board as FabB_SyncPlace leaves it (the default, --predict)
    python tools/emit_bodies.py --pcb BOARD     the same for a saved board as it is (no prediction), e.g. if the
                                                   synced board was saved before the bodies went on

Model. Pads and parts are read from the PcbDoc with tools/sync_altium_read.py (olefile; board frame, origin 0,0).
--predict starts from the pre-sync Fab B board (zulu_a7_fab_b.PcbDoc md5 33023787) and replaces U2, X4, U10,
R119-R134, U4, R34, C87, C88, C94, C99, C106 and R1 by their no-PMOD placement, footprint and pads from
tools/route/sync_altium/sync_data.json -- exactly what FabB_SyncPlace produces (it re-measures all 139 pads to
0.001 mm). Bodies are tools/body_check.py's (datasheet size centred on the pads, the connector outlines in
tools/body_mech.json -- X1, X3, X4 and the Pmod header J1 -- and X2 as four 1x10 housings on the BOTTOM side), so the
DRC rule and the release gate see the same parts. Heights: tools/body_heights.json height_max_mm; an entry listed
under 'provisional' (none since 2026-11-20) is used but reported, and tools/fab_notes.py refuses a release until it is
verified. Every body goes on Mechanical 13, projected to the part's own side (X2's housings to the Bottom),
standoff 0. Footprints without a body by design: the Creative Commons artwork and JP3/JP4 (do-not-stuff holes).

FabB_SyncBodies.pas, procedure SyncBodies. Guards on the TARGET path. Refuses, changing nothing, unless
  * every part that gets a body is on the board with the predicted footprint, side, rotation and origin (0.002 mm),
    i.e. FabB_SyncPlace has run and nothing has moved since;
  * the only bodies already on the board belong to the parts the ECO placed from the library copied from the
    no-PMOD project (U2, X4, U10, R119-R134; that library's footprints carry bodies), at most one each, and each such
    body's outline box is within 0.02 mm of the box emitted here (those bodies are KEPT; their heights are the same
    body_heights values, read back by tools/sync_altium_verify.py).
Then it adds every other body and re-counts the bodies of every part (X2 4, every other part 1); a miss is DO NOT
SAVE.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import body_check  # noqa: E402
import sync_altium_read as R  # noqa: E402
import sync_altium_emit as E  # noqa: E402

HEIGHTS = os.path.join(HERE, 'body_heights.json')
MECH = os.path.join(HERE, 'body_mech.json')
OUT_JSON = os.path.join(HERE, 'route', 'sync_altium', 'bodies.json')
EXEMPT = {'CC_BY', 'CC_CC', 'CC_COPYRIGHT', 'CC_SA', '1X03-NOSILK'}
SYNC = E.SWAP + E.NEW + E.MOVE
LIBSET = E.SWAP + E.NEW            # parts the ECO places from the copied library, which carries bodies
LIB_TOL = 0.02


def layers(layer):
    return [] if layer == 'Multi' else ['Top Layer' if layer == 'Top' else 'Bottom Layer' if layer == 'Bottom' else layer]


def model(pcb, predict):
    """(M, D, placements): body_check's model and comps, and {ref: (pattern, side, rot, x, y)} of every part."""
    B = R.read(pcb)
    if predict and B['md5'] != E.TGT_MD5_PRESYNC:
        raise SystemExit('--predict needs the pre-sync board (md5 %s); %s is %s. Use --pcb on a saved synced board.'
                         % (E.TGT_MD5_PRESYNC, os.path.basename(pcb), B['md5']))
    pads = [dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], w=p['w'], h=p['h'], layers=layers(p['layer']))
            for p in B['pads'] if p['ref']]
    comps = {c['ref']: dict(ref=c['ref'], layer='BOTTOM' if c['side'] == 'Bottom' else 'TOP', rot=round(c['rot'], 3),
                            pattern=c['pattern'], height=0.0) for c in B['comps']}
    place = {c['ref']: (c['pattern'], c['side'], c['rot'], c['x'], c['y']) for c in B['comps']}
    if predict:
        D = json.load(open(E.DATA, encoding='utf-8'))
        pads = [p for p in pads if p['ref'] not in SYNC]
        for ref in SYNC:
            s = D['parts'][ref]['src']
            pads += [dict(ref=ref, pad=q[0], x=q[1], y=q[2], w=q[4], h=q[5], layers=layers(q[6])) for q in s['pads']]
            comps[ref] = dict(ref=ref, layer='BOTTOM' if s['side'] == 'Bottom' else 'TOP', rot=round(s['rot'], 3),
                              pattern=s['pattern'], height=0.0)
            place[ref] = (s['pattern'], s['side'], s['rot'], s['x'], s['y'])
    mech = json.load(open(MECH))
    mech.pop('_note', None)
    return dict(pads=pads), dict(comps=sorted(comps.values(), key=lambda c: c['ref']), mech=mech), place


def bodies(M, D):
    Hd = json.load(open(HEIGHTS))
    H, prov = Hd['height_max_mm'], Hd.get('provisional', {})
    side = {c['ref']: c['layer'] for c in D['comps']}
    pat = {c['ref']: c['pattern'] for c in D['comps']}
    out, missing = [], []
    for s, parts in body_check.build(M, D).items():
        for ref, v in sorted(parts.items()):
            if not v['body']:
                continue
            base = ref.split('[')[0]
            if base == 'X2':                       # the four housings, on the Bottom
                p = 'ZULU-DIP37'
            else:
                if side[base] != ('TOP' if s == 'Top' else 'BOTTOM'):
                    continue
                p = pat[base]
            if p in EXEMPT:
                continue
            if p not in H:
                missing.append(p)
                continue
            b = v['body'][0]
            out.append(dict(ref=base, part=ref, pattern=p, bottom=(s == 'Bottom'), x0=b[0], y0=b[1], x1=b[2], y1=b[3],
                            h=H[p], provisional=p in prov))
    if missing:
        raise SystemExit('no height for: %s (add to tools/body_heights.json)' % ', '.join(sorted(set(missing))))
    refs = {c['ref'] for c in D['comps'] if c['pattern'] not in EXEMPT}
    have = {b['ref'] for b in out}
    if refs - have:
        raise SystemExit('parts without a body: %s' % ', '.join(sorted(refs - have)))
    return out


def f(v):
    return '%.4f' % v


def emit(B, place, source):
    today = datetime.date.today().isoformat()
    refs = sorted({b['ref'] for b in B})
    count = {r: sum(1 for b in B if b['ref'] == r) for r in refs}
    lib = [r for r in LIBSET if r in count]
    if any(count[r] != 1 for r in lib):
        raise SystemExit('a library-bodied part has %s bodies' % {r: count[r] for r in lib})
    prov = sorted({'%s (%s %.2f mm)' % (b['ref'], b['pattern'], b['h']) for b in B if b['provisional']})
    L = ['{ FabB_SyncBodies.pas -- GENERATED %s by tools/emit_bodies.py (%s); do not edit by hand.' % (today, source),
         '  %d extruded 3D bodies (Mechanical 13) on %d parts of zulu_a7_fab_b.PcbDoc, heights from tools/body_heights.json.'
         % (len(B), len(refs)),
         '  PROVISIONAL heights: %s.' % (', '.join(prov) if prov else 'none'),
         '  Run SyncBodies with zulu_a7_fab_b.PcbDoc focused, after FabB_SyncPlace, the copper script and FabB_SyncRules.',
         '  Refuses, changing nothing, unless every bodied part is at its predicted footprint/side/rotation/origin and the',
         '  only bodies already present are the library bodies of %s (at most one each, outline within %.2f mm;'
         % (', '.join(['U2', 'X4', 'U10', 'R119-R134']), LIB_TOL),
         '  those are kept). Then adds the rest and re-counts every part (X2 4, others 1). }',
         '',
         'Var',
         '    Brd   : IPCB_Board;',
         '    Bad   : String;',
         '    NBad  : Integer;',
         '    Skip  : TStringList;',
         '    Kept  : String;',
         '    NAdd  : Integer;',
         '']
    L += E.guard_lines('SyncBodies')
    L += [
        'Procedure Fail(S : String);',
        'Begin',
        '    NBad := NBad + 1;',
        '    If NBad <= 30 Then Bad := Bad + S + #13#10;',
        'End;',
        '',
        'Function RotOff(A, B : Double) : Double;',
        'Var',
        '    d : Double;',
        'Begin',
        '    d := A - B;',
        '    While d < 0 Do d := d + 360;',
        '    While d >= 360 Do d := d - 360;',
        '    If d > 180 Then d := 360 - d;',
        '    Result := d;',
        'End;',
        '',
        '{ a bodied part must be where the bodies were computed }',
        'Procedure Chk(Ref, Pat : String; Bot : Boolean; Rot, X, Y : Double);',
        'Var',
        '    C : IPCB_Component;',
        '    cx, cy : Double;',
        'Begin',
        '    C := Brd.GetPcbComponentByRefDes(Ref);',
        '    If C = Nil Then',
        '    Begin',
        "        Fail(Ref + ' is not on the board');",
        '        Exit;',
        '    End;',
        "    If C.Pattern <> Pat Then Fail(Ref + ' footprint is ' + C.Pattern + ', the bodies were computed for ' + Pat);",
        '    If Bot Then',
        '    Begin',
        "        If C.Layer <> eBottomLayer Then Fail(Ref + ' is not on the Bottom side');",
        '    End',
        '    Else',
        '    Begin',
        "        If C.Layer <> eTopLayer Then Fail(Ref + ' is not on the Top side');",
        '    End;',
        '    cx := CoordToMMs(C.X - Brd.XOrigin);',
        '    cy := CoordToMMs(C.Y - Brd.YOrigin);',
        '    If (Abs(cx - X) > 0.002) Or (Abs(cy - Y) > 0.002) Then',
        "        Fail(Ref + ' origin is (' + FormatFloat('0.0000', cx) + ', ' + FormatFloat('0.0000', cy) + '), the bodies were computed for (' + FormatFloat('0.0000', X) + ', ' + FormatFloat('0.0000', Y) + ')');",
        '    If RotOff(C.Rotation, Rot) > 0.01 Then',
        "        Fail(Ref + ' rotation is ' + FormatFloat('0.###', C.Rotation) + ', the bodies were computed for ' + FormatFloat('0.###', Rot));",
        'End;',
        '',
        '{ bodies owned by Ref, and the outline box of the last one }',
        'Function BodyCount(Ref : String; Var X0, Y0, X1, Y1 : Double) : Integer;',
        'Var',
        '    It : IPCB_BoardIterator;',
        '    B  : IPCB_ComponentBody;',
        '    Rc : TCoordRect;',
        'Begin',
        '    Result := 0;',
        '    It := Brd.BoardIterator_Create;',
        '    It.AddFilter_ObjectSet(MkSet(eComponentBodyObject));',
        '    It.AddFilter_LayerSet(AllLayers);',
        '    It.AddFilter_Method(eProcessAll);',
        '    B := It.FirstPCBObject;',
        '    While B <> Nil Do',
        '    Begin',
        '        If B.InComponent Then',
        '        Begin',
        '            If B.Component.Name.Text = Ref Then',
        '            Begin',
        '                Result := Result + 1;',
        '                Rc := B.BoundingRectangle;',
        '                X0 := CoordToMMs(Rc.Left - Brd.XOrigin);',
        '                Y0 := CoordToMMs(Rc.Bottom - Brd.YOrigin);',
        '                X1 := CoordToMMs(Rc.Right - Brd.XOrigin);',
        '                Y1 := CoordToMMs(Rc.Top - Brd.YOrigin);',
        '            End;',
        '        End;',
        '        B := It.NextPCBObject;',
        '    End;',
        '    Brd.BoardIterator_Destroy(It);',
        'End;',
        '',
        'Function AllBodies : Integer;',
        'Var',
        '    It : IPCB_BoardIterator;',
        '    B  : IPCB_ComponentBody;',
        'Begin',
        '    Result := 0;',
        '    It := Brd.BoardIterator_Create;',
        '    It.AddFilter_ObjectSet(MkSet(eComponentBodyObject));',
        '    It.AddFilter_LayerSet(AllLayers);',
        '    It.AddFilter_Method(eProcessAll);',
        '    B := It.FirstPCBObject;',
        '    While B <> Nil Do',
        '    Begin',
        '        Result := Result + 1;',
        '        B := It.NextPCBObject;',
        '    End;',
        '    Brd.BoardIterator_Destroy(It);',
        'End;',
        '',
        '{ a part the ECO placed from the no-PMOD library: keep its library body when it matches the emitted box }',
        'Function LibBody(Ref : String; X0, Y0, X1, Y1 : Double) : Integer;',
        'Var',
        '    n : Integer;',
        '    a, b, c, d : Double;',
        'Begin',
        '    a := 0; b := 0; c := 0; d := 0;',
        '    n := BodyCount(Ref, a, b, c, d);',
        '    Result := n;',
        '    If n = 1 Then',
        '    Begin',
        '        If (Abs(a - X0) > %s) Or (Abs(b - Y0) > %s) Or (Abs(c - X1) > %s) Or (Abs(d - Y1) > %s) Then' % ((LIB_TOL,) * 4),
        "            Fail(Ref + ' carries a library body at ' + FormatFloat('0.000', a) + ',' + FormatFloat('0.000', b) + ' - ' + FormatFloat('0.000', c) + ',' + FormatFloat('0.000', d) + ', not the emitted ' + FormatFloat('0.000', X0) + ',' + FormatFloat('0.000', Y0) + ' - ' + FormatFloat('0.000', X1) + ',' + FormatFloat('0.000', Y1))",
        '        Else',
        '        Begin',
        '            Skip.Add(Ref);',
        "            Kept := Kept + Ref + ' ';",
        '        End;',
        '    End;',
        '    If n > 1 Then',
        "        Fail(Ref + ' already carries ' + IntToStr(n) + ' bodies');",
        'End;',
        '',
        'Procedure AddBody(Ref : String; X0, Y0, X1, Y1, H : Double; Bot : Boolean);',
        'Var',
        '    Cm : IPCB_Component;',
        '    B  : IPCB_ComponentBody;',
        '    Ct : IPCB_Contour;',
        '    Md : IPCB_Model;',
        'Begin',
        '    If Skip.IndexOf(Ref) >= 0 Then Exit;',
        '    Cm := Brd.GetPcbComponentByRefDes(Ref);',
        '    B := PCBServer.PCBObjectFactory(eComponentBodyObject, eNoDimension, eCreate_Default);',
        '    Ct := PCBServer.PCBContourFactory;',
        '    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X0), Brd.YOrigin + MMsToCoord(Y0));',
        '    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X1), Brd.YOrigin + MMsToCoord(Y0));',
        '    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X1), Brd.YOrigin + MMsToCoord(Y1));',
        '    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X0), Brd.YOrigin + MMsToCoord(Y1));',
        '    B.SetOutlineContour(Ct);',
        '    B.Layer := eMechanical13;',
        '    If Bot Then B.BodyProjection := eBoardSide_Bottom Else B.BodyProjection := eBoardSide_Top;',
        '    Md := B.ModelFactory_CreateExtruded(0, MMsToCoord(H), $808080);',
        '    B.SetModel(Md);',
        '    Cm.AddPCBObject(B);',
        '    Brd.AddPCBObject(B);',
        '    NAdd := NAdd + 1;',
        'End;',
        '',
        'Procedure Recount(Ref : String; N : Integer);',
        'Var',
        '    a, b, c, d : Double;',
        '    k : Integer;',
        'Begin',
        '    a := 0; b := 0; c := 0; d := 0;',
        '    k := BodyCount(Ref, a, b, c, d);',
        "    If k <> N Then Fail(Ref + ' has ' + IntToStr(k) + ' bodies after the run, expected ' + IntToStr(N));",
        'End;',
        '',
        'Procedure SyncBodies;',
        'Var',
        '    nLib, nAll, n : Integer;',
        'Begin',
        '    Brd := SyncBoard;',
        '    If Brd = Nil Then Exit;',
        "    Bad := '';",
        '    NBad := 0;',
        "    Kept := '';",
        '    NAdd := 0;',
        '    Skip := TStringList.Create;',
        '',
        '    { ---- preconditions ---- }']
    for r in refs:
        pat, sd, rot, x, y = place[r]
        L.append("    Chk('%s', '%s', %s, %s, %s, %s);" % (r, pat, 'True' if sd == 'Bottom' else 'False', '%.6f' % rot,
                                                      '%.6f' % x, '%.6f' % y))
    L.append('    nLib := 0;')
    for r in lib:
        b = next(b for b in B if b['ref'] == r)
        L += ["    n := LibBody('%s', %s, %s, %s, %s);" % (r, f(b['x0']), f(b['y0']), f(b['x1']), f(b['y1'])),
              '    If n = 1 Then nLib := nLib + 1;']
    L += ['    nAll := AllBodies;',
          '    If nAll <> nLib Then',
          "        Fail(IntToStr(nAll - nLib) + ' bodies on the board belong to no part or to parts other than the library-placed ones (reload the board from disk)');",
          '    If NBad > 0 Then',
          '    Begin',
          "        ShowMessage('Refusing: ' + IntToStr(NBad) + ' precondition(s) failed; NOTHING was changed.' + #13#10 + Bad);",
          '        Skip.Free;',
          '        Exit;',
          '    End;',
          '',
          '    { ---- bodies ---- }',
          '    PCBServer.PreProcess;',
          '    Try']
    for b in B:
        L.append("        AddBody('%s', %s, %s, %s, %s, %.3f, %s);   { %s %s%s }" % (
            b['ref'], f(b['x0']), f(b['y0']), f(b['x1']), f(b['y1']), b['h'], 'True' if b['bottom'] else 'False',
            b['part'], b['pattern'], ' PROVISIONAL height' if b['provisional'] else ''))
    L += ['    Finally',
          '        PCBServer.PostProcess;',
          '    End;',
          '    Brd.ViewManager_FullUpdate;',
          '',
          '    { ---- re-count ---- }']
    for r in refs:
        L.append("    Recount('%s', %d);" % (r, count[r]))
    L += ['    nAll := AllBodies;',
          "    If nAll <> %d Then Fail(IntToStr(nAll) + ' bodies on the board, expected %d');" % (len(B), len(B)),
          '    If NBad > 0 Then',
          "        ShowMessage('DO NOT SAVE: ' + IntToStr(NBad) + ' check(s) failed after adding ' + IntToStr(NAdd) + ' bodies. Close the PcbDoc WITHOUT saving and reopen it.' + #13#10 + Bad)",
          '    Else',
          "        ShowMessage('SyncBodies OK: ' + IntToStr(NAdd) + ' bodies added, ' + IntToStr(nLib) + ' library bodies kept (' + Kept + '); %d bodies on %d parts (Mechanical 13).%s Save the board.');"
          % (len(B), len(refs), (' PROVISIONAL height: %s.' % ', '.join(prov)) if prov else ''),
          '    Skip.Free;',
          'End;',
          '']
    E.write_pas('FabB_SyncBodies', L)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(dict(source=source, bodies=B), open(OUT_JSON, 'w', newline='\n'), indent=1)
    print('%d bodies on %d parts (%d library parts may keep theirs) -> tools/FabB_SyncBodies.pas' % (len(B), len(refs), len(lib)))
    if prov:
        print('WARNING: provisional heights:', ', '.join(prov))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--pcb', help='a saved board to read as it is (default: predict the synced board)')
    a = ap.parse_args()
    if a.pcb:
        M, D, place = model(os.path.abspath(a.pcb), False)
        source = 'board %s md5 %s' % (os.path.basename(a.pcb), R.md5(a.pcb)[:8])
    else:
        M, D, place = model(E.TGT_PCB, True)
        source = 'predicted: pre-sync board md5 %s + sync_data.json md5 %s' % (E.TGT_MD5_PRESYNC[:8], R.md5(E.DATA)[:8])
    emit(bodies(M, D), place, source)


if __name__ == '__main__':
    main()
