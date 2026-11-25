{ FabB_Rev2Pads.pas -- Fab B Rev 2 (2026-11-11): X2 pads 10 (CHAN7) and 30 (CHAN20) move 10.16 mm east to x 36.83,
  their top-silk pin labels ('10', 'C7', '30 C20') move with them, and X1's designator is hidden (the new pin-10
  label sits where it was). Run it BEFORE FabBCopper_Rev2 (which moves X1/X4 and places the new copper).
  Refuses unless both pads are found at x 26.67 and all three labels at their old place; nothing changes then. }

Procedure Rev2Pads;
Var
    Brd : IPCB_Board;
    Cm  : IPCB_Component;
    GI  : IPCB_GroupIterator;
    It  : IPCB_BoardIterator;
    O   : IPCB_Primitive;
    P10, P30, Tx10, TxC7, Tx30 : IPCB_Primitive;
    D   : TCoord;
    x, y : Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Open Zulu_a7_no_pmod.PcbDoc first.'); Exit; End;
    If Pos('REV_2', UpperCase(Brd.FileName)) = 0 Then
    Begin ShowMessage('Refusing: the focused board is not the Rev_2 copy: ' + Brd.FileName); Exit; End;
    D := MMsToCoord(10.16);
    Cm := Brd.GetPcbComponentByRefDes('X2');
    If Cm = Nil Then Begin ShowMessage('Refusing: X2 not found.'); Exit; End;
    P10 := Nil; P30 := Nil;
    GI := Cm.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        x := CoordToMMs(O.X - Brd.XOrigin);
        If (O.Name = '10') And (Abs(x - 26.67) < 0.01) Then P10 := O;
        If (O.Name = '30') And (Abs(x - 26.67) < 0.01) Then P30 := O;
        O := GI.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(GI);
    If (P10 = Nil) Or (P30 = Nil) Then Begin ShowMessage('Refusing: X2 pad 10 or 30 is not at x 26.67.'); Exit; End;
    Tx10 := Nil; TxC7 := Nil; Tx30 := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If Not O.IsDesignator And Not O.IsComment Then
        Begin
            x := CoordToMMs(O.BoundingRectangle.Left - Brd.XOrigin);
            y := CoordToMMs(O.BoundingRectangle.Bottom - Brd.YOrigin);
            If (O.Text = '10') And (Abs(x - 26.13) < 0.15) And (y > 21) Then Tx10 := O;
            If (O.Text = 'C7') And (Abs(x - 26.13) < 0.15) And (y > 20) Then TxC7 := O;
            If (O.Text = '30 C20') And (Abs(x - 25.92) < 0.15) And (y < 3) Then Tx30 := O;
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (Tx10 = Nil) Or (TxC7 = Nil) Or (Tx30 = Nil) Then
    Begin ShowMessage('Refusing: a pin label (10 / C7 / 30 C20) was not found at its old place.'); Exit; End;

    PCBServer.PreProcess;
    P10.BeginModify; P10.MoveByXY(D, 0); P10.EndModify;
    P30.BeginModify; P30.MoveByXY(D, 0); P30.EndModify;
    Tx10.BeginModify; Tx10.MoveByXY(D, 0); Tx10.EndModify;
    TxC7.BeginModify; TxC7.MoveByXY(D, 0); TxC7.EndModify;
    Tx30.BeginModify; Tx30.MoveByXY(D, 0); Tx30.EndModify;
    Cm := Brd.GetPcbComponentByRefDes('X1');
    If Cm <> Nil Then Begin Cm.BeginModify; Cm.NameOn := False; Cm.EndModify; End;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Rev 2: X2 pads 10 and 30 now at x ' + FloatToStr(CoordToMMs(P10.X - Brd.XOrigin)) + ' / ' +
                FloatToStr(CoordToMMs(P30.X - Brd.XOrigin)) + '; labels moved; X1 designator hidden.');
End;
