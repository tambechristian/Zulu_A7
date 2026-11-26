{ NoPmodRxtxLabelMove.pas -- 2026-11-26, Rev 4: the RXTX label placed by NoPmodLedLabels.pas at (35.725, 20.800) rot 90
  ran up into the X2 pin-name row beside 'C7' and read as a pin name. Move it to the find_spots.py candidate east of
  LD6: (37.900, 17.100), rot 90 (0.267 mm clearance in the ink model). Refuses unless exactly one free RXTX text sits
  at the old spot. Save, then DRC. }
Procedure NoPmodRxtxLabelMove;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    T, F : IPCB_Text;
    R   : TCoordRect;
    n   : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_4\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_4 board first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    n := 0;
    F := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (Not T.InComponent) And (T.Text = 'RXTX') Then Begin n := n + 1; F := T; End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (n <> 1) Or (Abs(CoordToMMs(F.XLocation - Brd.XOrigin) - 35.725) > 0.002) Or (Abs(CoordToMMs(F.YLocation - Brd.YOrigin) - 20.800) > 0.002) Then
    Begin
        ShowMessage('Refusing: expected one free RXTX text at (35.725, 20.800); found ' + IntToStr(n) + '. Nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    F.BeginModify;
    F.XLocation := Brd.XOrigin + MMsToCoord(37.9000);
    F.YLocation := Brd.YOrigin + MMsToCoord(17.1000);
    F.EndModify;
    PCBServer.PostProcess;
    R := F.BoundingRectangle;
    Brd.ViewManager_FullUpdate;
    ShowMessage('RXTX moved: x ' + FormatFloat('0.000', CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Right - Brd.XOrigin)) +
                ' y ' + FormatFloat('0.000', CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Top - Brd.YOrigin)) + '. Save, then DRC.');
End;
