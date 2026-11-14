{ NoPmod_SupplyV.pas -- 2026-11-12. Zulu_a7_no_pmod Rev 2, signal-integrity set-up: the six 'Schematic Supply Nets'
  rules came over from the schematic with VOLTAGE 0. Altium SI uses these voltages for the IBIS supply/clamp rails,
  so set GND/GNDADC 0, VCC3V3 3.3, VCC1V8 1.8, VCCADC 1.8, VCC1V0 1.0. Reports every rule it touched. }
Function VoltFor(S : String) : Double;
Begin
    Result := -1;
    If Pos('''VCC3V3''', S) > 0 Then Result := 3.3
    Else If Pos('''VCC1V8''', S) > 0 Then Result := 1.8
    Else If Pos('''VCCADC''', S) > 0 Then Result := 1.8
    Else If Pos('''VCC1V0''', S) > 0 Then Result := 1.0
    Else If Pos('''GNDADC''', S) > 0 Then Result := 0
    Else If Pos('''GND''', S) > 0 Then Result := 0;
End;

Procedure NoPmodSupplyV;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    It  : IPCB_BoardIterator;
    R   : IPCB_Rule;
    v   : Double;
    n   : Integer;
    Msg : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    n := 0;
    Msg := '';
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
        Begin
            v := VoltFor(R.Scope1Expression);
            If v >= 0 Then
            Begin
                Try
                    R.BeginModify;
                    R.Voltage := v;
                    R.EndModify;
                    n := n + 1;
                    Msg := Msg + R.Name + ' ' + R.Scope1Expression + ' = ' + FloatToStr(R.Voltage) + #13#10;
                Except
                    Msg := Msg + R.Name + ': write rejected' + #13#10;
                End;
            End
            Else
                Msg := Msg + R.Name + ' ' + R.Scope1Expression + ': no voltage known, left alone' + #13#10;
        End;
        R := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    ShowMessage('Set ' + IntToStr(n) + ' supply-net voltages:' + #13#10 + Msg);
End;
