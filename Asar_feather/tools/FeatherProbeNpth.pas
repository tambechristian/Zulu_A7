{ FeatherProbeNpth.pas -- 2026-11-05: read-only apart from the scratch scope of the rule it restores. Clearance_Plane_NPTH with
  Scope2 = IsPad And InNet('No Net') left the pours 0.0762 mm from the non-plated holes, so that scope matched nothing.
  Reports how the six holes look from the API and how many pads each candidate scope matches.
  Run ProbeNpth with asar_feather.PcbDoc focused. }

Var
    Brd : IPCB_Board;

Function CountMatches(R : IPCB_Rule; E : String) : String;
Var
    It : IPCB_BoardIterator;
    P  : IPCB_Pad;
    NAll, NHole : Integer;
Begin
    R.Scope2Expression := E;
    NAll := 0;
    NHole := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If R.Scope2Includes(P) Then
        Begin
            NAll := NAll + 1;
            If (P.Net = Nil) And (P.HoleSize > 0) Then NHole := NHole + 1;
        End;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Result := E + ' -> ' + IntToStr(NAll) + ' pads, ' + IntToStr(NHole) + ' of the holes' + #13#10;
End;

Procedure ProbeNpth;
Var
    Doc : IDocument;
    It  : IPCB_BoardIterator;
    P   : IPCB_Pad;
    R, Hit : IPCB_Rule;
    Log, Old : String;
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

    Log := '';
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Net = Nil) And (P.HoleSize > 0) Then
            Log := Log + 'hole ' + FloatToStr(CoordToMMs(P.HoleSize)) + ' name [' + P.Name + '] plated ' +
                   BoolToStr(P.Plated, True) + ' layer ' + Layer2String(P.Layer) + #13#10;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    Old := Hit.Scope2Expression;
    Log := Log + CountMatches(Hit, 'IsPad');
    Log := Log + CountMatches(Hit, Old);
    Log := Log + CountMatches(Hit, 'IsPad And (Net = ''No Net'')');
    Log := Log + CountMatches(Hit, 'IsPad And (Not PadIsPlated)');
    Log := Log + CountMatches(Hit, 'IsPad And (PadIsPlated = False)');
    Log := Log + CountMatches(Hit, 'IsPad And (Name = ''X2-'')');
    Log := Log + CountMatches(Hit, 'IsPad And (Name = ''X1-'')');
    Log := Log + CountMatches(Hit, 'IsPad And (Not HasNet)');
    Hit.Scope2Expression := Old;
    ShowMessage(Log + 'Scope restored: ' + Hit.Scope2Expression);
End;
