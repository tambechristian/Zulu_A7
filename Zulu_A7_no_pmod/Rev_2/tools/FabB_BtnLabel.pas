{ Fab B BTN spread: put the BTN designator centred under the button, its top 0.30 mm below the pads' bottom edge
  (pads end at y 10.32), so it clears C158 (which the moved label overlapped) and every pad by the 0.254 silk rule. }
Procedure BtnLabel;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    T : IPCB_Text;
    R : TCoordRect;
    cx, top, dx, dy : Double;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Cm := Brd.GetPcbComponentByRefDes('BTN');
    If (Cm = Nil) Or (Abs(CoordToMMs(Cm.X - Brd.XOrigin) - 18.55) > 0.002) Then
    Begin
        ShowMessage('Refusing: BTN is missing or not at x 18.55; nothing changed.');
        Exit;
    End;
    T := Cm.Name;
    R := T.BoundingRectangle;
    cx := (CoordToMMs(R.Left - Brd.XOrigin) + CoordToMMs(R.Right - Brd.XOrigin)) / 2;
    top := CoordToMMs(R.Top - Brd.YOrigin);
    dx := 18.55 - cx;
    dy := 10.02 - top;
    PCBServer.PreProcess;
    Cm.ChangeNameAutoposition(eAutoPos_Manual);
    T.BeginModify;
    T.MoveByXY(MMsToCoord(dx), MMsToCoord(dy));
    T.EndModify;
    PCBServer.PostProcess;
    R := T.BoundingRectangle;
    ShowMessage('BTN label moved by (' + FloatToStr(dx) + ', ' + FloatToStr(dy) + ') mm; box now x ' +
        FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - Brd.XOrigin)) + ' y ' +
        FloatToStr(CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FloatToStr(CoordToMMs(R.Top - Brd.YOrigin)));
    Brd.ViewManager_FullUpdate;
End;
