{ FeatherRules3.pas -- 2026-11-04, the user's 3/3 mil decision: the global Clearance rule goes from 0.09 mm (JLC's
  3.5 mil floor, inherited from production) to 0.0762 mm (3 mil, PCBWay's HDI tier). Measured first: a 3 mil
  clearance opens the Top lanes between U1's 0.25 mm lands at 0.5 mm pitch (0.0869 mm track-to-land) and takes the
  global route from 25 open to 12 (docs/routing.md, 2026-11-04). The SDRAM inner-layer clearances (0.10 / 0.20 on
  L3/L4) and Clearance_Plane_ThruVia (0.175) are left alone -- the router models them as they are.
  Run with asar_feather.PcbDoc focused (File > Run Script > Browse > From file > tools/FeatherRules3.PrjScr):
    SetClearance3mil  - guarded: writes only if the rule named 'Clearance' is not already 0.0762; lists every
                        clearance rule before and after. Then Tools > Polygon Pours > Repour All, DRC, File > Save. }

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

Function MmText(C : TCoord) : String;
Begin
    Result := FormatFloat('0.0000', CoordToMMs(C)) + ' mm';
End;

Function ListClearances(Brd : IPCB_Board) : String;
Var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
Begin
    Result := '';
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.RuleKind = eRule_Clearance Then
            Result := Result + '  ' + R.Name + '  gap ' + MmText(R.Gap) + '  ' + R.Scope1Expression + ' / ' +
                      R.Scope2Expression + #13#10;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Function FindClearanceRule(Brd : IPCB_Board) : IPCB_Rule;
Var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
Begin
    { the rule named 'Clearance'; failing that, the clearance rule scoped All / All }
    Result := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.RuleKind = eRule_Clearance Then
        Begin
            If R.Name = 'Clearance' Then
            Begin
                Result := R;
                Break;
            End;
            If (Result = Nil) And (R.Scope1Expression = 'All') And (R.Scope2Expression = 'All') Then
                Result := R;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure SetClearance3mil;
Var
    Brd : IPCB_Board;
    R   : IPCB_Rule;
    Log : String;
    G   : Double;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    Log := 'Clearance rules before:' + #13#10 + ListClearances(Brd);
    R := FindClearanceRule(Brd);
    If R = Nil Then
        Log := Log + 'NO global clearance rule found -- nothing written' + #13#10
    Else
    Begin
        G := CoordToMMs(R.Gap);
        If Abs(G - 0.0762) < 0.0005 Then
            Log := Log + R.Name + ' is already 0.0762 mm -- nothing written' + #13#10
        Else
        Begin
            R.BeginModify;
            Try
                R.Gap := MMsToCoord(0.0762);
                Log := Log + R.Name + ' gap ' + FormatFloat('0.0000', G) + ' -> ' + MmText(R.Gap) + #13#10;
            Except
                Log := Log + R.Name + ' FAILED -- Gap write rejected' + #13#10;
            End;
            R.EndModify;
        End;
    End;
    Brd.ViewManager_FullUpdate;
    Log := Log + 'Clearance rules after:' + #13#10 + ListClearances(Brd);
    ShowMessage(Log + 'Now: Tools > Polygon Pours > Repour All, DRC, File > Save asar_feather.PcbDoc.');
End;
