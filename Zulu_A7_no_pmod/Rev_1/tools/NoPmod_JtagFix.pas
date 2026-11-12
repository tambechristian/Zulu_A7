{ NoPmod_JtagFix.pas -- 2026-11-08. Fixes the DRC findings after JP3/JP4 went on the board: JP3 x +0.01 mm (R35-2 clearance),
  two L3 stubs from the router's track ends to the round JTAG pads (the router saw the pads as squares), C12/C11 silk further
  from X3-G4. The planes are repoured. }
Var
    B : IPCB_Board;

Function NetNamed(AName : String) : IPCB_Net;
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    Result := Nil;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = AName Then Result := N;
        N := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
End;

Procedure Stub(N : IPCB_Net; X1, Y1, X2, Y2 : Double);
Var
    O : IPCB_Track;
Begin
    O := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    O.X1 := B.XOrigin + MMsToCoord(X1); O.Y1 := B.YOrigin + MMsToCoord(Y1);
    O.X2 := B.XOrigin + MMsToCoord(X2); O.Y2 := B.YOrigin + MMsToCoord(Y2);
    O.Layer := eMidLayer1; O.Width := MMsToCoord(0.0762); O.Net := N;
    B.AddPCBObject(O);
End;

Procedure NoPmodJtagFix;
Var
    Doc : IDocument;
    C   : IPCB_Component;
    It  : IPCB_BoardIterator;
    T   : IPCB_Text;
    P   : IPCB_Polygon;
    L   : TInterfaceList;
    i, n : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_1\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    C := B.GetPcbComponentByRefDes('JP3');
    If (C = Nil) Or (Abs(CoordToMMs(C.X - B.XOrigin) - 14.29) > 0.002) Then
    Begin
        ShowMessage('Refusing: JP3 is not at x 14.29.');
        Exit;
    End;
    C.BeginModify;
    C.X := C.X + MMsToCoord(0.01);
    C.EndModify;
    Stub(NetNamed('TCK'), 12.35, 21.45, 11.76, 22.045);
    Stub(NetNamed('TDI'), 2.2, 11.5, 1.6, 12.1);
    n := 0;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (Not T.InComponent) And (T.Text = 'C12') Then
        Begin
            T.BeginModify; T.XLocation := T.XLocation + MMsToCoord(0.20); T.EndModify; n := n + 1;
        End;
        If (Not T.InComponent) And (T.Text = 'C11') Then
        Begin
            T.BeginModify; T.XLocation := T.XLocation + MMsToCoord(0.25); T.EndModify; n := n + 1;
        End;
        T := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    L := TInterfaceList.Create;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        L.Add(P);
        P := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    PCBServer.SystemOptions.PolygonRepour := eAlwaysRepour;
    For i := 0 To L.Count - 1 Do
    Begin
        P := L.Items[i];
        P.Rebuild;
    End;
    B.ViewManager_FullUpdate;
    ShowMessage('JP3 +0.01 mm, 2 stubs added, ' + IntToStr(n) + ' labels moved, ' + IntToStr(L.Count) + ' polygons repoured.');
End;
