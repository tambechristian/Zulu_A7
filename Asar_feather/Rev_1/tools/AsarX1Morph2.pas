{ AsarX1Morph2.pas -- 2026-11-17 (AsarX1Morph.pas with the edge-line track taken from whatever layer is left: the
  Molex copy's file layer 72 did not match eMechanical16 on Altium 26.11.1). X1 becomes an Amphenol ICC 10118193-0001LF micro-USB B receptacle (flanged, 5 SMT
  contacts, 4 SMT shell pads, 2 plated-slot shell legs; drawing 10118193 Rev D; LCSC C132562). Chosen by workflow
  wf_6e5873ab-abc (four candidate families, fit on Asar, judge re-check) so the side-entry X4's west leg is cleared.
  New primitives cannot be scripted on Altium 26.11.1 (SendMessageToRobots crashes in a library), so this MORPHS a panel
  copy of MOLEX-105017-0001 renamed to AMPHENOL-10118193-0001LF (13 pads, 12 tracks, 5 arcs) by moving what exists.
  Frame: origin on the board edge (the maker's PCB END line) on the pin-3 (D+) axis, +x into the board, +y toward pin 1;
  rotation 0 = mouth facing -x. Pad names keep the X1 schematic pin designators:
    1..5  (4.125, +1.30 .. -1.30) 1.35 x 0.40       VBUS, D-, D+, ID, GND
    MP1 (3.90, +3.20) / MP2 (3.90, -3.20) 1.40 x 1.60   rear shell SMT pads
    MP3 (1.45, +1.20) / MP4 (1.45, -1.20) 1.90 x 1.90   front shell SMT pads under the body
    MH1 (1.45, +3.30) / MH2 (1.45, -3.30)  plated slot 0.50 x 1.20 along x, obround land 1.71 x 1.01 (0.255 ring)
  MS1 / MS2 (the Molex shell legs) are parked at (8, +2) / (8, -2) for deletion by hand in the editor.
  Mech3 body x -0.70..4.35, y +-3.45; Mech7 flange x -1.30..-0.70, y +-3.93; Mech16 board edge x 0; Mech2 courtyard
  x -1.40..4.95, y +-4.15; Mech7 pin-1 dot (5.25, +1.30). Height 2.7 mm.
  Run MorphAsarX1b with asar_feather.PcbLib focused, delete MS1/MS2, then File > Save. }

Var
    OffX, OffY : TCoord;

Function QX(V : Double) : TCoord;
Begin
    Result := OffX + MMsToCoord(V);
End;

Function QY(V : Double) : TCoord;
Begin
    Result := OffY + MMsToCoord(V);
End;

Procedure SmdPad(P : IPCB_Pad; X, Y, DX, DY : Double);
Begin
    P.BeginModify;
    P.X := QX(X); P.Y := QY(Y);
    P.TopShape := eRectangular; P.MidShape := eRectangular; P.BotShape := eRectangular;
    P.TopXSize := MMsToCoord(DX); P.TopYSize := MMsToCoord(DY);
    P.MidXSize := MMsToCoord(DX); P.MidYSize := MMsToCoord(DY);
    P.BotXSize := MMsToCoord(DX); P.BotYSize := MMsToCoord(DY);
    P.EndModify;
End;

Procedure SlotPad(P : IPCB_Pad; X, Y : Double);
Begin
    P.BeginModify;
    P.X := QX(X); P.Y := QY(Y);
    P.TopShape := eRounded; P.MidShape := eRounded; P.BotShape := eRounded;
    P.TopXSize := MMsToCoord(1.71); P.TopYSize := MMsToCoord(1.01);
    P.MidXSize := MMsToCoord(1.71); P.MidYSize := MMsToCoord(1.01);
    P.BotXSize := MMsToCoord(1.71); P.BotYSize := MMsToCoord(1.01);
    P.HoleSize := MMsToCoord(0.50);
    P.Plated := True;
    P.HoleType := eSlotHole;
    P.HoleWidth := MMsToCoord(1.20);
    P.HoleRotation := 0;
    P.EndModify;
End;

Procedure Park(P : IPCB_Pad; X, Y : Double);
Begin
    P.BeginModify;
    P.X := QX(X); P.Y := QY(Y);
    P.EndModify;
End;

Procedure Seg(T : IPCB_Track; X1, Y1, X2, Y2 : Double);
Begin
    T.BeginModify;
    T.X1 := QX(X1); T.Y1 := QY(Y1);
    T.X2 := QX(X2); T.Y2 := QY(Y2);
    T.EndModify;
End;

Procedure Dot(A : IPCB_Arc; X, Y, R : Double);
Begin
    A.BeginModify;
    A.XCenter := QX(X); A.YCenter := QY(Y);
    A.Radius := MMsToCoord(R);
    A.EndModify;
End;

Procedure MorphAsarX1b;
Var
    Lib : IPCB_Library;
    It : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI : IPCB_GroupIterator;
    O : IPCB_Primitive;
    P, P1, P3 : IPCB_Pad;
    Pads, L58, L59, L63, L72, A58, A63 : TInterfaceList;
    T : IPCB_Track;
    A : IPCB_Arc;
    Fn, nm : String;
    i, nDone : Integer;
Begin
    Lib := PCBServer.GetCurrentPCBLibrary;
    If Lib = Nil Then Begin ShowMessage('Refusing: no PCB library is focused.'); Exit; End;
    Fn := Lib.Board.FileName;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbLib', Fn) = 0 Then Begin ShowMessage('Refusing: the focused library is ' + Fn); Exit; End;
    Hit := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = 'AMPHENOL-10118193-0001LF' Then Hit := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Hit = Nil Then Begin ShowMessage('AMPHENOL-10118193-0001LF not found (copy MOLEX-105017-0001 and rename it first); nothing changed.'); Exit; End;

    Pads := TInterfaceList.Create;
    P1 := Nil; P3 := Nil;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        P := O;
        Pads.Add(P);
        If P.Name = '1' Then P1 := P;
        If P.Name = '3' Then P3 := P;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (Pads.Count <> 13) Or (P1 = Nil) Or (P3 = Nil) Then Begin ShowMessage('Refusing: expected the 13-pad Molex copy, found ' + IntToStr(Pads.Count) + ' pads.'); Pads.Free; Exit; End;
    { still the Molex copy? pad 1 is 1.3 mm from pad 3 along x and its pad is 0.4 x 1.35 }
    If (Abs(CoordToMMs(P1.X - P3.X) - 1.3) > 0.002) Or (Abs(CoordToMMs(P1.TopYSize) - 1.35) > 0.002) Then
    Begin ShowMessage('Refusing: the pads are not where the Molex copy has them (already morphed?).'); Pads.Free; Exit; End;
    { Molex pad 3 sits on its origin; the new origin is 4.125 mm behind pin 3 }
    OffX := P3.X - MMsToCoord(4.125);
    OffY := P3.Y;

    L58 := TInterfaceList.Create; L59 := TInterfaceList.Create; L63 := TInterfaceList.Create; L72 := TInterfaceList.Create;
    A58 := TInterfaceList.Create; A63 := TInterfaceList.Create;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        T := O;
        If T.Layer = eMechanical2 Then L58.Add(T);
        If T.Layer = eMechanical3 Then L59.Add(T);
        If T.Layer = eMechanical7 Then L63.Add(T);
        If (T.Layer <> eMechanical2) And (T.Layer <> eMechanical3) And (T.Layer <> eMechanical7) Then L72.Add(T);
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eArcObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        A := O;
        If A.Layer = eMechanical2 Then A58.Add(A);
        If A.Layer = eMechanical7 Then A63.Add(A);
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (L58.Count <> 4) Or (L59.Count <> 4) Or (L63.Count <> 3) Or (L72.Count <> 1) Or (A58.Count <> 4) Or (A63.Count <> 1) Then
    Begin
        ShowMessage('Refusing: mechanical primitives differ from the Molex copy (' + IntToStr(L58.Count) + '/' + IntToStr(L59.Count) + '/' +
            IntToStr(L63.Count) + '/' + IntToStr(L72.Count) + ' tracks, ' + IntToStr(A58.Count) + '/' + IntToStr(A63.Count) + ' arcs).');
        Pads.Free; Exit;
    End;

    nDone := 0;
    For i := 0 To Pads.Count - 1 Do
    Begin
        P := Pads.Items[i];
        nm := P.Name;
        If nm = '1' Then Begin SmdPad(P, 4.125, 1.30, 1.35, 0.40); nDone := nDone + 1; End;
        If nm = '2' Then Begin SmdPad(P, 4.125, 0.65, 1.35, 0.40); nDone := nDone + 1; End;
        If nm = '3' Then Begin SmdPad(P, 4.125, 0.00, 1.35, 0.40); nDone := nDone + 1; End;
        If nm = '4' Then Begin SmdPad(P, 4.125, -0.65, 1.35, 0.40); nDone := nDone + 1; End;
        If nm = '5' Then Begin SmdPad(P, 4.125, -1.30, 1.35, 0.40); nDone := nDone + 1; End;
        If nm = 'MP1' Then Begin SmdPad(P, 3.90, 3.20, 1.40, 1.60); nDone := nDone + 1; End;
        If nm = 'MP2' Then Begin SmdPad(P, 3.90, -3.20, 1.40, 1.60); nDone := nDone + 1; End;
        If nm = 'MP3' Then Begin SmdPad(P, 1.45, 1.20, 1.90, 1.90); nDone := nDone + 1; End;
        If nm = 'MP4' Then Begin SmdPad(P, 1.45, -1.20, 1.90, 1.90); nDone := nDone + 1; End;
        If nm = 'MH1' Then Begin SlotPad(P, 1.45, 3.30); nDone := nDone + 1; End;
        If nm = 'MH2' Then Begin SlotPad(P, 1.45, -3.30); nDone := nDone + 1; End;
        If nm = 'MS1' Then Begin Park(P, 8.0, 2.0); nDone := nDone + 1; End;
        If nm = 'MS2' Then Begin Park(P, 8.0, -2.0); nDone := nDone + 1; End;
    End;

    Seg(L59.Items[0], -0.70, -3.45, 4.35, -3.45);
    Seg(L59.Items[1], 4.35, -3.45, 4.35, 3.45);
    Seg(L59.Items[2], 4.35, 3.45, -0.70, 3.45);
    Seg(L59.Items[3], -0.70, 3.45, -0.70, -3.45);
    Seg(L63.Items[0], -1.30, -3.93, -1.30, 3.93);
    Seg(L63.Items[1], -1.30, 3.93, -0.70, 3.93);
    Seg(L63.Items[2], -1.30, -3.93, -0.70, -3.93);
    Seg(L72.Items[0], 0.00, -4.20, 0.00, 4.20);
    Seg(L58.Items[0], -1.40, -4.15, 4.95, -4.15);
    Seg(L58.Items[1], 4.95, -4.15, 4.95, 4.15);
    Seg(L58.Items[2], 4.95, 4.15, -1.40, 4.15);
    Seg(L58.Items[3], -1.40, 4.15, -1.40, -4.15);
    Dot(A63.Items[0], 5.25, 1.30, 0.15);
    Dot(A58.Items[0], 1.10, 3.30, 0.25);
    Dot(A58.Items[1], 1.80, 3.30, 0.25);
    Dot(A58.Items[2], 1.10, -3.30, 0.25);
    Dot(A58.Items[3], 1.80, -3.30, 0.25);

    Hit.Description := 'Amphenol 10118193-0001LF micro-USB B, flanged, SMT + 2 plated slot legs; origin board edge on pin-3 axis, mouth -x';
    Hit.Height := MMsToCoord(2.7);
    Lib.CurrentComponent := Hit;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('AMPHENOL-10118193-0001LF morphed: ' + IntToStr(nDone) + ' of 13 pads (MS1/MS2 parked at x 8 for deletion), 12 tracks, 5 arcs. Delete MS1 and MS2, then File > Save.');
    Pads.Free; L58.Free; L59.Free; L63.Free; L72.Free; A58.Free; A63.Free;
End;
