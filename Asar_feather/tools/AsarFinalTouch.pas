Var Brd : IPCB_Board; ox, oy : Integer; Msg : String; Bad : Integer;

Function C(v : Double) : Integer;
Begin
    Result := MMsToCoord(v);
End;

Function NetOf(O : IPCB_Primitive) : String;
Begin
    Result := '';
    If O.Net <> Nil Then Result := O.Net.Name;
End;

Function FindVia(NetName : String; X, Y : Double; Lo, Hi : TLayer) : IPCB_Via;
Var It : IPCB_BoardIterator; V : IPCB_Via; n : Integer;
Begin
    Result := Nil; n := 0;
    It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        If (NetOf(V) = NetName) And (Abs(V.X - ox - C(X)) < 30) And (Abs(V.Y - oy - C(Y)) < 30) And (V.LowLayer = Lo) And (V.HighLayer = Hi) Then Begin Result := V; n := n + 1; End;
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 1 Then Begin Result := Nil; Bad := Bad + 1; Msg := Msg + 'via ' + NetName + ' ' + FloatToStr(X) + ',' + FloatToStr(Y) + ' found ' + IntToStr(n) + #13; End;
End;

Function FindTrack(NetName : String; L : TLayer; X1, Y1, X2, Y2 : Double) : IPCB_Track;
Var It : IPCB_BoardIterator; T : IPCB_Track; n : Integer;
Begin
    Result := Nil; n := 0;
    It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eTrackObject)); It.AddFilter_LayerSet(MkSet(L)); It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (NetOf(T) = NetName) And
           (((Abs(T.X1 - ox - C(X1)) < 30) And (Abs(T.Y1 - oy - C(Y1)) < 30) And (Abs(T.X2 - ox - C(X2)) < 30) And (Abs(T.Y2 - oy - C(Y2)) < 30)) Or
            ((Abs(T.X2 - ox - C(X1)) < 30) And (Abs(T.Y2 - oy - C(Y1)) < 30) And (Abs(T.X1 - ox - C(X2)) < 30) And (Abs(T.Y1 - oy - C(Y2)) < 30))) Then
        Begin Result := T; n := n + 1; End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 1 Then Begin Result := Nil; Bad := Bad + 1; Msg := Msg + 'track ' + NetName + ' found ' + IntToStr(n) + #13; End;
End;

Procedure AsarFinalTouch;
Var DV, DT, UV : TInterfaceList; V : IPCB_Via; T : IPCB_Track; Cm : IPCB_Component; i : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit;
    If Pos('asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus asar_feather.PcbDoc'); Exit; End;
    ox := Brd.XOrigin; oy := Brd.YOrigin; Msg := ''; Bad := 0;
    DV := TInterfaceList.Create; DT := TInterfaceList.Create; UV := TInterfaceList.Create;
    V := FindVia('GND', 0.7, 4.375, eTopLayer, eBottomLayer); If V <> Nil Then DV.Add(V);
    V := FindVia('GND', 25.9, 4.075, eTopLayer, eBottomLayer); If V <> Nil Then DV.Add(V);
    V := FindVia('GND', 26.7, 2.675, eTopLayer, eBottomLayer); If V <> Nil Then DV.Add(V);
    V := FindVia('GND', 5.275, 5.025, eTopLayer, eBottomLayer); If V <> Nil Then DV.Add(V);
    V := FindVia('VBATT', 2.375, 5.275, eTopLayer, eBottomLayer); If V <> Nil Then DV.Add(V);
    V := FindVia('VCC1V0', 28.325, 3.475, eMidLayer2, eMidLayer4); If V <> Nil Then DV.Add(V);
    V := FindVia('VCC1V0', 28.325, 3.475, eMidLayer4, eBottomLayer); If V <> Nil Then DV.Add(V);
    T := FindTrack('VBATT', eBottomLayer, 2.375, 5.275, 2.4, 5.175); If T <> Nil Then DT.Add(T);
    T := FindTrack('VCC1V8', eBottomLayer, 27.025, 5.125, 27.6, 4.875); If T <> Nil Then DT.Add(T);
    T := FindTrack('PWR_FB2', eMidLayer2, 9.525, 13.95, 9.525, 14.575); If T <> Nil Then DT.Add(T);
    V := FindVia('USB5V0', 7.9, 13.88, eTopLayer, eMidLayer3); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 7.9, 13.88, eMidLayer3, eMidLayer1); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 7.9, 13.88, eMidLayer1, eMidLayer2); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 8.29, 8.98, eTopLayer, eMidLayer3); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 8.29, 8.98, eMidLayer3, eMidLayer1); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 8.29, 8.98, eMidLayer1, eMidLayer2); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 18.4, 20.525, eTopLayer, eMidLayer3); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 18.4, 20.525, eMidLayer3, eMidLayer1); If V <> Nil Then UV.Add(V);
    V := FindVia('USB5V0', 15.2, 16.7, eMidLayer1, eMidLayer2); If V <> Nil Then UV.Add(V);
    If Brd.GetPcbComponentByRefDes('L8') = Nil Then Begin Bad := Bad + 1; Msg := Msg + 'no L8' + #13; End;
    If Brd.GetPcbComponentByRefDes('C80') = Nil Then Begin Bad := Bad + 1; Msg := Msg + 'no C80' + #13; End;
    If Brd.GetPcbComponentByRefDes('C163') = Nil Then Begin Bad := Bad + 1; Msg := Msg + 'no C163' + #13; End;
    If Brd.GetPcbComponentByRefDes('C82') = Nil Then Begin Bad := Bad + 1; Msg := Msg + 'no C82' + #13; End;
    If Bad > 0 Then Begin ShowMessage('Refusing, nothing changed:' + #13 + Msg); Exit; End;
    PCBServer.PreProcess;
    For i := 0 To DT.Count - 1 Do Brd.RemovePCBObject(DT.Items[i]);
    For i := 0 To DV.Count - 1 Do Brd.RemovePCBObject(DV.Items[i]);
    V := UV.Items[0]; V.BeginModify; V.Size := C(0.3); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[1]; V.BeginModify; V.Size := C(0.3); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[2]; V.BeginModify; V.Size := C(0.27); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[3]; V.BeginModify; V.Size := C(0.3); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[4]; V.BeginModify; V.Size := C(0.3); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[5]; V.BeginModify; V.Size := C(0.27); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[6]; V.BeginModify; V.Size := C(0.3); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[7]; V.BeginModify; V.Size := C(0.3); V.HoleSize := C(0.15); V.EndModify;
    V := UV.Items[8]; V.BeginModify; V.Size := C(0.27); V.HoleSize := C(0.15); V.EndModify;
    Cm := Brd.GetPcbComponentByRefDes('L8'); Cm.BeginModify; Cm.MoveByXY(C(0), C(-0.01)); Cm.EndModify;
    Cm := Brd.GetPcbComponentByRefDes('C80'); Cm.BeginModify; Cm.MoveByXY(C(0.01), C(0)); Cm.EndModify;
    Cm := Brd.GetPcbComponentByRefDes('C163'); Cm.BeginModify; Cm.MoveByXY(C(0.02), C(0)); Cm.EndModify;
    Cm := Brd.GetPcbComponentByRefDes('C82'); Cm.BeginModify; Cm.MoveByXY(C(0.0025), C(0)); Cm.EndModify;
    PCBServer.PostProcess; Brd.ViewManager_FullUpdate;
    ShowMessage('Asar final touch: removed ' + IntToStr(DT.Count) + ' tracks, ' + IntToStr(DV.Count) + ' vias; resized ' + IntToStr(UV.Count) + ' USB5V0 vias; nudged L8 C80 C163 C82.');
End;
