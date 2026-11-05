{ FeatherNpthScope.pas -- 2026-11-05: Clearance_Plane_NPTH was added with Scope2 = IsPad And InNet('No Net'), which matches no
  pad at all (ProbeNpth), so the pours stayed 0.0762 mm from the six non-plated holes and the DRC passed vacuously. The
  probe found Name = 'X2-' (4 pads) and Name = 'X1-' (2 pads) match exactly those six holes. Writes that scope and refuses
  to keep it unless it matches 6 pads, all without a net and with a hole.
  Run NpthScope with asar_feather.PcbDoc focused, then Repour All, DRC, Save. }

Procedure NpthScope;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    P   : IPCB_Pad;
    R, Hit : IPCB_Rule;
    Old : String;
    NAll, NHole : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Hit := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = 'Clearance_Plane_NPTH' Then Hit := R;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Hit = Nil Then
    Begin
        ShowMessage('Refusing: Clearance_Plane_NPTH not found.');
        Exit;
    End;

    Old := Hit.Scope2Expression;
    Hit.BeginModify;
    Hit.Scope2Expression := 'IsPad And ((Name = ''X2-'') Or (Name = ''X1-''))';
    Hit.EndModify;
    NAll := 0;
    NHole := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If Hit.Scope2Includes(P) Then
        Begin
            NAll := NAll + 1;
            If (P.Net = Nil) And (P.HoleSize > 0) And (Not P.Plated) Then NHole := NHole + 1;
        End;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (NAll <> 6) Or (NHole <> 6) Then
    Begin
        Hit.BeginModify;
        Hit.Scope2Expression := Old;
        Hit.EndModify;
        ShowMessage('Refusing: the scope matched ' + IntToStr(NAll) + ' pads, ' + IntToStr(NHole) + ' holes; restored ' + Old);
        Exit;
    End;
    Doc.SetModified(True);
    ShowMessage(Hit.Name + ' gap ' + FloatToStr(CoordToMMs(Hit.Gap)) + ' mm, priority ' + IntToStr(Hit.Priority) + #13#10 +
                'Scope 2: ' + Hit.Scope2Expression + #13#10 + 'matches ' + IntToStr(NAll) + ' pads, ' + IntToStr(NHole) +
                ' non-plated holes.' + #13#10 + 'Now Repour All, DRC, Save.');
End;
