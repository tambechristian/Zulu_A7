{ NoPmod_Title21.pas -- the free Top Overlay title 'ZULU A7 2.0' becomes 'ZULU A7 2.1'. Anchor, size and stroke stay.
  Refuses unless exactly one such text exists. }
Procedure Title21;
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
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
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
    s := 'before x ' + FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - Brd.XOrigin));
    PCBServer.PreProcess;
    T.BeginModify;
    T.Text := 'ZULU A7 2.1';
    T.EndModify;
    T.GraphicallyInvalidate;
    PCBServer.PostProcess;
    R := T.BoundingRectangle;
    ShowMessage('Title now ''' + T.Text + '''. ' + s + '; after x ' + FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - Brd.XOrigin)));
    Brd.ViewManager_FullUpdate;
End;
