{ FeatherOutline.pas -- 2026-10-23. Board shape for asar_feather.PcbDoc by the method that worked on the
  production board (ZuluBoardOutline.pas SetBoardOutlineViaTracks): four 0.1 mm tracks on Mechanical 1 around
  0,0 .. 50.80,22.86 mm, selected, then Design > Board Shape > Define from Selected Objects.
  (Writing Board.BoardOutline directly reported success but did not change the shape.) }

Procedure FeatherEdge(Board : IPCB_Board; ax1, ay1, ax2, ay2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(ax1); T.Y1 := MMsToCoord(ay1);
    T.X2 := MMsToCoord(ax2); T.Y2 := MMsToCoord(ay2);
    T.Layer := eMechanical1;
    T.Width := MMsToCoord(0.1);
    Board.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_BroadCast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    T.Selected := True;
End;

Procedure FeatherOutlineViaTracks;
Var
    Board : IPCB_Board;
    Doc   : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Board := PCBServer.GetCurrentPCBBoard;
    Board.CurrentLayer := eMechanical1;
    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');
    PCBServer.PreProcess;
    Try
        FeatherEdge(Board, 0, 0, 50.8, 0);
        FeatherEdge(Board, 50.8, 0, 50.8, 22.86);
        FeatherEdge(Board, 50.8, 22.86, 0, 22.86);
        FeatherEdge(Board, 0, 22.86, 0, 0);
    Finally
        PCBServer.PostProcess;
    End;
    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Mode', 'BOARDOUTLINE_FROM_SEL_PRIMS');
    RunProcess('PCB:PlaceBoardOutline');
    ShowMessage('Feather outline tracks placed on Mechanical 1 and board shape redefined. Run ReportFeatherOutline.');
End;
