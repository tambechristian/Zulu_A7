{ =============================================================================
  ZuluRules.pas
  Zulu A7 - 69.85 x 25.40 mm, 6 layers (Top / L2-GND / L3-SIG / L4-SIG /
  L5-GND / Bottom), through-vias only, fabricated at JLCPCB.

  Nine stock design rules in zulu_a7.PcbDoc are still at Altium's factory
  values. This script rewrites them to the numbers in
  board/zulu_a7-6layer-jlcpcb.dru - JLCPCB's published multilayer capability,
  confirmed with JLC on 2026-08-27 - plus the project's stack decision.

  HOW TO RUN
      File > Run Script... > SetZuluRules       applies the nine rules
      File > Run Script... > ReportZuluRules    reads them all back

  Only parameterless procedures appear in the Run Script picker, so those two
  are the entry points; every helper below takes parameters and stays hidden.

  WHAT THIS SCRIPT DELIBERATELY DOES NOT DO
    * It does not create rules.  All nine ship as Altium defaults and exist
      exactly once in this document, so the job is to edit them in place - a
      second rule of the same kind would start a priority contest instead.
      If a kind has been deleted the iterator simply never sees it: nothing
      crashes, and the summary box lists it under NOT FOUND.  Re-add it by
      hand (Design > Rules, right-click the category, New Rule) and re-run.
    * It does not touch PasteMaskExpansion.  Out of scope, stays at 0.
    * It does not save.  Press Ctrl+S afterwards, then re-run
      Tools > Design Rule Check - existing violation markers stay stale until
      DRC runs again, and the values only reach the Rules6 stream on save.
    * It does not assign nets to the two Plane layers.  That is a layer-stack
      property (Design > Layer Stack Manager > L2-GND / L5-GND > Net Name),
      not a rule.  Until GND is assigned there, PlaneClearance and
      PlaneConnect have nothing to act on.

  SAFETY NET
    Property names differ slightly between Altium builds (MinSolderMaskSliver
    vs MinSolderMaskWidth, indexed vs scalar width, scalar vs per-primitive
    plane-connect setters).  Each write sits in its own Try..Except and the
    alternative spelling is attempted as a fallback, so one rejected name
    cannot abandon the other eight rules.  The summary box says which form
    landed; ReportZuluRules proves the values afterwards.
  ============================================================================= }


{ --- small helpers ---------------------------------------------------------
  All take parameters, so none of them shows up in the Run Script list.       }

Function MmText(C : TCoord) : String;
Begin
    { Everything in this script is metric; show four decimals so 0.0762 mm
      (the 3 mil BGA fan-out minimum) is readable rather than rounded away.  }
    Result := FloatToStr(Round(CoordToMMs(C) * 10000) / 10000) + ' mm';
End;


{ --- the nine writers ------------------------------------------------------ }

Procedure ApplyClearance(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Begin
    { 2026-09-14: only the global rule named 'Clearance'. The SDRAM bus now has
      Clearance_SDRAM_INNER (0.10) and Clearance_SDRAM_CLK (0.20) on L3/L4, set by
      SetSdramRules in ZuluSetup.pas; dispatching on RuleKind alone would write
      0.09 into both.                                                          }
    If R.Name <> 'Clearance' Then
    Begin
        Log.Add('Clearance (' + R.Name + ')  left alone - see SetSdramRules');
        Exit;
    End;
    Touched.Add('Clearance');
    R.BeginModify;
    Try
        { 0.09 mm (3.5 mil) is JLCPCB's published minimum copper-to-copper
          spacing on a multilayer board and the value every mdWireWire ..
          mdViaViaSameLayer line in zulu_a7-6layer-jlcpcb.dru carries.  The
          10 mil default is four times looser than the process and would make
          the 0.5 mm BGA escape impossible.  GENERICCLEARANCE in the file is
          the object-clearance matrix's generic cell, not a settable rule
          property - Altium keeps it in step with Gap by itself.             }
        R.Gap := MMsToCoord(0.09);
        Log.Add('Clearance                gap 0.09 mm');
    Except
        Log.Add('Clearance                FAILED - Gap was rejected');
    End;
    R.EndModify;
End;


Function ApplyWidthOnLayer(R : IPCB_Rule; L : TLayer) : Boolean;
Begin
    { On most builds Width is a per-layer table - MinWidth[L] in the API,
      written MinWidth(L) in DelphiScript because the script engine has no
      [] on properties.  Max goes first: the rule starts at 10/10/10 mil, so
      widening the window before dropping the floor keeps it legal at every
      intermediate step and stops Altium clamping the preferred value.       }
    Result := True;
    Try
        R.MaxWidth(L)     := MMsToCoord(0.5);
        R.MinWidth(L)     := MMsToCoord(0.0762);
        R.FavoredWidth(L) := MMsToCoord(0.1);
    Except
        Result := False;
    End;
End;


Procedure ApplyWidth(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Var
    OkTop, OkMid1, OkMid2, OkBot, OkLayers, OkScalar, OkPlain : Boolean;
Begin
    { 2026-09-14: ONLY the global rule named 'Width' is touched here. The board
      now carries per-layer power-rail Width rules (Width_PWR_VCC3V3,
      Width_PWR_U8, Width_PWR_VCC1V0, Width_PWR_RAILS, set by SetPwrRailWidths
      in ZuluSetup.pas) and Width_PWR_SWITCH. Dispatching on RuleKind alone
      used to reach every one of them, and the scalar writes below would have
      re-uniformed their layer tables to 0.0762 / 0.1 / 0.5 without a word.  }
    If R.Name <> 'Width' Then
    Begin
        Log.Add('Width (' + R.Name + ')  left alone - see SetPwrRailWidths');
        Exit;
    End;
    Touched.Add('Width');
    R.BeginModify;

    { The three widths, and why:
        min 0.0762 mm (3 mil) - JLC's absolute floor (msWidth in the .dru).
          It exists only so the BGA fan-out under U1 can neck down; nothing
          else on the board is allowed to be this thin by choice.
        preferred 0.1 mm - the everyday routing width, comfortably above the
          floor so normal tracks carry a margin against etch variation.
        max 0.5 mm - lets the three SC189 rails and the LiPo path be poured
          wide without DRC complaining, while still flagging a fat mistake. }

    { Form 1: the per-layer table, over this board's four signal layers.
      L2-GND and L5-GND are Plane layers and carry no width values.         }
    OkTop  := ApplyWidthOnLayer(R, eTopLayer);
    OkMid1 := ApplyWidthOnLayer(R, eMidLayer1);   { L3-SIG }
    OkMid2 := ApplyWidthOnLayer(R, eMidLayer2);   { L4-SIG }
    OkBot  := ApplyWidthOnLayer(R, eBottomLayer);
    OkLayers := OkTop And OkMid1 And OkMid2 And OkBot;

    { Form 2: the scalar aggregates.  These are the three keys the PcbDoc
      actually stores (MINLIMIT / MAXLIMIT / PREFEREDWIDTH - Altium's own
      one-r spelling), so writing them keeps the rule uniform rather than
      leaving it as a per-layer table.                                      }
    OkScalar := True;
    Try
        R.MaxLimit      := MMsToCoord(0.5);
        R.MinLimit      := MMsToCoord(0.0762);
        R.PreferedWidth := MMsToCoord(0.1);
    Except
        OkScalar := False;
    End;

    { Form 3: only if neither of the above was accepted - some builds expose
      MinWidth / MaxWidth / FavoredWidth here as plain scalars.             }
    OkPlain := False;
    If (Not OkLayers) And (Not OkScalar) Then
    Begin
        Try
            R.MaxWidth     := MMsToCoord(0.5);
            R.MinWidth     := MMsToCoord(0.0762);
            R.FavoredWidth := MMsToCoord(0.1);
            OkPlain := True;
        Except
            OkPlain := False;
        End;
    End;

    If OkLayers Or OkScalar Or OkPlain Then
        Log.Add('Width                    min 0.0762 / pref 0.1 / max 0.5 mm')
    Else
        Log.Add('Width                    FAILED - no width property form was accepted');
    R.EndModify;
End;


Procedure ApplyRoutingVias(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Begin
    Touched.Add('RoutingVias');
    R.BeginModify;
    Try
        { One via geometry for the whole board: 0.2 mm drill in a 0.35 mm pad,
          a 0.075 mm annular ring - JLC's own recommendation in their
          2026-09-14 reply (0.30 was their producible minimum; the change and
          its arithmetic are in docs/via_land_decision.md).  Min,
          max and preferred are set to the same number on purpose: the
          autorouter and the interactive router then cannot invent a second
          via size that the fab would have to quote separately.
          Order is min, then max, then preferred - the rule starts at a
          28 mil hole in a 50 mil pad, both far larger than the targets, so
          lowering the floor first keeps min <= max at every step.          }
        R.MinHoleWidth      := MMsToCoord(0.2);
        R.MaxHoleWidth      := MMsToCoord(0.2);
        R.PreferedHoleWidth := MMsToCoord(0.2);
        R.MaxWidth          := MMsToCoord(0.35);
        R.MinWidth          := MMsToCoord(0.35);
        R.PreferedWidth     := MMsToCoord(0.35);
        Log.Add('RoutingVias              hole 0.2 mm in 0.35 mm pad');
    Except
        Log.Add('RoutingVias              FAILED - a size property was rejected');
    End;

    { Already 'Through Hole' in the file - asserted so the six numbers above
      cannot be quietly reinterpreted as a blind/buried stack.  If the
      compiler rejects eViaThruHole, delete this block; nothing is lost.    }
    Try
        R.ViaStyle := eViaThruHole;
    Except
        Log.Add('RoutingVias              note: ViaStyle left as found');
    End;

    { With via templates on, the six numeric fields are ignored in favour of
      a named template and the change would silently not apply.             }
    Try
        R.UseViaTemplates := False;
    Except
        Log.Add('RoutingVias              note: UseViaTemplates left as found');
    End;
    R.EndModify;
End;


Procedure ApplyHoleSize(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Begin
    Touched.Add('HoleSize');
    R.BeginModify;
    Try
        { AbsoluteValues first: while it is False the limits are read as
          percentages of the pad and the coordinates below do nothing.      }
        R.AbsoluteValues := True;
        { 0.2 mm is the same JLC drill floor the via rule uses, so a stray
          smaller hole anywhere on the board is caught.  1.02 mm is the
          Sullins header drill on X2 - the largest hole the design legally
          contains, so anything bigger is a mistake rather than a part.     }
        R.MinLimit := MMsToCoord(0.2);
        R.MaxLimit := MMsToCoord(1.02);
        Log.Add('HoleSize                 0.2 mm to 1.02 mm, absolute');
    Except
        Log.Add('HoleSize                 FAILED - a limit property was rejected');
    End;
    R.EndModify;
End;


Procedure ApplyHoleToHole(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Begin
    Touched.Add('HoleToHoleClearance');
    R.BeginModify;
    Try
        { 0.2 mm hole-to-hole edge spacing is JLC's drill-to-drill minimum
          (mdDrill in the .dru).  It matters where the fan-out vias crowd
          under U1 and along the X2 header field.  AllowStackedMicroVias is
          left alone - irrelevant on an all-through-via board.              }
        R.Gap := MMsToCoord(0.2);
        Log.Add('HoleToHoleClearance      gap 0.2 mm');
    Except
        Log.Add('HoleToHoleClearance      FAILED - Gap was rejected');
    End;
    R.EndModify;
End;


Procedure ApplySolderMaskExpansion(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Begin
    Touched.Add('SolderMaskExpansion');
    R.BeginModify;
    Try
        { 0.05 mm per side, matching mlMinStopFrame / mlMaxStopFrame in the
          .dru.  The 0 mil default is a mask-defined opening, which JLC's
          registration tolerance cannot hold on the 0.5 mm BGA pitch - the
          mask would creep onto the lands.  0.05 mm gives a copper-defined
          pad with enough slop for their alignment.  UseSeparateExpansions is
          False in this document, so this single value covers both sides.   }
        R.Expansion := MMsToCoord(0.05);
        Log.Add('SolderMaskExpansion      0.05 mm per side');
    Except
        Log.Add('SolderMaskExpansion      FAILED - Expansion was rejected');
    End;
    R.EndModify;
End;


Procedure ApplySliver(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Var
    Done : Boolean;
Begin
    Touched.Add('MinimumSolderMaskSliver');
    R.BeginModify;

    { The critical one.  A 0.225 mm BGA land plus 0.05 mm expansion opens to
      0.325 mm; on the 0.5 mm pitch that leaves a 0.175 mm mask dam between
      neighbouring openings.  The 10 mil (0.254 mm) default would therefore
      flag every ball under U1 - hundreds of violations that are not real.
      0.1 mm is what JLC will actually print, and it still catches genuinely
      unprintable slivers elsewhere.
      Name trap: the PcbDoc key is MINSOLDERMASKWIDTH and the internal class
      publishes MinSolderMaskWidth, but the scripting property is normally
      MinSolderMaskSliver.  Try the script name, fall back to the file name. }
    Done := True;
    Try
        R.MinSolderMaskSliver := MMsToCoord(0.1);
    Except
        Done := False;
    End;
    If Not Done Then
    Begin
        Try
            R.MinSolderMaskWidth := MMsToCoord(0.1);
            Done := True;
        Except
            Done := False;
        End;
    End;

    If Done Then
        Log.Add('MinimumSolderMaskSliver  0.1 mm  (BGA dam is 0.175 mm)')
    Else
        Log.Add('MinimumSolderMaskSliver  FAILED - neither property name was accepted');
    R.EndModify;
End;


Procedure ApplyPlaneClearance(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Begin
    Touched.Add('PlaneClearance');
    R.BeginModify;
    Try
        { The anti-pad: how far L2-GND and L5-GND pull back from a hole that
          does NOT belong to their net.  0.25 mm is slThermalIsolate in the
          .dru and is a comfortable multiple of JLC's 0.09 mm minimum, which
          matters here because the plane is a drill-hit edge, not an etched
          feature.  Note this rule is a scalar Clearance, not a Gap - it is
          not the same property as the Clearance rule above.                }
        R.Clearance := MMsToCoord(0.25);
        Log.Add('PlaneClearance           0.25 mm anti-pad');
    Except
        Log.Add('PlaneClearance           FAILED - Clearance was rejected');
    End;
    R.EndModify;
End;


Procedure ApplyPlaneConnect(R : IPCB_Rule; Log : TStringList; Touched : TStringList);
Var
    Done : Boolean;
Begin
    Touched.Add('PlaneConnect');
    R.BeginModify;

    { Relief is kept rather than Direct so hand-soldering and rework on the
      GND pins stays possible - a direct connection into a 25 mm-wide copper
      pour wicks heat away faster than an iron can replace it.
      Conductor width and air gap both go to 0.25 mm: the spokes then carry
      real current for the three buck rails and the LiPo return, and the gap
      matches the anti-pad above so the plane is cut back by one consistent
      number everywhere.  Four entries keeps the connection symmetrical.
      RELIEFEXPANSION is left at its 20 mil default - not in the target list
      and out of scope here, but it IS inconsistent with the 0.25 mm used
      either side of it, so ReportZuluRules prints it for a later decision. }

    Done := True;
    Try
        R.PlaneConnectStyle    := eReliefConnectToPlane;
        R.ReliefConductorWidth := MMsToCoord(0.25);
        R.ReliefAirGap         := MMsToCoord(0.25);
        R.ReliefEntries        := 4;          { a spoke count, not a coordinate }
    Except
        Done := False;
    End;

    { Newer builds drop the scalars and store one parameter set per primitive
      type.  This document has a single set of PLANECONNECT* keys, i.e. pads
      and vias share parameters, so ePlanePadAndVia is the right index -
      writing ePlanePad and ePlaneVia separately would split the rule.      }
    If Not Done Then
    Begin
        Try
            R.SetPlaneConnectStyle   (ePlanePadAndVia, eReliefConnectToPlane);
            R.SetReliefConductorWidth(ePlanePadAndVia, MMsToCoord(0.25));
            R.SetReliefAirGap        (ePlanePadAndVia, MMsToCoord(0.25));
            R.SetReliefEntries       (ePlanePadAndVia, 4);
            Done := True;
        Except
            Done := False;
        End;
    End;

    If Done Then
        Log.Add('PlaneConnect             relief, 0.25 mm spokes, 0.25 mm gap, 4 entries')
    Else
        Log.Add('PlaneConnect             FAILED - neither property nor setter form worked');
    R.EndModify;
End;


{ --- the nine readers ------------------------------------------------------ }

Procedure ReportOneRule(R : IPCB_Rule; Log : TStringList);
Begin
    If R.RuleKind = eRule_Clearance Then
    Begin
        Log.Add('Clearance  (' + R.Name + ')   target 0.09 mm');
        Try
            Log.Add('    Gap                      = ' + MmText(R.Gap));
        Except
            Log.Add('    Gap                      = <could not read>');
        End;
    End

    Else If R.RuleKind = eRule_MaxMinWidth Then
    Begin
        Log.Add('Width  (' + R.Name + ')   target 0.0762 / 0.1 / 0.5 mm');
        Try
            Log.Add('    Top Layer min/pref/max   = ' + MmText(R.MinWidth(eTopLayer)) +
                    ' / ' + MmText(R.FavoredWidth(eTopLayer)) +
                    ' / ' + MmText(R.MaxWidth(eTopLayer)));
        Except
            Log.Add('    per-layer values         = <not exposed on this build>');
        End;
        Try
            Log.Add('    MinLimit/Prefered/MaxLimit = ' + MmText(R.MinLimit) +
                    ' / ' + MmText(R.PreferedWidth) + ' / ' + MmText(R.MaxLimit));
        Except
            Log.Add('    scalar limits            = <not exposed on this build>');
        End;
    End

    Else If R.RuleKind = eRule_RoutingViaStyle Then
    Begin
        Log.Add('RoutingVias  (' + R.Name + ')   target hole 0.2 mm, pad 0.35 mm');
        Try
            Log.Add('    hole min/pref/max        = ' + MmText(R.MinHoleWidth) +
                    ' / ' + MmText(R.PreferedHoleWidth) + ' / ' + MmText(R.MaxHoleWidth));
            Log.Add('    pad  min/pref/max        = ' + MmText(R.MinWidth) +
                    ' / ' + MmText(R.PreferedWidth) + ' / ' + MmText(R.MaxWidth));
        Except
            Log.Add('    via sizes                = <could not read>');
        End;
    End

    Else If R.RuleKind = eRule_MaxMinHoleSize Then
    Begin
        Log.Add('HoleSize  (' + R.Name + ')   target 0.2 mm to 1.02 mm');
        Try
            Log.Add('    MinLimit / MaxLimit      = ' + MmText(R.MinLimit) +
                    ' / ' + MmText(R.MaxLimit));
        Except
            Log.Add('    limits                   = <could not read>');
        End;
    End

    Else If R.RuleKind = eRule_HoleToHoleClearance Then
    Begin
        Log.Add('HoleToHoleClearance  (' + R.Name + ')   target 0.2 mm');
        Try
            Log.Add('    Gap                      = ' + MmText(R.Gap));
        Except
            Log.Add('    Gap                      = <could not read>');
        End;
    End

    Else If R.RuleKind = eRule_SolderMaskExpansion Then
    Begin
        Log.Add('SolderMaskExpansion  (' + R.Name + ')   target 0.05 mm per side');
        Try
            Log.Add('    Expansion                = ' + MmText(R.Expansion));
        Except
            Log.Add('    Expansion                = <could not read>');
        End;
    End

    Else If R.RuleKind = eRule_MinimumSolderMaskSliver Then
    Begin
        Log.Add('MinimumSolderMaskSliver  (' + R.Name + ')   target 0.1 mm');
        Try
            Log.Add('    MinSolderMaskSliver      = ' + MmText(R.MinSolderMaskSliver));
        Except
            Try
                Log.Add('    MinSolderMaskWidth       = ' + MmText(R.MinSolderMaskWidth));
            Except
                Log.Add('    sliver value             = <could not read>');
            End;
        End;
    End

    Else If R.RuleKind = eRule_PowerPlaneClearance Then
    Begin
        Log.Add('PlaneClearance  (' + R.Name + ')   target 0.25 mm');
        Try
            Log.Add('    Clearance                = ' + MmText(R.Clearance));
        Except
            Log.Add('    Clearance                = <could not read>');
        End;
    End

    Else If R.RuleKind = eRule_PowerPlaneConnectStyle Then
    Begin
        Log.Add('PlaneConnect  (' + R.Name + ')   target relief, 0.25 / 0.25 mm, 4');
        Try
            Log.Add('    ReliefConductorWidth     = ' + MmText(R.ReliefConductorWidth));
            Log.Add('    ReliefAirGap             = ' + MmText(R.ReliefAirGap));
            Log.Add('    ReliefEntries            = ' + IntToStr(R.ReliefEntries));
            Log.Add('    ReliefExpansion          = ' + MmText(R.ReliefExpansion) +
                    '   (left as found, out of scope)');
        Except
            Log.Add('    relief values            = <not readable as scalars on this build;');
            Log.Add('                                check Design > Rules by eye>');
        End;
    End;
End;


{ --- entry point 1: apply -------------------------------------------------- }

Procedure SetZuluRules;
Var
    Board    : IPCB_Board;
    Iterator : IPCB_BoardIterator;
    Rule     : IPCB_Rule;
    Log      : TStringList;
    Touched  : TStringList;
    Missing  : String;
    Msg      : String;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.' + #13#10 +
                    'Open zulu_a7.PcbDoc, click in the board window, and run again.');
        Exit;
    End;

    Log     := TStringList.Create;
    Touched := TStringList.Create;

    { Rules are ordinary board objects, so the normal board iterator reaches
      them - there is no separate rule iterator.  AllLayers is mandatory:
      rules sit on no layer, and any narrower layer set returns nothing at
      all, which would make the script report success having done nothing.  }
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eRuleObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);

    { PreProcess opens the undo transaction and quiets the robots; each rule's
      BeginModify/EndModify pair inside it is what registers the change and
      marks the document dirty.  Without them a value can sit in memory with
      no undo step and be lost on the next Ctrl+Z or an unsaved close.       }
    PCBServer.PreProcess;
    Try
        Rule := Iterator.FirstPCBObject;
        While Rule <> Nil Do
        Begin
            { Dispatch on RuleKind, never on Name: the board also carries
              fan-out rules, and a renamed rule must still be found.        }
            If      Rule.RuleKind = eRule_Clearance               Then ApplyClearance(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_MaxMinWidth             Then ApplyWidth(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_RoutingViaStyle         Then ApplyRoutingVias(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_MaxMinHoleSize          Then ApplyHoleSize(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_HoleToHoleClearance     Then ApplyHoleToHole(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_SolderMaskExpansion     Then ApplySolderMaskExpansion(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_MinimumSolderMaskSliver Then ApplySliver(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_PowerPlaneClearance     Then ApplyPlaneClearance(Rule, Log, Touched)
            Else If Rule.RuleKind = eRule_PowerPlaneConnectStyle  Then ApplyPlaneConnect(Rule, Log, Touched);
            { PasteMaskExpansion is deliberately absent from this chain.    }

            Rule := Iterator.NextPCBObject;
        End;
    Finally
        { Both of these must run even if a write raised, or the iterator and
          the robot suspension are left dangling for the rest of the session }
        Board.BoardIterator_Destroy(Iterator);
        PCBServer.PostProcess;
    End;

    { Any rule kind the iterator never saw has been deleted from the document.
      Nothing was created in its place - say so instead of failing silently. }
    Missing := '';
    If Touched.IndexOf('Clearance')               < 0 Then Missing := Missing + '    Clearance' + #13#10;
    If Touched.IndexOf('Width')                   < 0 Then Missing := Missing + '    Width' + #13#10;
    If Touched.IndexOf('RoutingVias')             < 0 Then Missing := Missing + '    RoutingVias' + #13#10;
    If Touched.IndexOf('HoleSize')                < 0 Then Missing := Missing + '    HoleSize' + #13#10;
    If Touched.IndexOf('HoleToHoleClearance')     < 0 Then Missing := Missing + '    HoleToHoleClearance' + #13#10;
    If Touched.IndexOf('SolderMaskExpansion')     < 0 Then Missing := Missing + '    SolderMaskExpansion' + #13#10;
    If Touched.IndexOf('MinimumSolderMaskSliver') < 0 Then Missing := Missing + '    MinimumSolderMaskSliver' + #13#10;
    If Touched.IndexOf('PlaneClearance')          < 0 Then Missing := Missing + '    PlaneClearance' + #13#10;
    If Touched.IndexOf('PlaneConnect')            < 0 Then Missing := Missing + '    PlaneConnect' + #13#10;

    Board.ViewManager_FullUpdate;

    Msg := 'Zulu A7 - JLCPCB 6-layer rules' + #13#10 +
           '(board/zulu_a7-6layer-jlcpcb.dru, JLC confirmed 2026-08-27)' + #13#10 + #13#10 +
           Log.Text + #13#10 +
           'Rules edited: ' + IntToStr(Touched.Count) + ' (nine expected)' + #13#10;

    If Touched.Count > 9 Then
        Msg := Msg + 'More than nine: a kind exists twice, e.g. a scoped variant.' + #13#10 +
                     'Check Design > Rules before saving.' + #13#10;

    If Missing <> '' Then
        Msg := Msg + #13#10 + 'NOT FOUND - no rule of this kind exists, nothing was created:' +
               #13#10 + Missing +
               'Add it in Design > Rules (right-click the category > New Rule) and re-run.' + #13#10;

    Msg := Msg + #13#10 +
           'Nothing is saved yet.  Ctrl+S, then re-run Tools > Design Rule Check' + #13#10 +
           '(old violation markers stay on screen until DRC runs again).' + #13#10 +
           'Reminder: L2-GND and L5-GND still need GND in the Layer Stack' + #13#10 +
           'Manager, or the two plane rules have nothing to act on.';

    ShowMessage(Msg);

    Log.Free;
    Touched.Free;
End;


{ --- entry point 2: read back ---------------------------------------------- }

Procedure ReportZuluRules;
Var
    Board    : IPCB_Board;
    Iterator : IPCB_BoardIterator;
    Rule     : IPCB_Rule;
    Log      : TStringList;
    Count    : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    Log   := TStringList.Create;
    Count := 0;

    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eRuleObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Try
        Rule := Iterator.FirstPCBObject;
        While Rule <> Nil Do
        Begin
            If (Rule.RuleKind = eRule_Clearance) Or
               (Rule.RuleKind = eRule_MaxMinWidth) Or
               (Rule.RuleKind = eRule_RoutingViaStyle) Or
               (Rule.RuleKind = eRule_MaxMinHoleSize) Or
               (Rule.RuleKind = eRule_HoleToHoleClearance) Or
               (Rule.RuleKind = eRule_SolderMaskExpansion) Or
               (Rule.RuleKind = eRule_MinimumSolderMaskSliver) Or
               (Rule.RuleKind = eRule_PowerPlaneClearance) Or
               (Rule.RuleKind = eRule_PowerPlaneConnectStyle) Then
            Begin
                ReportOneRule(Rule, Log);
                Count := Count + 1;
            End;
            Rule := Iterator.NextPCBObject;
        End;
    Finally
        Board.BoardIterator_Destroy(Iterator);
    End;

    ShowMessage('Zulu A7 rules as they stand now' + #13#10 + #13#10 +
                Log.Text + #13#10 +
                'Rules listed: ' + IntToStr(Count) + ' (nine expected).' + #13#10 +
                'These are the in-memory values; they reach the PcbDoc on save.');
    Log.Free;
End;


End.

{ End of ZuluRules.pas }
