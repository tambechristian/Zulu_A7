{ FeatherClearCopper.pas -- 2026-10-24: removes all routing copper (every free via, every free track on the six copper
  layers) before U1 is turned 180 degrees and routing is redone. Footprint primitives, polygons and overlay/mechanical
  objects are untouched. Third version (2026-10-25): refuses unless the counts are stage 1 R7 + SDRAM + stage 4 (1112 vias, 3783 tracks), so stage 4 can be replaced.
  Run ClearRoutingCopper with asar_feather.PcbDoc focused, then save. }

Procedure ClearRoutingCopper3;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    O   : IPCB_Primitive;
    L   : TInterfaceList;
    I, NV, NT : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    NV := 0; NT := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If Not O.InComponent Then Begin L.Add(O); NV := NV + 1; End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopLayer, eMidLayer1, eMidLayer2, eMidLayer3, eMidLayer4, eBottomLayer));
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If Not O.InComponent Then Begin L.Add(O); NT := NT + 1; End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (NV <> 1112) Or (NT <> 3783) Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(NV) + ' vias and ' + IntToStr(NT) + ' tracks, expected 1112 and 3783.');
        L.Free;
        Exit;
    End;
    For I := 0 To L.Count - 1 Do Brd.RemovePCBObject(L.Items[I]);
    L.Free;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed ' + IntToStr(NV) + ' vias and ' + IntToStr(NT) + ' tracks. Save.');
End;
