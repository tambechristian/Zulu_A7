{ AsarX4Legs.pas -- 2026-11-16. Puts the S2B-PH-SM4-TB housing's two rear legs into footprint JST-S2B-PH-SM4-TB.
  AsarX4Morph.pas drew the housing as 7.9 x 6.0 mm, but the housing has side legs at |x| 3.15..3.95 that reach 7.6 mm
  behind the face (JST ePH p.2 connector outline, KiCad JST_PH_S2B-PH-SM4-TB F.Fab). Footprint frame: origin at the housing
  centre, face y = +3.0, so the legs end at y = -4.6.
  No new primitives (SendMessageToRobots crashes the library script engine on Altium 26.11.1): the 4 Mechanical 3 and
  8 Mechanical 7 tracks are re-used. Mechanical 3 becomes the full 8-segment outline (4 of the Mechanical 7 tracks move
  to Mechanical 3); the other 4 Mechanical 7 tracks outline the two legs' rear ends and the front.
  Refuses unless the footprint still has the 7.9 x 6.0 outline (one Mechanical 3 track at y -3.0 spanning x -3.95..3.95).
  Run AddAsarX4Legs with asar_feather.PcbLib focused, then File > Save, then Update PCB With JST-S2B-PH-SM4-TB. }

Var
    OffX, OffY : TCoord;

Function LX(V : Double) : TCoord;
Begin
    Result := OffX + MMsToCoord(V);
End;

Function LY(V : Double) : TCoord;
Begin
    Result := OffY + MMsToCoord(V);
End;

Procedure SetSeg(T : IPCB_Track; L : TLayer; X1, Y1, X2, Y2 : Double);
Begin
    T.BeginModify;
    T.Layer := L;
    T.X1 := LX(X1); T.Y1 := LY(Y1);
    T.X2 := LX(X2); T.Y2 := LY(Y2);
    T.EndModify;
End;

Procedure AddAsarX4Legs;
Var
    Lib : IPCB_Library;
    It : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI : IPCB_GroupIterator;
    O : IPCB_Primitive;
    P, PM1, PM2 : IPCB_Pad;
    T : IPCB_Track;
    M3, M7 : TInterfaceList;
    Fn : String;
    i, nBack : Integer;
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
        If Fp.Name = 'JST-S2B-PH-SM4-TB' Then Hit := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Hit = Nil Then Begin ShowMessage('JST-S2B-PH-SM4-TB not found; nothing changed.'); Exit; End;
    PM1 := Nil; PM2 := Nil;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        P := O;
        If P.Name = 'MP1' Then PM1 := P;
        If P.Name = 'MP2' Then PM2 := P;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (PM1 = Nil) Or (PM2 = Nil) Then Begin ShowMessage('Refusing: MP1/MP2 not found.'); Exit; End;
    { MP1/MP2 sit at x -3.35 / +3.35, y +1.5 in the footprint frame }
    OffX := (PM1.X + PM2.X) Div 2;
    OffY := (PM1.Y + PM2.Y) Div 2 - MMsToCoord(1.5);
    M3 := TInterfaceList.Create;
    M7 := TInterfaceList.Create;
    nBack := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        T := O;
        If T.Layer = eMechanical3 Then
        Begin
            M3.Add(T);
            If (Abs(CoordToMMs(T.Y1 - OffY) + 3.0) < 0.002) And (Abs(CoordToMMs(T.Y2 - OffY) + 3.0) < 0.002) And
               (Abs(Abs(CoordToMMs(T.X1 - T.X2)) - 7.9) < 0.002) Then nBack := nBack + 1;
        End;
        If T.Layer = eMechanical7 Then M7.Add(T);
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (M3.Count <> 4) Or (M7.Count <> 8) Or (nBack <> 1) Then
    Begin
        ShowMessage('Refusing: expected the 7.9 x 6.0 outline (4 Mech3 incl. one full back line, 8 Mech7); found ' + IntToStr(M3.Count) + ' / ' + IntToStr(M7.Count) + ' / ' + IntToStr(nBack) + '.');
        M3.Free; M7.Free; Exit;
    End;
    { Mechanical 3: full housing outline with the rear legs (8 segments) }
    SetSeg(M3.Items[0], eMechanical3, -3.95, 3.00, 3.95, 3.00);
    SetSeg(M3.Items[1], eMechanical3, 3.95, 3.00, 3.95, -4.60);
    SetSeg(M3.Items[2], eMechanical3, 3.95, -4.60, 3.15, -4.60);
    SetSeg(M3.Items[3], eMechanical3, 3.15, -4.60, 3.15, -3.00);
    SetSeg(M7.Items[0], eMechanical3, 3.15, -3.00, -3.15, -3.00);
    SetSeg(M7.Items[1], eMechanical3, -3.15, -3.00, -3.15, -4.60);
    SetSeg(M7.Items[2], eMechanical3, -3.15, -4.60, -3.95, -4.60);
    SetSeg(M7.Items[3], eMechanical3, -3.95, -4.60, -3.95, 3.00);
    { Mechanical 7: the leg rear ends, the outer sides behind the tabs, and the front between the tabs }
    SetSeg(M7.Items[4], eMechanical7, -3.95, -4.60, -3.15, -4.60);
    SetSeg(M7.Items[5], eMechanical7, 3.15, -4.60, 3.95, -4.60);
    SetSeg(M7.Items[6], eMechanical7, -3.95, -4.60, -3.95, -0.45);
    SetSeg(M7.Items[7], eMechanical7, 3.95, -4.60, 3.95, -0.45);
    M3.Free; M7.Free;
    Lib.CurrentComponent := Hit;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('JST-S2B-PH-SM4-TB: rear legs added (Mech3 8-segment outline to y -4.6). File > Save, then Update PCB With JST-S2B-PH-SM4-TB.');
End;
