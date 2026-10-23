"""The six new Feather footprints as data, plus the DelphiScript that draws them into zulu_feather.PcbLib.

Millimetres, origin at the body centre, Altium axes (Y up), seen from the top. Sources:
  QFN-64-9X9-P0.5-EP4.35   FT2232H datasheet v2.21 Figure 8.1 (9.00 body, 0.50 pitch, lead 0.25 x 0.40,
                           exposed pad 4.35). Land 0.28 x 0.75 from 4.05 to 4.80 mm off centre (0.05 heel,
                           0.30 toe); EP land 4.20, left without a net (note 3: not internally grounded).
  FBGA-54-8X8-P0.8         AS4C32M16SB datasheet Rev 1.2 Figure 44 (8.00 body, e 0.80, ball 0.45) and
                           Figure 1.1 (A1 top left, columns 4-6 empty). 0.40 round lands.
  WSON-8-6X5-P1.27         W25Q128JV Rev M section 10.3 (D 6.00 across the pins, E 5.00, L 0.60, b 0.40,
                           EP 3.40 x 4.30). Land 1.00 x 0.50 from 2.35 to 3.35; EP land 3.30 x 4.20, no net
                           ("can be left floating").
  USB-C-HRO-TYPE-C-31-M-12 KiCad 10 Connector_USB footprint for the same part (pad centres, slot sizes),
                           Y flipped; mouth at -Y, body front at Y = -3.65. Shell lands widened to 1.10 for a
                           0.25 ring (PCBWay normal). Pad names carry the symbol pins: VBUS 1, D- 2, D+ 3,
                           CC1 4, CC2 MH1, GND 5 and MH2, shell MP1-MP4, SBU1/SBU2 unconnected.
  FEATHER-28               Adafruit Feather spec: 2.0 x 0.9 in board, 16-pin strip centred 1.0 in from the
                           USB end along the bottom edge, 12-pin strip centred 1.2 in along the top edge,
                           strips 0.8 in apart. Origin = board centre. 1.70 lands, 1.00 drill, pad 1 square;
                           four 2.50 mm non-plated holes 2.54 mm in from each corner.
  TP-1X03-SMD              three 1.00 round SMD test pads on 1.27 mm pitch (JTAG, bottom side).

    python tools/footprints.py        writes tools/footprints.json and tools/FeatherFootprints.pas
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SILK_W = 0.15


def smd(name, x, y, dx, dy, shape='rect'):
    return {'name': name, 'x': x, 'y': y, 'dx': dx, 'dy': dy, 'shape': shape, 'drill': 0}


def tht(name, x, y, dx, dy, drill, shape='round', slot=0, plated=True):
    return {'name': name, 'x': x, 'y': y, 'dx': dx, 'dy': dy, 'shape': shape, 'drill': drill,
            'slot': slot, 'plated': plated}


def qfn64():
    pads, c, w, ln = [], 4.425, 0.28, 0.75
    for k in range(16):
        o = 3.75 - 0.5 * k
        pads.append(smd(str(1 + k), -c, o, ln, w))            # left, top to bottom
        pads.append(smd(str(17 + k), -o, -c, w, ln))          # bottom, left to right
        pads.append(smd(str(33 + k), c, -o, ln, w))           # right, bottom to top
        pads.append(smd(str(49 + k), o, c, w, ln))            # top, right to left
    pads.append(smd('EP', 0, 0, 4.20, 4.20))
    s = 4.6
    silk = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            silk += [(sx * s, sy * s, sx * 4.15, sy * s), (sx * s, sy * s, sx * s, sy * 4.15)]
    silk.append((-5.25, 3.75, -5.25, 3.25))                  # pin-1 tick beside pad 1
    return {'name': 'QFN-64-9X9-P0.5-EP4.35', 'description': 'FT2232HQ QFN-64 9x9 mm 0.5 mm pitch, EP 4.35 mm',
            'pads': pads, 'silk': silk}


def fbga54():
    pads = []
    for r, row in enumerate('ABCDEFGHJ'):
        for col in (1, 2, 3, 7, 8, 9):
            pads.append(smd('%s%d' % (row, col), (col - 5) * 0.8, (4 - r) * 0.8, 0.40, 0.40, 'round'))
    b = 4.15
    silk = [(-b, b, b, b), (b, b, b, -b), (b, -b, -b, -b), (-b, -b, -b, b), (-b, b - 0.8, -b + 0.8, b)]
    return {'name': 'FBGA-54-8X8-P0.8', 'description': 'SDRAM 54-ball FBGA 8x8 mm 0.8 mm pitch (JEDEC x16)',
            'pads': pads, 'silk': silk}


def wson8():
    ys = [1.905, 0.635, -0.635, -1.905]
    pads = [smd(str(i + 1), -2.85, y, 1.00, 0.50) for i, y in enumerate(ys)]
    pads += [smd(str(i + 5), 2.85, -y, 1.00, 0.50) for i, y in enumerate(ys)]
    pads.append(smd('EP', 0, 0, 3.30, 4.20))
    silk = [(-2.2, 2.65, 2.2, 2.65), (-2.2, -2.65, 2.2, -2.65), (-3.6, 2.45, -3.6, 1.95)]
    return {'name': 'WSON-8-6X5-P1.27', 'description': 'SPI flash WSON-8 6x5 mm 1.27 mm pitch, EP no net',
            'pads': pads, 'silk': silk}


def usbc():
    y = 4.045
    pads = [
        smd('5', -3.25, y, 0.6, 1.45), smd('1', -2.45, y, 0.6, 1.45),       # A1/B12 GND, A4/B9 VBUS
        smd('4', -1.25, y, 0.3, 1.45), smd('2', 0.25, y, 0.3, 1.45),        # A5 CC1, A7 D-
        smd('3', -0.25, y, 0.3, 1.45), smd('SBU1', 1.25, y, 0.3, 1.45),     # A6 D+, A8 SBU1
        smd('1', 2.45, y, 0.6, 1.45), smd('MH2', 3.25, y, 0.6, 1.45),       # A9/B4 VBUS, A12/B1 GND
        smd('MH1', 1.75, y, 0.3, 1.45), smd('3', 0.75, y, 0.3, 1.45),       # B5 CC2, B6 D+
        smd('2', -0.75, y, 0.3, 1.45), smd('SBU2', -1.75, y, 0.3, 1.45),    # B7 D-, B8 SBU2
        tht('MP1', -4.32, 3.13, 1.10, 2.20, 0.60, 'round', slot=1.70),
        tht('MP2', 4.32, 3.13, 1.10, 2.20, 0.60, 'round', slot=1.70),
        tht('MP3', -4.32, -1.05, 1.10, 1.70, 0.60, 'round', slot=1.20),
        tht('MP4', 4.32, -1.05, 1.10, 1.70, 0.60, 'round', slot=1.20),
        tht('', -2.89, 2.60, 0.65, 0.65, 0.65, plated=False),
        tht('', 2.89, 2.60, 0.65, 0.65, 0.65, plated=False),
    ]
    return {'name': 'USB-C-HRO-TYPE-C-31-M-12', 'description': 'USB-C receptacle USB 2.0, HRO TYPE-C-31-M-12; '
            'board edge at Y = -3.65', 'pads': pads, 'silk': [(-4.47, -3.65, 4.47, -3.65)]}


def feather28():
    pads = []
    for k in range(16):
        pads.append(tht(str(1 + k), -19.05 + 2.54 * k, -10.16, 1.70, 1.70, 1.00, 'rect' if k == 0 else 'round'))
    for k in range(12):
        pads.append(tht(str(17 + k), -8.89 + 2.54 * k, 10.16, 1.70, 1.70, 1.00))
    for x in (-22.86, 22.86):
        for y in (-8.89, 8.89):
            pads.append(tht('', x, y, 2.50, 2.50, 2.50, plated=False))
    return {'name': 'FEATHER-28', 'description': 'Feather 16 + 12 pin 0.1 in headers and 4 corner holes; origin = '
            'centre of the 50.8 x 22.86 mm board, USB end at -X', 'pads': pads, 'silk': []}


def tp3():
    return {'name': 'TP-1X03-SMD', 'description': 'Three 1.0 mm SMD test pads, 1.27 mm pitch',
            'pads': [smd(str(i + 1), (i - 1) * 1.27, 0, 1.0, 1.0, 'round') for i in range(3)],
            'silk': [(-2.2, 0.4, -2.2, -0.4)]}


FOOTPRINTS = [tp3(), qfn64(), fbga54(), wson8(), usbc(), feather28()]

PAS_HEAD = """{ FeatherFootprints.pas -- GENERATED by tools/footprints.py; do not edit by hand.
  Draws the Feather footprints into zulu_feather.PcbLib. Focus that library, then run
  FeatherFpCanary (draws only TP-1X03-SMD), check it, then BuildFeatherFootprints (the other five).
  Refuses to draw a footprint whose name already exists. Library pad coordinates are footprint-relative. }

Function FeatherLibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\\Zulu_feather\\Zulu_feather.PrjPcb\\zulu_feather.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_feather\\Zulu_feather.PrjPcb\\zulu_feather.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function FpExists(Lib : IPCB_Library; Name : String) : Boolean;
Var
    It : IPCB_LibraryIterator;
    Fp : IPCB_LibComponent;
Begin
    Result := False;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = Name Then Result := True;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
End;

Function NewFp(Lib : IPCB_Library; Name, Descr : String) : IPCB_LibComponent;
Begin
    Result := Nil;
    If FpExists(Lib, Name) Then
    Begin
        ShowMessage(Name + ' already exists: not drawn.');
        Exit;
    End;
    Result := PCBServer.CreatePCBLibComp;
    Result.Name := Name;
    Result.Description := Descr;
    Lib.RegisterComponent(Result);
End;

Procedure AddPad(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY, Drill, Slot : Double; Shape : Integer; Plated : Boolean);
Var
    P : IPCB_Pad;
Begin
    P := PCBServer.PCBObjectFactory(ePadObject, eNoDimension, eCreate_Default);
    P.Name := Name;
    P.X := MMsToCoord(X);
    P.Y := MMsToCoord(Y);
    P.TopShape := Shape; P.MidShape := Shape; P.BotShape := Shape;
    P.TopXSize := MMsToCoord(DX); P.TopYSize := MMsToCoord(DY);
    P.MidXSize := MMsToCoord(DX); P.MidYSize := MMsToCoord(DY);
    P.BotXSize := MMsToCoord(DX); P.BotYSize := MMsToCoord(DY);
    If Drill > 0 Then
    Begin
        P.Layer := eMultiLayer;
        P.HoleSize := MMsToCoord(Drill);
        P.Plated := Plated;
        If Slot > 0 Then
        Begin
            P.HoleType := eSlotHole;
            P.HoleWidth := MMsToCoord(Slot);
            P.HoleRotation := 90;
        End;
    End
    Else
    Begin
        P.Layer := eTopLayer;
        P.HoleSize := 0;
    End;
    Fp.AddPCBObject(P);
    PCBServer.SendMessageToRobots(Fp.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, P.I_ObjectAddress);
End;

Procedure AddSilk(Fp : IPCB_LibComponent; X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1); T.Y1 := MMsToCoord(Y1);
    T.X2 := MMsToCoord(X2); T.Y2 := MMsToCoord(Y2);
    T.Width := MMsToCoord(%(silk_w)s);
    T.Layer := eTopOverlay;
    Fp.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Fp.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
End;
"""


def shape(p):
    return {'rect': 'eRectangular', 'round': 'eRounded'}[p['shape']]


def emit_fp(fp):
    lines = ['Procedure Draw_%s(Lib : IPCB_Library);' % fp['name'].replace('-', '_').replace('.', '_'),
             'Var', '    Fp : IPCB_LibComponent;', 'Begin',
             "    Fp := NewFp(Lib, '%s', '%s');" % (fp['name'], fp['description']),
             '    If Fp = Nil Then Exit;']
    for p in fp['pads']:
        lines.append("    AddPad(Fp, '%s', %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %s, %s);" % (
            p['name'], p['x'], p['y'], p['dx'], p['dy'], p['drill'], p.get('slot', 0), shape(p),
            'True' if p.get('plated', True) else 'False'))
    for s in fp['silk']:
        lines.append('    AddSilk(Fp, %.4f, %.4f, %.4f, %.4f);' % s)
    lines.append('    Lib.CurrentComponent := Fp;')
    lines.append('End;')
    return '\n'.join(lines)


def main():
    json.dump(FOOTPRINTS, open(os.path.join(HERE, 'footprints.json'), 'w'), indent=1)
    out = [PAS_HEAD % {'silk_w': '%.3f' % SILK_W}]
    out += [emit_fp(fp) for fp in FOOTPRINTS]
    names = [fp['name'].replace('-', '_').replace('.', '_') for fp in FOOTPRINTS]
    out.append('Procedure FeatherFpCanary;\nVar\n    Lib : IPCB_Library;\nBegin\n    Lib := FeatherLibOrNil;\n'
               '    If Lib = Nil Then Exit;\n    Draw_%s(Lib);\n    Lib.Board.ViewManager_FullUpdate;\n'
               "    ShowMessage('Canary drew TP-1X03-SMD. Check it, then run BuildFeatherFootprints.');\nEnd;" % names[0])
    body = '\n'.join('    Draw_%s(Lib);' % n for n in names[1:])
    out.append('Procedure BuildFeatherFootprints;\nVar\n    Lib : IPCB_Library;\nBegin\n    Lib := FeatherLibOrNil;\n'
               '    If Lib = Nil Then Exit;\n%s\n    Lib.Board.ViewManager_FullUpdate;\n'
               "    ShowMessage('Drew %d footprints. Save zulu_feather.PcbLib.');\nEnd;" % (body, len(names) - 1))
    pas = '\n\n'.join(out) + '\n'
    open(os.path.join(HERE, 'FeatherFootprints.pas'), 'w', newline='\r\n').write(pas)
    open(os.path.join(HERE, 'FeatherFootprints.PrjScr'), 'w', newline='\r\n').write(
        '[Design]\nVersion=1.0\n\n[Document1]\nDocumentPath=FeatherFootprints.pas\n')
    for fp in FOOTPRINTS:
        print('%-26s %3d pads %2d silk' % (fp['name'], len(fp['pads']), len(fp['silk'])))


if __name__ == '__main__':
    main()
