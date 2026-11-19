{ NoPmod_Sliver.pas -- 2026-11-12. Zulu_a7_no_pmod Rev 2, after the JTAG column change: DRC found four Bottom mask slivers.
    C78  x 2.80 -> 2.825: C78-1/-2 were 0.188 mm of copper from JP3-1/-2 (sliver 0.088 < 0.1).
    R108 y 13.45 -> 13.475: centred between L9-1 and L9-2 (0.20 mm copper gap each side, sliver 0.10).
  The routed tracks end at the old pad centres, which stay inside the moved pads.
  Refuses unless both parts are where the column change put them. }
Procedure NoPmodSliver;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    C, R : IPCB_Component;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    C := B.GetPcbComponentByRefDes('C78');
    R := B.GetPcbComponentByRefDes('R108');
    If (C = Nil) Or (R = Nil) Or
       (Abs(CoordToMMs(C.X - B.XOrigin) - 2.80) > 0.002) Or (Abs(CoordToMMs(C.Y - B.YOrigin) - 15.65) > 0.002) Or
       (Abs(CoordToMMs(R.X - B.XOrigin) - 6.00) > 0.002) Or (Abs(CoordToMMs(R.Y - B.YOrigin) - 13.45) > 0.002) Then
    Begin
        ShowMessage('Refusing: C78 is not at (2.80, 15.65) or R108 is not at (6.00, 13.45).');
        Exit;
    End;
    C.BeginModify;
    C.X := C.X + MMsToCoord(0.025);
    C.EndModify;
    R.BeginModify;
    R.Y := R.Y + MMsToCoord(0.025);
    R.EndModify;
    B.ViewManager_FullUpdate;
    ShowMessage('C78 now (' + FloatToStr(CoordToMMs(C.X - B.XOrigin)) + ', ' + FloatToStr(CoordToMMs(C.Y - B.YOrigin)) +
                '); R108 now (' + FloatToStr(CoordToMMs(R.X - B.XOrigin)) + ', ' + FloatToStr(CoordToMMs(R.Y - B.YOrigin)) + ').');
End;
