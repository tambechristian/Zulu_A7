{ NoPmod_HideJP3.pas -- 2026-11-12. Zulu_a7_no_pmod Rev 2: hide JP3's designator (user request; it sits off the
  west edge beside the JTAG column). JP4's designator is already hidden. }
Procedure NoPmodHideJP3;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    C   : IPCB_Component;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    C := B.GetPcbComponentByRefDes('JP3');
    If C = Nil Then
    Begin
        ShowMessage('Refusing: JP3 not found.');
        Exit;
    End;
    C.BeginModify;
    C.NameOn := False;
    C.EndModify;
    B.ViewManager_FullUpdate;
    ShowMessage('JP3 designator visible: ' + BoolToStr(C.NameOn, True) + '; JP4 designator visible: ' +
                BoolToStr(B.GetPcbComponentByRefDes('JP4').NameOn, True));
End;
