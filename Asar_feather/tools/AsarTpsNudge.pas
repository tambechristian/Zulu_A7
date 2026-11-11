{ AsarTpsNudge.pas -- 2026-11-09. DRC after the TPS63802 placement found 4 Minimum Solder Mask Sliver violations of
  0.0999 mm (rule 0.1): L1-1 to both C147 pads and L1-2 to both C80 pads sit 0.1999 mm apart. C147 moves 0.02 mm west and
  C80 0.02 mm east (their tracks end well inside the pads, so nothing disconnects). Refuses unless both are where
  AsarTpsPlace2 put them. Run AsarTpsNudge with asar_feather.PcbDoc focused, then save and re-run DRC. }

Procedure AsarTpsNudge;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    A, B : IPCB_Component;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    A := Brd.GetPcbComponentByRefDes('C147');
    B := Brd.GetPcbComponentByRefDes('C80');
    If (A = Nil) Or (B = Nil) Or (Abs(CoordToMMs(A.X - Brd.XOrigin) - 9.6) > 0.003) Or (Abs(CoordToMMs(B.X - Brd.XOrigin) - 14.9) > 0.003) Then
    Begin
        ShowMessage('Refusing: C147 or C80 is not at x 9.6 / 14.9; nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    A.BeginModify; A.X := A.X - MMsToCoord(0.02); A.EndModify;
    B.BeginModify; B.X := B.X + MMsToCoord(0.02); B.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('C147 now x ' + FormatFloat('0.000', CoordToMMs(A.X - Brd.XOrigin)) + ', C80 now x ' +
        FormatFloat('0.000', CoordToMMs(B.X - Brd.XOrigin)) + '. Save and re-run DRC.');
End;
