{ Fab B title: the free Top Overlay text 'ZULU A7' (37.5, 5.0 mm, 1.6 mm high, 0.2 mm stroke) becomes 'ZULU A7 2.0'
  at 1.3 mm high with a 0.18 mm stroke. Its anchor stays where it is. Refuses unless exactly one such text exists. }
Procedure Title20;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    O, T : IPCB_Text;
    n : Integer;
    R : TCoordRect;
    s : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_Fab_B\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_Fab_B\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    n := 0;
    T := Nil;
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If (Not O.InComponent) And (O.Text = 'ZULU A7') Then
        Begin
            T := O;
            n := n + 1;
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 1 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(n) + ' free ZULU A7 texts on Top Overlay; nothing changed.');
        Exit;
    End;
    R := T.BoundingRectangle;
    s := 'before x ' + FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - Brd.XOrigin)) +
        ' y ' + FloatToStr(CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FloatToStr(CoordToMMs(R.Top - Brd.YOrigin));
    PCBServer.PreProcess;
    T.BeginModify;
    T.Text := 'ZULU A7 2.0';
    T.Size := MMsToCoord(1.3);
    T.Width := MMsToCoord(0.18);
    T.EndModify;
    T.GraphicallyInvalidate;
    PCBServer.PostProcess;
    R := T.BoundingRectangle;
    ShowMessage('Title now ''' + T.Text + '''. ' + s + '; after x ' + FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' +
        FloatToStr(CoordToMMs(R.Right - Brd.XOrigin)) + ' y ' + FloatToStr(CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' +
        FloatToStr(CoordToMMs(R.Top - Brd.YOrigin)));
    Brd.ViewManager_FullUpdate;
End;
