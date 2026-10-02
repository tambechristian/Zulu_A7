{ tools/ZuluHdiRules.pas -- standalone; run via File > Run Script > Browse... }

{ ============================================================================
  HDI VIA RULES, 2026-09-29 -- docs/hdi_spec.md, section "Altium rules"

  The board goes to JLCPCB HDI 2-step on JLCH061611N2-2116 (the user's
  decision, 2026-09-29).  The six via types already exist in the Layer Stack
  Manager (commit c62c24d).  This adds the rules that give them geometry and
  DRC, using only rule kinds and properties this file already proves:

    RoutingVias_uVia    RoutingViaStyle  IsMicroVia    hole 0.15  land 0.30
    RoutingVias_Buried  RoutingViaStyle  IsBuriedVia   hole 0.15  land 0.27
    RoutingVias         (exists)         All -> IsThruVia     0.20 / 0.35
    HoleSize_uVia       HoleSize         IsMicroVia    0.15 .. 0.15 absolute
    HoleSize_Buried     HoleSize         IsBuriedVia   0.15 .. 0.55 absolute
    PlaneClearance_uVia PlaneClearance   IsMicroVia    0.165 (hole-edge model:
                                           2 x max(0.075+0.15, 0.15+0.09) = 0.48 void)
    HoleToHoleClearance (exists)         Gap 0.20 -> 0.24  (JLC: hole edge to
                                           hole edge >= 0.24 between nets)

  WHY 0.15 / 0.30: JLC's aspect rule is <= 1:1 (hole >= dielectric) and the
  named stack's outer prepreg is 0.112 mm of 2116, so 0.10 is illegal; pad >=
  hole + 0.15.  0.12 / 0.27 is also rule-legal if JLC laser a non-default size
  (board/JLCPCB-HDI-ENQUIRY.md question 2) -- change the four numbers below.

  PRIORITY.  IPCB_Rule.Priority is READ-ONLY; a new rule lands at priority 1
  and pushes the rest down (ZuluSetup.pas, SetPwrRailWidths).  So the buried
  rule is created BEFORE the microvia rule of each kind, to end at
  uVia 1, Buried 2, the existing rule 3.  Scopes are disjoint anyway.

  STYLE.  Everything is inline and every helper is a Procedure: the first
  version used Functions called as bare statements (no precedent in this
  project) and died silently before its first ShowMessage.  Checkpoint
  messages stay in so a future failure names its own step.

  NOT DONE HERE, because the rule kinds are unproven in this project and an
  undeclared name halts DelphiScript: MinimumAnnularRing (the min=max sizes
  above already fix the ring at 0.075 / 0.06) and BoardOutlineClearance (the
  0.80 mm convention lives in the routing gates).  Add those in the GUI.
  HoleToHoleClearance's "Allow Stacked Micro Vias" is already TRUE in the file
  (ALLOWSTACKEDMICROVIAS=TRUE), so it is not touched.
  ============================================================================ }

Function HdiFindRule(AName : String) : IPCB_Rule;
Var
    Board : IPCB_Board;
    It    : IPCB_BoardIterator;
    R     : IPCB_Rule;
Begin
    Result := Nil;
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then Exit;
    It := Board.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = AName Then Result := R;
        R := It.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(It);
End;


Procedure HdiAddViaRule(AName, AScope : String; Hole, Land : Double; Log : TStringList);
Var
    Board : IPCB_Board;
    R     : IPCB_Rule;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    R := PCBServer.PCBRuleFactory(eRule_RoutingViaStyle);
    R.Name             := AName;
    R.Scope1Expression := AScope;
    R.Scope2Expression := 'All';
    R.NetScope         := eNetScope_AnyNet;
    R.LayerKind        := eRuleLayerKind_SameLayer;
    R.MinHoleWidth      := MMsToCoord(Hole);
    R.MaxHoleWidth      := MMsToCoord(Hole);
    R.PreferedHoleWidth := MMsToCoord(Hole);
    R.MinWidth          := MMsToCoord(Land);
    R.MaxWidth          := MMsToCoord(Land);
    R.PreferedWidth     := MMsToCoord(Land);
    Board.AddPCBObject(R);
    Log.Add(AName + '  ' + AScope + '  hole ' + FloatToStr(Hole) + ' land ' + FloatToStr(Land) +
            '  read back hole ' + FloatToStr(CoordToMMs(R.PreferedHoleWidth)) +
            ' land ' + FloatToStr(CoordToMMs(R.PreferedWidth)));
End;


Procedure HdiAddHoleRule(AName, AScope : String; HMin, HMax : Double; Log : TStringList);
Var
    Board : IPCB_Board;
    R     : IPCB_Rule;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    R := PCBServer.PCBRuleFactory(eRule_MaxMinHoleSize);
    R.Name             := AName;
    R.Scope1Expression := AScope;
    R.Scope2Expression := 'All';
    R.NetScope         := eNetScope_AnyNet;
    R.LayerKind        := eRuleLayerKind_SameLayer;
    R.AbsoluteValues   := True;
    R.MinLimit         := MMsToCoord(HMin);
    R.MaxLimit         := MMsToCoord(HMax);
    Board.AddPCBObject(R);
    Log.Add(AName + '  ' + AScope + '  ' + FloatToStr(HMin) + ' .. ' + FloatToStr(HMax) +
            '  read back ' + FloatToStr(CoordToMMs(R.MinLimit)) + ' .. ' + FloatToStr(CoordToMMs(R.MaxLimit)));
End;


Procedure AddHdiRules;
Var
    Board : IPCB_Board;
    R     : IPCB_Rule;
    Log   : TStringList;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;
    If HdiFindRule('RoutingVias_uVia') <> Nil Then
    Begin
        ShowMessage('RoutingVias_uVia already exists - nothing changed.');
        Exit;
    End;
    If HdiFindRule('RoutingVias') = Nil Then
    Begin
        ShowMessage('The RoutingVias rule is missing - nothing changed.');
        Exit;
    End;
    ShowMessage('AddHdiRules: checkpoint 1 - guards passed, creating rules now.');

    Log := TStringList.Create;

    { buried first, microvia second: the later one lands at priority 1 }
    HdiAddViaRule('RoutingVias_Buried', 'IsBuriedVia', 0.15, 0.27, Log);
    HdiAddViaRule('RoutingVias_uVia',   'IsMicroVia',  0.15, 0.30, Log);
    ShowMessage('AddHdiRules: checkpoint 2 - via style rules created.' + #13#10 + Log.Text);

    HdiAddHoleRule('HoleSize_Buried', 'IsBuriedVia', 0.15, 0.55, Log);
    HdiAddHoleRule('HoleSize_uVia',   'IsMicroVia',  0.15, 0.15, Log);

    R := PCBServer.PCBRuleFactory(eRule_PowerPlaneClearance);
    R.Name             := 'PlaneClearance_uVia';
    R.Scope1Expression := 'IsMicroVia';
    R.Scope2Expression := 'All';
    R.NetScope         := eNetScope_AnyNet;
    R.LayerKind        := eRuleLayerKind_SameLayer;
    R.Clearance        := MMsToCoord(0.165);
    Board.AddPCBObject(R);
    Log.Add('PlaneClearance_uVia  IsMicroVia  0.165  read back ' + FloatToStr(CoordToMMs(R.Clearance)));

    R := HdiFindRule('RoutingVias');
    R.BeginModify;
    R.Scope1Expression := 'IsThruVia';
    R.EndModify;
    Log.Add('RoutingVias  scope -> ' + R.Scope1Expression);

    R := HdiFindRule('HoleToHoleClearance');
    If R <> Nil Then
    Begin
        R.BeginModify;
        R.Gap := MMsToCoord(0.24);
        R.EndModify;
        Log.Add('HoleToHoleClearance  gap -> ' + FloatToStr(CoordToMMs(R.Gap)));
    End
    Else
        Log.Add('HoleToHoleClearance  NOT FOUND by that name - set 0.24 in the GUI');

    Board.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - HDI via rules added.' + #13#10 + #13#10 + Log.Text + #13#10 +
                'Check Design > Rules (priorities: uVia 1, Buried 2, existing 3), then' + #13#10 +
                'Tools > Design Rule Check > Run, then Ctrl+S.');
    Log.Free;
End;
