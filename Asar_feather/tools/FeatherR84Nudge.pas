{ FeatherR84Nudge.pas -- 2026-11-06: R84's pads ended 0.202 mm from the 'ASAR A7' silk; the Silk To Solder Mask rule is 0.254. R84 goes
  0.06 mm north, pad 1 to 38.55, 5.96 (model.stemma.json). Its track and via ends stay inside the pads. Refuses unless pad 1 is at
  38.55, 5.90, so it runs once. Run R84Nudge with asar_feather.PcbDoc focused, then Repour All, DRC, Save. }

Procedure R84Nudge;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    C   : IPCB_Component;
    It  : IPCB_GroupIterator;
    P   : IPCB_Pad;
    Ok  : Boolean;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    C := Brd.GetPcbComponentByRefDes('R84');
    Ok := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = '1') And (Abs(CoordToMMs(P.X - Brd.XOrigin) - 38.55) < 0.01) And (Abs(CoordToMMs(P.Y - Brd.YOrigin) - 5.90) < 0.01) Then
            Ok := True;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Not Ok Then
    Begin
        ShowMessage('Refusing: R84 pad 1 is not at 38.55, 5.90.');
        Exit;
    End;
    C.BeginModify;
    C.Y := C.Y + MMsToCoord(0.06);
    C.EndModify;
    Brd.ViewManager_FullUpdate;
    ShowMessage('R84 moved 0.06 mm north. Repour All, DRC, Save.');
End;
