Procedure SelectStage13HdiProbe;
Var
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    V   : IPCB_Via;
    N   : String;
    C   : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    C := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        V.Selected := False;
        N := '';
        If V.Net <> Nil Then N := V.Net.Name;
        If (N = 'CHAN0') And
           (Abs(CoordToMMs(V.X) - 2.5) < 0.001) And
           (Abs(CoordToMMs(V.Y) - 2.0) < 0.001) And
           (V.LowLayer = eTopLayer) And
           (V.HighLayer = eInternalPlane1) Then
        Begin
            V.Selected := True;
            C := C + 1;
        End;
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Selected ' + IntToStr(C) + ' Top-to-L2 CHAN0 probe via(s).');
End;
