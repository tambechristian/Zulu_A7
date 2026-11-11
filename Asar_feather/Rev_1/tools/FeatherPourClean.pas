{ FeatherPourClean.pas -- 2026-11-05, stage 7 clean-up, from the plane audit:
    1. Remove Necks on L2_GND_FEATHER and L5_VCC3V3_FEATHER at 3 mil: 18 + 29 copper webs under 3 mil stay in the pour
       otherwise and go to the fab as sub-minimum copper. No GND or VCC3V3 object depends on them (docs/routing.md).
    2. New rule Clearance_Plane_NPTH: the two pours stay 0.25 mm from the six non-plated holes (X2 corners 2.5 mm, X1
       pegs 0.65 mm); until now only the 3 mil All / All rule held them, 0.0762 mm from the hole. The six are the only
       drilled pads without a net, and SMD pads without a net never meet L2 / L5, so IsPad + No Net scopes exactly them.
  Refuses unless both pours are found and the rule does not exist yet.
  Run PourClean with asar_feather.PcbDoc focused, then Tools > Polygon Pours > Repour All, DRC, Save. }

Procedure PourClean;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    P   : IPCB_Polygon;
    R   : IPCB_Rule;
    L   : TInterfaceList;
    I   : Integer;
    Log : String;
    Has : Boolean;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;

    Has := False;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = 'Clearance_Plane_NPTH' Then Has := True;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Has Then
    Begin
        ShowMessage('Refusing: Clearance_Plane_NPTH already exists; nothing changed.');
        Exit;
    End;

    L := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = 'L2_GND_FEATHER') Or (P.Name = 'L5_VCC3V3_FEATHER') Then L.Add(P);
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If L.Count <> 2 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(L.Count) + ' of the 2 pours; nothing changed.');
        L.Free;
        Exit;
    End;

    PCBServer.PreProcess;
    Log := '';
    For I := 0 To 1 Do
    Begin
        P := L.Items[I];
        P.BeginModify;
        P.RemoveNarrowNecks := True;
        P.NeckWidthThreshold := MilsToCoord(3);
        P.EndModify;
        Log := Log + P.Name + ': remove necks ' + BoolToStr(P.RemoveNarrowNecks, True) + ' below ' +
               FloatToStr(CoordToMils(P.NeckWidthThreshold)) + ' mil' + #13#10;
    End;
    L.Free;

    R := PCBServer.PCBRuleFactory(eRule_Clearance);
    R.Name := 'Clearance_Plane_NPTH';
    R.Scope1Expression := '(InNamedPolygon(''L2_GND_FEATHER'') Or InNamedPolygon(''L5_VCC3V3_FEATHER''))';
    R.Scope2Expression := 'IsPad And InNet(''No Net'')';
    R.NetScope := eNetScope_AnyNet;
    R.LayerKind := eRuleLayerKind_SameLayer;
    R.Gap := MMsToCoord(0.25);
    Brd.AddPCBObject(R);
    Log := Log + R.Name + ' added: gap ' + FloatToStr(CoordToMMs(R.Gap)) + ' mm, priority ' + IntToStr(R.Priority) + #13#10;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage(Log + 'Now Place the widened tracks, Repour All, DRC, Save.');
End;
