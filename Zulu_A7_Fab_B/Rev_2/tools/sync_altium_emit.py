# -*- coding: utf-8 -*-
"""Fab B Rev 2 <- no-PMOD Rev 2 sync: data extract + DelphiScript generator (2026-11-20).  Read-only on the boards.

    python tools/sync_altium_emit.py            -> tools/route/sync_altium/sync_data.json (if missing) and
                                                   tools/FabB_SyncPlace.pas/.PrjScr, tools/FabB_SyncRules.pas/.PrjScr,
                                                   tools/FabB_SyncRepour.pas/.PrjScr
                                                   (FabB_SyncBodies comes from tools/emit_bodies.py)
    python tools/sync_altium_emit.py --refresh  re-extract sync_data.json (needs both boards at the md5s below)

SOURCE = Zulu_A7_no_pmod/Rev_2 Zulu_a7_no_pmod.PcbDoc at commit 427960e (md5 9b0341ba; read from the working copy
when its md5 matches, else from `git show 427960e:...`). TARGET = this folder's zulu_a7_fab_b.PcbDoc BEFORE the
sync (md5 33023787, the 2026-11-12 Fab B Rev 2 release board). sync_data.json keeps everything the scripts need, so
they can be regenerated after the TARGET board has changed.

Scripts (each its own .pas + .PrjScr: a procedure added to an already-compiled .pas is a silent no-op in Altium):
  FabB_SyncPlace.pas  procedure SyncPlace -- after the library copy + ECO. Puts U2, X4, U10 (footprints swapped by
      the ECO), R119-R134 (added by the ECO, parked off the board), U4, R34, C87, C88, C94, C99, C106 and R1 at the
      no-PMOD board's exact origin / rotation / side, then sets every designator (and U1's, moved for R132) to the
      no-PMOD position and visibility. Refuses, changing nothing, unless every part is on the board with the
      no-PMOD footprint and pad count, every pad carries the no-PMOD net (U3's 16 DQ pads included: they must be
      SDRAM-D0..D15 after the ECO), every existing part sits at its pre-sync Fab B origin/rotation/side and every
      new resistor is still parked off the board. After the moves it re-measures all 139 pads (0.001 mm) and
      every designator; any miss is reported as DO NOT SAVE.
  FabB_SyncRules.pas  procedure SyncRules -- ComponentClearance_R131R132 (0 mm) then ComponentClearance_X2
      (0.05 mm) (new rules land at priority 1, so this order gives the no-PMOD priorities X2 = 1, R131R132 = 2),
      SolderMaskExpansion_U2 (0.035 mm, priority 1), the six Schematic Supply Nets voltages (VCC1V0 1.0,
      VCC1V8 1.8, VCC3V3 3.3, VCCADC 1.8, GND/GNDADC 0) and SDRAM-D0..D15 added to net class SDRAM_DATA, then
      invalidates U2's 65 pad mask caches (a new mask rule does not reach existing pads otherwise;
      no-PMOD tools/NoPmodU2MaskCache.pas). Refuses, changing nothing, if any of the three rules exists, the six
      supply-net rules are not exactly the six scopes, SDRAM_DATA is missing or duplicated, any SDRAM-Dn net is
      missing, or U2 is not the 65-pad FT2232HQ-QFN64.
  FabB_SyncRepour.pas procedure SyncRepour -- rebuilds the two plane polygons (no-PMOD NoPmod_Repour.pas); refuses
      unless the board has exactly 2 polygons.
All guard on the focused document's full path (built here with chr(92), never a .replace) and on the board's
file name. DelphiScript traps honoured: no `(X = Nil) Or (X.Prop ...)` (it does not short-circuit); only API names
already proven in this project's scripts; designators move with ChangeNameAutoposition(eAutoPos_Manual) +
MoveToXY inside the component's BeginModify/EndModify (no-PMOD NoPmodU2Label2.pas; writing XLocation is ignored).
"""
# 2026-11-20: IPCB_ObjectClass.IsMember takes the member OBJECT; IsMember('name') is always False on this build
# (the first SyncRules run refused on all 16 D-nets that ARE members), so every test passes NetByName(...).
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                                   # .../Zulu_A7_Fab_B/Rev_2
REPO = os.path.normpath(os.path.join(ROOT, '..', '..'))
sys.path.insert(0, HERE)
import sync_altium_read as R  # noqa: E402

SRC_REL = 'Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc'
SRC_COMMIT = '427960e'
SRC_MD5 = '9b0341ba09f3aec84459e361271cd9b0'
TGT_PCB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'zulu_a7_fab_b.PcbDoc')
TGT_MD5_PRESYNC = '330237878e325c882fca3f689b55ec0c'
DATA = os.path.join(HERE, 'route', 'sync_altium', 'sync_data.json')
# every part of the 2026-11-12 Fab B Rev 2 release board (md5 33023787), for tools/fab_notes.py's change list
RELEASE_COMPONENTS = os.path.join(HERE, 'route', 'sync_altium', 'release_2026-11-11_components.json')
BS = chr(92)
GUARD = BS + BS.join(['Zulu_A7_Fab_B', 'Rev_2', 'Imported zulu_a7.PrjPcb', 'zulu_a7_fab_b.PcbDoc'])
BOARD_FILE = 'zulu_a7_fab_b.PcbDoc'
BOARD_W, BOARD_H = 69.85, 25.40

SWAP = ['U2', 'X4', 'U10']                                     # footprint changed by the ECO, origin kept
NEW = ['R%d' % i for i in range(119, 135)]                     # added by the ECO, parked off the board
MOVE = ['U4', 'R34', 'C87', 'C88', 'C94', 'C99', 'C106', 'R1']  # same footprint, moved on the no-PMOD board
DESIG_ONLY = ['U1']                                            # designator moved for R132 (SeriesRDesig.pas)
SDRAM_NETS = ['SDRAM-D%d' % i for i in range(16)]
NEW_RULES = ('ComponentClearance_X2', 'ComponentClearance_R131R132', 'SolderMaskExpansion_U2')
SUPPLY_SCOPES = ["InNet('VCC1V0')", "InNet('GND')", "InNet('GNDADC')", "InNet('VCC1V8')", "InNet('VCC3V3')",
                 "InNet('VCCADC')"]


def source_pcb():
    """Path of the no-PMOD board at 427960e: the working copy if it still is that file, else a git export."""
    path = os.path.join(REPO, *SRC_REL.split('/'))
    if os.path.isfile(path) and R.md5(path) == SRC_MD5:
        return path
    raw = subprocess.run(['git', '-C', REPO, 'show', '%s:%s' % (SRC_COMMIT, SRC_REL)], check=True,
                         capture_output=True).stdout
    if hashlib.md5(raw).hexdigest() != SRC_MD5:
        raise SystemExit('git %s:%s is not md5 %s' % (SRC_COMMIT, SRC_REL, SRC_MD5))
    tmp = os.path.join(tempfile.mkdtemp(prefix='sync_src_'), 'Zulu_a7_no_pmod.PcbDoc')
    open(tmp, 'wb').write(raw)
    return tmp


def comp_entry(B, ref):
    c = {x['ref']: x for x in B['comps']}.get(ref)
    if c is None:
        return None
    d = [t for t in B['texts'] if t['comp'] == ref and t['designator']]
    if len(d) != 1:
        raise SystemExit('%s: %d designator texts' % (ref, len(d)))
    return dict(pattern=c['pattern'], side=c['side'], rot=round(c['rot'], 6), x=c['x'], y=c['y'],
                x_mil=c['x_mil'], y_mil=c['y_mil'], name_on=c['name_on'], comment_on=c['comment_on'],
                name_autopos=c['name_autopos'], libref=c['libref'], fpdesc=c['fpdesc'],
                desig=dict(x=d[0]['x'], y=d[0]['y'], rot=round(d[0]['rot'], 6), layer=d[0]['layer']),
                pads=sorted(([p['pad'], p['x'], p['y'], p['net'] or '', p['w'], p['h'], p['layer']]
                             for p in B['pads'] if p['ref'] == ref), key=lambda q: q[0]))


def extract():
    tgt_md5 = R.md5(TGT_PCB)
    if tgt_md5 != TGT_MD5_PRESYNC:
        raise SystemExit('the TARGET board is md5 %s, not the pre-sync %s: keep the existing %s'
                         % (tgt_md5, TGT_MD5_PRESYNC, os.path.relpath(DATA, ROOT)))
    S, T = R.read(source_pcb()), R.read(TGT_PCB)
    parts = {}
    for group, refs in (('swap', SWAP), ('new', NEW), ('move', MOVE), ('desig', DESIG_ONLY)):
        for ref in refs:
            s, t = comp_entry(S, ref), comp_entry(T, ref)
            if s is None:
                raise SystemExit('%s missing on the no-PMOD board' % ref)
            if (t is None) != (group == 'new'):
                raise SystemExit('%s: unexpected presence on the Fab B board' % ref)
            parts[ref] = dict(group=group, src=s, tgt=t)
    u3 = sorted([p['pad'], p['net']] for p in S['pads'] if p['ref'] == 'U3' and (p['net'] or '').startswith('SDRAM-D'))
    if sorted(n for _, n in u3) != sorted(SDRAM_NETS):
        raise SystemExit('U3 DQ pads on the no-PMOD board: %s' % u3)
    rules = {r.get('NAME'): r for r in S['rules']}
    trules = {r.get('NAME'): r for r in T['rules']}
    keep = ('RULEKIND', 'NAME', 'PRIORITY', 'SCOPE1EXPRESSION', 'SCOPE2EXPRESSION', 'GAP', 'VERTICALGAP',
            'COLLISIONCHECKMODE', 'EXPANSION', 'VOLTAGE', 'NETSCOPE', 'LAYERKIND', 'ENABLED', 'ISTENTINGTOP')
    src_rules = {n: {k: v for k, v in r.items() if k in keep} for n, r in rules.items()
                 if n in NEW_RULES or r.get('RULEKIND') in ('SupplyNets', 'ComponentClearance', 'SolderMaskExpansion')}
    tgt_rules = {n: {k: v for k, v in r.items() if k in keep} for n, r in trules.items()
                 if r.get('RULEKIND') in ('SupplyNets', 'ComponentClearance', 'SolderMaskExpansion')}
    cls = {c.get('NAME'): R.class_members(c) for c in S['classes'] if c.get('KIND') == '0'}
    tcls = {c.get('NAME'): R.class_members(c) for c in T['classes'] if c.get('KIND') == '0'}
    in_classes = sorted(n for n, m in cls.items() if set(SDRAM_NETS) & set(m))
    data = dict(
        _note='Generated by tools/sync_altium_emit.py; mm, board frame (origin 0,0 on both boards), y up. src = the '
              'no-PMOD board at 427960e, tgt = the Fab B Rev 2 board before the sync. pads: [name, x, y, net, '
              'w, h, layer] with w/h the axis-aligned extent after the pad rotation.',
        source=dict(commit=SRC_COMMIT, md5=S['md5'], path=SRC_REL), target=dict(md5=T['md5']),
        parts=parts, u3_dq=u3, src_rules=src_rules, tgt_rules=tgt_rules,
        sdram_classes=in_classes, src_sdram_data=sorted(cls.get('SDRAM_DATA', [])),
        tgt_sdram_data=sorted(tcls.get('SDRAM_DATA', [])),
        src_outline=S['outline'], tgt_outline=T['outline'])
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    json.dump(data, open(DATA, 'w', encoding='utf-8', newline='\n'), indent=1, sort_keys=True)
    print('wrote', os.path.relpath(DATA, ROOT), 'md5', R.md5(DATA))
    rel = dict(_note='Every part of the Fab B Rev 2 release board zulu_a7_fab_b.PcbDoc (md5 %s, saved 2026-11-12 00:16:55, '
                     'released 2026-11-11), from Components6: [pattern, side, rotation, x mm, y mm]. Written by '
                     'tools/sync_altium_emit.py; tools/fab_notes.py lists the parts the sync moved against it.' % T['md5'],
               md5=T['md5'], parts={c['ref']: [c['pattern'], c['side'], round(c['rot'], 6), c['x'], c['y']]
                                    for c in T['comps']})
    json.dump(rel, open(RELEASE_COMPONENTS, 'w', encoding='utf-8', newline='\n'), indent=1, sort_keys=True)
    print('wrote', os.path.relpath(RELEASE_COMPONENTS, ROOT))
    return data


def f6(v):
    return '%.6f' % v


def guard_lines(proc_msg):
    return [
        'Function SyncBoard : IPCB_Board;',
        'Var',
        '    Doc : IDocument;',
        '    Ok  : Boolean;',
        'Begin',
        '    Result := Nil;',
        '    Ok := False;',
        '    Doc := GetWorkspace.DM_FocusedDocument;',
        '    If Doc <> Nil Then',
        "        If Pos('%s', Doc.DM_FullPath) > 0 Then Ok := True;" % GUARD,
        '    If Not Ok Then',
        '    Begin',
        "        ShowMessage('Refusing (%s): focus %s first; nothing changed.');" % (proc_msg, GUARD[1:]),
        '        Exit;',
        '    End;',
        '    Result := PCBServer.GetCurrentPCBBoard;',
        '    If Result = Nil Then',
        '    Begin',
        "        ShowMessage('Refusing (%s): no PCB board is current; nothing changed.');" % proc_msg,
        '        Exit;',
        '    End;',
        "    If Pos('%s', Result.FileName) = 0 Then" % BOARD_FILE,
        '    Begin',
        "        ShowMessage('Refusing (%s): the current board is ' + Result.FileName + ', not %s; nothing changed.');"
        % (proc_msg, BOARD_FILE),
        '        Result := Nil;',
        '        Exit;',
        '    End;',
        'End;',
        '']


def prjscr(name):
    return '[Design]\r\nVersion=1.0\r\n\r\n[Document1]\r\nDocumentPath=%s.pas\r\n' % name


def write_pas(name, lines):
    open(os.path.join(HERE, name + '.pas'), 'w', newline='\r\n', encoding='ascii').write('\n'.join(lines) + '\n')
    open(os.path.join(HERE, name + '.PrjScr'), 'w', newline='', encoding='ascii').write(prjscr(name))
    print('wrote tools/%s.pas + .PrjScr (%d lines)' % (name, len(lines)))


def emit_place(D):
    P = D['parts']
    today = datetime.date.today().isoformat()
    npads = sum(len(P[r]['src']['pads']) for r in SWAP + NEW + MOVE)
    L = ['{ FabB_SyncPlace.pas -- GENERATED %s by tools/sync_altium_emit.py from tools/route/sync_altium/sync_data.json'
         % today,
         '  (no-PMOD Zulu_a7_no_pmod.PcbDoc at %s, md5 %s; Fab B zulu_a7_fab_b.PcbDoc before the sync, md5 %s).'
         % (D['source']['commit'], D['source']['md5'][:8], D['target']['md5'][:8]),
         '  Do not edit by hand. Run SyncPlace with zulu_a7_fab_b.PcbDoc focused, AFTER the library copy and the ECO',
         '  (U2/X4/U10 footprints swapped in place, R119-R134 added off the board, U3 DQ pads re-netted; saved, closed',
         '  and reopened). Moves %s, %s, %s and the designators of those parts and U1.'
         % (', '.join(SWAP), 'R119-R134', ', '.join(MOVE)),
         '  Preconditions (all checked before anything moves): footprint and pad count per part, every pad net, U3 DQ',
         '  nets, pre-sync Fab B origin/rotation/side of U2 X4 U10 U4 R34 C87 C88 C94 C99 C106 R1, R119-R134 parked off',
         '  the board, U1 designator at its pre-sync place. After the moves all %d pads are re-measured (0.001 mm) and'
         % npads,
         '  every designator (0.005 mm); a miss is reported as DO NOT SAVE (close without saving and reopen). }',
         '',
         'Var',
         '    Brd    : IPCB_Board;',
         '    Bad    : String;',
         '    NBad   : Integer;',
         '    Info   : String;',
         '    Forced : String;',
         '    NPadOk : Integer;',
         '']
    L += guard_lines('SyncPlace')
    L += [
        'Function FindPad(C : IPCB_Component; PName : String) : IPCB_Pad;',
        'Var',
        '    It : IPCB_GroupIterator;',
        '    P  : IPCB_Pad;',
        'Begin',
        '    Result := Nil;',
        '    It := C.GroupIterator_Create;',
        '    It.AddFilter_ObjectSet(MkSet(ePadObject));',
        '    P := It.FirstPCBObject;',
        '    While P <> Nil Do',
        '    Begin',
        '        If P.Name = PName Then Result := P;',
        '        P := It.NextPCBObject;',
        '    End;',
        '    C.GroupIterator_Destroy(It);',
        'End;',
        '',
        'Function PadCount(C : IPCB_Component) : Integer;',
        'Var',
        '    It : IPCB_GroupIterator;',
        '    P  : IPCB_Pad;',
        'Begin',
        '    Result := 0;',
        '    It := C.GroupIterator_Create;',
        '    It.AddFilter_ObjectSet(MkSet(ePadObject));',
        '    P := It.FirstPCBObject;',
        '    While P <> Nil Do',
        '    Begin',
        '        Result := Result + 1;',
        '        P := It.NextPCBObject;',
        '    End;',
        '    C.GroupIterator_Destroy(It);',
        'End;',
        '',
        'Function NetOf(P : IPCB_Pad) : String;',
        'Begin',
        "    Result := '';",
        '    If P.Net <> Nil Then Result := P.Net.Name;',
        'End;',
        '',
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
        'Function FmtXY(X, Y : Double) : String;',
        'Begin',
        "    Result := '(' + FormatFloat('0.0000', X) + ', ' + FormatFloat('0.0000', Y) + ')';",
        'End;',
        '',
        '{ Mode 0: an existing part, must be at its pre-sync Fab B origin/rotation/side. Mode 1: a part the ECO added,',
        '  must be parked off the board (origin more than 0.5 mm outside the 69.85 x 25.40 mm outline). }',
        'Procedure PreComp(Ref, Pat : String; NP, Mode : Integer; Bot : Boolean; Rot, X, Y : Double);',
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
        '    If C.Pattern <> Pat Then',
        '    Begin',
        "        Fail(Ref + ' footprint is ' + C.Pattern + ', expected ' + Pat);",
        '        Exit;',
        '    End;',
        '    If PadCount(C) <> NP Then',
        "        Fail(Ref + ' has ' + IntToStr(PadCount(C)) + ' pads, expected ' + IntToStr(NP));",
        '    cx := CoordToMMs(C.X - Brd.XOrigin);',
        '    cy := CoordToMMs(C.Y - Brd.YOrigin);',
        '    If Mode = 1 Then',
        '    Begin',
        '        If (cx > -0.5) And (cx < %s) And (cy > -0.5) And (cy < %s) Then' % (f6(BOARD_W + 0.5), f6(BOARD_H + 0.5)),
        "            Fail(Ref + ' is already on the board at ' + FmtXY(cx, cy) + '; the ECO leaves it parked off the board');",
        '        Exit;',
        '    End;',
        '    If Bot Then',
        '    Begin',
        "        If C.Layer <> eBottomLayer Then Fail(Ref + ' is not on the Bottom side');",
        '    End',
        '    Else',
        '    Begin',
        "        If C.Layer <> eTopLayer Then Fail(Ref + ' is not on the Top side');",
        '    End;',
        '    If (Abs(cx - X) > 0.002) Or (Abs(cy - Y) > 0.002) Then',
        "        Fail(Ref + ' origin is ' + FmtXY(cx, cy) + ', not its pre-sync Fab B ' + FmtXY(X, Y));",
        '    If RotOff(C.Rotation, Rot) > 0.01 Then',
        "        Fail(Ref + ' rotation is ' + FormatFloat('0.###', C.Rotation) + ', not ' + FormatFloat('0.###', Rot));",
        'End;',
        '',
        'Procedure PreNet(Ref, PName, Net : String);',
        'Var',
        '    C : IPCB_Component;',
        '    P : IPCB_Pad;',
        'Begin',
        '    C := Brd.GetPcbComponentByRefDes(Ref);',
        '    If C = Nil Then Exit;',
        '    P := FindPad(C, PName);',
        '    If P = Nil Then',
        '    Begin',
        "        Fail(Ref + '-' + PName + ' pad is missing');",
        '        Exit;',
        '    End;',
        '    If NetOf(P) <> Net Then',
        "        Fail(Ref + '-' + PName + ' net is \"' + NetOf(P) + '\", expected \"' + Net + '\"');",
        'End;',
        '',
        'Procedure PreDesig(Ref : String; X, Y : Double);',
        'Var',
        '    C : IPCB_Component;',
        '    tx, ty : Double;',
        'Begin',
        '    C := Brd.GetPcbComponentByRefDes(Ref);',
        '    If C = Nil Then',
        '    Begin',
        "        Fail(Ref + ' is not on the board');",
        '        Exit;',
        '    End;',
        '    tx := CoordToMMs(C.Name.XLocation - Brd.XOrigin);',
        '    ty := CoordToMMs(C.Name.YLocation - Brd.YOrigin);',
        '    If (Abs(tx - X) > 0.002) Or (Abs(ty - Y) > 0.002) Then',
        "        Fail(Ref + ' designator is at ' + FmtXY(tx, ty) + ', not its pre-sync Fab B place ' + FmtXY(X, Y));",
        'End;',
        '',
        'Procedure PlaceAt(Ref : String; Bot : Boolean; Rot, X, Y : Double);',
        'Var',
        '    C : IPCB_Component;',
        'Begin',
        '    C := Brd.GetPcbComponentByRefDes(Ref);',
        '    If Bot Then',
        '    Begin',
        '        If C.Layer <> eBottomLayer Then',
        '        Begin',
        '            C.BeginModify;',
        '            C.Layer := eBottomLayer;',
        '            C.EndModify;',
        '        End;',
        '    End',
        '    Else',
        '    Begin',
        '        If C.Layer <> eTopLayer Then',
        '        Begin',
        '            C.BeginModify;',
        '            C.Layer := eTopLayer;',
        '            C.EndModify;',
        '        End;',
        '    End;',
        '    C.BeginModify;',
        '    C.Rotation := Rot;',
        '    C.EndModify;',
        '    C.BeginModify;',
        '    C.X := Brd.XOrigin + MMsToCoord(X);',
        '    C.Y := Brd.YOrigin + MMsToCoord(Y);',
        '    C.EndModify;',
        'End;',
        '',
        'Function PadAt(Ref, PName : String; X, Y : Double) : Boolean;',
        'Var',
        '    C : IPCB_Component;',
        '    P : IPCB_Pad;',
        'Begin',
        '    Result := False;',
        '    C := Brd.GetPcbComponentByRefDes(Ref);',
        '    If C = Nil Then Exit;',
        '    P := FindPad(C, PName);',
        '    If P = Nil Then Exit;',
        '    If (Abs(CoordToMMs(P.X - Brd.XOrigin) - X) <= 0.001) And (Abs(CoordToMMs(P.Y - Brd.YOrigin) - Y) <= 0.001) Then',
        '        Result := True;',
        'End;',
        '',
        '{ a two-pad resistor the ECO added: side, then the planned rotation (or +90/+180/+270 if the flip turned it),',
        '  then the origin; accepted only when both pads land within 0.001 mm of the no-PMOD pads }',
        'Procedure PlaceR(Ref : String; Bot : Boolean; Rot, X, Y, X1, Y1, X2, Y2 : Double);',
        'Var',
        '    k : Integer;',
        '    ok, ok1, ok2 : Boolean;',
        '    r : Double;',
        'Begin',
        '    ok := False;',
        '    k := 0;',
        '    While (Not ok) And (k < 4) Do',
        '    Begin',
        '        r := Rot + 90 * k;',
        '        While r >= 360 Do r := r - 360;',
        '        PlaceAt(Ref, Bot, r, X, Y);',
        "        ok1 := PadAt(Ref, '1', X1, Y1);",
        "        ok2 := PadAt(Ref, '2', X2, Y2);",
        '        ok := ok1 And ok2;',
        '        k := k + 1;',
        '    End;',
        '    If Not ok Then',
        "        Fail(Ref + ' pads do not land on the no-PMOD pads at any rotation')",
        '    Else',
        '    Begin',
        "        If k > 1 Then Info := Info + Ref + ' took rotation +' + IntToStr(90 * (k - 1)) + '; ';",
        '    End;',
        'End;',
        '',
        'Procedure VPad(Ref, PName : String; X, Y : Double);',
        'Begin',
        '    If PadAt(Ref, PName, X, Y) Then',
        '        NPadOk := NPadOk + 1',
        '    Else',
        "        Fail(Ref + '-' + PName + ' is not at ' + FmtXY(X, Y));",
        'End;',
        '',
        '{ designator: visibility as on the no-PMOD board; when the text is not at the no-PMOD place after the moves, set',
        '  manual auto-position and move it (no-PMOD NoPmodU2Label2.pas pattern) }',
        'Procedure Desig(Ref : String; NOn, COn : Boolean; X, Y, Rot : Double);',
        'Var',
        '    C : IPCB_Component;',
        '    T : IPCB_Text;',
        '    tx, ty : Double;',
        'Begin',
        '    C := Brd.GetPcbComponentByRefDes(Ref);',
        '    C.BeginModify;',
        '    C.NameOn := NOn;',
        '    C.CommentOn := COn;',
        '    C.EndModify;',
        '    T := C.Name;',
        '    tx := CoordToMMs(T.XLocation - Brd.XOrigin);',
        '    ty := CoordToMMs(T.YLocation - Brd.YOrigin);',
        '    If (Abs(tx - X) > 0.002) Or (Abs(ty - Y) > 0.002) Or (RotOff(T.Rotation, Rot) > 0.01) Then',
        '    Begin',
        '        C.BeginModify;',
        '        C.ChangeNameAutoposition(eAutoPos_Manual);',
        '        T.BeginModify;',
        '        T.MoveToXY(Brd.XOrigin + MMsToCoord(X), Brd.YOrigin + MMsToCoord(Y));',
        '        T.Rotation := Rot;',
        '        T.EndModify;',
        '        C.EndModify;',
        '        T.GraphicallyInvalidate;',
        "        Forced := Forced + Ref + ' ';",
        '    End;',
        '    T := C.Name;',
        '    tx := CoordToMMs(T.XLocation - Brd.XOrigin);',
        '    ty := CoordToMMs(T.YLocation - Brd.YOrigin);',
        '    If (Abs(tx - X) > 0.005) Or (Abs(ty - Y) > 0.005) Then',
        "        Fail(Ref + ' designator is at ' + FmtXY(tx, ty) + ', not ' + FmtXY(X, Y));",
        '    If C.NameOn <> NOn Then',
        "        Fail(Ref + ' designator visibility did not take');",
        'End;',
        '',
        'Procedure SyncPlace;',
        'Begin',
        '    Brd := SyncBoard;',
        '    If Brd = Nil Then Exit;',
        "    Bad := '';",
        '    NBad := 0;',
        "    Info := '';",
        "    Forced := '';",
        '    NPadOk := 0;',
        '',
        '    { ---- preconditions: nothing changes unless all of them hold ---- }']
    for ref in SWAP + MOVE:
        s, t = P[ref]['src'], P[ref]['tgt']
        if s['side'] != t['side']:
            raise SystemExit('%s changes side; PreComp mode 0 cannot express that' % ref)
        L.append("    PreComp('%s', '%s', %d, 0, %s, %s, %s, %s);" % (
            ref, s['pattern'], len(s['pads']), 'True' if t['side'] == 'Bottom' else 'False', f6(t['rot']),
            f6(t['x']), f6(t['y'])))
    for ref in NEW:
        s = P[ref]['src']
        L.append("    PreComp('%s', '%s', %d, 1, %s, 0, 0, 0);" % (ref, s['pattern'], len(s['pads']),
                                                                 'True' if s['side'] == 'Bottom' else 'False'))
    for ref in SWAP + NEW + MOVE:
        for name, x, y, net in (q[:4] for q in P[ref]['src']['pads']):
            L.append("    PreNet('%s', '%s', '%s');" % (ref, name, net))
    for pad, net in D['u3_dq']:
        L.append("    PreNet('U3', '%s', '%s');" % (pad, net))
    u1 = P['U1']['tgt']['desig']
    L.append("    PreDesig('U1', %s, %s);" % (f6(u1['x']), f6(u1['y'])))
    L += ['    If NBad > 0 Then',
          '    Begin',
          "        ShowMessage('Refusing: ' + IntToStr(NBad) + ' precondition(s) failed; NOTHING was changed.' + #13#10 + Bad);",
          '        Exit;',
          '    End;',
          '',
          '    { ---- moves ---- }',
          '    PCBServer.PreProcess;',
          '    Try']
    for ref in SWAP + MOVE:
        s = P[ref]['src']
        L.append("        PlaceAt('%s', %s, %s, %s, %s);" % (ref, 'True' if s['side'] == 'Bottom' else 'False', f6(s['rot']),
                                                         f6(s['x']), f6(s['y'])))
    for ref in NEW:
        s = P[ref]['src']
        pads = {p[0]: p for p in s['pads']}
        if set(pads) != {'1', '2'}:
            raise SystemExit('%s pads %s' % (ref, sorted(pads)))
        L.append("        PlaceR('%s', %s, %s, %s, %s, %s, %s, %s, %s);" % (
            ref, 'True' if s['side'] == 'Bottom' else 'False', f6(s['rot']), f6(s['x']), f6(s['y']),
            f6(pads['1'][1]), f6(pads['1'][2]), f6(pads['2'][1]), f6(pads['2'][2])))
    L.append('        { designators after every move: a move re-applies a component\'s auto-position }')
    for ref in SWAP + NEW + MOVE + DESIG_ONLY:
        s = P[ref]['src']
        L.append("        Desig('%s', %s, %s, %s, %s, %s);" % (
            ref, 'True' if s['name_on'] else 'False', 'True' if s['comment_on'] else 'False',
            f6(s['desig']['x']), f6(s['desig']['y']), f6(s['desig']['rot'])))
    L += ['    Finally',
          '        PCBServer.PostProcess;',
          '    End;',
          '    Brd.ViewManager_FullUpdate;',
          '',
          '    { ---- re-measure every pad of every moved part ---- }']
    for ref in SWAP + NEW + MOVE:
        for name, x, y, net in (q[:4] for q in P[ref]['src']['pads']):
            L.append("    VPad('%s', '%s', %s, %s);" % (ref, name, f6(x), f6(y)))
    L += ['    If NBad > 0 Then',
          "        ShowMessage('DO NOT SAVE: ' + IntToStr(NBad) + ' check(s) failed after the moves (' + IntToStr(NPadOk) + ' of %d pads at the no-PMOD place). Close the PcbDoc WITHOUT saving and reopen it.' + #13#10 + Bad + Info)" % npads,
          '    Else',
          "        ShowMessage('SyncPlace OK: %d parts placed, %d of %d pads within 0.001 mm of the no-PMOD board, ' +"
          % (len(SWAP + NEW + MOVE), npads, npads),
          "            '%d designators set (forced to manual: ' + Forced + '). ' + Info + 'Next: the copper script, then FabB_SyncRules. Save only after the copper script reports success.');"
          % len(SWAP + NEW + MOVE + DESIG_ONLY),
          'End;',
          '']
    # the OK message's pad count must agree with the VPad lines
    assert sum(1 for x in L if x.startswith("    VPad('")) == npads
    write_pas('FabB_SyncPlace', L)


def emit_rules(D):
    sr = D['src_rules']
    # the values come from the no-PMOD Rules6, so a drift there would show here
    want = {'ComponentClearance_X2': ("InComponent('X2')", 'All', '1.9685mil'),
            'ComponentClearance_R131R132': ("InComponent('R131')", "InComponent('R132')", '0mil')}
    for name, (s1, s2, gap) in want.items():
        r = sr[name]
        if (r['SCOPE1EXPRESSION'], r['SCOPE2EXPRESSION'], r['GAP'], r['VERTICALGAP']) != (s1, s2, gap, gap):
            raise SystemExit('no-PMOD %s is %s' % (name, r))
    m = sr['SolderMaskExpansion_U2']
    if (m['SCOPE1EXPRESSION'], m['SCOPE2EXPRESSION'], m['EXPANSION']) != ("InComponent('U2')", 'All', '1.378mil'):
        raise SystemExit('no-PMOD SolderMaskExpansion_U2 is %s' % m)
    volts = {}
    for name, r in sr.items():
        if r.get('RULEKIND') == 'SupplyNets':
            volts[r['SCOPE1EXPRESSION']] = float(r['VOLTAGE'])
    if sorted(volts) != sorted(SUPPLY_SCOPES):
        raise SystemExit('no-PMOD supply-net scopes %s' % sorted(volts))
    tsup = sorted(r['SCOPE1EXPRESSION'] for r in D['tgt_rules'].values() if r.get('RULEKIND') == 'SupplyNets')
    if tsup != sorted(SUPPLY_SCOPES):
        raise SystemExit('Fab B supply-net scopes %s' % tsup)
    if D['sdram_classes'] != ['SDRAM_DATA']:
        raise SystemExit('no-PMOD classes holding SDRAM-Dn: %s' % D['sdram_classes'])
    today = datetime.date.today().isoformat()
    L = ['{ FabB_SyncRules.pas -- GENERATED %s by tools/sync_altium_emit.py from tools/route/sync_altium/sync_data.json'
         % today,
         '  (the no-PMOD Rules6 / Classes6 at %s). Do not edit by hand. Run SyncRules with zulu_a7_fab_b.PcbDoc focused,'
         % D['source']['commit'],
         '  after FabB_SyncPlace and the copper script. Adds, as on the no-PMOD board:',
         "    ComponentClearance_R131R132  InComponent('R131') vs InComponent('R132'), 0 mm (created first -> priority 2)",
         "    ComponentClearance_X2        InComponent('X2') vs All, 0.05 mm, vertical 0.05 mm (created second -> priority 1)",
         "    SolderMaskExpansion_U2       InComponent('U2'), 0.035 mm, AnyNet, SameLayer (priority 1)",
         '  sets the Schematic Supply Nets voltages %s,' % ', '.join(
             '%s %g' % (s[7:-2], volts[s]) for s in SUPPLY_SCOPES),
         '  adds SDRAM-D0..SDRAM-D15 to net class SDRAM_DATA (the only class the no-PMOD board puts them in), and',
         "  invalidates U2's 65 pad mask caches so the new mask rule reaches them. Priority is read-only from scripts:",
         '  read Rules6 back after saving (tools/sync_altium_verify.py). Refuses, changing nothing, unless every',
         '  precondition holds. }',
         '',
         'Var',
         '    Brd  : IPCB_Board;',
         '    Bad  : String;',
         '    NBad : Integer;',
         '']
    L += guard_lines('SyncRules')
    L += [
        'Procedure Fail(S : String);',
        'Begin',
        '    NBad := NBad + 1;',
        '    If NBad <= 30 Then Bad := Bad + S + #13#10;',
        'End;',
        '',
        'Function NetByName(AName : String) : IPCB_Net;',
        'Var',
        '    It : IPCB_BoardIterator;',
        '    N  : IPCB_Net;',
        'Begin',
        '    Result := Nil;',
        '    It := Brd.BoardIterator_Create;',
        '    It.AddFilter_ObjectSet(MkSet(eNetObject));',
        '    It.AddFilter_LayerSet(AllLayers);',
        '    It.AddFilter_Method(eProcessAll);',
        '    N := It.FirstPCBObject;',
        '    While N <> Nil Do',
        '    Begin',
        '        If N.Name = AName Then Result := N;',
        '        N := It.NextPCBObject;',
        '    End;',
        '    Brd.BoardIterator_Destroy(It);',
        'End;',
        '',
        'Function RuleCount(AName : String) : Integer;',
        'Var',
        '    It : IPCB_BoardIterator;',
        '    R  : IPCB_Rule;',
        'Begin',
        '    Result := 0;',
        '    It := Brd.BoardIterator_Create;',
        '    It.AddFilter_ObjectSet(MkSet(eRuleObject));',
        '    It.AddFilter_LayerSet(AllLayers);',
        '    It.AddFilter_Method(eProcessAll);',
        '    R := It.FirstPCBObject;',
        '    While R <> Nil Do',
        '    Begin',
        '        If R.Name = AName Then Result := Result + 1;',
        '        R := It.NextPCBObject;',
        '    End;',
        '    Brd.BoardIterator_Destroy(It);',
        'End;',
        '',
        'Function FindRule(AName : String) : IPCB_Rule;',
        'Var',
        '    It : IPCB_BoardIterator;',
        '    R  : IPCB_Rule;',
        'Begin',
        '    Result := Nil;',
        '    It := Brd.BoardIterator_Create;',
        '    It.AddFilter_ObjectSet(MkSet(eRuleObject));',
        '    It.AddFilter_LayerSet(AllLayers);',
        '    It.AddFilter_Method(eProcessAll);',
        '    R := It.FirstPCBObject;',
        '    While R <> Nil Do',
        '    Begin',
        '        If R.Name = AName Then Result := R;',
        '        R := It.NextPCBObject;',
        '    End;',
        '    Brd.BoardIterator_Destroy(It);',
        'End;',
        '',
        '{ the expected voltage of a Schematic Supply Nets rule, from its scope; -1 = not one of the six }',
        'Function VoltFor(S : String) : Double;',
        'Begin',
        '    Result := -1;']
    first = True
    for s in SUPPLY_SCOPES:
        L.append("    %sIf S = '%s' Then Result := %s" % ('' if first else 'Else ', s.replace("'", "''"), repr(volts[s])))
        first = False
    L[-1] += ';'
    L += ['End;',
          '',
          'Function DataClass(Var N : Integer) : IPCB_ObjectClass;',
          'Var',
          '    It  : IPCB_BoardIterator;',
          '    Cls : IPCB_ObjectClass;',
          'Begin',
          '    Result := Nil;',
          '    N := 0;',
          '    It := Brd.BoardIterator_Create;',
          '    It.AddFilter_ObjectSet(MkSet(eClassObject));',
          '    It.AddFilter_LayerSet(AllLayers);',
          '    It.AddFilter_Method(eProcessAll);',
          '    Cls := It.FirstPCBObject;',
          '    While Cls <> Nil Do',
          '    Begin',
          '        If (Cls.MemberKind = eClassMemberKind_Net) And (Cls.Name = \'SDRAM_DATA\') Then',
          '        Begin',
          '            Result := Cls;',
          '            N := N + 1;',
          '        End;',
          '        Cls := It.NextPCBObject;',
          '    End;',
          '    Brd.BoardIterator_Destroy(It);',
          'End;',
          '',
          'Procedure AddCC(AName, S1, S2 : String; G : Double);',
          'Var',
          '    R : IPCB_Rule;',
          'Begin',
          '    R := PCBServer.PCBRuleFactory(eRule_ComponentClearance);',
          '    R.Name := AName;',
          '    R.Scope1Expression := S1;',
          '    R.Scope2Expression := S2;',
          '    R.Gap := MMsToCoord(G);',
          '    R.VerticalGap := MMsToCoord(G);',
          '    Brd.AddPCBObject(R);',
          'End;',
          '',
          'Procedure SyncRules;',
          'Var',
          '    It    : IPCB_BoardIterator;',
          '    R     : IPCB_Rule;',
          '    Cls   : IPCB_ObjectClass;',
          '    U2    : IPCB_Component;',
          '    GI    : IPCB_GroupIterator;',
          '    P     : IPCB_Pad;',
          '    Ch    : TPadCache;',
          '    nCls, nSup, nAdd, nHad, nCache, nPads, k : Integer;',
          '    Msg   : String;',
          '    v     : Double;',
          'Begin',
          '    Brd := SyncBoard;',
          '    If Brd = Nil Then Exit;',
          "    Bad := '';",
          '    NBad := 0;',
          '',
          '    { ---- preconditions ---- }']
    for name in NEW_RULES:
        L.append("    If RuleCount('%s') <> 0 Then Fail('rule %s already exists (run once only, on a board without it)');"
                 % (name, name))
    L += ["    If RuleCount('ComponentClearance') <> 1 Then Fail('the board-wide rule ComponentClearance is not there exactly once');",
          "    If RuleCount('SolderMaskExpansion') <> 1 Then Fail('the board-wide rule SolderMaskExpansion is not there exactly once');",
          "    If Brd.GetPcbComponentByRefDes('X2') = Nil Then Fail('X2 is not on the board');",
          "    If Brd.GetPcbComponentByRefDes('R131') = Nil Then Fail('R131 is not on the board (run FabB_SyncPlace first)');",
          "    If Brd.GetPcbComponentByRefDes('R132') = Nil Then Fail('R132 is not on the board (run FabB_SyncPlace first)');",
          "    U2 := Brd.GetPcbComponentByRefDes('U2');",
          "    If U2 = Nil Then Fail('U2 is not on the board')",
          '    Else',
          '    Begin',
          "        If U2.Pattern <> 'FT2232HQ-QFN64' Then Fail('U2 footprint is ' + U2.Pattern + ', expected FT2232HQ-QFN64');",
          '        nPads := 0;',
          '        GI := U2.GroupIterator_Create;',
          '        GI.AddFilter_ObjectSet(MkSet(ePadObject));',
          '        P := GI.FirstPCBObject;',
          '        While P <> Nil Do',
          '        Begin',
          '            nPads := nPads + 1;',
          '            P := GI.NextPCBObject;',
          '        End;',
          '        U2.GroupIterator_Destroy(GI);',
          "        If nPads <> 65 Then Fail('U2 has ' + IntToStr(nPads) + ' pads, expected 65');",
          '    End;',
          '    { exactly the six Schematic Supply Nets rules, one per expected scope }',
          '    nSup := 0;',
          '    It := Brd.BoardIterator_Create;',
          '    It.AddFilter_ObjectSet(MkSet(eRuleObject));',
          '    It.AddFilter_LayerSet(AllLayers);',
          '    It.AddFilter_Method(eProcessAll);',
          '    R := It.FirstPCBObject;',
          '    While R <> Nil Do',
          '    Begin',
          "        If Pos('Schematic Supply Nets', R.Name) = 1 Then",
          '        Begin',
          '            nSup := nSup + 1;',
          '            If VoltFor(R.Scope1Expression) < 0 Then',
          "                Fail('supply-net rule ' + R.Name + ' has an unexpected scope ' + R.Scope1Expression);",
          '        End;',
          '        R := It.NextPCBObject;',
          '    End;',
          '    Brd.BoardIterator_Destroy(It);',
          "    If nSup <> 6 Then Fail(IntToStr(nSup) + ' Schematic Supply Nets rules, expected 6');"]
    for s in SUPPLY_SCOPES:
        L += ['    k := 0;',
              '    It := Brd.BoardIterator_Create;',
              '    It.AddFilter_ObjectSet(MkSet(eRuleObject));',
              '    It.AddFilter_LayerSet(AllLayers);',
              '    It.AddFilter_Method(eProcessAll);',
              '    R := It.FirstPCBObject;',
              '    While R <> Nil Do',
              '    Begin',
              "        If Pos('Schematic Supply Nets', R.Name) = 1 Then",
              "            If R.Scope1Expression = '%s' Then k := k + 1;" % s.replace("'", "''"),
              '        R := It.NextPCBObject;',
              '    End;',
              '    Brd.BoardIterator_Destroy(It);',
              "    If k <> 1 Then Fail(IntToStr(k) + ' supply-net rules scoped %s, expected 1');" % s.replace("'", "''")]
    L += ['    Cls := DataClass(nCls);',
          "    If nCls <> 1 Then Fail(IntToStr(nCls) + ' net classes named SDRAM_DATA, expected 1');"]
    for n in SDRAM_NETS:
        L.append("    If NetByName('%s') = Nil Then Fail('net %s is not on the board (the ECO adds it)');" % (n, n))
    for k in range(16):
        L += ['    If nCls = 1 Then',
              "        If Not Cls.IsMember(NetByName('D%d')) Then Fail('SDRAM_DATA does not hold D%d (wrong class?)');" % (k, k)]
    L += ['    If NBad > 0 Then',
          '    Begin',
          "        ShowMessage('Refusing: ' + IntToStr(NBad) + ' precondition(s) failed; NOTHING was changed.' + #13#10 + Bad);",
          '        Exit;',
          '    End;',
          '',
          '    { ---- apply ---- }',
          "    Msg := '';",
          '    PCBServer.PreProcess;',
          '    Try',
          "        AddCC('ComponentClearance_R131R132', 'InComponent(''R131'')', 'InComponent(''R132'')', 0.0);",
          "        AddCC('ComponentClearance_X2', 'InComponent(''X2'')', 'All', 0.05);",
          '        R := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);',
          "        R.Name := 'SolderMaskExpansion_U2';",
          "        R.Scope1Expression := 'InComponent(''U2'')';",
          "        R.Scope2Expression := 'All';",
          '        R.Expansion := MMsToCoord(0.035);',
          '        R.NetScope := eNetScope_AnyNet;',
          '        R.LayerKind := eRuleLayerKind_SameLayer;',
          '        Brd.AddPCBObject(R);',
          '        { supply-net voltages }',
          '        It := Brd.BoardIterator_Create;',
          '        It.AddFilter_ObjectSet(MkSet(eRuleObject));',
          '        It.AddFilter_LayerSet(AllLayers);',
          '        It.AddFilter_Method(eProcessAll);',
          '        R := It.FirstPCBObject;',
          '        While R <> Nil Do',
          '        Begin',
          "            If Pos('Schematic Supply Nets', R.Name) = 1 Then",
          '            Begin',
          '                v := VoltFor(R.Scope1Expression);',
          '                Try',
          '                    R.BeginModify;',
          '                    R.Voltage := v;',
          '                    R.EndModify;',
          "                    Msg := Msg + '  ' + R.Scope1Expression + ' = ' + FloatToStr(R.Voltage) + ' V' + #13#10;",
          '                    If Abs(R.Voltage - v) > 0.0001 Then',
          "                        Fail(R.Name + ' voltage reads back ' + FloatToStr(R.Voltage));",
          '                Except',
          "                    Fail(R.Name + ': the voltage write was rejected');",
          '                End;',
          '            End;',
          '            R := It.NextPCBObject;',
          '        End;',
          '        Brd.BoardIterator_Destroy(It);',
          '        { net class }',
          '        nAdd := 0;',
          '        nHad := 0;']
    for n in SDRAM_NETS:
        L += ["        If Cls.IsMember(NetByName('%s')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('%s'); nAdd := nAdd + 1; End;"
              % (n, n)]
    for n in SDRAM_NETS:
        L.append("        If Not Cls.IsMember(NetByName('%s')) Then Fail('%s did not join SDRAM_DATA');" % (n, n))
    L += ['        { U2 pad mask caches, so SolderMaskExpansion_U2 reaches the pads (no-PMOD NoPmodU2MaskCache.pas) }',
          '        nCache := 0;',
          '        GI := U2.GroupIterator_Create;',
          '        GI.AddFilter_ObjectSet(MkSet(ePadObject));',
          '        P := GI.FirstPCBObject;',
          '        While P <> Nil Do',
          '        Begin',
          '            Ch := P.Cache;',
          '            Ch.SolderMaskExpansionValid := eCacheInvalid;',
          '            P.BeginModify;',
          '            P.Cache := Ch;',
          '            P.EndModify;',
          '            nCache := nCache + 1;',
          '            P := GI.NextPCBObject;',
          '        End;',
          '        U2.GroupIterator_Destroy(GI);',
          '    Finally',
          '        PCBServer.PostProcess;',
          '    End;',
          '    Brd.ViewManager_FullUpdate;',
          '',
          '    { ---- read back ---- }',
          "    R := FindRule('ComponentClearance_X2');",
          "    If R = Nil Then Fail('ComponentClearance_X2 is not on the board after adding it')",
          "    Else If (Abs(CoordToMMs(R.Gap) - 0.05) > 0.0001) Or (Abs(CoordToMMs(R.VerticalGap) - 0.05) > 0.0001) Then Fail('ComponentClearance_X2 gap reads ' + FloatToStr(CoordToMMs(R.Gap)));",
          "    R := FindRule('ComponentClearance_R131R132');",
          "    If R = Nil Then Fail('ComponentClearance_R131R132 is not on the board after adding it')",
          "    Else If (Abs(CoordToMMs(R.Gap)) > 0.0001) Or (Abs(CoordToMMs(R.VerticalGap)) > 0.0001) Then Fail('ComponentClearance_R131R132 gap reads ' + FloatToStr(CoordToMMs(R.Gap)));",
          "    R := FindRule('SolderMaskExpansion_U2');",
          "    If R = Nil Then Fail('SolderMaskExpansion_U2 is not on the board after adding it')",
          "    Else If Abs(CoordToMMs(R.Expansion) - 0.035) > 0.0001 Then Fail('SolderMaskExpansion_U2 expansion reads ' + FloatToStr(CoordToMMs(R.Expansion)));",
          "    If nCache <> 65 Then Fail(IntToStr(nCache) + ' U2 pad mask caches invalidated, expected 65');",
          '    If NBad > 0 Then',
          "        ShowMessage('DO NOT SAVE: ' + IntToStr(NBad) + ' read-back check(s) failed. Close the PcbDoc WITHOUT saving and reopen it.' + #13#10 + Bad)",
          '    Else',
          "        ShowMessage('SyncRules OK: added ComponentClearance_R131R132 (0 mm), ComponentClearance_X2 (0.05 mm), ' +",
          "            'SolderMaskExpansion_U2 (0.035 mm); supply-net voltages:' + #13#10 + Msg + 'SDRAM_DATA: ' + IntToStr(nAdd) + ' SDRAM-Dn added, ' +",
          "            IntToStr(nHad) + ' already members (16 in all); U2 mask caches invalidated: ' + IntToStr(nCache) + ' of 65. Next: FabB_SyncBodies.');",
          'End;',
          '']
    write_pas('FabB_SyncRules', L)


def emit_repour():
    today = datetime.date.today().isoformat()
    L = ['{ FabB_SyncRepour.pas -- GENERATED %s by tools/sync_altium_emit.py. Rebuilds the two plane polygons of' % today,
         '  zulu_a7_fab_b.PcbDoc (L2_GND_PLANE, L5_VCC3V3_PLANE) after the sync copper, as no-PMOD NoPmod_Repour.pas does',
         '  (same API names). Refuses unless the board has exactly 2 polygons. Run SyncRepour after reopening the board',
         '  that tools/mark_microvias.py edited; then rebuild the ratsnest (FabB_RebuildConnR2) and run the DRC. }',
         '',
         'Var',
         '    Brd : IPCB_Board;',
         '']
    L += guard_lines('SyncRepour')
    L += ['Procedure SyncRepour;',
          'Var',
          '    It : IPCB_BoardIterator;',
          '    P  : IPCB_Polygon;',
          '    Ls : TInterfaceList;',
          '    i  : Integer;',
          'Begin',
          '    Brd := SyncBoard;',
          '    If Brd = Nil Then Exit;',
          '    Ls := TInterfaceList.Create;',
          '    It := Brd.BoardIterator_Create;',
          '    It.AddFilter_ObjectSet(MkSet(ePolyObject));',
          '    It.AddFilter_LayerSet(AllLayers);',
          '    It.AddFilter_Method(eProcessAll);',
          '    P := It.FirstPCBObject;',
          '    While P <> Nil Do',
          '    Begin',
          '        Ls.Add(P);',
          '        P := It.NextPCBObject;',
          '    End;',
          '    Brd.BoardIterator_Destroy(It);',
          '    If Ls.Count <> 2 Then',
          '    Begin',
          "        ShowMessage('Refusing: ' + IntToStr(Ls.Count) + ' polygons on the board, expected the 2 planes; nothing changed.');",
          '        Ls.Free;',
          '        Exit;',
          '    End;',
          '    PCBServer.SystemOptions.PolygonRepour := eAlwaysRepour;',
          '    For i := 0 To Ls.Count - 1 Do',
          '    Begin',
          '        P := Ls.Items[i];',
          '        P.Rebuild;',
          '    End;',
          '    Brd.ViewManager_FullUpdate;',
          "    ShowMessage('SyncRepour OK: repoured ' + IntToStr(Ls.Count) + ' polygons. Next: FabB_RebuildConnR2, save, DRC.');",
          '    Ls.Free;',
          'End;',
          '']
    write_pas('FabB_SyncRepour', L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--refresh', action='store_true', help='re-extract sync_data.json from both boards')
    a = ap.parse_args()
    if a.refresh or not os.path.isfile(DATA):
        D = extract()
    else:
        D = json.load(open(DATA, encoding='utf-8'))
        print('using', os.path.relpath(DATA, ROOT), 'md5', R.md5(DATA))
    emit_place(D)
    emit_rules(D)
    emit_repour()


if __name__ == '__main__':
    main()
