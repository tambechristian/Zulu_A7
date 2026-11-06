Function Stage13FindRule(AName : String) : IPCB_Rule;
Var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
Begin
    Result := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = AName Then Result := R;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;


Function Stage13PolygonCount : Integer;
Var
    It : IPCB_BoardIterator;
    P  : IPCB_Polygon;
Begin
    Result := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(MkSet(eMidLayer3, eMidLayer4));
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        Result := Result + 1;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;


Procedure Stage13AddClearanceRule;
Var
    R : IPCB_Rule;
Begin
    R := PCBServer.PCBRuleFactory(eRule_Clearance);
    R.Name             := 'Clearance_Plane_ThruVia';
    R.Scope1Expression := '(InNamedPolygon(''L2_GND_PLANE'') Or ' +
                          'InNamedPolygon(''L5_VCC3V3_PLANE''))';
    R.Scope2Expression := 'IsThruVia';
    R.NetScope         := eNetScope_DifferentNetsOnly;
    R.LayerKind        := eRuleLayerKind_SameLayer;
    R.Gap              := MMsToCoord(0.175);
    Brd.AddPCBObject(R);
End;


Procedure Stage13AddPolygonRule;
Var
    R : IPCB_Rule;
Begin
    R := PCBServer.PCBRuleFactory(eRule_PolygonConnectStyle);
    R.Name             := 'PolygonConnect_Vias';
    R.Scope1Expression := 'IsVia';
    R.Scope2Expression := 'All';
    R.NetScope         := eNetScope_AnyNet;
    R.LayerKind        := eRuleLayerKind_SameLayer;
    R.ConnectStyle     := eDirectConnectToPlane;
    Brd.AddPCBObject(R);
End;


Procedure Stage13AddPlanePolygon(N : IPCB_Net; L : TLayer; AName : String);
Var
    P   : IPCB_Polygon;
    Seg : TPolySegment;
Begin
    P := PCBServer.PCBObjectFactory(ePolyObject, eNoDimension, eCreate_Default);
    P.Layer          := L;
    P.Net            := N;
    P.Name           := AName;
    P.PolygonType    := eSignalLayerPolygon;
    P.PolyHatchStyle := ePolySolid;
    P.PourOver       := ePolygonPourOver_SameNet;
    P.RemoveDead     := True;
    P.RemoveNarrowNecks := False;
    P.RemoveIslandsByArea := False;
    P.TrackSize      := MMsToCoord(0.10);
    P.Grid           := MMsToCoord(0.05);
    P.PointCount     := 4;

    Seg := P.Segments[0];
    Seg.Kind := ePolySegmentLine;
    Seg.vx := MMsToCoord(0.25);
    Seg.vy := MMsToCoord(0.25);
    P.Segments[0] := Seg;
    Seg.vx := MMsToCoord(69.60);
    P.Segments[1] := Seg;
    Seg.vy := MMsToCoord(25.15);
    P.Segments[2] := Seg;
    Seg.vx := MMsToCoord(0.25);
    P.Segments[3] := Seg;

    Brd.AddPCBObject(P);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_Broadcast,
                                  PCBM_BoardRegisteration, P.I_ObjectAddress);
    P.SetState_CopperPourInvalid;
    P.Rebuild;
End;


Procedure RepairStage13SignalPlanes;
Var
    R  : IPCB_Rule;
    It : IPCB_BoardIterator;
    P  : IPCB_Polygon;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    If Stage13PolygonCount <> 2 Then
    Begin
        ShowMessage('Stage 13 signal-plane repair refused: expected exactly two L2/L5 polygons.');
        Exit;
    End;

    R := Stage13FindRule('Clearance_Plane_ThruVia');
    If R = Nil Then
    Begin
        ShowMessage('Stage 13 signal-plane repair refused: clearance rule is missing.');
        Exit;
    End;

    PCBServer.SystemOptions.PolygonRepour := eAlwaysRepour;
    PCBServer.PreProcess;
    Try
        R.Scope1Expression := '(InNamedPolygon(''L2_GND_PLANE'') Or ' +
                              'InNamedPolygon(''L5_VCC3V3_PLANE''))';
        R.Scope2Expression := 'IsThruVia';

        It := Brd.BoardIterator_Create;
        It.AddFilter_ObjectSet(MkSet(ePolyObject));
        It.AddFilter_LayerSet(MkSet(eMidLayer3, eMidLayer4));
        It.AddFilter_Method(eProcessAll);
        P := It.FirstPCBObject;
        While P <> Nil Do
        Begin
            P.SetState_CopperPourInvalid;
            P.Rebuild;
            P := It.NextPCBObject;
        End;
        Brd.BoardIterator_Destroy(It);
    Finally
        PCBServer.PostProcess;
    End;

    Brd.RebuildPadCaches;
    Brd.SetState_DocumentHasChanged;
    Brd.ViewManager_FullUpdate;
    Brd.GraphicallyInvalidate;
    ShowMessage('Stage 13 signal-plane clearance rule repaired and polygons rebuilt.' + #13#10 +
                'Press Ctrl+S, then rerun DRC and Gerbers.');
End;


Procedure AddStage13SignalPlanes;
Var
    GND, VCC : IPCB_Net;
    Count    : Integer;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    GND := FanNet('GND');
    VCC := FanNet('VCC3V3');
    If (GND = Nil) Or (VCC = Nil) Then
    Begin
        ShowMessage('Stage 13 signal-plane conversion refused: GND or VCC3V3 is missing.');
        Exit;
    End;

    Count := Stage13PolygonCount;
    If Count <> 0 Then
    Begin
        If (Count = 2) And
           (Stage13FindRule('Clearance_Plane_ThruVia') <> Nil) And
           (Stage13FindRule('PolygonConnect_Vias') <> Nil) Then
            ShowMessage('Stage 13 signal-plane polygons and rules already exist - nothing changed.')
        Else
            ShowMessage('Stage 13 signal-plane conversion refused: found ' +
                        IntToStr(Count) + ' existing polygon(s) on L2/L5.');
        Exit;
    End;

    If (Stage13FindRule('Clearance_Plane_ThruVia') <> Nil) Or
       (Stage13FindRule('PolygonConnect_Vias') <> Nil) Then
    Begin
        ShowMessage('Stage 13 signal-plane conversion refused: only part of the rule set exists.');
        Exit;
    End;

    PCBServer.SystemOptions.PolygonRepour := eAlwaysRepour;
    PCBServer.PreProcess;
    Try
        Stage13AddClearanceRule;
        Stage13AddPolygonRule;
        Stage13AddPlanePolygon(GND, eMidLayer3, 'L2_GND_PLANE');
        Stage13AddPlanePolygon(VCC, eMidLayer4, 'L5_VCC3V3_PLANE');
    Finally
        PCBServer.PostProcess;
    End;

    Brd.RebuildPadCaches;
    Brd.SetState_DocumentHasChanged;
    Brd.ViewManager_FullUpdate;
    Brd.GraphicallyInvalidate;
    ShowMessage('Stage 13 signal planes placed on L2-GND and L5-VCC3V3.' + #13#10 +
                'Press Ctrl+S, then place the HDI probe and rerun DRC/Gerbers.');
End;
