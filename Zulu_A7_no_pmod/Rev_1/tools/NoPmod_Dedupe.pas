{ NoPmod_Dedupe.pas -- 2026-11-08. The R5-1 tie landed on an existing GND through via at (57.55, 20.30): two identical
  vias at one point. Removes exactly one of them. }
Procedure NoPmodDedupe;
Var
    Doc   : IDocument;
    Board : IPCB_Board;
    It    : IPCB_BoardIterator;
    V     : IPCB_Via;
    L     : TInterfaceList;
    x, y  : Double;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_1\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Board := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        x := CoordToMMs(V.X - Board.XOrigin);
        y := CoordToMMs(V.Y - Board.YOrigin);
        If (Abs(x - 57.55) < 0.002) And (Abs(y - 20.30) < 0.002) Then L.Add(V);
        V := It.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(It);
    If L.Count <> 2 Then
    Begin
        ShowMessage('Refusing: expected 2 vias at (57.55, 20.30), found ' + IntToStr(L.Count));
        Exit;
    End;
    Board.RemovePCBObject(L.Items[0]);
    Board.ViewManager_FullUpdate;
    ShowMessage('Removed 1 duplicate via at (57.55, 20.30).');
End;
