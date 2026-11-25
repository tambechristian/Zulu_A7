{ NoPmodU10Fix.pas -- 2026-11-14. FabBCopper_NoPmodBodies2 flipped U10 to the Top side, but Altium mirrors a flipped part
  about its centre, not its origin (pad 1), so U10 landed 4.93 mm east of the planned site (pad 1 at 28.095, 18.895).
  Moves U10 back by -4.930 mm in x and checks that pad 1 is then at (23.165, 18.895) and pad 5 at (18.235, 22.705). }
Procedure FixU10;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    PIt : IPCB_GroupIterator;
    Pd : IPCB_Pad;
    Msg : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Cm := Brd.GetPcbComponentByRefDes('U10');
    If (Cm = Nil) Or (Cm.Layer <> eTopLayer) Then
    Begin
        ShowMessage('Refusing: U10 missing or not on Top.');
        Exit;
    End;
    PIt := Cm.GroupIterator_Create;
    PIt.AddFilter_ObjectSet(MkSet(ePadObject));
    Pd := PIt.FirstPCBObject;
    While Pd <> Nil Do
    Begin
        If (Pd.Name = '1') And ((Abs(CoordToMMs(Pd.X - Brd.XOrigin) - 28.095) > 0.005) Or (Abs(CoordToMMs(Pd.Y - Brd.YOrigin) - 18.895) > 0.005)) Then
        Begin
            Cm.GroupIterator_Destroy(PIt);
            ShowMessage('Refusing: U10 pad 1 is not at (28.095, 18.895); nothing changed.');
            Exit;
        End;
        Pd := PIt.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(PIt);
    Cm.BeginModify;
    Cm.X := Cm.X - MMsToCoord(4.930);
    Cm.EndModify;
    Msg := '';
    PIt := Cm.GroupIterator_Create;
    PIt.AddFilter_ObjectSet(MkSet(ePadObject));
    Pd := PIt.FirstPCBObject;
    While Pd <> Nil Do
    Begin
        If (Pd.Name = '1') Or (Pd.Name = '5') Then
            Msg := Msg + ' pad ' + Pd.Name + ' at ' + FormatFloat('0.000', CoordToMMs(Pd.X - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Pd.Y - Brd.YOrigin));
        Pd := PIt.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(PIt);
    Brd.ViewManager_FullUpdate;
    ShowMessage('U10 moved -4.930 mm:' + Msg + ' (expected pad 1 23.165,18.895; pad 5 18.235,22.705)');
End;
