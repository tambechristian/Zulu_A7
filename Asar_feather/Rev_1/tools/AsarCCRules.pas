{ AsarCCRules.pas -- 2026-11-19 (docs/body_fixes.md). Component Clearance exceptions above the board-wide 0.254 mm rule,
  for Altium's Component Clearance check on the 3D bodies (new rules land at priority 1; read Rules6 back after saving):
    ComponentClearance_X2        InComponent('X2') vs All, 0.05 mm: X2's two header housings sit on the Bottom (the
                                 headers ship loose, Feather style) and the 0201 row C40..C38 (0.105 mm after the
                                 2026-11-19 move), C101/C102 (0.14) and C139 (0.24) are closer than 0.254 without
                                 touching. Same rule as the no-PMOD board.
    ComponentClearance_C165R117  0.15 mm: 0402 / 0201 pair 0.20 mm apart on the Bottom since the LTC3556 block.
    ComponentClearance_C166R118  0.15 mm: 0402 / 0201 pair 0.25 mm apart (just under 0.254).
    ComponentClearance_R1R34     0.15 mm: the two resistor arrays 0.22 mm apart on the Bottom.
  Run AddRules with asar_feather.PcbDoc focused, then save. Refuses if any of these rules exists. }
Procedure AddCC(Brd : IPCB_Board; Name, S1, S2 : String; G : Double);
Var
    R : IPCB_Rule;
Begin
    R := PCBServer.PCBRuleFactory(eRule_ComponentClearance);
    R.Name := Name;
    R.Scope1Expression := S1;
    R.Scope2Expression := S2;
    R.Gap := MMsToCoord(G);
    R.VerticalGap := MMsToCoord(G);
    Brd.AddPCBObject(R);
End;

Procedure AddRules;
Var
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    R   : IPCB_Rule;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('asar_feather.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus asar_feather.PcbDoc first.');
        Exit;
    End;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If (R.Name = 'ComponentClearance_X2') Or (R.Name = 'ComponentClearance_C165R117') Or
           (R.Name = 'ComponentClearance_C166R118') Or (R.Name = 'ComponentClearance_R1R34') Then
        Begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('Refusing: ' + R.Name + ' already exists.');
            Exit;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    AddCC(Brd, 'ComponentClearance_R1R34', 'InComponent(''R1'')', 'InComponent(''R34'')', 0.15);
    AddCC(Brd, 'ComponentClearance_C166R118', 'InComponent(''C166'')', 'InComponent(''R118'')', 0.15);
    AddCC(Brd, 'ComponentClearance_C165R117', 'InComponent(''C165'')', 'InComponent(''R117'')', 0.15);
    AddCC(Brd, 'ComponentClearance_X2', 'InComponent(''X2'')', 'All', 0.05);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Added ComponentClearance_X2 (0.05 mm) and three 0.15 mm chip-pair rules. Save, then re-run the DRC.');
End;
