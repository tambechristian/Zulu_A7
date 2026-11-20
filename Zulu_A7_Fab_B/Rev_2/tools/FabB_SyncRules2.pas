{ FabB_SyncRules.pas -- GENERATED 2026-11-20 by tools/sync_altium_emit.py from tools/route/sync_altium/sync_data.json
  (the no-PMOD Rules6 / Classes6 at 427960e). Do not edit by hand. Run SyncRules with zulu_a7_fab_b.PcbDoc focused,
  after FabB_SyncPlace and the copper script. Adds, as on the no-PMOD board:
    ComponentClearance_R131R132  InComponent('R131') vs InComponent('R132'), 0 mm (created first -> priority 2)
    ComponentClearance_X2        InComponent('X2') vs All, 0.05 mm, vertical 0.05 mm (created second -> priority 1)
    SolderMaskExpansion_U2       InComponent('U2'), 0.035 mm, AnyNet, SameLayer (priority 1)
  sets the Schematic Supply Nets voltages VCC1V0 1, GND 0, GNDADC 0, VCC1V8 1.8, VCC3V3 3.3, VCCADC 1.8,
  adds SDRAM-D0..SDRAM-D15 to net class SDRAM_DATA (the only class the no-PMOD board puts them in), and
  invalidates U2's 65 pad mask caches so the new mask rule reaches them. Priority is read-only from scripts:
  read Rules6 back after saving (tools/sync_altium_verify.py). Refuses, changing nothing, unless every
  precondition holds. }

Var
    Brd  : IPCB_Board;
    Bad  : String;
    NBad : Integer;

Function SyncBoard : IPCB_Board;
Var
    Doc : IDocument;
    Ok  : Boolean;
Begin
    Result := Nil;
    Ok := False;
    Doc := GetWorkspace.DM_FocusedDocument;
    If Doc <> Nil Then
        If Pos('\Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc', Doc.DM_FullPath) > 0 Then Ok := True;
    If Not Ok Then
    Begin
        ShowMessage('Refusing (SyncRules): focus Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc first; nothing changed.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
    If Result = Nil Then
    Begin
        ShowMessage('Refusing (SyncRules): no PCB board is current; nothing changed.');
        Exit;
    End;
    If Pos('zulu_a7_fab_b.PcbDoc', Result.FileName) = 0 Then
    Begin
        ShowMessage('Refusing (SyncRules): the current board is ' + Result.FileName + ', not zulu_a7_fab_b.PcbDoc; nothing changed.');
        Result := Nil;
        Exit;
    End;
End;

Procedure Fail(S : String);
Begin
    NBad := NBad + 1;
    If NBad <= 30 Then Bad := Bad + S + #13#10;
End;

Function NetByName(AName : String) : IPCB_Net;
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    Result := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = AName Then Result := N;
        N := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Function RuleCount(AName : String) : Integer;
Var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
Begin
    Result := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = AName Then Result := Result + 1;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Function FindRule(AName : String) : IPCB_Rule;
Var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
Begin
    Result := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = AName Then Result := R;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

{ the expected voltage of a Schematic Supply Nets rule, from its scope; -1 = not one of the six }
Function VoltFor(S : String) : Double;
Begin
    Result := -1;
    If S = 'InNet(''VCC1V0'')' Then Result := 1.0
    Else If S = 'InNet(''GND'')' Then Result := 0.0
    Else If S = 'InNet(''GNDADC'')' Then Result := 0.0
    Else If S = 'InNet(''VCC1V8'')' Then Result := 1.8
    Else If S = 'InNet(''VCC3V3'')' Then Result := 3.3
    Else If S = 'InNet(''VCCADC'')' Then Result := 1.8;
End;

Function DataClass(Var N : Integer) : IPCB_ObjectClass;
Var
    It  : IPCB_BoardIterator;
    Cls : IPCB_ObjectClass;
Begin
    Result := Nil;
    N := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eClassObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Cls := It.FirstPCBObject;
    While Cls <> Nil Do
    Begin
        If (Cls.MemberKind = eClassMemberKind_Net) And (Cls.Name = 'SDRAM_DATA') Then
        Begin
            Result := Cls;
            N := N + 1;
        End;
        Cls := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure AddCC(AName, S1, S2 : String; G : Double);
Var
    R : IPCB_Rule;
Begin
    R := PCBServer.PCBRuleFactory(eRule_ComponentClearance);
    R.Name := AName;
    R.Scope1Expression := S1;
    R.Scope2Expression := S2;
    R.Gap := MMsToCoord(G);
    R.VerticalGap := MMsToCoord(G);
    Brd.AddPCBObject(R);
End;

Procedure SyncRules;
Var
    It    : IPCB_BoardIterator;
    R     : IPCB_Rule;
    Cls   : IPCB_ObjectClass;
    U2    : IPCB_Component;
    GI    : IPCB_GroupIterator;
    P     : IPCB_Pad;
    Ch    : TPadCache;
    nCls, nSup, nAdd, nHad, nCache, nPads, k : Integer;
    Msg   : String;
    v     : Double;
Begin
    Brd := SyncBoard;
    If Brd = Nil Then Exit;
    Bad := '';
    NBad := 0;

    { ---- preconditions ---- }
    If RuleCount('ComponentClearance_X2') <> 0 Then Fail('rule ComponentClearance_X2 already exists (run once only, on a board without it)');
    If RuleCount('ComponentClearance_R131R132') <> 0 Then Fail('rule ComponentClearance_R131R132 already exists (run once only, on a board without it)');
    If RuleCount('SolderMaskExpansion_U2') <> 0 Then Fail('rule SolderMaskExpansion_U2 already exists (run once only, on a board without it)');
    If RuleCount('ComponentClearance') <> 1 Then Fail('the board-wide rule ComponentClearance is not there exactly once');
    If RuleCount('SolderMaskExpansion') <> 1 Then Fail('the board-wide rule SolderMaskExpansion is not there exactly once');
    If Brd.GetPcbComponentByRefDes('X2') = Nil Then Fail('X2 is not on the board');
    If Brd.GetPcbComponentByRefDes('R131') = Nil Then Fail('R131 is not on the board (run FabB_SyncPlace first)');
    If Brd.GetPcbComponentByRefDes('R132') = Nil Then Fail('R132 is not on the board (run FabB_SyncPlace first)');
    U2 := Brd.GetPcbComponentByRefDes('U2');
    If U2 = Nil Then Fail('U2 is not on the board')
    Else
    Begin
        If U2.Pattern <> 'FT2232HQ-QFN64' Then Fail('U2 footprint is ' + U2.Pattern + ', expected FT2232HQ-QFN64');
        nPads := 0;
        GI := U2.GroupIterator_Create;
        GI.AddFilter_ObjectSet(MkSet(ePadObject));
        P := GI.FirstPCBObject;
        While P <> Nil Do
        Begin
            nPads := nPads + 1;
            P := GI.NextPCBObject;
        End;
        U2.GroupIterator_Destroy(GI);
        If nPads <> 65 Then Fail('U2 has ' + IntToStr(nPads) + ' pads, expected 65');
    End;
    { exactly the six Schematic Supply Nets rules, one per expected scope }
    nSup := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
        Begin
            nSup := nSup + 1;
            If VoltFor(R.Scope1Expression) < 0 Then
                Fail('supply-net rule ' + R.Name + ' has an unexpected scope ' + R.Scope1Expression);
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If nSup <> 6 Then Fail(IntToStr(nSup) + ' Schematic Supply Nets rules, expected 6');
    k := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
            If R.Scope1Expression = 'InNet(''VCC1V0'')' Then k := k + 1;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If k <> 1 Then Fail(IntToStr(k) + ' supply-net rules scoped InNet(''VCC1V0''), expected 1');
    k := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
            If R.Scope1Expression = 'InNet(''GND'')' Then k := k + 1;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If k <> 1 Then Fail(IntToStr(k) + ' supply-net rules scoped InNet(''GND''), expected 1');
    k := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
            If R.Scope1Expression = 'InNet(''GNDADC'')' Then k := k + 1;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If k <> 1 Then Fail(IntToStr(k) + ' supply-net rules scoped InNet(''GNDADC''), expected 1');
    k := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
            If R.Scope1Expression = 'InNet(''VCC1V8'')' Then k := k + 1;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If k <> 1 Then Fail(IntToStr(k) + ' supply-net rules scoped InNet(''VCC1V8''), expected 1');
    k := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
            If R.Scope1Expression = 'InNet(''VCC3V3'')' Then k := k + 1;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If k <> 1 Then Fail(IntToStr(k) + ' supply-net rules scoped InNet(''VCC3V3''), expected 1');
    k := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If Pos('Schematic Supply Nets', R.Name) = 1 Then
            If R.Scope1Expression = 'InNet(''VCCADC'')' Then k := k + 1;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If k <> 1 Then Fail(IntToStr(k) + ' supply-net rules scoped InNet(''VCCADC''), expected 1');
    Cls := DataClass(nCls);
    If nCls <> 1 Then Fail(IntToStr(nCls) + ' net classes named SDRAM_DATA, expected 1');
    If NetByName('SDRAM-D0') = Nil Then Fail('net SDRAM-D0 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D1') = Nil Then Fail('net SDRAM-D1 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D2') = Nil Then Fail('net SDRAM-D2 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D3') = Nil Then Fail('net SDRAM-D3 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D4') = Nil Then Fail('net SDRAM-D4 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D5') = Nil Then Fail('net SDRAM-D5 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D6') = Nil Then Fail('net SDRAM-D6 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D7') = Nil Then Fail('net SDRAM-D7 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D8') = Nil Then Fail('net SDRAM-D8 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D9') = Nil Then Fail('net SDRAM-D9 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D10') = Nil Then Fail('net SDRAM-D10 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D11') = Nil Then Fail('net SDRAM-D11 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D12') = Nil Then Fail('net SDRAM-D12 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D13') = Nil Then Fail('net SDRAM-D13 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D14') = Nil Then Fail('net SDRAM-D14 is not on the board (the ECO adds it)');
    If NetByName('SDRAM-D15') = Nil Then Fail('net SDRAM-D15 is not on the board (the ECO adds it)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D0')) Then Fail('SDRAM_DATA does not hold D0 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D1')) Then Fail('SDRAM_DATA does not hold D1 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D2')) Then Fail('SDRAM_DATA does not hold D2 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D3')) Then Fail('SDRAM_DATA does not hold D3 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D4')) Then Fail('SDRAM_DATA does not hold D4 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D5')) Then Fail('SDRAM_DATA does not hold D5 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D6')) Then Fail('SDRAM_DATA does not hold D6 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D7')) Then Fail('SDRAM_DATA does not hold D7 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D8')) Then Fail('SDRAM_DATA does not hold D8 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D9')) Then Fail('SDRAM_DATA does not hold D9 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D10')) Then Fail('SDRAM_DATA does not hold D10 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D11')) Then Fail('SDRAM_DATA does not hold D11 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D12')) Then Fail('SDRAM_DATA does not hold D12 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D13')) Then Fail('SDRAM_DATA does not hold D13 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D14')) Then Fail('SDRAM_DATA does not hold D14 (wrong class?)');
    If nCls = 1 Then
        If Not Cls.IsMember(NetByName('D15')) Then Fail('SDRAM_DATA does not hold D15 (wrong class?)');
    If NBad > 0 Then
    Begin
        ShowMessage('Refusing: ' + IntToStr(NBad) + ' precondition(s) failed; NOTHING was changed.' + #13#10 + Bad);
        Exit;
    End;

    { ---- apply ---- }
    Msg := '';
    PCBServer.PreProcess;
    Try
        AddCC('ComponentClearance_R131R132', 'InComponent(''R131'')', 'InComponent(''R132'')', 0.0);
        AddCC('ComponentClearance_X2', 'InComponent(''X2'')', 'All', 0.05);
        R := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);
        R.Name := 'SolderMaskExpansion_U2';
        R.Scope1Expression := 'InComponent(''U2'')';
        R.Scope2Expression := 'All';
        R.Expansion := MMsToCoord(0.035);
        R.NetScope := eNetScope_AnyNet;
        R.LayerKind := eRuleLayerKind_SameLayer;
        Brd.AddPCBObject(R);
        { supply-net voltages }
        It := Brd.BoardIterator_Create;
        It.AddFilter_ObjectSet(MkSet(eRuleObject));
        It.AddFilter_LayerSet(AllLayers);
        It.AddFilter_Method(eProcessAll);
        R := It.FirstPCBObject;
        While R <> Nil Do
        Begin
            If Pos('Schematic Supply Nets', R.Name) = 1 Then
            Begin
                v := VoltFor(R.Scope1Expression);
                Try
                    R.BeginModify;
                    R.Voltage := v;
                    R.EndModify;
                    Msg := Msg + '  ' + R.Scope1Expression + ' = ' + FloatToStr(R.Voltage) + ' V' + #13#10;
                    If Abs(R.Voltage - v) > 0.0001 Then
                        Fail(R.Name + ' voltage reads back ' + FloatToStr(R.Voltage));
                Except
                    Fail(R.Name + ': the voltage write was rejected');
                End;
            End;
            R := It.NextPCBObject;
        End;
        Brd.BoardIterator_Destroy(It);
        { net class }
        nAdd := 0;
        nHad := 0;
        If Cls.IsMember(NetByName('SDRAM-D0')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D0'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D1')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D1'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D2')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D2'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D3')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D3'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D4')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D4'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D5')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D5'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D6')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D6'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D7')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D7'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D8')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D8'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D9')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D9'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D10')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D10'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D11')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D11'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D12')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D12'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D13')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D13'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D14')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D14'); nAdd := nAdd + 1; End;
        If Cls.IsMember(NetByName('SDRAM-D15')) Then nHad := nHad + 1 Else Begin Cls.AddMemberByName('SDRAM-D15'); nAdd := nAdd + 1; End;
        If Not Cls.IsMember(NetByName('SDRAM-D0')) Then Fail('SDRAM-D0 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D1')) Then Fail('SDRAM-D1 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D2')) Then Fail('SDRAM-D2 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D3')) Then Fail('SDRAM-D3 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D4')) Then Fail('SDRAM-D4 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D5')) Then Fail('SDRAM-D5 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D6')) Then Fail('SDRAM-D6 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D7')) Then Fail('SDRAM-D7 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D8')) Then Fail('SDRAM-D8 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D9')) Then Fail('SDRAM-D9 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D10')) Then Fail('SDRAM-D10 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D11')) Then Fail('SDRAM-D11 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D12')) Then Fail('SDRAM-D12 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D13')) Then Fail('SDRAM-D13 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D14')) Then Fail('SDRAM-D14 did not join SDRAM_DATA');
        If Not Cls.IsMember(NetByName('SDRAM-D15')) Then Fail('SDRAM-D15 did not join SDRAM_DATA');
        { U2 pad mask caches, so SolderMaskExpansion_U2 reaches the pads (no-PMOD NoPmodU2MaskCache.pas) }
        nCache := 0;
        GI := U2.GroupIterator_Create;
        GI.AddFilter_ObjectSet(MkSet(ePadObject));
        P := GI.FirstPCBObject;
        While P <> Nil Do
        Begin
            Ch := P.Cache;
            Ch.SolderMaskExpansionValid := eCacheInvalid;
            P.BeginModify;
            P.Cache := Ch;
            P.EndModify;
            nCache := nCache + 1;
            P := GI.NextPCBObject;
        End;
        U2.GroupIterator_Destroy(GI);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    { ---- read back ---- }
    R := FindRule('ComponentClearance_X2');
    If R = Nil Then Fail('ComponentClearance_X2 is not on the board after adding it')
    Else If (Abs(CoordToMMs(R.Gap) - 0.05) > 0.0001) Or (Abs(CoordToMMs(R.VerticalGap) - 0.05) > 0.0001) Then Fail('ComponentClearance_X2 gap reads ' + FloatToStr(CoordToMMs(R.Gap)));
    R := FindRule('ComponentClearance_R131R132');
    If R = Nil Then Fail('ComponentClearance_R131R132 is not on the board after adding it')
    Else If (Abs(CoordToMMs(R.Gap)) > 0.0001) Or (Abs(CoordToMMs(R.VerticalGap)) > 0.0001) Then Fail('ComponentClearance_R131R132 gap reads ' + FloatToStr(CoordToMMs(R.Gap)));
    R := FindRule('SolderMaskExpansion_U2');
    If R = Nil Then Fail('SolderMaskExpansion_U2 is not on the board after adding it')
    Else If Abs(CoordToMMs(R.Expansion) - 0.035) > 0.0001 Then Fail('SolderMaskExpansion_U2 expansion reads ' + FloatToStr(CoordToMMs(R.Expansion)));
    If nCache <> 65 Then Fail(IntToStr(nCache) + ' U2 pad mask caches invalidated, expected 65');
    If NBad > 0 Then
        ShowMessage('DO NOT SAVE: ' + IntToStr(NBad) + ' read-back check(s) failed. Close the PcbDoc WITHOUT saving and reopen it.' + #13#10 + Bad)
    Else
        ShowMessage('SyncRules OK: added ComponentClearance_R131R132 (0 mm), ComponentClearance_X2 (0.05 mm), ' +
            'SolderMaskExpansion_U2 (0.035 mm); supply-net voltages:' + #13#10 + Msg + 'SDRAM_DATA: ' + IntToStr(nAdd) + ' SDRAM-Dn added, ' +
            IntToStr(nHad) + ' already members (16 in all); U2 mask caches invalidated: ' + IntToStr(nCache) + ' of 65. Next: FabB_SyncBodies.');
End;

