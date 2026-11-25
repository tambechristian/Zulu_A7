{ NoPmodX3Fix.pas -- 2026-11-24, no-PMOD Rev 4, after the 3M X3 placement (DRC 9 -> 0):
  1. Remove the 4 stacked VCC3V3 microvias (Top>L2, L2>L3, L3>L4, L4>L5) the router put on top of the existing
     VCC3V3 through via at (22.575, 7.500): the through via already reaches the L5 plane; the stack only made
     4 hole-to-hole items.
  2. X3 silk: the outline corner next to BTN pad 1 is cut back -- the Top Overlay line at y 5.64 now ends at
     x 17.35 (was 17.76), the line at x 17.76 now starts at y 7.00 (was 5.64): >= 0.29 mm from BTN-1's mask.
  3. Designators: BTN -> (18.50, 7.20) rotation 0, above the button; X3 -> (6.20, 20.20) rotation 0, above the socket.
  Refuses unless the Rev_4 board is focused and every object is found exactly as expected. Save after. }
Procedure FixX3b;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    GI : IPCB_GroupIterator;
    V : IPCB_Via;
    Kill : TInterfaceList;
    Cm, Bt : IPCB_Component;
    Tk, H, Vt : IPCB_Track;
    T : IPCB_Text;
    i, nH, nV : Integer;
    x1, y1, x2, y2 : Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_4\', Brd.FileName) = 0) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin ShowMessage('Refusing: focus the Rev_4 Zulu_a7_no_pmod.PcbDoc first.'); Exit; End;
    { 1: the stacked vias }
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        If (V.Net <> Nil) And (V.Net.Name = 'VCC3V3') And (Abs(CoordToMMs(V.X - Brd.XOrigin) - 22.575) < 0.002)
           And (Abs(CoordToMMs(V.Y - Brd.YOrigin) - 7.5) < 0.002) And Not ((V.LowLayer = eTopLayer) And (V.HighLayer = eBottomLayer)) Then
            Kill.Add(V);
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Kill.Count <> 4 Then Begin ShowMessage('Refusing: found ' + IntToStr(Kill.Count) + ' stacked VCC3V3 vias at (22.575, 7.5), expected 4.'); Kill.Free; Exit; End;
    { 2: X3 overlay lines }
    Cm := Brd.GetPcbComponentByRefDes('X3');
    Bt := Brd.GetPcbComponentByRefDes('BTN');
    If (Cm = Nil) Or (Bt = Nil) Then Begin ShowMessage('Refusing: X3 or BTN missing.'); Kill.Free; Exit; End;
    nH := 0; nV := 0; H := Nil; Vt := Nil;
    GI := Cm.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    Tk := GI.FirstPCBObject;
    While Tk <> Nil Do
    Begin
        If Tk.Layer = eTopOverlay Then
        Begin
            x1 := CoordToMMs(Tk.X1 - Brd.XOrigin); y1 := CoordToMMs(Tk.Y1 - Brd.YOrigin);
            x2 := CoordToMMs(Tk.X2 - Brd.XOrigin); y2 := CoordToMMs(Tk.Y2 - Brd.YOrigin);
            { no Min/Max: DelphiScript's work on integers }
            If (Abs(y1 - 5.64) < 0.01) And (Abs(y2 - 5.64) < 0.01) And ((Abs(x1 - 17.76) < 0.01) Or (Abs(x2 - 17.76) < 0.01)) Then Begin H := Tk; nH := nH + 1; End;
            If (Abs(x1 - 17.76) < 0.01) And (Abs(x2 - 17.76) < 0.01) And (((Abs(y1 - 5.64) < 0.01) And (Abs(y2 - 10.68) < 0.01)) Or ((Abs(y2 - 5.64) < 0.01) And (Abs(y1 - 10.68) < 0.01))) Then Begin Vt := Tk; nV := nV + 1; End;
        End;
        Tk := GI.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(GI);
    If (nH <> 1) Or (nV <> 1) Then Begin ShowMessage('Refusing: X3 corner silk lines found ' + IntToStr(nH) + '/' + IntToStr(nV) + ', expected 1/1.'); Kill.Free; Exit; End;
    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do Brd.RemovePCBObject(Kill.Items[i]);
    Kill.Free;
    H.BeginModify;
    If CoordToMMs(H.X1 - Brd.XOrigin) > CoordToMMs(H.X2 - Brd.XOrigin) Then H.X1 := Brd.XOrigin + MMsToCoord(17.35) Else H.X2 := Brd.XOrigin + MMsToCoord(17.35);
    H.EndModify;
    Vt.BeginModify;
    If CoordToMMs(Vt.Y1 - Brd.YOrigin) < CoordToMMs(Vt.Y2 - Brd.YOrigin) Then Vt.Y1 := Brd.YOrigin + MMsToCoord(7.00) Else Vt.Y2 := Brd.YOrigin + MMsToCoord(7.00);
    Vt.EndModify;
    { 3: designators }
    Bt.BeginModify;
    Bt.ChangeNameAutoposition(eAutoPos_Manual);
    T := Bt.Name; T.BeginModify; T.Rotation := 0; T.MoveToXY(Brd.XOrigin + MMsToCoord(18.50), Brd.YOrigin + MMsToCoord(7.20)); T.EndModify;
    Bt.EndModify;
    Cm.BeginModify;
    Cm.ChangeNameAutoposition(eAutoPos_Manual);
    T := Cm.Name; T.BeginModify; T.Rotation := 0; T.MoveToXY(Brd.XOrigin + MMsToCoord(6.20), Brd.YOrigin + MMsToCoord(20.20)); T.EndModify;
    Cm.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed 4 stacked vias; X3 corner silk cut back; BTN at ' + FormatFloat('0.000', CoordToMMs(Bt.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Bt.Name.YLocation - Brd.YOrigin)) + ', X3 at ' + FormatFloat('0.000', CoordToMMs(Cm.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Cm.Name.YLocation - Brd.YOrigin)) + '. Save the board.');
End;
