{ NoPmod_TurnJP4.pas -- 2026-11-12. Zulu_a7_no_pmod Rev 2: after the copper plan has moved JP4 to the west-edge column
  (origin 1.10, 8.89), turn it to rotation 90 so its pins run +y: TDI 6.35, TDO 8.89, VCC3V3 11.43. }

Function GuardDoc : Boolean;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    Result := (Doc <> Nil) And (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) > 0);
    If Not Result Then ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
End;

Procedure NoPmodTurnJP4;
Var
    Board : IPCB_Board;
    C     : IPCB_Component;
Begin
    If Not GuardDoc Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    C := Board.GetPcbComponentByRefDes('JP4');
    If C = Nil Then Begin ShowMessage('No JP4.'); Exit; End;
    If (Abs(CoordToMMs(C.X - Board.XOrigin) - 1.10) > 0.01) Or (Abs(CoordToMMs(C.Y - Board.YOrigin) - 8.89) > 0.01) Then
    Begin
        ShowMessage('Refusing: run the copper plan first (JP4 must be at 1.10, 8.89).');
        Exit;
    End;
    C.BeginModify;
    C.Rotation := 90;
    C.EndModify;
    Board.ViewManager_FullUpdate;
    ShowMessage('JP4 rotation now ' + FloatToStr(C.Rotation));
End;

