{ NoPmodU2Label.pas -- 2026-11-19. U2's designator sat in X2's pin-label row (DRC Silk-to-Silk against 'C8' and 'C9').
  Moves the designator text (rot 0, 0.8 mm) from its anchor (22.534, 20.589) to (24.750, 8.650), off U2's south-west
  corner, chosen by tools/route/u2_label/find_spot.py: 0.349 mm from every pad and every other silk item (rules 0.254).
  Refuses unless the text is where expected. Nothing else changes. }
Procedure MoveU2Label;
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
    T.BeginModify;
    T.XLocation := Brd.XOrigin + MMsToCoord(24.750);
    T.YLocation := Brd.YOrigin + MMsToCoord(8.650);
    T.EndModify;
    T.GraphicallyInvalidate;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('U2 designator now at ' + FormatFloat('0.000', CoordToMMs(T.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(T.YLocation - Brd.YOrigin)) + ' (expected 24.750, 8.650)');
End;
