{ SI_DetachSupply.pas -- 2026-11-12. SI-ONLY COPY: Altium SI simulated every driver to a 5.000 V top value although the
  'Schematic Supply Nets' rules on the board say VCC3V3 = 3.3 V. Those rules are flagged DefinedByLogicalDocument, so
  the SI engine may re-derive them from the schematic power ports (no voltage there -> default 5 V).
  SIDetachSupplyRules: removes the stray 'SI_GND' rule a failed first attempt added, then marks every 'Schematic Supply
  Nets' rule as board-defined (DefinedByLogicalDocument := False) keeping its voltage, and reports name/scope/voltage.
  Refuses to run on anything but the SI copy. }
Procedure SIDetachSupplyRules;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    It  : IPCB_BoardIterator;
    R   : IPCB_Rule;
    L   : TInterfaceList;
    i   : Integer;
    Msg : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\si\altium_si\Zulu_a7_no_pmod_SI.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the SI copy si\altium_si\Zulu_a7_no_pmod_SI.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    Msg := '';
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        L.Add(R);
        R := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    For i := 0 To L.Count - 1 Do
    Begin
        R := L.Items[i];
        If R.Name = 'SI_GND' Then
        Begin
            B.RemovePCBObject(R);
            Msg := Msg + 'removed SI_GND' + #13#10;
        End
        Else If Pos('Schematic Supply Nets', R.Name) = 1 Then
        Begin
            Try
                R.BeginModify;
                R.DefinedByLogicalDocument := False;
                R.EndModify;
                Msg := Msg + R.Name + ' ' + R.Scope1Expression + ' V=' + FloatToStr(R.Voltage) + ' logical=' + BoolToStr(R.DefinedByLogicalDocument, True) + #13#10;
            Except
                Msg := Msg + R.Name + ': write rejected' + #13#10;
            End;
        End;
    End;
    ShowMessage(Msg);
End;
