{ NoPmod_Jtag.pas -- 2026-11-08. Zulu_a7_no_pmod: turn JP4 to rotation 90 after the copper plan has moved it, then repour
  the two plane polygons so the relocated JTAG holes get their thermals and the old antipads close. }

Function GuardDoc : Boolean;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    Result := (Doc <> Nil) And (Pos('\Zulu_A7_no_pmod\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) > 0);
    If Not Result Then ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
End;

Procedure NoPmodTurnJP4;
Var
    Board : IPCB_Board;
    C     : IPCB_Component;
Begin
    If Not GuardDoc Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    C := Board.GetPcbComponentByRefDes('JP4');
    If C = Nil Then Begin ShowMessage('No JP4.'); Exit; End;
    If (Abs(CoordToMMs(C.X - Board.XOrigin) - 1.60) > 0.01) Or (Abs(CoordToMMs(C.Y - Board.YOrigin) - 14.64) > 0.01) Then
    Begin
        ShowMessage('Refusing: run the copper plan first (JP4 must be at 1.60, 14.64).');
        Exit;
    End;
    C.BeginModify;
    C.Rotation := 90;
    C.EndModify;
    Board.ViewManager_FullUpdate;
    ShowMessage('JP4 rotation now ' + FloatToStr(C.Rotation));
End;

Procedure NoPmodRepour;
Var
    Board : IPCB_Board;
    It    : IPCB_BoardIterator;
    P     : IPCB_Polygon;
    L     : TInterfaceList;
    i     : Integer;
Begin
    If Not GuardDoc Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        L.Add(P);
        P := It.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(It);
    PCBServer.SystemOptions.PolygonRepour := eAlwaysRepour;
    For i := 0 To L.Count - 1 Do
    Begin
        P := L.Items[i];
        P.Rebuild;
    End;
    Board.ViewManager_FullUpdate;
    ShowMessage('Repoured ' + IntToStr(L.Count) + ' polygons.');
End;
