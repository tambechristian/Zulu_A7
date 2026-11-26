{ NoPmodBtnLabel8.pas -- 2026-11-24, Rev 4: move the BTN designator from (15.469, 9.732) to (16.935, 9.065) below the button, as Rev 3 (after FixJtag left it rotated about the wrong point);
  the button. Pattern of FabB_BtnLabel.pas: ChangeNameAutoposition then T.MoveByXY with no component Begin/EndModify
  (the component's EndModify re-applies autoposition). Save after. }
Procedure MoveBtnLabel8;
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
    dx := 16.935 - CoordToMMs(T.XLocation - Brd.XOrigin);
    dy := 9.065 - CoordToMMs(T.YLocation - Brd.YOrigin);
    If (Abs(dx - 1.466) > 0.01) Or (Abs(dy + 0.667) > 0.01) Then Begin ShowMessage('Refusing: BTN designator not at (15.469, 9.732).'); Exit; End;
    PCBServer.PreProcess;
    Cm.ChangeNameAutoposition(eAutoPos_Manual);
    T.BeginModify;
    T.MoveByXY(MMsToCoord(dx), MMsToCoord(dy));
    T.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('BTN designator at ' + FormatFloat('0.000', CoordToMMs(Cm.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Cm.Name.YLocation - Brd.YOrigin)) + ' (expected 16.935, 9.065). Save the board.');
End;
