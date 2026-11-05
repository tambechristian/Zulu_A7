{ FeatherLibU1.pas -- 2026-11-05, stage 7 clean-up: footprint XC7A35T-CPG236 in asar_feather.PcbLib gets the 0.25 mm lands
  the board's U1 has had since VipPrepare2 (the 0.10 mm laser via-in-pad needs the 0.075 mm ring). Until now the library
  still said 0.225, so an update from the library would have put 0.225 lands under 0.25 via lands.
  Refuses unless the footprint is found with exactly 238 pads, all at 0.225 mm, so it runs once. Position, shape, layer
  and names are untouched.
  Run LibU1Lands with asar_feather.PcbLib focused, then File > Save. }

Procedure LibU1Lands;
Var
    Doc : IDocument;
    Lib : IPCB_Library;
    It  : IPCB_LibraryIterator;
    Fp  : IPCB_LibComponent;
    Hit : IPCB_LibComponent;
    GI  : IPCB_GroupIterator;
    P   : IPCB_Pad;
    N, NB : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbLib first.');
        Exit;
    End;
    Lib := PCBServer.GetCurrentPCBLibrary;
    Hit := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = 'XC7A35T-CPG236' Then Hit := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Hit = Nil Then
    Begin
        ShowMessage('Refusing: footprint XC7A35T-CPG236 not found; nothing changed.');
        Exit;
    End;

    N := 0;
    NB := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    P := GI.FirstPCBObject;
    While P <> Nil Do
    Begin
        N := N + 1;
        If (Abs(CoordToMMs(P.TopXSize) - 0.225) > 0.002) Or (Abs(CoordToMMs(P.TopYSize) - 0.225) > 0.002) Then NB := NB + 1;
        P := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (N <> 238) Or (NB <> 0) Then
    Begin
        ShowMessage('Refusing: ' + IntToStr(N) + ' pads, ' + IntToStr(NB) + ' not 0.225 mm; nothing changed.');
        Exit;
    End;

    PCBServer.PreProcess;
    N := 0;
    GI := Hit.GroupIterator_Create;
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
    Hit.GroupIterator_Destroy(GI);
    PCBServer.PostProcess;
    Lib.RefreshView;
    ShowMessage('XC7A35T-CPG236: ' + IntToStr(N) + ' pads set to 0.25 mm. Save the library.');
End;
