{ Apply the validated X4 south-edge tab and place JST-S2B-PH-SM4-TB.
  Board-relative outline:
    (0,0) -> (25.30,0) -> (25.60,-3.70) -> (34.40,-3.70) ->
    (34.70,0) -> (60.96,0) -> (60.96,25.40) -> (0,25.40) -> (0,0)
  X4 origin (30.00,1.20), rotation 180 degrees. }

Const
    BW = 60.96;
    BH = 25.40;

Function X4TabGuard : Boolean;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    Result := (Doc <> Nil) And
              (Pos('\Zulu_A7_no_pmod\Rev_3\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) > 0);
    If Not Result Then ShowMessage('Refusing: focus the Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
End;

Function X4TabOldEdge(Board : IPCB_Board; T : IPCB_Track) : Boolean;
Var
    x1, y1, x2, y2, e : Double;
Begin
    e := 0.01;
    x1 := CoordToMMs(T.X1 - Board.XOrigin);
    y1 := CoordToMMs(T.Y1 - Board.YOrigin);
    x2 := CoordToMMs(T.X2 - Board.XOrigin);
    y2 := CoordToMMs(T.Y2 - Board.YOrigin);
    Result := ((Abs(x1) < e) Or (Abs(x1 - BW) < e)) And
              ((Abs(x2) < e) Or (Abs(x2 - BW) < e)) And
              ((Abs(y1) < e) Or (Abs(y1 - BH) < e)) And
              ((Abs(y2) < e) Or (Abs(y2 - BH) < e));
End;

Procedure X4TabEdge(Board : IPCB_Board; X1, Y1, X2, Y2 : Double);
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
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    T.Selected := True;
End;

Procedure ApplyX4Tab;
Var
    Board : IPCB_Board;
    It : IPCB_BoardIterator;
    T : IPCB_Track;
    Kill : TInterfaceList;
    C : IPCB_Component;
    PIt : IPCB_GroupIterator;
    P : IPCB_Pad;
    i, PadsFound : Integer;
    Msg : String;
Begin
    If Not X4TabGuard Then Exit;
    Board := PCBServer.GetCurrentPCBBoard;
    C := Board.GetPcbComponentByRefDes('X4');
    If (C = Nil) Or (C.Layer <> eTopLayer) Or (C.Pattern <> 'JST-S2B-PH-SM4-TB') Then
    Begin
        ShowMessage('Refusing: X4 is missing, not on Top, or does not use JST-S2B-PH-SM4-TB.');
        Exit;
    End;

    Kill := TInterfaceList.Create;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eMechanical1));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If X4TabOldEdge(Board, T) Then Kill.Add(T);
        T := It.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(It);
    If Kill.Count <> 4 Then
    Begin
        ShowMessage('Refusing: expected 4 rectangular Mechanical 1 edge tracks, found ' + IntToStr(Kill.Count));
        Kill.Free;
        Exit;
    End;

    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');
    PCBServer.PreProcess;
    Try
        For i := 0 To Kill.Count - 1 Do Board.RemovePCBObject(Kill.Items[i]);
        X4TabEdge(Board, 0.00, 0.00, 25.30, 0.00);
        X4TabEdge(Board, 25.30, 0.00, 25.60, -3.70);
        X4TabEdge(Board, 25.60, -3.70, 34.40, -3.70);
        X4TabEdge(Board, 34.40, -3.70, 34.70, 0.00);
        X4TabEdge(Board, 34.70, 0.00, 60.96, 0.00);
        X4TabEdge(Board, 60.96, 0.00, 60.96, 25.40);
        X4TabEdge(Board, 60.96, 25.40, 0.00, 25.40);
        X4TabEdge(Board, 0.00, 25.40, 0.00, 0.00);
        C.BeginModify;
        C.X := Board.XOrigin + MMsToCoord(30.00);
        C.Y := Board.YOrigin + MMsToCoord(1.20);
        C.Rotation := 180.0;
        C.EndModify;
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

    PadsFound := 0;
    Msg := '';
    PIt := C.GroupIterator_Create;
    PIt.AddFilter_ObjectSet(MkSet(ePadObject));
    P := PIt.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = '1') Or (P.Name = '2') Or (P.Name = 'MP1') Or (P.Name = 'MP2') Then
        Begin
            PadsFound := PadsFound + 1;
            Msg := Msg + ' ' + P.Name + '=' +
                   FormatFloat('0.000', CoordToMMs(P.X - Board.XOrigin)) + ',' +
                   FormatFloat('0.000', CoordToMMs(P.Y - Board.YOrigin));
        End;
        P := PIt.NextPCBObject;
    End;
    C.GroupIterator_Destroy(PIt);
    ShowMessage('X4 tab applied; outline points=' + IntToStr(Board.BoardOutline.PointCount) +
                '; pads found=' + IntToStr(PadsFound) + ':' + Msg +
                '. Expected 1=31.000,4.050 2=29.000,4.050 MP1=33.350,-1.700 MP2=26.650,-1.700.');
End;
