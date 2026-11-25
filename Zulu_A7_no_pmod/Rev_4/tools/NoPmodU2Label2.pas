{ NoPmodU2Label2.pas -- 2026-11-19. Second try of NoPmodU2Label.pas: writing XLocation/YLocation on the designator was
  ignored (the text stayed at 22.534, 20.589). Designators are moved with the component in modify mode, autoposition
  set to manual, then MoveToXY. Target anchor (24.750, 8.650), from tools/route/u2_label/find_spot.py. }
Procedure MoveU2Label2;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    T : IPCB_Text;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Cm := Brd.GetPcbComponentByRefDes('U2');
    If Cm = Nil Then
    Begin
        ShowMessage('Refusing: U2 not found.');
        Exit;
    End;
    T := Cm.Name;
    If (Abs(CoordToMMs(T.XLocation - Brd.XOrigin) - 22.534) > 0.005) Or (Abs(CoordToMMs(T.YLocation - Brd.YOrigin) - 20.589) > 0.005) Then
    Begin
        ShowMessage('Refusing: U2 designator is at ' + FormatFloat('0.000', CoordToMMs(T.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(T.YLocation - Brd.YOrigin)) + ', not (22.534, 20.589); nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    Cm.BeginModify;
    Cm.ChangeNameAutoposition(eAutoPos_Manual);
    T.BeginModify;
    T.MoveToXY(Brd.XOrigin + MMsToCoord(24.750), Brd.YOrigin + MMsToCoord(8.650));
    T.EndModify;
    Cm.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    T := Cm.Name;
    ShowMessage('U2 designator now at ' + FormatFloat('0.000', CoordToMMs(T.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(T.YLocation - Brd.YOrigin)) + ' (expected 24.750, 8.650)');
End;
