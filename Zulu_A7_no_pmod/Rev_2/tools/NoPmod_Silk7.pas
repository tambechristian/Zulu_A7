{ NoPmod_Silk7.pas -- 2026-11-12, fifth DRC pass on Zulu_a7_no_pmod Rev 2. Raising '20' put it 0.223 mm from X2-20's
  mask (rule 0.254), so '20' goes back down 0.09 mm and '1V0' is shrunk to 85 % height with its bottom edge kept, which
  opens the '1V0'-'20' gap instead. }
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

Function NetNamed(B : IPCB_Board; AName : String) : IPCB_Net;
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    Result := Nil;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = AName Then Result := N;
        N := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
End;

Procedure NoPmodSilk7;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    T   : IPCB_Text;
    U   : IPCB_Text;
    R, R2 : TCoordRect;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    T := FindIn(B, '20', 0, 3.5, 22.0, 23.8);
    If T = Nil Then
    Begin
        ShowMessage('Refusing: label 20 not found exactly once.');
        Exit;
    End;
    T.BeginModify; T.YLocation := T.YLocation - MMsToCoord(0.09); T.EndModify;
    U := FindIn(B, '1V0', 0, 3.5, 20.5, 22.5);
    If U = Nil Then
    Begin
        ShowMessage('1V0 not found exactly once; only 20 was moved.');
        Exit;
    End;
    R := U.BoundingRectangle;
    U.BeginModify; U.Size := Round(U.Size * 0.85); U.EndModify;
    R2 := U.BoundingRectangle;
    U.BeginModify; U.YLocation := U.YLocation + (R.Bottom - R2.Bottom); U.XLocation := U.XLocation + ((R.Left + R.Right) Div 2 - (R2.Left + R2.Right) Div 2); U.EndModify;
    B.ViewManager_FullUpdate;
    ShowMessage('20 back down 0.09 mm; 1V0 now ' + FloatToStr(CoordToMMs(U.Size)) + ' mm high.');
End;
