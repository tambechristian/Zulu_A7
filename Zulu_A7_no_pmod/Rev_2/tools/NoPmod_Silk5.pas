{ NoPmod_Silk5.pas -- 2026-11-12, third DRC pass on Zulu_a7_no_pmod Rev 2. JP3's pin 1 is a SQUARE pad: its bottom edge was
  0.10 mm above R108-1, leaving a 0.003 mm Bottom mask web (rule 0.1). JP3 goes up 0.10 mm (and '1V0' with it, to keep
  its silk-to-mask clearance to JP3-3). The JTAG tracks still end inside the pads. }
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

Procedure NoPmodSilk5;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    C   : IPCB_Component;
    T   : IPCB_Text;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    C := B.GetPcbComponentByRefDes('JP3');
    If (C = Nil) Or (Abs(CoordToMMs(C.Y - B.YOrigin) - 17.33) > 0.002) Then
    Begin
        ShowMessage('Refusing: JP3 is not at y 17.33.');
        Exit;
    End;
    T := FindIn(B, '1V0', 0, 3.5, 20.5, 22.5);
    If T = Nil Then
    Begin
        ShowMessage('Refusing: 1V0 label not found exactly once.');
        Exit;
    End;
    C.BeginModify; C.Y := C.Y + MMsToCoord(0.10); C.EndModify;
    T.BeginModify; T.YLocation := T.YLocation + MMsToCoord(0.10); T.EndModify;
    B.ViewManager_FullUpdate;
    ShowMessage('JP3 now at y ' + FloatToStr(CoordToMMs(C.Y - B.YOrigin)) + '; 1V0 raised 0.10 mm.');
End;
