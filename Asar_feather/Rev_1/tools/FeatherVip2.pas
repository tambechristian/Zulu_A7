{ FeatherVip2.pas -- 2026-11-05, stage 7 (via-in-pad laser microvias on U1, layer-per-ring scheme, 3/3 mil).
  FeatherVip.pas with U1's pads found through the component's group iterator (the spelling proven in
  FeatherFixC3Mask.pas); FeatherVip.pas itself was never run.
  What VipPrepare2 does, with asar_feather.PcbDoc focused:
    1. every pad of U1 (238) -> 0.25 x 0.25 mm Top land (was 0.225): the 0.10 laser via needs a 0.075 ring;
    2. rule HoleSize_uVia (IsMicroVia): 0.10 .. 0.15 (was 0.15 .. 0.15);
    3. rule RoutingVias_uVia (IsMicroVia): hole 0.10 .. 0.15 preferred 0.15, land 0.25 .. 0.30 preferred 0.30.
  The 0.27/0.15 buried and 0.35/0.20 through classes are untouched. It refuses unless both rules exist and all 238
  pads are 0.225, so it runs once. Save afterwards. The PcbLib footprint keeps 0.225: never update U1 from the
  library. }

Function Vip2FindRule(Brd : IPCB_Board; Name : String) : IPCB_Rule;
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
        If R.Name = Name Then Result := R;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure VipPrepare2;
Var
    Doc  : IDocument;
    Brd  : IPCB_Board;
    C    : IPCB_Component;
    GI   : IPCB_GroupIterator;
    P    : IPCB_Pad;
    R    : IPCB_Rule;
    N, NB : Integer;
    Log  : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Vip2FindRule(Brd, 'HoleSize_uVia') = Nil) Or (Vip2FindRule(Brd, 'RoutingVias_uVia') = Nil) Then
    Begin
        ShowMessage('Refusing: HoleSize_uVia / RoutingVias_uVia not found; nothing changed.');
        Exit;
    End;
    C := Brd.GetPcbComponentByRefDes('U1');
    If C = Nil Then
    Begin
        ShowMessage('Refusing: U1 not found; nothing changed.');
        Exit;
    End;
    { count U1's pads first: all 238 at 0.225 or nothing }
    N := 0; NB := 0;
    GI := C.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    P := GI.FirstPCBObject;
    While P <> Nil Do
    Begin
        N := N + 1;
        If (Abs(CoordToMMs(P.TopXSize) - 0.225) > 0.002) Or (Abs(CoordToMMs(P.TopYSize) - 0.225) > 0.002) Then NB := NB + 1;
        P := GI.NextPCBObject;
    End;
    C.GroupIterator_Destroy(GI);
    If (N <> 238) Or (NB <> 0) Then
    Begin
        ShowMessage('Refusing: U1 has ' + IntToStr(N) + ' pads, ' + IntToStr(NB) + ' not 0.225 mm; nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    N := 0;
    GI := C.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    P := GI.FirstPCBObject;
    While P <> Nil Do
    Begin
        P.BeginModify;
        P.TopXSize := MMsToCoord(0.25);
        P.TopYSize := MMsToCoord(0.25);
        P.EndModify;
        N := N + 1;
        P := GI.NextPCBObject;
    End;
    C.GroupIterator_Destroy(GI);
    Log := 'U1: ' + IntToStr(N) + ' pads set to 0.25 mm' + #13#10;

    R := Vip2FindRule(Brd, 'HoleSize_uVia');
    R.BeginModify;
    R.AbsoluteValues := True;
    R.MinLimit := MMsToCoord(0.10);
    R.MaxLimit := MMsToCoord(0.15);
    R.EndModify;
    Log := Log + 'HoleSize_uVia 0.10 .. 0.15, read back ' + FloatToStr(CoordToMMs(R.MinLimit)) + ' .. ' + FloatToStr(CoordToMMs(R.MaxLimit)) + #13#10;

    R := Vip2FindRule(Brd, 'RoutingVias_uVia');
    R.BeginModify;
    R.MinHoleWidth := MMsToCoord(0.10);
    R.MaxHoleWidth := MMsToCoord(0.15);
    R.PreferedHoleWidth := MMsToCoord(0.15);
    R.MinWidth := MMsToCoord(0.25);
    R.MaxWidth := MMsToCoord(0.30);
    R.PreferedWidth := MMsToCoord(0.30);
    R.EndModify;
    Log := Log + 'RoutingVias_uVia hole 0.10..0.15, land 0.25..0.30, read back hole ' + FloatToStr(CoordToMMs(R.MinHoleWidth)) + ' land ' + FloatToStr(CoordToMMs(R.MinWidth)) + #13#10;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage(Log + 'Save the board.');
End;
