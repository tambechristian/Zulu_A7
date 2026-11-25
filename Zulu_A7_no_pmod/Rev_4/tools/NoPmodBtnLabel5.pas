{ NoPmodBtnLabel5.pas -- 2026-11-24, Rev 4: BTN designator (rotation 0, at 17.833, 5.734 on BTN pad 1 after FixX3b)
  -> anchor (18.50, 7.20), above the button. Refuses unless found where expected. Save after. }
Procedure MoveBtnLabel5;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    T : IPCB_Text;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_4\', Brd.FileName) = 0) Then Begin ShowMessage('Refusing: focus the Rev_4 board.'); Exit; End;
    Cm := Brd.GetPcbComponentByRefDes('BTN');
    T := Cm.Name;
    If (Abs(CoordToMMs(T.XLocation - Brd.XOrigin) - 17.833) > 0.005) Or (Abs(CoordToMMs(T.YLocation - Brd.YOrigin) - 5.734) > 0.005) Then
    Begin ShowMessage('Refusing: BTN designator not at (17.833, 5.734).'); Exit; End;
    PCBServer.PreProcess;
    Cm.BeginModify;
    Cm.NameAutoPosition := eAutoPos_Manual;
    T.BeginModify;
    T.XLocation := Brd.XOrigin + MMsToCoord(18.50);
    T.YLocation := Brd.YOrigin + MMsToCoord(7.20);
    T.EndModify;
    Cm.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('BTN designator at ' + FormatFloat('0.000', CoordToMMs(Cm.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Cm.Name.YLocation - Brd.YOrigin)) + ' (expected 18.500, 7.200). Save the board.');
End;
