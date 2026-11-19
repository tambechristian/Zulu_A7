{ NoPmod_Silk4.pas -- 2026-11-12, second DRC pass on Zulu_a7_no_pmod Rev 2.
  - JP3 x 1.40 -> 1.10: its pad 1 left a 0.003 mm Bottom mask sliver to R108-1 (rule 0.1 mm); copper stays 0.34 mm
    inside the board edge, and the JTAG tracks still end inside the moved pads.
  - '40'/'39'/'38' down 0.03 mm and 'AI1'/'AI0'/'C28' up 0.03 mm: the two rows were 0.20 mm apart (rule 0.254).
  - '1V0' up 0.03 mm: 0.24 mm from JP3-3's mask (rule 0.254).
  - TMS reached JP3-2 on L4 at (1.625, 16.725), which is outside the moved pad: an L4 stub joins it to the new centre.
  Refuses unless each label is found exactly once in its window. }
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

Procedure NoPmodSilk4;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    C   : IPCB_Component;
    N   : TStringList;
    L   : TInterfaceList;
    T   : IPCB_Text;
    i   : Integer;
    dy  : Double;
    O   : IPCB_Track;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    C := B.GetPcbComponentByRefDes('JP3');
    If (C = Nil) Or (Abs(CoordToMMs(C.X - B.XOrigin) - 1.40) > 0.002) Then
    Begin
        ShowMessage('Refusing: JP3 is not at x 1.40.');
        Exit;
    End;
    N := TStringList.Create;
    N.Add('40'); N.Add('39'); N.Add('38'); N.Add('AI1'); N.Add('AI0'); N.Add('C28'); N.Add('1V0');
    L := TInterfaceList.Create;
    For i := 0 To 6 Do
    Begin
        If i < 3 Then T := FindIn(B, N.Strings[i], 0, 9, 3.9, 5.0)
        Else If i < 6 Then T := FindIn(B, N.Strings[i], 0, 9, 5.0, 6.1)
        Else T := FindIn(B, N.Strings[i], 0, 3.5, 20.5, 22.5);
        If T = Nil Then
        Begin
            ShowMessage('Refusing: label ' + N.Strings[i] + ' not found exactly once; nothing changed.');
            Exit;
        End;
        L.Add(T);
    End;
    For i := 0 To 6 Do
    Begin
        T := L.Items[i];
        If i < 3 Then dy := -0.03 Else dy := 0.03;
        T.BeginModify;
        T.YLocation := T.YLocation + MMsToCoord(dy);
        T.EndModify;
    End;
    C.BeginModify;
    C.X := C.X - MMsToCoord(0.30);
    C.EndModify;
    O := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    O.X1 := B.XOrigin + MMsToCoord(1.625); O.Y1 := B.YOrigin + MMsToCoord(16.725);
    O.X2 := B.XOrigin + MMsToCoord(1.10);  O.Y2 := B.YOrigin + MMsToCoord(17.33);
    O.Layer := eMidLayer2; O.Width := MMsToCoord(0.0762); O.Net := NetNamed(B, 'TMS');
    B.AddPCBObject(O);
    B.ViewManager_FullUpdate;
    ShowMessage('JP3 now at x ' + FloatToStr(CoordToMMs(C.X - B.XOrigin)) + ' y ' + FloatToStr(CoordToMMs(C.Y - B.YOrigin)) + '; 7 labels nudged.');
End;
