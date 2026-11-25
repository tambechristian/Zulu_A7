{ NoPmodTitle24.pas -- 2026-11-21, no-PMOD Rev 3: the Top Overlay board title 'ZULU A7 2.3' (Rev 2's) becomes
  'ZULU A7 2.4' so a Rev 3 board can be told from a Rev 2 one. Same length, same font and position.
  Refuses unless the Rev_3 Zulu_a7_no_pmod.PcbDoc is focused and the text is found exactly once. Save after. }
Procedure SetTitle24;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    T, Hit : IPCB_Text;
    n : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_3\', Brd.FileName) = 0) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_3 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    n := 0;
    Hit := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If T.Text = 'ZULU A7 2.3' Then
        Begin
            Hit := T;
            n := n + 1;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 1 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(n) + ' "ZULU A7 2.3" texts.');
        Exit;
    End;
    PCBServer.PreProcess;
    Hit.BeginModify;
    Hit.Text := 'ZULU A7 2.4';
    Hit.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Title set to ZULU A7 2.4.');
End;
