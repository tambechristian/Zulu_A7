{ HdiX1Rules.pas -- Zulu_Altium_VS_Code_HDI_Optimized, 2026-10-07.
  HdiX1Pads.pas created Clearance_X1MS_L5Plane with the scope (InPad('X1-MS1') Or InPad('X1-MS2')); InPad is not an
  Altium query keyword, so the rule could never match and every evaluation raised "Undeclared identifier: InPad".
  This sets the scope to InComponent('X1'). On L5 that covers X1's through-hole pads only (MS1/MS2 and the GND pegs
  MH1/MH2), so the plane keeps 0.10 mm from all four. Run with zulu_a7_hdi_optimized.PcbDoc focused. }

Procedure FixX1RuleScope;
Var
    WS  : IWorkspace;
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    R   : IPCB_Rule;
    Hit : IPCB_Rule;
Begin
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Doc := WS.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_Altium_VS_Code_HDI_Optimized\Imported zulu_a7.PrjPcb\zulu_a7_hdi_optimized.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus zulu_a7_hdi_optimized.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    Hit := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = 'Clearance_X1MS_L5Plane' Then Hit := R;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Hit = Nil Then Begin ShowMessage('Clearance_X1MS_L5Plane not found.'); Exit; End;
    Hit.BeginModify;
    Hit.Scope1Expression := 'InComponent(''X1'')';
    Hit.EndModify;
    ShowMessage('Clearance_X1MS_L5Plane scope 1 is now: ' + Hit.Scope1Expression + #13#10 +
        'scope 2: ' + Hit.Scope2Expression + '   gap ' + FloatToStr(CoordToMMs(Hit.Gap)));
End;
