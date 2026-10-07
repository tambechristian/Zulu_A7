{ ProdX1Slots.pas -- production copy (Zulu_Altium_VS_Code), 2026-10-07.
  Ported from Zulu_Altium_VS_Code_HDI_Optimized/tools/CorrectX1Slots.pas (that file is untouched).
  Only the document guards and message text differ; the geometry, guards on the pre-fix CHAN12
  route, the X1 designator move and the HoleSize_X1 rule are identical.
  Run CorrectX1Slots, ResolveX1SlotClearances, RefineX1SlotClearances in that order. }

function X1Near(A, B : Double) : Boolean;
begin
    Result := Abs(A - B) < 0.01;
end;

function X1SlotCorrect(P : IPCB_Pad) : Boolean;
begin
    Result :=
        (P.HoleType = eSlotHole) And
        X1Near(CoordToMMs(P.HoleSize), 0.60) And
        X1Near(CoordToMMs(P.HoleWidth), 1.30) And
        X1Near(P.HoleRotation, 90.0);
end;

procedure CorrectX1Slots;
var
    WS       : IWorkspace;
    Doc      : IDocument;
    Brd      : IPCB_Board;
    Comp     : IPCB_Component;
    It       : IPCB_GroupIterator;
    P        : IPCB_Pad;
    MS1      : IPCB_Pad;
    MS2      : IPCB_Pad;
    Hits1    : Integer;
    Hits2    : Integer;
    Changed  : Integer;
begin
    WS := GetWorkspace;
    if WS = nil then
    begin
        ShowMessage('No active Altium workspace.');
        Exit;
    end;
    Doc := WS.DM_FocusedDocument;
    if Doc = nil then
    begin
        ShowMessage('No focused document.');
        Exit;
    end;
    if (Pos('\Zulu_Altium_VS_Code\Imported zulu_a7.PrjPcb\zulu_a7.PcbDoc', Doc.DM_FullPath) = 0) Or
       (Pos('HDI_Optimized', Doc.DM_FullPath) > 0) then
    begin
        ShowMessage(
            'Refusing to modify the focused document:' +
            #13#10 + Doc.DM_FullPath);
        Exit;
    end;

    Brd := PCBServer.GetCurrentPCBBoard;
    if Brd = nil then
    begin
        ShowMessage('No active PCB document.');
        Exit;
    end;

    Comp := Brd.GetPcbComponentByRefDes('X1');
    if Comp = nil then
    begin
        ShowMessage('X1 was not found on the production board.');
        Exit;
    end;

    MS1 := nil;
    MS2 := nil;
    Hits1 := 0;
    Hits2 := 0;
    It := Comp.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    while P <> nil do
    begin
        if P.Name = 'MS1' then
        begin
            MS1 := P;
            Hits1 := Hits1 + 1;
        end;
        if P.Name = 'MS2' then
        begin
            MS2 := P;
            Hits2 := Hits2 + 1;
        end;
        P := It.NextPCBObject;
    end;
    Comp.GroupIterator_Destroy(It);

    if (Hits1 <> 1) Or (Hits2 <> 1) then
    begin
        ShowMessage(
            'Expected exactly one X1-MS1 and one X1-MS2.' + #13#10 +
            'MS1 count: ' + IntToStr(Hits1) + #13#10 +
            'MS2 count: ' + IntToStr(Hits2));
        Exit;
    end;

    if Not MS1.Plated Or Not MS2.Plated then
    begin
        ShowMessage('X1 MS1/MS2 must remain plated.');
        Exit;
    end;
    if Not X1Near(CoordToMMs(MS1.X), 29.5199) Or
       Not X1Near(CoordToMMs(MS1.Y), 23.9585) Or
       Not X1Near(CoordToMMs(MS2.X), 36.5201) Or
       Not X1Near(CoordToMMs(MS2.Y), 23.9585) then
    begin
        ShowMessage('X1 MS1/MS2 centers do not match the guarded layout.');
        Exit;
    end;

    if X1SlotCorrect(MS1) And X1SlotCorrect(MS2) then
    begin
        ShowMessage(
            'X1 MS1/MS2 are already 0.60 x 1.30 mm plated slots at 90 degrees.');
        Exit;
    end;

    PCBServer.PreProcess;
    Changed := 0;
    if Not X1SlotCorrect(MS1) then
    begin
        MS1.BeginModify;
        MS1.HoleType := eSlotHole;
        MS1.HoleSize := MMsToCoord(0.60);
        MS1.HoleWidth := MMsToCoord(1.30);
        MS1.HoleRotation := 90;
        MS1.EndModify;
        Changed := Changed + 1;
    end;
    if Not X1SlotCorrect(MS2) then
    begin
        MS2.BeginModify;
        MS2.HoleType := eSlotHole;
        MS2.HoleSize := MMsToCoord(0.60);
        MS2.HoleWidth := MMsToCoord(1.30);
        MS2.HoleRotation := 90;
        MS2.EndModify;
        Changed := Changed + 1;
    end;
    PCBServer.PostProcess;

    Brd.ViewManager_FullUpdate;
    ShowMessage(
        'Corrected ' + IntToStr(Changed) + ' X1 rear shell openings.' +
        #13#10 + 'MS1/MS2: plated 0.60 x 1.30 mm slots, rotation 90 degrees.' +
        #13#10 + 'Save only Zulu_Altium_VS_Code zulu_a7.PcbDoc.');
end;

function X1SameTrack(
    T : IPCB_Track;
    AX, AY, BX, BY : Double) : Boolean;
var
    X1, Y1, X2, Y2 : Double;
begin
    X1 := CoordToMMs(T.X1);
    Y1 := CoordToMMs(T.Y1);
    X2 := CoordToMMs(T.X2);
    Y2 := CoordToMMs(T.Y2);
    Result :=
        (X1Near(X1, AX) And X1Near(Y1, AY) And
         X1Near(X2, BX) And X1Near(Y2, BY)) Or
        (X1Near(X1, BX) And X1Near(Y1, BY) And
         X1Near(X2, AX) And X1Near(Y2, AY));
end;

function X1FindRule(Brd : IPCB_Board; AName : String) : IPCB_Rule;
var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
begin
    Result := nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    while R <> nil do
    begin
        if R.Name = AName then
            Result := R;
        R := It.NextPCBObject;
    end;
    Brd.BoardIterator_Destroy(It);
end;

procedure ResolveX1SlotClearances;
var
    WS       : IWorkspace;
    Doc      : IDocument;
    Brd      : IPCB_Board;
    Comp     : IPCB_Component;
    It       : IPCB_BoardIterator;
    T        : IPCB_Track;
    V        : IPCB_Via;
    BLead    : IPCB_Track;
    BRun     : IPCB_Track;
    BVia     : IPCB_Track;
    L4Via    : IPCB_Track;
    OldVias  : TInterfaceList;
    R        : IPCB_Rule;
    I        : Integer;
    Changed  : Integer;
begin
    WS := GetWorkspace;
    if WS = nil then
    begin
        ShowMessage('No active Altium workspace.');
        Exit;
    end;
    Doc := WS.DM_FocusedDocument;
    if Doc = nil then
    begin
        ShowMessage('No focused document.');
        Exit;
    end;
    if (Pos('\Zulu_Altium_VS_Code\Imported zulu_a7.PrjPcb\zulu_a7.PcbDoc', Doc.DM_FullPath) = 0) Or
       (Pos('HDI_Optimized', Doc.DM_FullPath) > 0) then
    begin
        ShowMessage(
            'Refusing to modify the focused document:' +
            #13#10 + Doc.DM_FullPath);
        Exit;
    end;

    Brd := PCBServer.GetCurrentPCBBoard;
    if Brd = nil then
    begin
        ShowMessage('No active PCB document.');
        Exit;
    end;
    Comp := Brd.GetPcbComponentByRefDes('X1');
    if Comp = nil then
    begin
        ShowMessage('X1 was not found on the production board.');
        Exit;
    end;

    BLead := nil;
    BRun := nil;
    BVia := nil;
    L4Via := nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    while T <> nil do
    begin
        if (T.Net <> nil) And (T.Net.Name = 'CHAN12') then
        begin
            if (T.Layer = eBottomLayer) And
               X1SameTrack(T, 16.15, 23.30, 16.25, 23.20) then
                BLead := T;
            if (T.Layer = eBottomLayer) And
               X1SameTrack(T, 16.25, 23.20, 36.10, 23.20) then
                BRun := T;
            if (T.Layer = eBottomLayer) And
               X1SameTrack(T, 36.10, 23.20, 36.15, 23.25) then
                BVia := T;
            if (T.Layer = eMidLayer2) And
               X1SameTrack(T, 36.15, 23.25, 36.25, 23.15) then
                L4Via := T;
        end;
        T := It.NextPCBObject;
    end;
    Brd.BoardIterator_Destroy(It);

    OldVias := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    while V <> nil do
    begin
        if (V.Net <> nil) And (V.Net.Name = 'CHAN12') And
           X1Near(CoordToMMs(V.X), 36.15) And
           X1Near(CoordToMMs(V.Y), 23.25) then
            OldVias.Add(V);
        V := It.NextPCBObject;
    end;
    Brd.BoardIterator_Destroy(It);

    if (BLead = nil) Or (BRun = nil) Or (BVia = nil) Or (L4Via = nil) Or
       (OldVias.Count <> 2) then
    begin
        ShowMessage(
            'Guarded CHAN12 route did not match the expected pre-fix state.' +
            #13#10 + 'Tracks found: ' +
            BoolToStr(BLead <> nil, True) + ', ' +
            BoolToStr(BRun <> nil, True) + ', ' +
            BoolToStr(BVia <> nil, True) + ', ' +
            BoolToStr(L4Via <> nil, True) +
            #13#10 + 'Vias found: ' + IntToStr(OldVias.Count));
        OldVias.Free;
        Exit;
    end;

    if Not X1Near(CoordToMMs(Comp.Name.XLocation), 37.167) Or
       Not X1Near(CoordToMMs(Comp.Name.YLocation), 22.300) then
    begin
        ShowMessage(
            'X1 designator is not at the guarded pre-fix location:' +
            #13#10 + FloatToStr(CoordToMMs(Comp.Name.XLocation)) + ', ' +
            FloatToStr(CoordToMMs(Comp.Name.YLocation)));
        OldVias.Free;
        Exit;
    end;

    PCBServer.PreProcess;
    Changed := 0;

    BLead.BeginModify;
    if X1Near(CoordToMMs(BLead.X1), 16.25) then
    begin
        BLead.X1 := MMsToCoord(16.25);
        BLead.Y1 := MMsToCoord(23.15);
    end
    else
    begin
        BLead.X2 := MMsToCoord(16.25);
        BLead.Y2 := MMsToCoord(23.15);
    end;
    BLead.EndModify;
    Changed := Changed + 1;

    BRun.BeginModify;
    BRun.X1 := MMsToCoord(16.25);
    BRun.Y1 := MMsToCoord(23.15);
    BRun.X2 := MMsToCoord(35.80);
    BRun.Y2 := MMsToCoord(23.15);
    BRun.EndModify;
    Changed := Changed + 1;

    BVia.BeginModify;
    BVia.X1 := MMsToCoord(35.80);
    BVia.Y1 := MMsToCoord(23.15);
    BVia.X2 := MMsToCoord(35.80);
    BVia.Y2 := MMsToCoord(23.20);
    BVia.EndModify;
    Changed := Changed + 1;

    L4Via.BeginModify;
    if X1Near(CoordToMMs(L4Via.X1), 36.15) then
    begin
        L4Via.X1 := MMsToCoord(35.80);
        L4Via.Y1 := MMsToCoord(23.20);
    end
    else
    begin
        L4Via.X2 := MMsToCoord(35.80);
        L4Via.Y2 := MMsToCoord(23.20);
    end;
    L4Via.EndModify;
    Changed := Changed + 1;

    for I := 0 to OldVias.Count - 1 do
    begin
        V := OldVias.Items[I];
        V.BeginModify;
        V.X := MMsToCoord(35.80);
        V.Y := MMsToCoord(23.20);
        V.EndModify;
        Changed := Changed + 1;
    end;

    Comp.ChangeNameAutoposition(eAutoPos_Manual);
    Comp.Name.MoveToXY(MMsToCoord(37.442), MMsToCoord(22.250));
    Changed := Changed + 1;

    R := X1FindRule(Brd, 'HoleSize_X1');
    if R = nil then
    begin
        R := PCBServer.PCBRuleFactory(eRule_MaxMinHoleSize);
        R.Name := 'HoleSize_X1';
        R.Scope1Expression := 'InComponent(''X1'')';
        R.Scope2Expression := 'All';
        R.NetScope := eNetScope_AnyNet;
        R.LayerKind := eRuleLayerKind_SameLayer;
        R.AbsoluteValues := True;
        R.MinLimit := MMsToCoord(0.20);
        R.MaxLimit := MMsToCoord(1.30);
        Brd.AddPCBObject(R);
        Changed := Changed + 1;
    end;

    PCBServer.PostProcess;
    OldVias.Free;
    Brd.ViewManager_FullUpdate;
    ShowMessage(
        'Resolved X1 slot clearances with ' + IntToStr(Changed) +
        ' guarded updates.' + #13#10 +
        'CHAN12 route/vias moved clear, X1 text moved clear, and ' +
        'HoleSize_X1 permits the required 1.30 mm slot length.' +
        #13#10 + 'Save only Zulu_Altium_VS_Code zulu_a7.PcbDoc, then rerun DRC.');
end;

procedure RefineX1SlotClearances;
var
    WS       : IWorkspace;
    Doc      : IDocument;
    Brd      : IPCB_Board;
    Comp     : IPCB_Component;
    It       : IPCB_BoardIterator;
    T        : IPCB_Track;
    V        : IPCB_Via;
    BVia     : IPCB_Track;
    L4Via    : IPCB_Track;
    Vias     : TInterfaceList;
    I        : Integer;
begin
    WS := GetWorkspace;
    if WS = nil then
    begin
        ShowMessage('No active Altium workspace.');
        Exit;
    end;
    Doc := WS.DM_FocusedDocument;
    if Doc = nil then
    begin
        ShowMessage('No focused document.');
        Exit;
    end;
    if (Pos('\Zulu_Altium_VS_Code\Imported zulu_a7.PrjPcb\zulu_a7.PcbDoc', Doc.DM_FullPath) = 0) Or
       (Pos('HDI_Optimized', Doc.DM_FullPath) > 0) then
    begin
        ShowMessage(
            'Refusing to modify the focused document:' +
            #13#10 + Doc.DM_FullPath);
        Exit;
    end;

    Brd := PCBServer.GetCurrentPCBBoard;
    if Brd = nil then
    begin
        ShowMessage('No active PCB document.');
        Exit;
    end;
    Comp := Brd.GetPcbComponentByRefDes('X1');
    if Comp = nil then
    begin
        ShowMessage('X1 was not found on the production board.');
        Exit;
    end;

    BVia := nil;
    L4Via := nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    while T <> nil do
    begin
        if (T.Net <> nil) And (T.Net.Name = 'CHAN12') then
        begin
            if (T.Layer = eBottomLayer) And
               X1SameTrack(T, 35.80, 23.15, 35.80, 23.20) then
                BVia := T;
            if (T.Layer = eMidLayer2) And
               X1SameTrack(T, 35.80, 23.20, 36.25, 23.15) then
                L4Via := T;
        end;
        T := It.NextPCBObject;
    end;
    Brd.BoardIterator_Destroy(It);

    Vias := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    while V <> nil do
    begin
        if (V.Net <> nil) And (V.Net.Name = 'CHAN12') And
           X1Near(CoordToMMs(V.X), 35.80) And
           X1Near(CoordToMMs(V.Y), 23.20) then
            Vias.Add(V);
        V := It.NextPCBObject;
    end;
    Brd.BoardIterator_Destroy(It);

    if (BVia = nil) Or (L4Via = nil) Or (Vias.Count <> 2) then
    begin
        ShowMessage(
            'Guarded first-pass CHAN12 route did not match.' +
            #13#10 + 'Tracks found: ' +
            BoolToStr(BVia <> nil, True) + ', ' +
            BoolToStr(L4Via <> nil, True) +
            #13#10 + 'Vias found: ' + IntToStr(Vias.Count));
        Vias.Free;
        Exit;
    end;
    if Not X1Near(CoordToMMs(Comp.Name.XLocation), 37.442) Or
       Not X1Near(CoordToMMs(Comp.Name.YLocation), 22.250) then
    begin
        ShowMessage(
            'X1 designator is not at the guarded final location:' +
            #13#10 + FloatToStr(CoordToMMs(Comp.Name.XLocation)) + ', ' +
            FloatToStr(CoordToMMs(Comp.Name.YLocation)));
        Vias.Free;
        Exit;
    end;

    PCBServer.PreProcess;

    BVia.BeginModify;
    if X1Near(CoordToMMs(BVia.Y1), 23.20) then
        BVia.Y1 := MMsToCoord(23.35)
    else
        BVia.Y2 := MMsToCoord(23.35);
    BVia.EndModify;

    L4Via.BeginModify;
    if X1Near(CoordToMMs(L4Via.X1), 35.80) then
    begin
        L4Via.X1 := MMsToCoord(35.80);
        L4Via.Y1 := MMsToCoord(23.35);
    end
    else
    begin
        L4Via.X2 := MMsToCoord(35.80);
        L4Via.Y2 := MMsToCoord(23.35);
    end;
    L4Via.EndModify;

    for I := 0 to Vias.Count - 1 do
    begin
        V := Vias.Items[I];
        V.BeginModify;
        V.Y := MMsToCoord(23.35);
        V.EndModify;
    end;

    PCBServer.PostProcess;
    Vias.Free;
    Brd.ViewManager_FullUpdate;
    ShowMessage(
        'Refined the two remaining X1-slot clearance fixes.' +
        #13#10 + 'CHAN12 stacked vias: 35.80, 23.35 mm.' +
        #13#10 + 'X1 designator: 37.442, 22.250 mm.' +
        #13#10 + 'Save only Zulu_Altium_VS_Code zulu_a7.PcbDoc, then rerun DRC.');
end;
