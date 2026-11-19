{ NoPmod_Board.pas -- 2026-11-08. Zulu_a7_no_pmod: cut the board to 2.400 x 1.000 in (60.96 x 25.40 mm).
  NoPmodOutline  replaces the four Mechanical 1 edge tracks and redefines the board shape from them (the method that
                 worked on production and on the Feather; writing Board.BoardOutline directly does not stick).
  NoPmodPolygons moves the east vertices of the L2 and L5 pours to the new 0.25 mm pullback and rebuilds them. }

Const
    OLD_W = 69.85;
    NEW_W = 60.96;
    H     = 25.40;

Function GuardDoc : Boolean;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    Result := (Doc <> Nil) And (Pos('\Zulu_A7_no_pmod\Rev_1\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) > 0);
    If Not Result Then ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
End;

Function OnOldEdge(Board : IPCB_Board; T : IPCB_Track) : Boolean;
Var
    x1, y1, x2, y2, e : Double;
Begin
    e := 0.01;
    x1 := CoordToMMs(T.X1 - Board.XOrigin); y1 := CoordToMMs(T.Y1 - Board.YOrigin);
    x2 := CoordToMMs(T.X2 - Board.XOrigin); y2 := CoordToMMs(T.Y2 - Board.YOrigin);
    Result := ((Abs(x1) < e) Or (Abs(x1 - OLD_W) < e)) And ((Abs(x2) < e) Or (Abs(x2 - OLD_W) < e))
          And ((Abs(y1) < e) Or (Abs(y1 - H) < e)) And ((Abs(y2) < e) Or (Abs(y2 - H) < e));
End;

Procedure Edge(Board : IPCB_Board; ax1, ay1, ax2, ay2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := Board.XOrigin + MMsToCoord(ax1); T.Y1 := Board.YOrigin + MMsToCoord(ay1);
    T.X2 := Board.XOrigin + MMsToCoord(ax2); T.Y2 := Board.YOrigin + MMsToCoord(ay2);
    T.Layer := eMechanical1;
    T.Width := MMsToCoord(0.1);
    Board.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_BroadCast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    T.Selected := True;
End;

Procedure NoPmodOutline;
Var
    Board : IPCB_Board;
    It    : IPCB_BoardIterator;
    T     : IPCB_Track;
    Kill  : TInterfaceList;
    i     : Integer;
Begin
    If Not GuardDoc Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    Kill := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eMechanical1));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If OnOldEdge(Board, T) Then Kill.Add(T);
        T := It.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(It);
    If Kill.Count <> 4 Then
    Begin
        ShowMessage('Refusing: expected 4 Mechanical 1 edge tracks, found ' + IntToStr(Kill.Count));
        Exit;
    End;
    Board.CurrentLayer := eMechanical1;
    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');
    PCBServer.PreProcess;
    Try
        For i := 0 To Kill.Count - 1 Do Board.RemovePCBObject(Kill.Items[i]);
        Edge(Board, 0, 0, NEW_W, 0);
        Edge(Board, NEW_W, 0, NEW_W, H);
        Edge(Board, NEW_W, H, 0, H);
        Edge(Board, 0, H, 0, 0);
    Finally
        PCBServer.PostProcess;
    End;
    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Mode', 'BOARDOUTLINE_FROM_SEL_PRIMS');
    RunProcess('PCB:PlaceBoardOutline');
    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');
    ShowMessage('NoPmodOutline done: outline points = ' + IntToStr(Board.BoardOutline.PointCount) + ', east x = ' +
                FloatToStr(CoordToMMs(Board.BoardOutline.Segments[1].vx - Board.XOrigin)));
End;


Procedure NoPmodTurnR5;
Var
    Board : IPCB_Board;
    C     : IPCB_Component;
Begin
    If Not GuardDoc Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    C := Board.GetPcbComponentByRefDes('R5');
    If C = Nil Then Begin ShowMessage('No R5.'); Exit; End;
    If Abs(CoordToMMs(C.X - Board.XOrigin) - 56.70) > 0.01 Then
    Begin
        ShowMessage('Refusing: run the copper plan first (R5 must be at x 56.70).');
        Exit;
    End;
    C.BeginModify;
    C.Rotation := 180;
    C.EndModify;
    Board.ViewManager_FullUpdate;
    ShowMessage('R5 rotation now ' + FloatToStr(C.Rotation));
End;

Procedure NoPmodPolygons;
Var
    Board : IPCB_Board;
    It    : IPCB_BoardIterator;
    P     : IPCB_Polygon;
    Seg   : TPolySegment;
    L     : TInterfaceList;
    i, k, n, moved : Integer;
    x     : Double;
    S     : String;
Begin
    If Not GuardDoc Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        L.Add(P);
        P := It.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(It);
    If L.Count <> 2 Then
    Begin
        ShowMessage('Refusing: expected 2 polygons, found ' + IntToStr(L.Count));
        Exit;
    End;
    PCBServer.SystemOptions.PolygonRepour := eAlwaysRepour;
    S := '';
    For i := 0 To L.Count - 1 Do
    Begin
        P := L.Items[i];
        n := P.PointCount;
        moved := 0;
        P.BeginModify;
        For k := 0 To n - 1 Do
        Begin
            Seg := P.Segments[k];
            x := CoordToMMs(Seg.vx - Board.XOrigin);
            If x > NEW_W Then
            Begin
                Seg.vx := Board.XOrigin + MMsToCoord(NEW_W - 0.25);
                P.Segments[k] := Seg;
                moved := moved + 1;
            End;
        End;
        P.EndModify;
        P.Rebuild;
        S := S + P.Name + ': ' + IntToStr(moved) + ' vertices moved of ' + IntToStr(n) + #13#10;
    End;
    Board.ViewManager_FullUpdate;
    ShowMessage('NoPmodPolygons done.' + #13#10 + S);
End;
