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

Function NetByName(AName : String) : IPCB_Net;
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    Result := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = AName Then Result := N;
        N := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure AsarFinalTouch2;
Var DV, DT : TInterfaceList; V : IPCB_Via; T : IPCB_Track; N : IPCB_Net; i : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit;
    If Pos('asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus asar_feather.PcbDoc'); Exit; End;
    ox := Brd.XOrigin; oy := Brd.YOrigin; Msg := ''; Bad := 0;
    DV := TInterfaceList.Create; DT := TInterfaceList.Create;
    V := FindVia('VCC1V8', 25.2, 6.875, eMidLayer2, eMidLayer4); If V <> Nil Then DV.Add(V);
    V := FindVia('VCC1V8', 25.2, 6.875, eMidLayer4, eBottomLayer); If V <> Nil Then DV.Add(V);
    V := FindVia('VCC1V8', 25.825, 7.05, eMidLayer2, eMidLayer4); If V <> Nil Then DV.Add(V);
    V := FindVia('VCC1V8', 25.825, 7.05, eMidLayer4, eBottomLayer); If V <> Nil Then DV.Add(V);
    T := FindTrack('GND', eBottomLayer, 0.7, 4.375, 0.7, 4.4); If T <> Nil Then DT.Add(T);
    T := FindTrack('GND', eBottomLayer, 25.9, 4.075, 25.9, 4.1); If T <> Nil Then DT.Add(T);
    T := FindTrack('GND', eBottomLayer, 26.7, 2.675, 26.7, 2.7); If T <> Nil Then DT.Add(T);
    T := FindTrack('GND', eBottomLayer, 5.25, 5.025, 5.275, 5.025); If T <> Nil Then DT.Add(T);
    T := FindTrack('VCC1V0', eMidLayer2, 25.775, 3.55, 28.325, 3.475); If T <> Nil Then DT.Add(T);
    T := FindTrack('VCC1V0', eBottomLayer, 28.325, 3.475, 28.4, 3.475); If T <> Nil Then DT.Add(T);
    T := FindTrack('VCC1V8', eBottomLayer, 25.2, 6.875, 27.025, 5.125); If T <> Nil Then DT.Add(T);
    T := FindTrack('VCC1V8', eMidLayer2, 25.2, 6.875, 25.825, 7.05); If T <> Nil Then DT.Add(T);
    T := FindTrack('VCC1V8', eBottomLayer, 25.825, 7.05, 26.325, 8.775); If T <> Nil Then DT.Add(T);
    N := NetByName('PWR_FB2'); If N = Nil Then Begin Bad := Bad + 1; Msg := Msg + 'no PWR_FB2' + #13; End;
    If Bad > 0 Then Begin ShowMessage('Refusing, nothing changed:' + #13 + Msg); Exit; End;
    PCBServer.PreProcess;
    For i := 0 To DT.Count - 1 Do Brd.RemovePCBObject(DT.Items[i]);
    For i := 0 To DV.Count - 1 Do Brd.RemovePCBObject(DV.Items[i]);
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := ox + C(9.525); T.Y1 := oy + C(14.475); T.X2 := ox + C(9.525); T.Y2 := oy + C(14.575); T.Width := C(0.0762); T.Layer := eMidLayer2;
    T.Net := N; Brd.AddPCBObject(T); N.AddPCBObject(T);
    PCBServer.PostProcess; Brd.ViewManager_FullUpdate;
    ShowMessage('Asar final touch 2: removed ' + IntToStr(DT.Count) + ' tracks, ' + IntToStr(DV.Count) + ' vias; restored PWR_FB2 link.');
End;
