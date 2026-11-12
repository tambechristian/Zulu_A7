{ NoPmod_Silk2.pas -- 2026-11-12. Zulu_a7_no_pmod Rev 2: JP4 sits on the X2 labels of pins 40/39/38 (numbers) and
  AI1/AI0/C28 (names). The only free silk between JP4's pads and the microSD socket above is about 1.8 mm, so both rows
  are shrunk to 0.8 mm text and restacked above JP4: numbers with their bottom at y 4.10, names at y 5.00. Each label
  keeps its horizontal centre. Refuses unless all six are found exactly once. }
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
            If (CoordToMMs(R.Left - B.XOrigin) < 9) And (CoordToMMs(R.Bottom - B.YOrigin) > 1.5) And (CoordToMMs(R.Bottom - B.YOrigin) < 4.0) Then
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
    T.Size := MMsToCoord(0.8);
    T.Width := MMsToCoord(0.12);
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

Procedure NoPmodSilk2;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    N   : TStringList;
    L   : TInterfaceList;
    T   : IPCB_Text;
    i   : Integer;
    S   : String;
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
    B.ViewManager_FullUpdate;
    ShowMessage('Restacked 6 labels above JP4:' + #13#10 + S);
End;
