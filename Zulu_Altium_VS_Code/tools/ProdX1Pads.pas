{ ProdX1Pads.pas -- production copy (Zulu_Altium_VS_Code), 2026-10-07.
  Follow-up to ProdX1Slots*.pas: the 0.60 x 1.30 mm X1 MS1/MS2 slots had 0.90 mm round lands (no ring at the slot
  ends on Bottom/inner layers) and copper closer than 0.15 mm to the slot walls. This script:
    1. makes MS1/MS2 oblong lands PAD_W x PAD_H on top, mid and bottom (ring (PAD_W-0.60)/2 all round);
    2. re-routes CHAN12 over the slots on Bottom (y 24.95) and moves its L4-L5 / L5-Bottom stacked microvias from
       (35.80, 23.35) to (37.35, 24.40), east of MS2; the L4 run then starts at (37.35, 23.15).
  The geometry was checked beforehand against the KiCad copy (scratchpad x1fix2/check.py).
  Run X1PadsCanary first (reads only), then FixX1PadsAndClearances. Re-pour the polygons and run DRC afterwards. }

Const
    PAD_W = 0.90;
    PAD_H = 1.60;
    TW    = 0.0762;

Function PNear(A, B : Double) : Boolean;
Begin
    Result := Abs(A - B) < 0.001;
End;

Function ProdDocOk : Boolean;
Var
    WS  : IWorkspace;
    Doc : IDocument;
Begin
    Result := False;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Doc := WS.DM_FocusedDocument;
    If Doc = Nil Then Exit;
    If (Pos('\Zulu_Altium_VS_Code\Imported zulu_a7.PrjPcb\zulu_a7.PcbDoc', Doc.DM_FullPath) = 0) Or
       (Pos('HDI_Optimized', Doc.DM_FullPath) > 0) Then
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

Procedure X1PadsCanary;
Var
    Brd : IPCB_Board;
    P   : IPCB_Pad;
    S   : String;
Begin
    If Not ProdDocOk Then Exit;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    P := FindMS(Brd, 'MS1');
    If P = Nil Then Begin ShowMessage('X1-MS1 not found.'); Exit; End;
    S := 'MS1 mode ' + IntToStr(P.Mode) +
         #13#10 + 'top ' + FloatToStr(CoordToMMs(P.TopXSize)) + ' x ' + FloatToStr(CoordToMMs(P.TopYSize)) + ' shape ' + IntToStr(P.TopShape) +
         #13#10 + 'mid ' + FloatToStr(CoordToMMs(P.MidXSize)) + ' x ' + FloatToStr(CoordToMMs(P.MidYSize)) + ' shape ' + IntToStr(P.MidShape) +
         #13#10 + 'bot ' + FloatToStr(CoordToMMs(P.BotXSize)) + ' x ' + FloatToStr(CoordToMMs(P.BotYSize)) + ' shape ' + IntToStr(P.BotShape) +
         #13#10 + 'hole ' + FloatToStr(CoordToMMs(P.HoleSize)) + ' x ' + FloatToStr(CoordToMMs(P.HoleWidth)) + ' type ' + IntToStr(P.HoleType) +
         ' rot ' + FloatToStr(P.HoleRotation) + #13#10 + 'eRounded = ' + IntToStr(eRounded);
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
    P.TopShape := eRounded; P.MidShape := eRounded; P.BotShape := eRounded;
    P.TopXSize := MMsToCoord(PAD_W); P.TopYSize := MMsToCoord(PAD_H);
    P.MidXSize := MMsToCoord(PAD_W); P.MidYSize := MMsToCoord(PAD_H);
    P.BotXSize := MMsToCoord(PAD_W); P.BotYSize := MMsToCoord(PAD_H);
    P.EndModify;
End;

Procedure FixX1PadsAndClearances;
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
    If Not ProdDocOk Then Exit;
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
    { Bottom: the run now stops west of MS1, rises, crosses both slots at y 24.95 and drops to the moved vias }
    SetTrk(BRun, 16.25, 23.15, 27.95, 23.15);
    SetTrk(BStub, 27.95, 23.15, 28.80, 24.00);
    AddTrk(Brd, N, eBottomLayer, 28.80, 24.00, 28.80, 24.50);
    AddTrk(Brd, N, eBottomLayer, 28.80, 24.50, 29.25, 24.95);
    AddTrk(Brd, N, eBottomLayer, 29.25, 24.95, 36.80, 24.95);
    AddTrk(Brd, N, eBottomLayer, 36.80, 24.95, 37.35, 24.40);
    { L4: from the moved vias straight down to the existing run }
    SetTrk(L4Stub, 37.35, 24.40, 37.35, 23.15);
    SetTrk(L4Run, 37.35, 23.15, 46.45, 23.15);
    For I := 0 To Vias.Count - 1 Do
    Begin
        V := Vias.Items[I];
        V.BeginModify;
        V.X := MMsToCoord(37.35);
        V.Y := MMsToCoord(24.40);
        V.EndModify;
    End;
    PCBServer.PostProcess;
    Vias.Free;
    Brd.ViewManager_FullUpdate;
    ShowMessage('X1-MS1/MS2 lands now ' + FloatToStr(PAD_W) + ' x ' + FloatToStr(PAD_H) + ' mm oblong on all layers.' + #13#10 +
        'CHAN12 re-routed over the slots on Bottom (y 24.95); vias moved to 37.35, 24.40.' + #13#10 +
        'Re-pour the polygons, run DRC, then save Zulu_Altium_VS_Code zulu_a7.PcbDoc.');
End;
