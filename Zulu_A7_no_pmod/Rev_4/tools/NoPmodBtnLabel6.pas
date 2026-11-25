{ NoPmodBtnLabel6.pas -- 2026-11-24, Rev 4: move the BTN designator from (17.833, 5.734) to anchor (18.50, 7.20), above
  the button. Pattern of FabB_BtnLabel.pas: ChangeNameAutoposition then T.MoveByXY with no component Begin/EndModify
  (the component's EndModify re-applies autoposition). Save after. }
Procedure MoveBtnLabel6;
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
    dx := 18.50 - CoordToMMs(T.XLocation - Brd.XOrigin);
    dy := 7.20 - CoordToMMs(T.YLocation - Brd.YOrigin);
    If (Abs(dx - 0.667) > 0.01) Or (Abs(dy - 1.466) > 0.01) Then Begin ShowMessage('Refusing: BTN designator not at (17.833, 5.734).'); Exit; End;
    PCBServer.PreProcess;
    Cm.ChangeNameAutoposition(eAutoPos_Manual);
    T.BeginModify;
    T.MoveByXY(MMsToCoord(dx), MMsToCoord(dy));
    T.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('BTN designator at ' + FormatFloat('0.000', CoordToMMs(Cm.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Cm.Name.YLocation - Brd.YOrigin)) + ' (expected 18.500, 7.200). Save the board.');
End;
