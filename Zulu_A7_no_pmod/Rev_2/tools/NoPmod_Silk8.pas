{ NoPmod_Silk8.pas -- 2026-11-12. Zulu_a7_no_pmod Rev 2: JP4 has left the south-west corner (all six JTAG holes are now
  in one column on the west edge), so the X2 labels that were squeezed for it go back to the row format:
    '40' '39' '38'      take the size and stroke of '37' and sit on its baseline row
    'AI1' 'AI0' 'C28'   take the size and stroke of 'C27' and sit on its row
    '1V0'               takes the size and stroke of '1V8' and sits on its row (it was shrunk and raised for JP3-3)
  Each label is centred on its own X2 pin with the same offset its sibling has from its pin
  (X2 pins: 40 at x 1.27, 39 at 3.81, 38 at 6.35, 37 at 8.89; top row 20 at 1.27, 19 at 3.81).
  Refuses unless every label and sibling is found exactly once in its window. }
Function FindIn(B : IPCB_Board; S : String; x0, x1, y0, y1 : Double) : IPCB_Text;
Var
    It : IPCB_BoardIterator;
    T  : IPCB_Text;
    R  : TCoordRect;
    n  : Integer;
    cx, cy : Double;
Begin
    Result := Nil;
    n := 0;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (Not T.InComponent) And (T.Text = S) Then
        Begin
            R := T.BoundingRectangle;
            cx := CoordToMMs((R.Left + R.Right) Div 2 - B.XOrigin);
            cy := CoordToMMs((R.Bottom + R.Top) Div 2 - B.YOrigin);
            If (cx > x0) And (cx < x1) And (cy > y0) And (cy < y1) Then
            Begin
                Result := T;
                n := n + 1;
            End;
        End;
        T := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    If n <> 1 Then Result := Nil;
End;

Function Restore(B : IPCB_Board; T, Sib : IPCB_Text; PinX, SibPinX : Double) : String;
Var
    RS, R : TCoordRect;
    tx : TCoord;
Begin
    RS := Sib.BoundingRectangle;
    T.BeginModify;
    T.Size := Sib.Size;
    T.Width := Sib.Width;
    T.EndModify;
    R := T.BoundingRectangle;
    { centre on its own pin with the sibling's offset; bottom on the sibling's bottom }
    tx := (RS.Left + RS.Right) Div 2 + MMsToCoord(PinX - SibPinX);
    T.BeginModify;
    T.XLocation := T.XLocation + (tx - (R.Left + R.Right) Div 2);
    T.YLocation := T.YLocation + (RS.Bottom - R.Bottom);
    T.EndModify;
    R := T.BoundingRectangle;
    Result := T.Text + ': x ' + FloatToStr(CoordToMMs(R.Left - B.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - B.XOrigin)) +
              ' y ' + FloatToStr(CoordToMMs(R.Bottom - B.YOrigin)) + '..' + FloatToStr(CoordToMMs(R.Top - B.YOrigin)) + #13#10;
End;

Procedure NoPmodSilk8;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    T, S37, SC27, S1V8 : IPCB_Text;
    N   : TStringList;
    L   : TInterfaceList;
    i   : Integer;
    Msg : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    S37  := FindIn(B, '37', 7.5, 10.5, 1.5, 4.5);
    SC27 := FindIn(B, 'C27', 7.5, 10.5, 3.0, 6.0);
    S1V8 := FindIn(B, '1V8', 2.5, 5.5, 20.0, 23.0);
    If (S37 = Nil) Or (SC27 = Nil) Or (S1V8 = Nil) Then
    Begin
        ShowMessage('Refusing: a sibling label (37, C27 or 1V8) was not found exactly once.');
        Exit;
    End;
    N := TStringList.Create;
    N.Add('40'); N.Add('39'); N.Add('38'); N.Add('AI1'); N.Add('AI0'); N.Add('C28'); N.Add('1V0');
    L := TInterfaceList.Create;
    For i := 0 To 6 Do
    Begin
        If i < 3 Then T := FindIn(B, N.Strings[i], 0, 8.0, 3.9, 5.0)
        Else If i < 6 Then T := FindIn(B, N.Strings[i], 0, 8.5, 5.0, 6.1)
        Else T := FindIn(B, N.Strings[i], 0, 3.5, 20.5, 22.8);
        If T = Nil Then
        Begin
            ShowMessage('Refusing: label ' + N.Strings[i] + ' not found exactly once; nothing changed.');
            Exit;
        End;
        L.Add(T);
    End;
    Msg := '';
    Msg := Msg + Restore(B, L.Items[0], S37, 1.27, 8.89);
    Msg := Msg + Restore(B, L.Items[1], S37, 3.81, 8.89);
    Msg := Msg + Restore(B, L.Items[2], S37, 6.35, 8.89);
    Msg := Msg + Restore(B, L.Items[3], SC27, 1.27, 8.89);
    Msg := Msg + Restore(B, L.Items[4], SC27, 3.81, 8.89);
    Msg := Msg + Restore(B, L.Items[5], SC27, 6.35, 8.89);
    Msg := Msg + Restore(B, L.Items[6], S1V8, 1.27, 3.81);
    B.ViewManager_FullUpdate;
    ShowMessage('Restored 7 X2 labels:' + #13#10 + Msg);
End;
