{ NoPmodBtnLabel9.pas -- 2026-11-25, Rev 4: after BTN moved +0.475 mm east (centred between the X3 shell and the LEDs),
  put the BTN designator at (17.410, 9.065), the same offset below the button as before. Accepts the label at the old
  (16.935, 9.065) or already at the target (the component move may carry it). Pattern of NoPmodBtnLabel8.pas:
  ChangeNameAutoposition then T.MoveByXY with no component Begin/EndModify. Save after. }
Procedure MoveBtnLabel9;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    T : IPCB_Text;
    dx, dy : Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_4\', Brd.FileName) = 0) Then Begin ShowMessage('Refusing: focus the Rev_4 board.'); Exit; End;
    Cm := Brd.GetPcbComponentByRefDes('BTN');
    T := Cm.Name;
    dx := 17.410 - CoordToMMs(T.XLocation - Brd.XOrigin);
    dy := 9.065 - CoordToMMs(T.YLocation - Brd.YOrigin);
    If (Abs(dy) > 0.01) Or ((Abs(dx - 0.475) > 0.01) And (Abs(dx) > 0.01)) Then Begin
        ShowMessage('Refusing: BTN designator at ' + FormatFloat('0.000', CoordToMMs(T.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(T.YLocation - Brd.YOrigin)));
        Exit;
    End;
    If Abs(dx) > 0.001 Then Begin
        PCBServer.PreProcess;
        Cm.ChangeNameAutoposition(eAutoPos_Manual);
        T.BeginModify;
        T.MoveByXY(MMsToCoord(dx), MMsToCoord(dy));
        T.EndModify;
        PCBServer.PostProcess;
        Brd.ViewManager_FullUpdate;
    End;
    ShowMessage('BTN at ' + FormatFloat('0.000', CoordToMMs(Cm.X - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Cm.Y - Brd.YOrigin)) + '; designator at ' + FormatFloat('0.000', CoordToMMs(Cm.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Cm.Name.YLocation - Brd.YOrigin)) + ' (expected BTN 18.475,12.920; label 17.410, 9.065). Save the board.');
End;
