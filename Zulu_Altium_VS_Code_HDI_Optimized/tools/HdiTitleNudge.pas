{ HdiTitleNudge.pas -- 2026-10-07. After X2PinLabels.pas the 'ZULU A7' title (1.6 mm, anchor 37.5, 5.25) ran
  0.05 mm under U1's 10 x 10 mm CPG236 body (body starts at y 6.9; title ink top was 6.95). Move the anchor to
  (37.5, 5.0): ink top 6.70, 0.20 mm clear of the body, still 0.36 mm above the pin 22-29 name line.
  Run NudgeHdiTitle with the HDI PcbDoc focused, run DRC, save. }

Procedure NudgeHdiTitle;
Var
    WS  : IWorkspace;
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    T   : IPCB_Text;
    N   : Integer;
Begin
    WS := GetWorkspace;
    Doc := WS.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_Altium_VS_Code_HDI_Optimized\Imported zulu_a7.PrjPcb\zulu_a7_hdi_optimized.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the HDI PcbDoc.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    N := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (T.Text = 'ZULU A7') And (Abs(CoordToMMs(T.XLocation) - 37.5) < 0.001) And (Abs(CoordToMMs(T.YLocation) - 5.25) < 0.001) Then
        Begin
            T.BeginModify;
            T.YLocation := MMsToCoord(5.0);
            T.EndModify;
            N := N + 1;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Moved ' + IntToStr(N) + ' title(s) to (37.5, 5.0). Expected 1. Run DRC, then save.');
End;
