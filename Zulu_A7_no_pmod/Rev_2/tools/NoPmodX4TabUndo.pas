{ Restore the original flat 60.96 x 25.40 mm Rev_2 board outline.
  This removes only the eight validated X4 edge-tab Mechanical 1 segments. }

Const
    BW = 60.96;
    BH = 25.40;

Function X4FlatGuard : Boolean;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    Result := (Doc <> Nil) And
              (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc',
                   Doc.DM_FullPath) > 0);
    If Not Result Then ShowMessage('Refusing: focus the Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
End;

Function X4FlatNear(A, B : Double) : Boolean;
Begin
    Result := Abs(A - B) < 0.01;
End;

Function X4FlatSegment(Board : IPCB_Board; T : IPCB_Track;
                       AX, AY, BX, BY : Double) : Boolean;
Var
    X1, Y1, X2, Y2 : Double;
Begin
    X1 := CoordToMMs(T.X1 - Board.XOrigin);
    Y1 := CoordToMMs(T.Y1 - Board.YOrigin);
    X2 := CoordToMMs(T.X2 - Board.XOrigin);
    Y2 := CoordToMMs(T.Y2 - Board.YOrigin);
    Result := (X4FlatNear(X1, AX) And X4FlatNear(Y1, AY) And
               X4FlatNear(X2, BX) And X4FlatNear(Y2, BY)) Or
              (X4FlatNear(X2, AX) And X4FlatNear(Y2, AY) And
               X4FlatNear(X1, BX) And X4FlatNear(Y1, BY));
End;

Function X4FlatTabEdge(Board : IPCB_Board; T : IPCB_Track) : Boolean;
Begin
    Result :=
        X4FlatSegment(Board, T,  0.00,  0.00, 25.30,  0.00) Or
        X4FlatSegment(Board, T, 25.30,  0.00, 25.60, -3.70) Or
        X4FlatSegment(Board, T, 25.60, -3.70, 34.40, -3.70) Or
        X4FlatSegment(Board, T, 34.40, -3.70, 34.70,  0.00) Or
        X4FlatSegment(Board, T, 34.70,  0.00, 60.96,  0.00) Or
        X4FlatSegment(Board, T, 60.96,  0.00, 60.96, 25.40) Or
        X4FlatSegment(Board, T, 60.96, 25.40,  0.00, 25.40) Or
        X4FlatSegment(Board, T,  0.00, 25.40,  0.00,  0.00);
End;

Procedure X4FlatAddEdge(Board : IPCB_Board; X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := Board.XOrigin + MMsToCoord(X1);
    T.Y1 := Board.YOrigin + MMsToCoord(Y1);
    T.X2 := Board.XOrigin + MMsToCoord(X2);
    T.Y2 := Board.YOrigin + MMsToCoord(Y2);
    T.Layer := eMechanical1;
    T.Width := MMsToCoord(0.10);
    Board.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                  PCBM_BoardRegisteration, T.I_ObjectAddress);
    T.Selected := True;
End;

Procedure RestoreFlatOutline;
Var
    Board : IPCB_Board;
    It : IPCB_BoardIterator;
    T : IPCB_Track;
    Kill : TInterfaceList;
    I : Integer;
Begin
    If Not X4FlatGuard Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    Kill := TInterfaceList.Create;

    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eMechanical1));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If X4FlatTabEdge(Board, T) Then Kill.Add(T);
        T := It.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(It);

    If Kill.Count <> 8 Then
    Begin
        ShowMessage('Refusing: expected all 8 X4 tab-outline segments, found ' +
                    IntToStr(Kill.Count) + '. Nothing changed.');
        Kill.Free;
        Exit;
    End;

    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');
    PCBServer.PreProcess;
    Try
        For I := 0 To Kill.Count - 1 Do Board.RemovePCBObject(Kill.Items[I]);
        X4FlatAddEdge(Board, 0.00, 0.00, BW, 0.00);
        X4FlatAddEdge(Board, BW, 0.00, BW, BH);
        X4FlatAddEdge(Board, BW, BH, 0.00, BH);
        X4FlatAddEdge(Board, 0.00, BH, 0.00, 0.00);
    Finally
        PCBServer.PostProcess;
        Kill.Free;
    End;

    Board.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Mode', 'BOARDOUTLINE_FROM_SEL_PRIMS');
    RunProcess('PCB:PlaceBoardOutline');
    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');
    ShowMessage('Original flat 60.96 x 25.40 mm board outline restored. Save only the PCB.');
End;
