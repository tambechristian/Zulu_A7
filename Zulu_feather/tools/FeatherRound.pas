{ FeatherRound.pas -- 2026-10-23. Rounded Feather outline and plane layers that follow it, for zulu_feather.PcbDoc.
  Run in this order, each from File > Run Script:
    PlaneReport        reads only: every split-plane / region / polygon object on L2 and L5, with net and extent
    ArcCanary          places one test arc on Mechanical 1, reads it back, removes it (proves the arc names)
    RoundOutline       replaces the Mechanical 1 outline with 4 lines + 4 arcs (radius CR) and redefines the board
                       shape from them (the method that worked for FeatherOutline.pas)
    DeletePlaneShapes  removes the split-plane / region objects left on L2/L5 at the old 69.85 x 25.4 mm extent
    PlaneReport        again: see what Altium regenerated
    AssignPlaneNets    L2 objects -> GND, L5 objects -> VCC3V3 (the production board's ZuluPlaneNets method) }

Const
    FW = 50.8;
    FH = 22.86;
    CR = 2.54;          { corner radius, 0.1 in }

Function FBoard : IPCB_Board;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
End;

Function IsPlane(L : TLayer) : Boolean;
Begin
    Result := (L = eInternalPlane1) Or (L = eInternalPlane2);
End;

Procedure CollectPlaneShapes(Brd : IPCB_Board; List : TInterfaceList);
Var
    It : IPCB_BoardIterator;
    O  : IPCB_Primitive;
Begin
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject, eSplitPlaneObject, eRegionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If IsPlane(O.Layer) Then List.Add(O);
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure PlaneReport;
Var
    Brd : IPCB_Board;
    L   : TInterfaceList;
    I   : Integer;
    O   : IPCB_Primitive;
    R   : TCoordRect;
    S, N : String;
Begin
    Brd := FBoard;
    If Brd = Nil Then Exit;
    L := TInterfaceList.Create;
    CollectPlaneShapes(Brd, L);
    S := 'Plane-layer shapes: ' + IntToStr(L.Count) + #13#10;
    For I := 0 To L.Count - 1 Do
    Begin
        O := L.Items[I];
        R := O.BoundingRectangle;
        If O.Net = Nil Then N := '(none)' Else N := O.Net.Name;
        S := S + 'kind ' + IntToStr(O.ObjectId) + '  ' + Layer2String(O.Layer) + '  net ' + N + '  x ' +
             FloatToStr(CoordToMMs(R.Left)) + '..' + FloatToStr(CoordToMMs(R.Right)) + '  y ' +
             FloatToStr(CoordToMMs(R.Bottom)) + '..' + FloatToStr(CoordToMMs(R.Top)) + #13#10;
    End;
    L.Free;
    ShowMessage(S);
End;

Function NewArc(Brd : IPCB_Board; CX, CY, R, A1, A2 : Double) : IPCB_Arc;
Begin
    Result := PCBServer.PCBObjectFactory(eArcObject, eNoDimension, eCreate_Default);
    Result.XCenter := MMsToCoord(CX);
    Result.YCenter := MMsToCoord(CY);
    Result.Radius := MMsToCoord(R);
    Result.StartAngle := A1;
    Result.EndAngle := A2;
    Result.LineWidth := MMsToCoord(0.1);
    Result.Layer := eMechanical1;
    Brd.AddPCBObject(Result);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_BroadCast, PCBM_BoardRegisteration, Result.I_ObjectAddress);
End;

Procedure ArcCanary;
Var
    Brd : IPCB_Board;
    A   : IPCB_Arc;
    S   : String;
Begin
    Brd := FBoard;
    If Brd = Nil Then Exit;
    A := NewArc(Brd, 25.4, 11.43, 1.0, 0, 90);
    S := 'Arc read back: centre ' + FloatToStr(CoordToMMs(A.XCenter)) + ', ' + FloatToStr(CoordToMMs(A.YCenter)) +
         '  r ' + FloatToStr(CoordToMMs(A.Radius)) + '  ' + FloatToStr(A.StartAngle) + '..' + FloatToStr(A.EndAngle);
    Brd.RemovePCBObject(A);
    Brd.ViewManager_FullUpdate;
    ShowMessage(S + #13#10 + 'Test arc removed.');
End;

Procedure NewLine(Brd : IPCB_Board; X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1); T.Y1 := MMsToCoord(Y1);
    T.X2 := MMsToCoord(X2); T.Y2 := MMsToCoord(Y2);
    T.Layer := eMechanical1;
    T.Width := MMsToCoord(0.1);
    Brd.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_BroadCast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    T.Selected := True;
End;

Procedure RoundOutline;
Var
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    O   : IPCB_Primitive;
    Old : TInterfaceList;
    I   : Integer;
    A   : IPCB_Arc;
Begin
    Brd := FBoard;
    If Brd = Nil Then Exit;
    Old := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject));
    It.AddFilter_LayerSet(MkSet(eMechanical1));
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If Not O.InComponent Then Old.Add(O);
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    For I := 0 To Old.Count - 1 Do Brd.RemovePCBObject(Old.Items[I]);

    Brd.CurrentLayer := eMechanical1;
    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');
    NewLine(Brd, CR, 0, FW - CR, 0);
    NewLine(Brd, FW, CR, FW, FH - CR);
    NewLine(Brd, FW - CR, FH, CR, FH);
    NewLine(Brd, 0, FH - CR, 0, CR);
    A := NewArc(Brd, FW - CR, CR, CR, 270, 360);  A.Selected := True;
    A := NewArc(Brd, FW - CR, FH - CR, CR, 0, 90); A.Selected := True;
    A := NewArc(Brd, CR, FH - CR, CR, 90, 180);    A.Selected := True;
    A := NewArc(Brd, CR, CR, CR, 180, 270);        A.Selected := True;
    Brd.ViewManager_FullUpdate;
    ResetParameters;
    AddStringParameter('Mode', 'BOARDOUTLINE_FROM_SEL_PRIMS');
    RunProcess('PCB:PlaceBoardOutline');
    ShowMessage('Removed ' + IntToStr(Old.Count) + ' old Mechanical 1 outline objects; rounded outline (r ' +
                FloatToStr(CR) + ' mm) placed and the board shape redefined from it.');
    Old.Free;
End;

Procedure DeletePlaneShapes;
Var
    Brd : IPCB_Board;
    L   : TInterfaceList;
    I   : Integer;
Begin
    Brd := FBoard;
    If Brd = Nil Then Exit;
    L := TInterfaceList.Create;
    CollectPlaneShapes(Brd, L);
    For I := 0 To L.Count - 1 Do Brd.RemovePCBObject(L.Items[I]);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed ' + IntToStr(L.Count) + ' plane-layer shapes. Run PlaneReport.');
    L.Free;
End;

Procedure AssignPlaneNets;
Var
    Brd : IPCB_Board;
    L   : TInterfaceList;
    I   : Integer;
    O   : IPCB_Primitive;
    G, V : IPCB_Net;
    It  : IPCB_BoardIterator;
    N   : IPCB_Net;
    S   : String;
Begin
    Brd := FBoard;
    If Brd = Nil Then Exit;
    G := Nil; V := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = 'GND' Then G := N;
        If N.Name = 'VCC3V3' Then V := N;
        N := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (G = Nil) Or (V = Nil) Then Begin ShowMessage('GND or VCC3V3 net not found.'); Exit; End;
    L := TInterfaceList.Create;
    CollectPlaneShapes(Brd, L);
    S := '';
    PCBServer.PreProcess;
    For I := 0 To L.Count - 1 Do
    Begin
        O := L.Items[I];
        O.BeginModify;
        If O.Layer = eInternalPlane1 Then O.Net := G Else O.Net := V;
        O.EndModify;
        S := S + Layer2String(O.Layer) + ' -> ' + O.Net.Name + #13#10;
    End;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Plane shapes assigned: ' + IntToStr(L.Count) + #13#10 + S);
    L.Free;
End;
