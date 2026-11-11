{ FeatherRules.pas -- 2026-10-23, pre-routing rules check for the Feather (6-layer HDI stack and rules kept).
  Run with asar_feather.PcbDoc focused:
    FixFeatherRules2  - Clearance_Plane_ThruVia scoped the production pours L2_GND_PLANE/L5_VCC3V3_PLANE, which do not
                       exist on the Feather (its pours are L2_GND_FEATHER/L5_VCC3V3_FEATHER), so it matched nothing:
                       re-scope it to the Feather pours.
                     - the Feather's four 2.50 mm corner holes (X2) exceed HoleSize (max 1.02 mm): add HoleSize_X2,
                       0.20-2.60 mm, scoped to X2 only (like HoleSize_X1 for the USB-C slots).
                     - HoleSize_X1 (from production, max 1.30 mm) is short of this USB-C footprint's 0.6 x 1.7 mm
                       shell slots: raise its max to 1.80 mm.
                     Each change is guarded, so a second run changes nothing. }

Function FBrd : IPCB_Board;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
End;

Function FindRule(Brd : IPCB_Board; Name : String) : IPCB_Rule;
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
        If R.Name = Name Then
        Begin
            Result := R;
            Break;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure FixFeatherRules2;
Var
    Brd  : IPCB_Board;
    R    : IPCB_Rule;
    Want : String;
    Log  : String;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    Log := '';
    Want := '(InNamedPolygon(''L2_GND_FEATHER'') Or InNamedPolygon(''L5_VCC3V3_FEATHER''))';
    R := FindRule(Brd, 'Clearance_Plane_ThruVia');
    If R = Nil Then
        Log := Log + 'Clearance_Plane_ThruVia not found' + #13#10
    Else If R.Scope1Expression = Want Then
        Log := Log + 'Clearance_Plane_ThruVia already Feather-scoped' + #13#10
    Else
    Begin
        R.BeginModify;
        R.Scope1Expression := Want;
        R.EndModify;
        Log := Log + 'Clearance_Plane_ThruVia re-scoped to ' + R.Scope1Expression + #13#10;
    End;

    R := FindRule(Brd, 'HoleSize_X2');
    If R <> Nil Then
        Log := Log + 'HoleSize_X2 already exists' + #13#10
    Else
    Begin
        R := PCBServer.PCBRuleFactory(eRule_MaxMinHoleSize);
        R.Name := 'HoleSize_X2';
        R.Scope1Expression := 'InComponent(''X2'')';
        R.Scope2Expression := 'All';
        R.NetScope := eNetScope_AnyNet;
        R.LayerKind := eRuleLayerKind_SameLayer;
        R.AbsoluteValues := True;
        R.MinLimit := MMsToCoord(0.20);
        R.MaxLimit := MMsToCoord(2.60);
        Brd.AddPCBObject(R);
        Log := Log + 'HoleSize_X2 added (0.20-2.60 mm, X2 only)' + #13#10;
    End;
    R := FindRule(Brd, 'HoleSize_X1');
    If R = Nil Then
        Log := Log + 'HoleSize_X1 not found' + #13#10
    Else If R.MaxLimit >= MMsToCoord(1.80) Then
        Log := Log + 'HoleSize_X1 already allows 1.80 mm' + #13#10
    Else
    Begin
        R.BeginModify;
        R.MaxLimit := MMsToCoord(1.80);
        R.EndModify;
        Log := Log + 'HoleSize_X1 max raised to 1.80 mm' + #13#10;
    End;
    Brd.ViewManager_FullUpdate;
    ShowMessage(Log + 'Save asar_feather.PcbDoc.');
End;
