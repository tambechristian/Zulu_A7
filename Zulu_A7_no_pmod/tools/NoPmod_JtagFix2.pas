{ NoPmod_JtagFix2.pas -- 2026-11-08. JP3 at x 14.30 is 0.088 mm from VCC1V8 (L3, x 15.30); at 14.29 it was 0.088 from R35-2.
  14.295 clears both. Repours the planes. }
Procedure NoPmodJtagFix2;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    C   : IPCB_Component;
    It  : IPCB_BoardIterator;
    P   : IPCB_Polygon;
    L   : TInterfaceList;
    i   : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    C := B.GetPcbComponentByRefDes('JP3');
    If (C = Nil) Or (Abs(CoordToMMs(C.X - B.XOrigin) - 14.30) > 0.002) Then
    Begin
        ShowMessage('Refusing: JP3 is not at x 14.30.');
        Exit;
    End;
    C.BeginModify;
    C.X := C.X - MMsToCoord(0.005);
    C.EndModify;
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
    ShowMessage('JP3 now at x ' + FloatToStr(CoordToMMs(C.X - B.XOrigin)) + '; polygons repoured.');
End;
