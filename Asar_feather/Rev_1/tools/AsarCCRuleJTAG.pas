{ AsarCCRuleJTAG.pas -- 2026-11-21 (docs/jtag_block.md). Component Clearance exception for the JTAG test-pad block:
    ComponentClearance_JP3JP4  InComponent('JP3') vs InComponent('JP4'), 0.10 mm.
  JP3 (TCK/TMS/GND) and JP4 (TDI/TDO/VCC3V3) now form one 2x3 block of 1.0 mm pads at 1.27 mm pitch on the Bottom:
  0.27 mm copper gap, 0.17 mm mask web (pad_gate). Neither has a 3D body (test pads, exempt in emit_bodies.py), so
  Altium measures their primitive boxes and flags the pair under the 0.254 mm board-wide rule.
  Run AddJtagRule with asar_feather.PcbDoc focused, then save. Refuses if the rule exists. }
Procedure AddJtagRule;
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
        If R.Name = 'ComponentClearance_JP3JP4' Then
        Begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('Refusing: ComponentClearance_JP3JP4 already exists.');
            Exit;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    R := PCBServer.PCBRuleFactory(eRule_ComponentClearance);
    R.Name := 'ComponentClearance_JP3JP4';
    R.Scope1Expression := 'InComponent(''JP3'')';
    R.Scope2Expression := 'InComponent(''JP4'')';
    R.Gap := MMsToCoord(0.10);
    R.VerticalGap := MMsToCoord(0.10);
    Brd.AddPCBObject(R);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Added ComponentClearance_JP3JP4 (0.10 mm). Save, then re-run the DRC.');
End;
