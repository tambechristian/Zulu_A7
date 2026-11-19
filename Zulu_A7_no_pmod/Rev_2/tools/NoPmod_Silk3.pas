{ NoPmod_Silk3.pas -- 2026-11-12, after the first DRC on Zulu_a7_no_pmod Rev 2. The six X2 labels above JP4 (40/39/38
  and AI1/AI0/C28) go to 0.6 mm text so both rows fit between JP4 and the microSD pads with the 0.254 mm silk rules:
  numbers with their bottom at y 4.10, names at y 5.00, each keeping its horizontal centre. Also hides the JP4 designator
  (it sat on X2's pads) and moves JP3 up 0.04 mm (0.063 mm from R108-1 -> about 0.10). }
Function FindLabel(B : IPCB_Board; S : String) : IPCB_Text;
Var
    It : IPCB_BoardIterator;
    T  : IPCB_Text;
    R  : TCoordRect;
    n  : Integer;
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
            If (CoordToMMs(R.Left - B.XOrigin) < 9) And (CoordToMMs(R.Bottom - B.YOrigin) > 3.9) And (CoordToMMs(R.Bottom - B.YOrigin) < 5.3) Then
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

Function Restack(B : IPCB_Board; T : IPCB_Text; Bottom : Double) : String;
Var
    R : TCoordRect;
    cx : TCoord;
Begin
    R := T.BoundingRectangle;
    cx := (R.Left + R.Right) Div 2;
    T.BeginModify;
    T.Size := MMsToCoord(0.6);
    T.Width := MMsToCoord(0.1);
    T.EndModify;
    R := T.BoundingRectangle;
    T.BeginModify;
    T.XLocation := T.XLocation + (cx - (R.Left + R.Right) Div 2);
    T.YLocation := T.YLocation + (B.YOrigin + MMsToCoord(Bottom) - R.Bottom);
    T.EndModify;
    R := T.BoundingRectangle;
    Result := T.Text + ': x ' + FloatToStr(CoordToMMs(R.Left - B.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - B.XOrigin)) +
         ' y ' + FloatToStr(CoordToMMs(R.Bottom - B.YOrigin)) + '..' + FloatToStr(CoordToMMs(R.Top - B.YOrigin)) + #13#10;
End;

Procedure NoPmodSilk3;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    N   : TStringList;
    L   : TInterfaceList;
    T   : IPCB_Text;
    i   : Integer;
    S   : String;
    C   : IPCB_Component;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    N := TStringList.Create;
    N.Add('40'); N.Add('39'); N.Add('38'); N.Add('AI1'); N.Add('AI0'); N.Add('C28');
    L := TInterfaceList.Create;
    For i := 0 To 5 Do
    Begin
        T := FindLabel(B, N.Strings[i]);
        If T = Nil Then
        Begin
            ShowMessage('Refusing: label ' + N.Strings[i] + ' not found exactly once near JP4; nothing changed.');
            Exit;
        End;
        L.Add(T);
    End;
    S := '';
    For i := 0 To 5 Do
    Begin
        T := L.Items[i];
        If i < 3 Then S := S + Restack(B, T, 4.10) Else S := S + Restack(B, T, 5.00);
    End;
    C := B.GetPcbComponentByRefDes('JP4');
    If C <> Nil Then Begin C.BeginModify; C.NameOn := False; C.EndModify; End;
    C := B.GetPcbComponentByRefDes('JP3');
    If (C <> Nil) And (Abs(CoordToMMs(C.Y - B.YOrigin) - 17.29) < 0.002) Then
    Begin
        C.BeginModify; C.Y := C.Y + MMsToCoord(0.04); C.EndModify;     { 0.063 -> ~0.10 mm from R108-1 }
        S := S + 'JP3 now at y ' + FloatToStr(CoordToMMs(C.Y - B.YOrigin)) + #13#10;
    End;
    B.ViewManager_FullUpdate;
    ShowMessage('Restacked 6 labels above JP4, JP4 designator hidden:' + #13#10 + S);
End;
