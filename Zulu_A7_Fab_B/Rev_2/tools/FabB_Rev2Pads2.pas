{ FabB_Rev2Pads2.pas (label test fixed: match by text in a loose window, exactly one each) -- Fab B Rev 2 (2026-11-11): X2 pads 10 (CHAN7) and 30 (CHAN20) move 10.16 mm east to x 36.83,
  their top-silk pin labels ('10', 'C7', '30 C20') move with them, and X1's designator is hidden (the new pin-10
  label sits where it was). Run it BEFORE FabBCopper_Rev2 (which moves X1/X4 and places the new copper).
  Refuses unless both pads are found at x 26.67 and all three labels at their old place; nothing changes then. }

Procedure Rev2Pads2;
Var
    Brd : IPCB_Board;
    Cm  : IPCB_Component;
    GI  : IPCB_GroupIterator;
    It  : IPCB_BoardIterator;
    O   : IPCB_Primitive;
    P10, P30, Tx10, TxC7, Tx30 : IPCB_Primitive;
    D   : TCoord;
    x, y : Double;
    n10, nC7, n30 : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Open zulu_a7_fab_b.PcbDoc first.'); Exit; End;
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
    Tx10 := Nil; TxC7 := Nil; Tx30 := Nil; n10 := 0; nC7 := 0; n30 := 0;
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
            If (O.Text = '10') And (x > 25.5) And (x < 27.5) And (y > 21) Then Begin Tx10 := O; n10 := n10 + 1; End;
            If (O.Text = 'C7') And (x > 25.5) And (x < 27.5) And (y > 20) Then Begin TxC7 := O; nC7 := nC7 + 1; End;
            If (O.Text = '30 C20') And (x > 25.5) And (x < 27.5) And (y < 4) Then Begin Tx30 := O; n30 := n30 + 1; End;
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (n10 <> 1) Or (nC7 <> 1) Or (n30 <> 1) Then
    Begin ShowMessage('Refusing: pin labels found 10:' + IntToStr(n10) + ' C7:' + IntToStr(nC7) + ' 30 C20:' + IntToStr(n30) + ' (each must be 1).'); Exit; End;

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
