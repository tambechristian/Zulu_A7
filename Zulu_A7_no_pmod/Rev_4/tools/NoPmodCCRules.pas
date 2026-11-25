{ NoPmodCCRules.pas -- 2026-11-19, user decision "fix real overlaps only". Two Component Clearance exceptions, added
  above the board-wide 0.254 mm rule (new rules land at priority 1; read Rules6 back after saving):
    ComponentClearance_X2       InComponent('X2') vs All, 0.05 mm: X2's 1x10 header housings sit on the Bottom and
                                L4-L7 / R10 / R11 / the C0603 row are 0.06 mm from them, touching nothing.
    ComponentClearance_R131R132 InComponent('R131') vs InComponent('R132'), 0 mm: the DQ series-resistor spacing the
                                user accepted on 2026-11-13 (docs/dq_series_resistors.md).
  Run AddRules with Zulu_a7_no_pmod.PcbDoc focused, then save. Refuses if either rule exists. }
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
    If (Brd = Nil) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If (R.Name = 'ComponentClearance_X2') Or (R.Name = 'ComponentClearance_R131R132') Then
        Begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('Refusing: ' + R.Name + ' already exists.');
            Exit;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    AddCC(Brd, 'ComponentClearance_R131R132', 'InComponent(''R131'')', 'InComponent(''R132'')', 0.0);
    AddCC(Brd, 'ComponentClearance_X2', 'InComponent(''X2'')', 'All', 0.05);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Added ComponentClearance_X2 (0.05 mm) and ComponentClearance_R131R132 (0 mm). Save, then re-run the DRC.');
End;
