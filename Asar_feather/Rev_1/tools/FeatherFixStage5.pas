{ FeatherFixStage5.pas -- 2026-10-31: clears the 2 Hole To Hole violations of docs/drc_stage5.drc.
  The stage-5 plan (tools/route/stage5/tie38_swapB.json) carries the stage-4 artefact again: a VCC3V3 through via
  and a VCC3V3 L4>L5>Bottom microvia stack at the same point (34.95, 12.425). The through via already joins every
  layer, so the two microvias go (the plan JSON is trimmed to match by tools/route/stage5/fix_stage5.py).
  Run FixStage5 with asar_feather.PcbDoc focused, then save. }

Procedure FixStage5;
Var
    Doc  : IDocument;
    Brd  : IPCB_Board;
    It   : IPCB_BoardIterator;
    V    : IPCB_Via;
    Kill : TInterfaceList;
    I    : Integer;
    X, Y : TCoord;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    X := Brd.XOrigin + MMsToCoord(34.95);
    Y := Brd.YOrigin + MMsToCoord(12.425);
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        If (Abs(V.X - X) < MMsToCoord(0.002)) And (Abs(V.Y - Y) < MMsToCoord(0.002)) And
           (Abs(V.HoleSize - MMsToCoord(0.15)) < MMsToCoord(0.002)) And (V.Net <> Nil) Then
            If V.Net.Name = 'VCC3V3' Then Kill.Add(V);
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Kill.Count <> 2 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(Kill.Count) + ' of the 2 microvias; nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    For I := 0 To Kill.Count - 1 Do
        Brd.RemovePCBObject(Kill[I]);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed the 2 VCC3V3 microvias at (34.95, 12.425). Save.');
End;
