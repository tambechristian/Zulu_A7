{ FeatherMask.pas -- 2026-10-23: clears the 4 Minimum Solder Mask Sliver violations of docs/drc_prerouting.drc.
  They sit at U2's four QFN corners (pads 16/17, 32/33, 48/49, 64/1): the last pad of one side and the first of the
  next are 0.185 mm apart, so the board-wide 0.05 mm mask expansion leaves a 0.085 mm web (< 0.1 mm). A U2-only
  expansion of 0.035 mm leaves 0.115 mm. Production does the same for U1 (SolderMaskExpansion_U1, 0 mm).
  Run with asar_feather.PcbDoc focused:
    AddU2Mask   adds SolderMaskExpansion_U2, InComponent('U2'), 0.035 mm (refuses if it exists). Priority is
                read-only from scripts: read Rules6 back after saving and check it outranks the global rule. }

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

Procedure AddU2Mask;
Var
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    R   : IPCB_Rule;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = 'SolderMaskExpansion_U2' Then
        Begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('SolderMaskExpansion_U2 already exists; no change made.');
            Exit;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    R := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);
    R.Name := 'SolderMaskExpansion_U2';
    R.Scope1Expression := 'InComponent(''U2'')';
    R.Scope2Expression := 'All';
    R.Expansion := MMsToCoord(0.035);
    R.NetScope := eNetScope_AnyNet;
    R.LayerKind := eRuleLayerKind_SameLayer;
    Brd.AddPCBObject(R);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Added SolderMaskExpansion_U2 (U2 pads, 0.035 mm). Save, then re-run the DRC.');
End;
