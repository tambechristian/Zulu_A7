{ SeriesRDesig.pas -- 2026-11-13. Moves U1's visible designator from (39.2168, 16.6251) to (39.7000, 16.5500), rot 0
  (docs/dq_series_resistors.md decision 13 / designator_moves in si/series_r/dq_series_r_plan.json): at its old place it
  sits 0.045 mm from R132-1's mask opening (Silk To Solder Mask 0.254 is in the batch DRC). SeriesRPlace2 set the
  location properties but they did not take, so this uses MoveToXY on the text itself. Refuses unless the text is still
  at its old place. Run SeriesRDesig with Zulu_a7_no_pmod.PcbDoc focused, check the message, save. }

Procedure SeriesRDesig;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    U   : IPCB_Component;
    T   : IPCB_Text;
    x, y : Double;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    U := Brd.GetPcbComponentByRefDes('U1');
    If U = Nil Then Begin ShowMessage('Refusing: U1 not found.'); Exit; End;
    T := U.Name;
    x := CoordToMMs(T.XLocation - Brd.XOrigin); y := CoordToMMs(T.YLocation - Brd.YOrigin);
    If (Abs(x - 39.2168) > 0.002) Or (Abs(y - 16.6251) > 0.002) Then
    Begin
        ShowMessage('Refusing: U1 designator is at ' + FormatFloat('0.0000', x) + ',' + FormatFloat('0.0000', y) + ', not at its old place; nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    U.BeginModify;
    U.NameAutoPosition := eAutoPos_Manual;
    U.EndModify;
    T.BeginModify;
    T.MoveToXY(Brd.XOrigin + MMsToCoord(39.7000), Brd.YOrigin + MMsToCoord(16.5500));
    T.Rotation := 0;
    T.EndModify;
    T.GraphicallyInvalidate;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    x := CoordToMMs(T.XLocation - Brd.XOrigin); y := CoordToMMs(T.YLocation - Brd.YOrigin);
    ShowMessage('U1 designator now at ' + FormatFloat('0.0000', x) + ',' + FormatFloat('0.0000', y) + ' rot ' + FormatFloat('0', T.Rotation) +
        ' (target 39.7000,16.5500 rot 0). Undo (Ctrl+Z) if off; else save.');
End;
