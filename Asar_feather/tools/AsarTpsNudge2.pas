{ AsarTpsNudge2.pas -- 2026-11-09. Follow-up to AsarTpsNudge: moving C147 0.02 west put its GND pad 0.063 from a track west
  of it (clearance 0.076). C147 goes back to x 9.600 and L1 moves 0.01 mm east instead, so both L1 pads sit 0.21 mm from the
  C147 / C80 pads (C80 keeps its +0.02). L1's two stubs end well inside its pads. Refuses unless C147 is at 9.580, C80 at
  14.920 and L1 at 12.250. Run AsarTpsNudge2 with asar_feather.PcbDoc focused, then save and re-run DRC. }

Procedure AsarTpsNudge2;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    A, B, L : IPCB_Component;
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
    L := Brd.GetPcbComponentByRefDes('L1');
    If (A = Nil) Or (B = Nil) Or (L = Nil) Or (Abs(CoordToMMs(A.X - Brd.XOrigin) - 9.58) > 0.003) Or
       (Abs(CoordToMMs(B.X - Brd.XOrigin) - 14.92) > 0.003) Or (Abs(CoordToMMs(L.X - Brd.XOrigin) - 12.25) > 0.003) Then
    Begin
        ShowMessage('Refusing: C147 / C80 / L1 are not at x 9.580 / 14.920 / 12.250; nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    A.BeginModify; A.X := A.X + MMsToCoord(0.02); A.EndModify;
    L.BeginModify; L.X := L.X + MMsToCoord(0.01); L.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('C147 x ' + FormatFloat('0.000', CoordToMMs(A.X - Brd.XOrigin)) + ', L1 x ' +
        FormatFloat('0.000', CoordToMMs(L.X - Brd.XOrigin)) + ', C80 x ' + FormatFloat('0.000', CoordToMMs(B.X - Brd.XOrigin)) +
        '. Save and re-run DRC.');
End;
