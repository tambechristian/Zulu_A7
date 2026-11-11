{ FeatherVip.pas -- 2026-10-31, stage 7 (via-in-pad laser microvias on U1). NOT RUN YET: run VipPrepare only after
  a stage-7 plan passes route_check on tools/route/stage7 models with --land 0.25, and PCBWay has confirmed the
  0.10 mm laser via in a 0.25 mm land (docs/pcbway_vip_enquiry.md).
  What it does, with asar_feather.PcbDoc focused:
    1. every pad of U1 (238) -> 0.25 x 0.25 mm Top land (was 0.225): the 0.10 laser via needs a 0.075 ring;
    2. rule HoleSize_uVia (IsMicroVia): 0.10 .. 0.15 (was 0.15 .. 0.15);
    3. rule RoutingVias_uVia (IsMicroVia): hole 0.10 .. 0.15 preferred 0.15, land 0.25 .. 0.30 preferred 0.30.
  The 0.27/0.15 buried and 0.35/0.20 through classes are untouched. Save afterwards; the PcbLib footprint keeps
  0.225 until tools/FeatherFootprints.pas is re-run with the new size. Rule API as ZuluHdiRules.pas (proven). }

Function VipFindRule(Brd : IPCB_Board; Name : String) : IPCB_Rule;
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

Procedure VipPrepare;
Var
    Doc  : IDocument;
    Brd  : IPCB_Board;
    It   : IPCB_BoardIterator;
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
    If (VipFindRule(Brd, 'HoleSize_uVia') = Nil) Or (VipFindRule(Brd, 'RoutingVias_uVia') = Nil) Then
    Begin
        ShowMessage('Refusing: HoleSize_uVia / RoutingVias_uVia not found; nothing changed.');
        Exit;
    End;
    { count U1's pads first: all 238 at 0.225 or nothing }
    N := 0; NB := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Component <> Nil) And (P.Component.Name.Text = 'U1') Then
        Begin
            N := N + 1;
            If (Abs(CoordToMMs(P.TopXSize) - 0.225) > 0.002) Or (Abs(CoordToMMs(P.TopYSize) - 0.225) > 0.002) Then NB := NB + 1;
        End;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (N <> 238) Or (NB <> 0) Then
    Begin
        ShowMessage('Refusing: U1 has ' + IntToStr(N) + ' pads, ' + IntToStr(NB) + ' not 0.225 mm; nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Component <> Nil) And (P.Component.Name.Text = 'U1') Then
        Begin
            P.BeginModify;
            P.TopXSize := MMsToCoord(0.25); P.TopYSize := MMsToCoord(0.25);
            P.EndModify;
        End;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Log := 'U1: 238 pads set to 0.25 mm' + #13#10;

    R := VipFindRule(Brd, 'HoleSize_uVia');
    R.BeginModify;
    R.AbsoluteValues := True;
    R.MinLimit := MMsToCoord(0.10);
    R.MaxLimit := MMsToCoord(0.15);
    R.EndModify;
    Log := Log + 'HoleSize_uVia 0.10 .. 0.15, read back ' + FloatToStr(CoordToMMs(R.MinLimit)) + ' .. ' + FloatToStr(CoordToMMs(R.MaxLimit)) + #13#10;

    R := VipFindRule(Brd, 'RoutingVias_uVia');
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
