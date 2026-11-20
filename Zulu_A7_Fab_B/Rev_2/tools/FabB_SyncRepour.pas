{ FabB_SyncRepour.pas -- GENERATED 2026-11-20 by tools/sync_altium_emit.py. Rebuilds the two plane polygons of
  zulu_a7_fab_b.PcbDoc (L2_GND_PLANE, L5_VCC3V3_PLANE) after the sync copper, as no-PMOD NoPmod_Repour.pas does
  (same API names). Refuses unless the board has exactly 2 polygons. Run SyncRepour after reopening the board
  that tools/mark_microvias.py edited; then rebuild the ratsnest (FabB_RebuildConnR2) and run the DRC. }

Var
    Brd : IPCB_Board;

Function SyncBoard : IPCB_Board;
Var
    Doc : IDocument;
    Ok  : Boolean;
Begin
    Result := Nil;
    Ok := False;
    Doc := GetWorkspace.DM_FocusedDocument;
    If Doc <> Nil Then
        If Pos('\Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc', Doc.DM_FullPath) > 0 Then Ok := True;
    If Not Ok Then
    Begin
        ShowMessage('Refusing (SyncRepour): focus Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc first; nothing changed.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
    If Result = Nil Then
    Begin
        ShowMessage('Refusing (SyncRepour): no PCB board is current; nothing changed.');
        Exit;
    End;
    If Pos('zulu_a7_fab_b.PcbDoc', Result.FileName) = 0 Then
    Begin
        ShowMessage('Refusing (SyncRepour): the current board is ' + Result.FileName + ', not zulu_a7_fab_b.PcbDoc; nothing changed.');
        Result := Nil;
        Exit;
    End;
End;

Procedure SyncRepour;
Var
    It : IPCB_BoardIterator;
    P  : IPCB_Polygon;
    Ls : TInterfaceList;
    i  : Integer;
Begin
    Brd := SyncBoard;
    If Brd = Nil Then Exit;
    Ls := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        Ls.Add(P);
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Ls.Count <> 2 Then
    Begin
        ShowMessage('Refusing: ' + IntToStr(Ls.Count) + ' polygons on the board, expected the 2 planes; nothing changed.');
        Ls.Free;
        Exit;
    End;
    PCBServer.SystemOptions.PolygonRepour := eAlwaysRepour;
    For i := 0 To Ls.Count - 1 Do
    Begin
        P := Ls.Items[i];
        P.Rebuild;
    End;
    Brd.ViewManager_FullUpdate;
    ShowMessage('SyncRepour OK: repoured ' + IntToStr(Ls.Count) + ' polygons. Next: FabB_RebuildConnR2, save, DRC.');
    Ls.Free;
End;

