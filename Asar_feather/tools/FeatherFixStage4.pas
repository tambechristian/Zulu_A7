{ FeatherFixStage4.pas -- 2026-10-25: clears the 6 new violations of docs/drc_stage4.drc.
    Hole To Hole (2): stage 4 put a VCC3V3 through via and a VCC3V3 L4>L5>Bottom microvia stack at the same point
                      (34.95, 12.425). The through via already joins every layer, so the two microvias go.
    Mask Sliver (4):  C3 (moved with U3's rotation) sits 0.185 mm from X3's pads; the board-wide 0.05 mm expansion
                      leaves 0.085 mm. A C3-only 0.035 mm expansion (later 0.02 mm, FeatherFixC3Mask.pas), and
                      C3's pad caches are invalidated so the DRC sees it.
  Run FixStage4 with asar_feather.PcbDoc focused. }

Procedure FixStage4;
Var
    Doc  : IDocument;
    Brd  : IPCB_Board;
    It   : IPCB_BoardIterator;
    V    : IPCB_Via;
    R    : IPCB_Rule;
    C    : IPCB_Component;
    GI   : IPCB_GroupIterator;
    P    : IPCB_Pad;
    Ch   : TPadCache;
    Kill : TInterfaceList;
    I, N : Integer;
    X, Y : TCoord;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    X := Brd.XOrigin + MMsToCoord(34.95);
    Y := Brd.YOrigin + MMsToCoord(12.425);
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        If (Abs(V.X - X) < MMsToCoord(0.002)) And (Abs(V.Y - Y) < MMsToCoord(0.002)) And
           (Abs(V.HoleSize - MMsToCoord(0.15)) < MMsToCoord(0.002)) And (V.Net <> Nil) Then
            If V.Net.Name = 'VCC3V3' Then Kill.Add(V);
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Kill.Count <> 2 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(Kill.Count) + ' of the 2 microvias; nothing changed.');
        Exit;
    End;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = 'SolderMaskExpansion_C3' Then
        Begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('SolderMaskExpansion_C3 already exists; nothing changed.');
            Exit;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PreProcess;
    For I := 0 To Kill.Count - 1 Do
        Brd.RemovePCBObject(Kill[I]);
    R := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);
    R.Name := 'SolderMaskExpansion_C3';
    R.Scope1Expression := 'InComponent(''C3'')';
    R.Scope2Expression := 'All';
    R.Expansion := MMsToCoord(0.035);
    R.NetScope := eNetScope_AnyNet;
    R.LayerKind := eRuleLayerKind_SameLayer;
    Brd.AddPCBObject(R);
    PCBServer.PostProcess;
    C := Brd.GetPcbComponentByRefDes('C3');
    N := 0;
    GI := C.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    P := GI.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Cache.SolderMaskExpansionValid <> eCacheManual Then
        Begin
            Ch := P.Cache;
            Ch.SolderMaskExpansionValid := eCacheInvalid;
            P.BeginModify;
            P.Cache := Ch;
            P.EndModify;
            N := N + 1;
        End;
        P := GI.NextPCBObject;
    End;
    C.GroupIterator_Destroy(GI);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed 2 microvias, added SolderMaskExpansion_C3 (0.035 mm), ' + IntToStr(N) +
                ' C3 pad caches invalidated. Save, then re-run the DRC.');
End;
