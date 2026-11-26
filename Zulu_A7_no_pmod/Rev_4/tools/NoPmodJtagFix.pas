{ NoPmodJtagFix.pas -- 2026-11-25, Rev 4 after the JTAG row move (DRC 13 -> 0):
  1. JP3/JP4 pads: Bottom-side land 1.524 -> 1.30 mm (local pad stack; Top and inner stay 1.524). The bottom 0402/0603
     caps beside the row (C11, C12, C13, C149, R35) left 0.03-0.07 mm mask webs; 1.30 gives >= 0.14 mm and U7's
     pin-1 silk dot 0.255 mm. Bottom ring 0.142 mm (1.016 hole) -- the X1 rule's 0.14 minimum.
  2. X3 designator hidden (it sat on the JTAG row); R34's Bottom designator hidden (it sat on JP3-3).
  3. BTN designator back below the button as in Rev 3: rotation 0, anchor (16.935, 9.065).
  Refuses unless the Rev_4 board is focused and every object is as expected. Save after. }
Procedure FixJtag;
Var
    Brd : IPCB_Board;
    Cm, X3, R34, Bt : IPCB_Component;
    It : IPCB_GroupIterator;
    P : IPCB_Pad;
    T : IPCB_Text;
    n, k : Integer;
    S : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_4\', Brd.FileName) = 0) Then Begin ShowMessage('Refusing: focus the Rev_4 board.'); Exit; End;
    X3 := Brd.GetPcbComponentByRefDes('X3');
    R34 := Brd.GetPcbComponentByRefDes('R34');
    Bt := Brd.GetPcbComponentByRefDes('BTN');
    If (X3 = Nil) Or (R34 = Nil) Or (Bt = Nil) Then Begin ShowMessage('Refusing: X3/R34/BTN missing.'); Exit; End;
    n := 0;
    PCBServer.PreProcess;
    For k := 3 To 4 Do
    Begin
        Cm := Brd.GetPcbComponentByRefDes('JP' + IntToStr(k));
        If Cm = Nil Then Begin ShowMessage('Refusing: JP' + IntToStr(k) + ' missing.'); PCBServer.PostProcess; Exit; End;
        It := Cm.GroupIterator_Create;
        It.AddFilter_ObjectSet(MkSet(ePadObject));
        P := It.FirstPCBObject;
        While P <> Nil Do
        Begin
            P.BeginModify;
            P.Mode := ePadMode_LocalStack;
            P.BotXSize := MMsToCoord(1.30);
            P.BotYSize := MMsToCoord(1.30);
            P.EndModify;
            n := n + 1;
            P := It.NextPCBObject;
        End;
        Cm.GroupIterator_Destroy(It);
    End;
    X3.BeginModify; X3.NameOn := False; X3.EndModify;
    R34.BeginModify; R34.NameOn := False; R34.EndModify;
    Bt.ChangeNameAutoposition(eAutoPos_Manual);
    T := Bt.Name;
    T.BeginModify;
    T.Rotation := 0;
    T.MoveByXY(Brd.XOrigin + MMsToCoord(16.935) - T.XLocation, Brd.YOrigin + MMsToCoord(9.065) - T.YLocation);
    T.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    S := IntToStr(n) + ' JTAG pads set to a 1.30 mm Bottom land; X3 and R34 designators hidden; BTN designator at ' +
         FormatFloat('0.000', CoordToMMs(Bt.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Bt.Name.YLocation - Brd.YOrigin)) +
         ' rot ' + FloatToStr(Bt.Name.Rotation) + ' (expected 16.935, 9.065, 0). Save the board.';
    ShowMessage(S);
End;
