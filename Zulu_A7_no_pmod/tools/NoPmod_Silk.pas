{ NoPmod_Silk.pas -- 2026-11-08. JP3's pads landed on six X2 labels. Moves '16','15','14' down 2.28 mm and 'C13','C12',
  'C11' down 2.78 mm, below JP3's pad row; hides the R34 (Bottom) and JP3 designators, which sat on pads (JP3's would hit X2's lands). }
Procedure NoPmodSilk;
Var
    Doc   : IDocument;
    B     : IPCB_Board;
    It    : IPCB_BoardIterator;
    T     : IPCB_Text;
    C     : IPCB_Component;
    L     : TInterfaceList;
    D     : TStringList;
    i, n  : Integer;
    S     : String;
    R     : TCoordRect;
    y     : Double;
    dy    : Double;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (Not T.InComponent) And ((T.Text = '16') Or (T.Text = '15') Or (T.Text = '14') Or (T.Text = 'C13') Or (T.Text = 'C12') Or (T.Text = 'C11')) Then
        Begin
            R := T.BoundingRectangle;
            y := CoordToMMs(R.Bottom - B.YOrigin);
            If (y > 20.3) And (y < 22.2) Then L.Add(T);
        End;
        T := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    If L.Count <> 6 Then
    Begin
        ShowMessage('Refusing: expected 6 labels, found ' + IntToStr(L.Count));
        Exit;
    End;
    n := 0;
    S := '';
    For i := 0 To L.Count - 1 Do
    Begin
        T := L.Items[i];
        If Copy(T.Text, 1, 1) = 'C' Then dy := -2.78 Else dy := -2.28;
        T.BeginModify;
        T.YLocation := T.YLocation + MMsToCoord(dy);
        If T.Text = 'C12' Then T.XLocation := T.XLocation + MMsToCoord(1.90);   { clear of X3 pad G4 }
        If T.Text = 'C11' Then T.XLocation := T.XLocation + MMsToCoord(2.10);   { clear of the moved C12 }
        T.EndModify;
        R := T.BoundingRectangle;
        S := S + T.Text + ' y ' + FloatToStr(CoordToMMs(R.Bottom - B.YOrigin)) + #13#10;
        n := n + 1;
    End;
    C := B.GetPcbComponentByRefDes('R34');
    If C <> Nil Then Begin C.BeginModify; C.NameOn := False; C.EndModify; End;
    C := B.GetPcbComponentByRefDes('JP3');
    If C <> Nil Then Begin C.BeginModify; C.NameOn := False; C.EndModify; End;
    B.ViewManager_FullUpdate;
    ShowMessage('Moved ' + IntToStr(n) + ' labels:' + #13#10 + S);
End;
