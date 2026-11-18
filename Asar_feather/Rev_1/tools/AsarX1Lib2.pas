{ AsarX1Lib2.pas -- 2026-11-17, fixes to footprint AMPHENOL-10118193-0001LF from the review (wf_3b983b44-cc8):
  F2/C4  MH1/MH2 were full-stack pads left from the Molex copy: L2 got the 1.71 x 1.01 obround but L3/L4/L5 kept
         1.45 mm rounds (0.125 mm ring at the 1.20 mm slot ends, VCC3V3 plane 0.20 mm from the slot wall).
         -> simple pad mode, 1.71 x 1.01 obround on every copper layer (0.255 ring everywhere).
  M1     the courtyard rectangle sat on Mechanical 2, which this board names 'Route Tool Path' (router kind)
         -> moved to Mechanical 7, the courtyard layer of the other top-side parts.
  F3     the four Mechanical 2 slot-end arcs kept the Molex angles (half circles opening toward +-y)
         -> Mechanical 3 (X1's body layer), turned to cap the slots along x (left caps 90..270, right 270..90).
  F1     description notes the slot-land deviation from the drawing (1.60 x 0.90) and why.
  Refuses unless the footprint still has 11 pads, 4 Mechanical 2 tracks and 4 Mechanical 2 arcs.
  Run FixAsarX1Lib with asar_feather.PcbLib focused, then File > Save, then update X1 on the board from the library. }

Procedure FixAsarX1Lib;
Var
    Lib : IPCB_Library;
    It : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI : IPCB_GroupIterator;
    O : IPCB_Primitive;
    P, P3 : IPCB_Pad;
    Slots, Tr, Ar : TInterfaceList;
    T : IPCB_Track;
    A : IPCB_Arc;
    i, nPads : Integer;
    Fn : String;
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
    If Hit = Nil Then Begin ShowMessage('AMPHENOL-10118193-0001LF not found; nothing changed.'); Exit; End;
    Slots := TInterfaceList.Create; Tr := TInterfaceList.Create; Ar := TInterfaceList.Create;
    nPads := 0; P3 := Nil;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject, eTrackObject, eArcObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        If O.ObjectId = ePadObject Then
        Begin
            P := O; nPads := nPads + 1;
            If (P.Name = 'MH1') Or (P.Name = 'MH2') Then Slots.Add(P);
            If P.Name = '3' Then P3 := P;
        End
        Else If O.ObjectId = eTrackObject Then
        Begin
            T := O;
            If T.Layer = eMechanical2 Then Tr.Add(T);
        End
        Else
        Begin
            A := O;
            If A.Layer = eMechanical2 Then Ar.Add(A);
        End;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (nPads <> 11) Or (Slots.Count <> 2) Or (P3 = Nil) Or (Tr.Count <> 4) Or (Ar.Count <> 4) Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(nPads) + ' pads (11), ' + IntToStr(Slots.Count) + ' slot pads (2), ' +
            IntToStr(Tr.Count) + ' Mech2 tracks (4), ' + IntToStr(Ar.Count) + ' Mech2 arcs (4); nothing changed.');
        Slots.Free; Tr.Free; Ar.Free; Exit;
    End;
    For i := 0 To Slots.Count - 1 Do
    Begin
        P := Slots.Items[i];
        P.BeginModify;
        P.Mode := ePadMode_Simple;
        P.TopShape := eRounded; P.MidShape := eRounded; P.BotShape := eRounded;
        P.TopXSize := MMsToCoord(1.71); P.TopYSize := MMsToCoord(1.01);
        P.MidXSize := MMsToCoord(1.71); P.MidYSize := MMsToCoord(1.01);
        P.BotXSize := MMsToCoord(1.71); P.BotYSize := MMsToCoord(1.01);
        P.EndModify;
    End;
    For i := 0 To Tr.Count - 1 Do
    Begin
        T := Tr.Items[i];
        T.BeginModify;
        T.Layer := eMechanical7;
        T.EndModify;
    End;
    For i := 0 To Ar.Count - 1 Do
    Begin
        A := Ar.Items[i];
        A.BeginModify;
        A.Layer := eMechanical3;
        { slot centres are 2.675 mm behind pin 3; the left cap centre is 0.35 mm further out }
        If A.XCenter < P3.X - MMsToCoord(2.675) Then
        Begin
            A.StartAngle := 90; A.EndAngle := 270;
        End
        Else
        Begin
            A.StartAngle := 270; A.EndAngle := 90;
        End;
        A.EndModify;
    End;
    Hit.Description := 'Amphenol 10118193-0001LF micro-USB B; origin pin 3, mouth -x; slot lands 1.71x1.01 (drawing 1.60x0.90) for a 0.255 ring';
    Lib.CurrentComponent := Hit;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('AMPHENOL-10118193-0001LF: MH1/MH2 simple 1.71 x 1.01 on all layers, courtyard to Mech 7, slot caps to Mech 3. File > Save.');
    Slots.Free; Tr.Free; Ar.Free;
End;
