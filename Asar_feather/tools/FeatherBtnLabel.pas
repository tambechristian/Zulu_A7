{ FeatherBtnLabel.pas -- 2026-11-06: the moved R80 and R81 sit where BTN's designator used to print, and the auto-positions do not
  fit (below the part: y 1.93..3.04, into X2's pads). BTN's designator goes off and a free 'BTN' text takes its place in the strip
  between X2's pads and BTN, the same way 'ASAR A7' was made: 0.6 mm high, so that it keeps 0.254 mm from X2's mask and BTN's silk.
  Refuses if the text exists. Run BtnLabel with asar_feather.PcbDoc focused. }

Procedure BtnLabel;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    T   : IPCB_Text;
    C   : IPCB_Component;
    R   : TCoordRect;
    Dup : Boolean;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Dup := False;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (T.Text = 'BTN') And (Not T.InComponent) Then Dup := True;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Dup Then
    Begin
        ShowMessage('Refusing: a free BTN text exists already.');
        Exit;
    End;
    C := Brd.GetPcbComponentByRefDes('BTN');
    C.BeginModify;
    C.NameOn := False;
    C.EndModify;
    T := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
    T.XLocation := Brd.XOrigin + MMsToCoord(42.5);
    T.YLocation := Brd.YOrigin + MMsToCoord(2.5);
    T.Layer := eTopOverlay;
    T.Text := 'BTN';
    T.Size := MMsToCoord(0.6);
    T.Width := MMsToCoord(0.1);
    T.Rotation := 0;
    T.UseTTFonts := False;
    Brd.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    R := T.BoundingRectangle;
    Brd.ViewManager_FullUpdate;
    ShowMessage('BTN label box x ' + FloatToStr(CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(R.Right - Brd.XOrigin)) +
                ' y ' + FloatToStr(CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FloatToStr(CoordToMMs(R.Top - Brd.YOrigin)) + '. Save.');
End;
