Var Brd : IPCB_Board; ox, oy : Integer; Msg : String; Bad : Integer;

Function C(v : Double) : Integer;
Begin
    Result := MMsToCoord(v);
End;

Function FindTrack(NetName : String; L : TLayer; X1, Y1, X2, Y2 : Double) : IPCB_Track;
Var It : IPCB_BoardIterator; T : IPCB_Track; nm : String; n : Integer;
Begin
    Result := Nil; n := 0;
    It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eTrackObject)); It.AddFilter_LayerSet(MkSet(L)); It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        nm := ''; If T.Net <> Nil Then nm := T.Net.Name;
        If (nm = NetName) And
           (((Abs(T.X1 - ox - C(X1)) < 30) And (Abs(T.Y1 - oy - C(Y1)) < 30) And (Abs(T.X2 - ox - C(X2)) < 30) And (Abs(T.Y2 - oy - C(Y2)) < 30)) Or
            ((Abs(T.X2 - ox - C(X1)) < 30) And (Abs(T.Y2 - oy - C(Y1)) < 30) And (Abs(T.X1 - ox - C(X2)) < 30) And (Abs(T.Y1 - oy - C(Y2)) < 30))) Then
        Begin Result := T; n := n + 1; End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 1 Then Begin Result := Nil; Bad := Bad + 1; Msg := Msg + 'track ' + NetName + ' found ' + IntToStr(n) + #13; End;
End;

Procedure FabBFinalTouch;
Var T1, T2, T3, T4, S1, S2 : IPCB_Track; V : IPCB_Via; It : IPCB_BoardIterator; O : IPCB_Via; nv : Integer; Cm : IPCB_Component; i : Integer;
    Names : Array[0..2] Of String; Dx : Array[0..2] Of Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit;
    If Pos('zulu_a7_fab_b.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus zulu_a7_fab_b.PcbDoc'); Exit; End;
    ox := Brd.XOrigin; oy := Brd.YOrigin; Msg := ''; Bad := 0;
    T1 := FindTrack('VCC1V0', eBottomLayer, 1.27, 23.05, 15.3, 23.05);
    T2 := FindTrack('VCC1V8', eMidLayer1, 0.5, 23.05, 6.35, 23.05);
    T3 := FindTrack('VBATT', eTopLayer, 12.7, 2.3, 13.3, 2.5);
    T4 := FindTrack('VBATT', eTopLayer, 13.3, 2.5, 15.1, 2.5);
    S1 := FindTrack('', eBottomOverlay, 7.35, 20.075, 7.65, 20.075);
    S2 := FindTrack('', eBottomOverlay, 7.2, 11.75, 7.5, 11.75);
    V := Nil; nv := 0;
    It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If (O.Net <> Nil) And (O.Net.Name = 'GND') And (Abs(O.X - ox - C(9.8)) < 30) And (Abs(O.Y - oy - C(2.58)) < 30) Then Begin V := O; nv := nv + 1; End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If nv <> 1 Then Begin Bad := Bad + 1; Msg := Msg + 'GND via found ' + IntToStr(nv) + #13; End;
    Names[0] := 'C78'; Dx[0] := -0.01; Names[1] := 'C80'; Dx[1] := 0.01; Names[2] := 'R103'; Dx[2] := -0.01;
    For i := 0 To 2 Do
        If Brd.GetPcbComponentByRefDes(Names[i]) = Nil Then Begin Bad := Bad + 1; Msg := Msg + 'no ' + Names[i] + #13; End;
    If (S1 <> Nil) And ((Not S1.InComponent) Or (S1.Component.Name.Text <> 'U7')) Then Begin Bad := Bad + 1; Msg := Msg + 'S1 not U7 silk' + #13; End;
    If (S2 <> Nil) And ((Not S2.InComponent) Or (S2.Component.Name.Text <> 'U8')) Then Begin Bad := Bad + 1; Msg := Msg + 'S2 not U8 silk' + #13; End;
    If Bad > 0 Then Begin ShowMessage('Refusing, nothing changed:' + #13 + Msg); Exit; End;
    PCBServer.PreProcess;
    T1.BeginModify; T1.X1 := ox + C(1.27); T1.Y1 := oy + C(23.05); T1.X2 := ox + C(14.525); T1.Y2 := oy + C(23.05); T1.EndModify;
    T2.BeginModify; T2.X1 := ox + C(3.81); T2.Y1 := oy + C(23.05); T2.X2 := ox + C(6.35); T2.Y2 := oy + C(23.05); T2.EndModify;
    Brd.RemovePCBObject(T3); Brd.RemovePCBObject(T4); Brd.RemovePCBObject(V);
    Cm := S1.Component; Cm.RemovePCBObject(S1); Brd.RemovePCBObject(S1);
    Cm := S2.Component; Cm.RemovePCBObject(S2); Brd.RemovePCBObject(S2);
    For i := 0 To 2 Do
    Begin
        Cm := Brd.GetPcbComponentByRefDes(Names[i]);
        Cm.BeginModify; Cm.MoveByXY(C(Dx[i]), 0); Cm.EndModify;
    End;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Final touch done: 2 stubs trimmed, 2 VBATT stubs + GND via removed, U7/U8 silk dashes removed, C78/C80/R103 nudged 0.01 mm. Save, DRC.');
End;
