{ NoPmod_Repour.pas -- 2026-11-12. Rebuilds every polygon on Zulu_a7_no_pmod Rev 2 (closes the antipads of removed vias). }
Procedure NoPmodRepour;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    It  : IPCB_BoardIterator;
    P   : IPCB_Polygon;
    L   : TInterfaceList;
    i   : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_2\...\Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
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
    ShowMessage('Repoured ' + IntToStr(L.Count) + ' polygons.');
End;
