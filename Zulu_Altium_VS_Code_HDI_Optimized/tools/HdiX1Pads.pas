{ HdiX1Pads.pas -- Zulu_Altium_VS_Code_HDI_Optimized, 2026-10-07.
  Completes the X1 slot fix on this copy (review: CorrectX1Slots.pas set only the slot; the 0.90 round lands
  left the slot ends uncovered, the L5 plane 0.090 mm and CHAN12 0.120 mm from the slot walls).
  Same geometry as the production board (Zulu_Altium_VS_Code/tools/ProdX1Pads3.pas, docs/x1_slot_fix.md),
  re-checked on this copy's own geometry before use:
    1. MS1/MS2 lands top/middle/bottom: 1.11 x 1.81 / 0.90 x 1.60 / 1.11 x 1.81 oblong (PCBWay normal outer ring);
    2. CHAN12 re-routed over the slots on Bottom (y 25.02); its L4-L5 / L5-Bottom stacked microvias moved from
       (35.80, 23.35) to (37.45, 24.40); the L4 run starts at (37.45, 23.15);
    3. rules: Clearance_X1MS_L5Plane (X1 MS pads vs L5_VCC3V3_PLANE, 0.10 mm) and AnnularRing_X1 (InComponent X1,
       minimum 0.14 mm, so a slot breaking out of its land is a DRC error).
  Run with zulu_a7_hdi_optimized.PcbDoc focused: HdiX1Canary (reads only), then FixHdiX1. Re-pour, DRC, save. }

Const
    OUT_W = 1.11;
    OUT_H = 1.81;
    IN_W  = 0.90;
    IN_H  = 1.60;
    TW    = 0.0762;

Function PNear(A, B : Double) : Boolean;
Begin
    Result := Abs(A - B) < 0.001;
End;

Function HdiDocOk : Boolean;
Var
    WS  : IWorkspace;
    Doc : IDocument;
Begin
    Result := False;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Doc := WS.DM_FocusedDocument;
    If Doc = Nil Then Exit;
    If Pos('\Zulu_Altium_VS_Code_HDI_Optimized\Imported zulu_a7.PrjPcb\zulu_a7_hdi_optimized.PcbDoc', Doc.DM_FullPath) = 0 Then
    Begin
        ShowMessage('Refusing to modify the focused document:' + #13#10 + Doc.DM_FullPath);
        Exit;
    End;
    Result := True;
End;

Function FindMS(Brd : IPCB_Board; AName : String) : IPCB_Pad;
Var
    Comp : IPCB_Component;
    It   : IPCB_GroupIterator;
    P    : IPCB_Pad;
Begin
    Result := Nil;
    Comp := Brd.GetPcbComponentByRefDes('X1');
    If Comp = Nil Then Exit;
    It := Comp.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = AName Then Result := P;
        P := It.NextPCBObject;
    End;
    Comp.GroupIterator_Destroy(It);
End;

Procedure HdiX1Canary;
Var
    Brd : IPCB_Board;
    P   : IPCB_Pad;
    S   : String;
    RC  : IPCB_Rule;
    RA  : IPCB_Rule;
Begin
    If Not HdiDocOk Then Exit;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    P := FindMS(Brd, 'MS1');
    If P = Nil Then Begin ShowMessage('X1-MS1 not found.'); Exit; End;
    S := 'MS1 mode ' + IntToStr(P.Mode) +
         #13#10 + 'top ' + FloatToStr(CoordToMMs(P.TopXSize)) + ' x ' + FloatToStr(CoordToMMs(P.TopYSize)) + ' shape ' + IntToStr(P.TopShape) +
         #13#10 + 'mid ' + FloatToStr(CoordToMMs(P.MidXSize)) + ' x ' + FloatToStr(CoordToMMs(P.MidYSize)) + ' shape ' + IntToStr(P.MidShape) +
         #13#10 + 'bot ' + FloatToStr(CoordToMMs(P.BotXSize)) + ' x ' + FloatToStr(CoordToMMs(P.BotYSize)) + ' shape ' + IntToStr(P.BotShape) +
         #13#10 + 'hole ' + FloatToStr(CoordToMMs(P.HoleSize)) + ' x ' + FloatToStr(CoordToMMs(P.HoleWidth)) + ' type ' + IntToStr(P.HoleType) +
         ' rot ' + FloatToStr(P.HoleRotation) + #13#10 + 'eRounded = ' + IntToStr(eRounded) +
         #13#10 + 'ePadMode_Simple = ' + IntToStr(ePadMode_Simple) + ', ePadMode_LocalStack = ' + IntToStr(ePadMode_LocalStack);
    RC := PCBServer.PCBRuleFactory(eRule_Clearance);
    RC.Gap := MMsToCoord(0.10);
    RA := PCBServer.PCBRuleFactory(eRule_MinimumAnnularRing);
    RA.Minimum := MMsToCoord(0.14);
    S := S + #13#10 + 'rule probes (not added): clearance gap ' + FloatToStr(CoordToMMs(RC.Gap)) +
         ', annular ring minimum ' + FloatToStr(CoordToMMs(RA.Minimum));
    ShowMessage(S);
End;

Function SameTrk(T : IPCB_Track; L : TLayer; AX, AY, BX, BY : Double) : Boolean;
Var
    X1, Y1, X2, Y2 : Double;
Begin
    Result := False;
    If T.Layer <> L Then Exit;
    X1 := CoordToMMs(T.X1); Y1 := CoordToMMs(T.Y1); X2 := CoordToMMs(T.X2); Y2 := CoordToMMs(T.Y2);
    Result := (PNear(X1, AX) And PNear(Y1, AY) And PNear(X2, BX) And PNear(Y2, BY)) Or
              (PNear(X1, BX) And PNear(Y1, BY) And PNear(X2, AX) And PNear(Y2, AY));
End;

Procedure SetTrk(T : IPCB_Track; AX, AY, BX, BY : Double);
Begin
    T.BeginModify;
    T.X1 := MMsToCoord(AX); T.Y1 := MMsToCoord(AY);
    T.X2 := MMsToCoord(BX); T.Y2 := MMsToCoord(BY);
    T.EndModify;
End;

Procedure AddTrk(Brd : IPCB_Board; N : IPCB_Net; L : TLayer; AX, AY, BX, BY : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(AX); T.Y1 := MMsToCoord(AY);
    T.X2 := MMsToCoord(BX); T.Y2 := MMsToCoord(BY);
    T.Layer := L;
    T.Width := MMsToCoord(TW);
    T.Net := N;
    Brd.AddPCBObject(T);
    N.AddPCBObject(T);
End;

Procedure SetLand(P : IPCB_Pad);
Begin
    P.BeginModify;
    P.Mode := ePadMode_LocalStack;
    P.TopShape := eRounded; P.MidShape := eRounded; P.BotShape := eRounded;
    P.TopXSize := MMsToCoord(OUT_W); P.TopYSize := MMsToCoord(OUT_H);
    P.MidXSize := MMsToCoord(IN_W);  P.MidYSize := MMsToCoord(IN_H);
    P.BotXSize := MMsToCoord(OUT_W); P.BotYSize := MMsToCoord(OUT_H);
    P.EndModify;
End;

Function RuleByName(Brd : IPCB_Board; AName : String) : IPCB_Rule;
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

Procedure AddX1Rules(Brd : IPCB_Board);
Var
    R : IPCB_Rule;
Begin
    If RuleByName(Brd, 'Clearance_X1MS_L5Plane') = Nil Then
    Begin
        R := PCBServer.PCBRuleFactory(eRule_Clearance);
        R.Name             := 'Clearance_X1MS_L5Plane';
        R.Scope1Expression := '(InPad(''X1-MS1'') Or InPad(''X1-MS2''))';
        R.Scope2Expression := 'InNamedPolygon(''L5_VCC3V3_PLANE'')';
        R.NetScope         := eNetScope_AnyNet;
        R.LayerKind        := eRuleLayerKind_SameLayer;
        R.Gap              := MMsToCoord(0.10);
        Brd.AddPCBObject(R);
    End;
    If RuleByName(Brd, 'AnnularRing_X1') = Nil Then
    Begin
        R := PCBServer.PCBRuleFactory(eRule_MinimumAnnularRing);
        R.Name             := 'AnnularRing_X1';
        R.Scope1Expression := 'InComponent(''X1'')';
        R.Scope2Expression := 'All';
        R.NetScope         := eNetScope_AnyNet;
        R.LayerKind        := eRuleLayerKind_SameLayer;
        R.Minimum          := MMsToCoord(0.14);
        Brd.AddPCBObject(R);
    End;
End;

Procedure FixHdiX1;
Var
    Brd     : IPCB_Board;
    MS1     : IPCB_Pad;
    MS2     : IPCB_Pad;
    It      : IPCB_BoardIterator;
    T       : IPCB_Track;
    V       : IPCB_Via;
    N       : IPCB_Net;
    BRun    : IPCB_Track;
    BStub   : IPCB_Track;
    L4Stub  : IPCB_Track;
    L4Run   : IPCB_Track;
    Vias    : TInterfaceList;
    I       : Integer;
Begin
    If Not HdiDocOk Then Exit;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;

    MS1 := FindMS(Brd, 'MS1');
    MS2 := FindMS(Brd, 'MS2');
    If (MS1 = Nil) Or (MS2 = Nil) Then Begin ShowMessage('X1-MS1/MS2 not found.'); Exit; End;
    If (MS1.HoleType <> eSlotHole) Or (MS2.HoleType <> eSlotHole) Or
       Not PNear(CoordToMMs(MS1.HoleWidth), 1.30) Or Not PNear(CoordToMMs(MS2.HoleWidth), 1.30) Or
       Not PNear(CoordToMMs(MS1.X), 29.5199) Or Not PNear(CoordToMMs(MS2.X), 36.5201) Or
       Not PNear(CoordToMMs(MS1.Y), 23.9585) Or Not PNear(CoordToMMs(MS2.Y), 23.9585) Then
    Begin
        ShowMessage('X1-MS1/MS2 are not the 0.60 x 1.30 slots at the guarded positions; run ProdX1Slots first.');
        Exit;
    End;
    If Not PNear(CoordToMMs(MS1.BotYSize), 0.8999) Or Not PNear(CoordToMMs(MS2.BotYSize), 0.8999) Then
    Begin
        ShowMessage('X1-MS1/MS2 lands are not the guarded 0.90 mm round; already changed?');
        Exit;
    End;

    BRun := Nil; BStub := Nil; L4Stub := Nil; L4Run := Nil; N := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (T.Net <> Nil) And (T.Net.Name = 'CHAN12') Then
        Begin
            If SameTrk(T, eBottomLayer, 16.25, 23.15, 35.80, 23.15) Then BRun := T;
            If SameTrk(T, eBottomLayer, 35.80, 23.15, 35.80, 23.35) Then BStub := T;
            If SameTrk(T, eMidLayer2, 35.80, 23.35, 36.25, 23.15) Then L4Stub := T;
            If SameTrk(T, eMidLayer2, 36.25, 23.15, 46.45, 23.15) Then L4Run := T;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    Vias := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        If (V.Net <> Nil) And (V.Net.Name = 'CHAN12') And PNear(CoordToMMs(V.X), 35.80) And PNear(CoordToMMs(V.Y), 23.35) Then
            Vias.Add(V);
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    If (BRun = Nil) Or (BStub = Nil) Or (L4Stub = Nil) Or (L4Run = Nil) Or (Vias.Count <> 2) Then
    Begin
        ShowMessage('Guarded CHAN12 route did not match the post-slot-fix state.' + #13#10 +
            'Tracks: ' + BoolToStr(BRun <> Nil, True) + ', ' + BoolToStr(BStub <> Nil, True) + ', ' +
            BoolToStr(L4Stub <> Nil, True) + ', ' + BoolToStr(L4Run <> Nil, True) + #13#10 +
            'Vias: ' + IntToStr(Vias.Count));
        Vias.Free;
        Exit;
    End;
    N := BRun.Net;

    PCBServer.PreProcess;
    SetLand(MS1);
    SetLand(MS2);
    { Bottom: the run now stops west of MS1, rises, crosses both slots at y 25.02 and drops to the moved vias }
    SetTrk(BRun, 16.25, 23.15, 27.95, 23.15);
    SetTrk(BStub, 27.95, 23.15, 28.72, 23.92);
    AddTrk(Brd, N, eBottomLayer, 28.72, 23.92, 28.72, 24.62);
    AddTrk(Brd, N, eBottomLayer, 28.72, 24.62, 29.12, 25.02);
    AddTrk(Brd, N, eBottomLayer, 29.12, 25.02, 36.83, 25.02);
    AddTrk(Brd, N, eBottomLayer, 36.83, 25.02, 37.45, 24.40);
    { L4: from the moved vias straight down to the existing run }
    SetTrk(L4Stub, 37.45, 24.40, 37.45, 23.15);
    SetTrk(L4Run, 37.45, 23.15, 46.45, 23.15);
    For I := 0 To Vias.Count - 1 Do
    Begin
        V := Vias.Items[I];
        V.BeginModify;
        V.X := MMsToCoord(37.45);
        V.Y := MMsToCoord(24.40);
        V.EndModify;
    End;
    AddX1Rules(Brd);
    PCBServer.PostProcess;
    Vias.Free;
    Brd.ViewManager_FullUpdate;
    ShowMessage('X1-MS1/MS2 lands now ' + FloatToStr(OUT_W) + ' x ' + FloatToStr(OUT_H) + ' mm (Top/Bottom) and ' +
        FloatToStr(IN_W) + ' x ' + FloatToStr(IN_H) + ' mm (inner), oblong.' + #13#10 +
        'CHAN12 re-routed over the slots on Bottom (y 25.02); vias moved to 37.45, 24.40.' + #13#10 +
        'Rules Clearance_X1MS_L5Plane (0.10) and AnnularRing_X1 (0.14) added.' + #13#10 + 'Re-pour the polygons, run DRC, then save zulu_a7_hdi_optimized.PcbDoc.');
End;
