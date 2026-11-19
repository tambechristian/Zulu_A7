{ FabB_Title22.pas -- Fab B Rev 2 (2026-11-12, user): the free Top Overlay title 'ZULU A7 2.0' (37.7, 5.0 mm, 1.3 mm high,
  0.18 mm stroke) becomes 'ZULU A7 2.2' (Rev 1 = 2.0, the no-PMOD board = 2.1). Size, stroke and anchor unchanged.
  Refuses unless exactly one such text exists. Copied from FabB_Title.pas. }
Procedure Title22;
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
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc first.');
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
        If (Not O.InComponent) And (O.Text = 'ZULU A7 2.0') Then
        Begin
            T := O;
            n := n + 1;
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 1 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(n) + ' free ZULU A7 2.0 texts on Top Overlay; nothing changed.');
        Exit;
    End;
    R := T.BoundingRectangle;
    s := 'before x ' + FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - Brd.XOrigin)) +
        ' y ' + FloatToStr(CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FloatToStr(CoordToMMs(R.Top - Brd.YOrigin));
    PCBServer.PreProcess;
    T.BeginModify;
    T.Text := 'ZULU A7 2.2';
    T.EndModify;
    T.GraphicallyInvalidate;
    PCBServer.PostProcess;
    R := T.BoundingRectangle;
    ShowMessage('Title now ''' + T.Text + '''. ' + s + '; after x ' + FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' +
        FloatToStr(CoordToMMs(R.Right - Brd.XOrigin)) + ' y ' + FloatToStr(CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' +
        FloatToStr(CoordToMMs(R.Top - Brd.YOrigin)));
    Brd.ViewManager_FullUpdate;
End;
