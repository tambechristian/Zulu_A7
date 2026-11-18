{ AsarX4Morph.pas -- 2026-11-16. Turns the library copy "JST-S2B-PH-SM4-TB" (made in the PCB Library panel by Copy /
  Paste of JST-B2B-PH-SM4-TB, then renamed) into the side-entry land. New primitives could not be scripted on Altium
  26.11.1: SendMessageToRobots after the first pad crashes ScriptingSystem.DLL (AsarX4Footprint.pas, ...3.pas) and without
  it the pads are not saved (...4.pas). Editing primitives that already exist needs no registration.
  Land = JST ePH catalogue p.2, side entry (minimum land); mouth toward +y, origin at the housing centre (face y = +3.0):
    pads 1, 2   1.0 x 3.5 at x +1.0 / -1.0, y -4.25      MP1, MP2   1.5 x 3.4 at x -3.35 / +3.35, y +1.5
  Pin 1 (battery +) is the EAST pad. Mechanical 3 (4 tracks): housing 7.9 x 6.0. Mechanical 7 (8 tracks): the housing
  outline broken at the pads (6 segments, the last two repeated). Mechanical 7 arc: pin-1 dot at (+1.0, -6.45).
  Coordinates are written relative to the copy's own origin, measured from MP1/MP2 (B2B: x -3.4 / +3.4, y 0).
  Run MorphAsarX4 with asar_feather.PcbLib focused, then File > Save. }

Var
    OffX, OffY : TCoord;

Function MX(V : Double) : TCoord;
Begin
    Result := OffX + MMsToCoord(V);
End;

Function MY(V : Double) : TCoord;
Begin
    Result := OffY + MMsToCoord(V);
End;

Procedure SetPad(P : IPCB_Pad; X, Y, DX, DY : Double);
Begin
    P.BeginModify;
    P.X := MX(X);
    P.Y := MY(Y);
    P.TopXSize := MMsToCoord(DX); P.TopYSize := MMsToCoord(DY);
    P.MidXSize := MMsToCoord(DX); P.MidYSize := MMsToCoord(DY);
    P.BotXSize := MMsToCoord(DX); P.BotYSize := MMsToCoord(DY);
    P.EndModify;
End;

Procedure SetTrack(T : IPCB_Track; X1, Y1, X2, Y2 : Double);
Begin
    T.BeginModify;
    T.X1 := MX(X1); T.Y1 := MY(Y1);
    T.X2 := MX(X2); T.Y2 := MY(Y2);
    T.EndModify;
End;

Procedure MorphAsarX4;
Var
    Lib : IPCB_Library;
    It : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI : IPCB_GroupIterator;
    O : IPCB_Primitive;
    P, P1, P2, PM1, PM2 : IPCB_Pad;
    T : IPCB_Track;
    A : IPCB_Arc;
    M3, M7 : TInterfaceList;
    nArc : Integer;
    Fn : String;
Begin
    Lib := PCBServer.GetCurrentPCBLibrary;
    If Lib = Nil Then Begin ShowMessage('Refusing: no PCB library is focused.'); Exit; End;
    Fn := Lib.Board.FileName;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbLib', Fn) = 0 Then
    Begin ShowMessage('Refusing: the focused library is ' + Fn); Exit; End;
    Hit := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = 'JST-S2B-PH-SM4-TB' Then Hit := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Hit = Nil Then Begin ShowMessage('JST-S2B-PH-SM4-TB not found; nothing changed.'); Exit; End;

    P1 := Nil; P2 := Nil; PM1 := Nil; PM2 := Nil;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        P := O;
        If P.Name = '1' Then P1 := P;
        If P.Name = '2' Then P2 := P;
        If P.Name = 'MP1' Then PM1 := P;
        If P.Name = 'MP2' Then PM2 := P;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (P1 = Nil) Or (P2 = Nil) Or (PM1 = Nil) Or (PM2 = Nil) Then Begin ShowMessage('Refusing: pads 1/2/MP1/MP2 not all found.'); Exit; End;
    { the copy is still the B2B land: MP1/MP2 at x -3.4 / +3.4, y 0, so their midpoint is the origin }
    If Abs(CoordToMMs(PM2.X - PM1.X) - 6.8) > 0.002 Then Begin ShowMessage('Refusing: MP1-MP2 are not 6.8 mm apart; already morphed?'); Exit; End;
    OffX := (PM1.X + PM2.X) Div 2;
    OffY := (PM1.Y + PM2.Y) Div 2;

    M3 := TInterfaceList.Create;
    M7 := TInterfaceList.Create;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        T := O;
        If T.Layer = eMechanical3 Then M3.Add(T);
        If T.Layer = eMechanical7 Then M7.Add(T);
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (M3.Count <> 4) Or (M7.Count <> 8) Then
    Begin
        ShowMessage('Refusing: expected 4 Mechanical 3 and 8 Mechanical 7 tracks, found ' + IntToStr(M3.Count) + ' and ' + IntToStr(M7.Count));
        M3.Free; M7.Free; Exit;
    End;

    SetPad(P1, 1.00, -4.25, 1.00, 3.50);
    SetPad(P2, -1.00, -4.25, 1.00, 3.50);
    SetPad(PM1, -3.35, 1.50, 1.50, 3.40);
    SetPad(PM2, 3.35, 1.50, 1.50, 3.40);

    SetTrack(M3.Items[0], -3.95, -3.00, 3.95, -3.00);
    SetTrack(M3.Items[1], 3.95, -3.00, 3.95, 3.00);
    SetTrack(M3.Items[2], 3.95, 3.00, -3.95, 3.00);
    SetTrack(M3.Items[3], -3.95, 3.00, -3.95, -3.00);
    SetTrack(M7.Items[0], -3.95, -3.00, -1.75, -3.00);
    SetTrack(M7.Items[1], -0.25, -3.00, 0.25, -3.00);
    SetTrack(M7.Items[2], 1.75, -3.00, 3.95, -3.00);
    SetTrack(M7.Items[3], 3.95, -3.00, 3.95, -0.45);
    SetTrack(M7.Items[4], -3.95, -3.00, -3.95, -0.45);
    SetTrack(M7.Items[5], -2.35, 3.00, 2.35, 3.00);
    SetTrack(M7.Items[6], -3.95, -3.00, -1.75, -3.00);
    SetTrack(M7.Items[7], 1.75, -3.00, 3.95, -3.00);
    M3.Free; M7.Free;

    nArc := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eArcObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        A := O;
        A.BeginModify;
        A.XCenter := MX(1.00);
        A.YCenter := MY(-6.45);
        A.EndModify;
        nArc := nArc + 1;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);

    Hit.Description := 'JST PH 2.0 mm 2-pin side-entry SMT header S2B-PH-SM4-TB; JST ePH land; origin at housing centre, mouth +y, pin 1 east';
    Hit.Height := MMsToCoord(5.5);
    Lib.CurrentComponent := Hit;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('JST-S2B-PH-SM4-TB morphed: 4 pads, 4 + 8 mechanical tracks, ' + IntToStr(nArc) + ' arc (expect 1). File > Save the library.');
End;
