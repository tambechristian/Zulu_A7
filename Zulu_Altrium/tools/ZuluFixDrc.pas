{..............................................................................}
{  ZuluFixDrc.pas                 DelphiScript for Altium Designer             }
{                                                                              }
{  The two DRC classes that can actually be fixed right now, before routing.   }
{                                                                              }
{  1. SILKSCREEN -- 1098 of the board's 1991 violations                        }
{     724 Silk To Solder Mask and 374 Silk to Silk, and every single one is    }
{     designator text: there are no tracks and no arcs on either overlay, so   }
{     the only objects there are the 350 designator and comment strings. All   }
{     175 components carry NAMEON=TRUE at Altium's stock 60 mil height, and a  }
{     two-character designator is 110 mil wide against a 47 mil shelf pitch    }
{     between 0201s. Shrinking the text to JLCPCB's 31.5 mil floor was         }
{     measured against the real pad geometry and clears only about half; 298   }
{     of the survivors still overlap a pad in x, which no legal font size      }
{     fixes. Hiding is the step that works.                                    }
{                                                                              }
{     HideChipDesignators hides the designator on the 145 chip passives --     }
{     every C0201/C0402/C0603/C0805, R0201/R0402, IND0603 and LED0603. The 30  }
{     parts that keep theirs are every IC, connector, inductor, the RGB LED,   }
{     the transistor, the oscillator and the three resistor arrays, which is   }
{     the silkscreen a person actually reads. This is normal practice at this  }
{     density: assembly places from the pick-and-place file and the assembly   }
{     drawing, not from the silkscreen.                                        }
{                                                                              }
{     It is also position-independent -- a per-component boolean that survives  }
{     any later move -- so doing it now costs nothing if parts move again.      }
{     ShowAllDesignators puts every one of them back.                          }
{                                                                              }
{  2. THE SOLDER-MASK SLIVER -- 1 violation                                    }
{     3.933 mil against a 3.937 mil minimum, between X3-8 and X3-G1. That is   }
{     a shortfall of 102 NANOMETRES on a fab whose mask registration tolerance }
{     is around 50 micrometres, i.e. some 500 times larger. Hirose's own       }
{     recommended pattern puts that copper gap at exactly 0.200 mm, and the    }
{     global 0.05 mm mask expansion per side makes the dam exactly 0.100 mm --  }
{     the design TIES the rule and the EAGLE import's coordinate rounding      }
{     pushed it 102 nm under.                                                  }
{                                                                              }
{     AddX3MaskRule adds a SolderMaskExpansion rule scoped to InComponent('X3')}
{     at 0.04 mm instead of the global 0.05, which opens the dam from 0.0999   }
{     to 0.1199 mm -- a real 20% margin rather than a tie. Both pads belong to }
{     the same footprint, so no amount of placement could have fixed this.     }
{                                                                              }
{  NOT touched here, deliberately:                                             }
{     607 Un-Routed Net      nothing is routed yet; the count is correct       }
{     283 Component Clearance  measures Altium's INFLATED bounding rectangle,  }
{                             not copper; unsatisfiable at this density        }
{       2 Power Plane Connect  starved thermals on X2-20; one spoke survives   }
{                                                                              }
{  Run:  File > Run Script... > HideChipDesignators                            }
{        File > Run Script... > AddX3MaskRule                                  }
{        File > Run Script... > ShowAllDesignators   to undo the first          }
{  Then Ctrl+S and re-run the DRC.                                             }
{..............................................................................}

Var
    Brd : IPCB_Board;


{ helper - the chip passives, by footprint name }
Function IsChipPassive(P : String) : Boolean;
Begin
    Result := (P = 'C0201') Or (P = 'C0402') Or (P = 'C0603') Or (P = 'C0805') Or
              (P = 'R0201') Or (P = 'R0402') Or (P = 'IND0603') Or (P = 'LED0603');
End;


{ helper - walks every component and sets NameOn, returning how many changed }
Function SetDesignators(OnlyChips : Boolean; Show : Boolean) : Integer;
Var
    Iter : IPCB_BoardIterator;
    C    : IPCB_Component;
Begin
    Result := 0;
    Iter := Brd.BoardIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iter.AddFilter_LayerSet(AllLayers);
    Iter.AddFilter_Method(eProcessAll);
    C := Iter.FirstPCBObject;
    While C <> Nil Do
    Begin
        If (Not OnlyChips) Or IsChipPassive(C.Pattern) Then
        Begin
            If C.NameOn <> Show Then
            Begin
                C.BeginModify;
                C.NameOn := Show;
                C.EndModify;
                Result := Result + 1;
            End;
        End;
        C := Iter.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(Iter);
End;


Procedure HideChipDesignators;
Var
    N : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        N := SetDesignators(True, False);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - chip designators hidden' + #13#10 + #13#10 +
                '   components changed: ' + IntToStr(N) + #13#10 +
                '   (145 chip passives expected; 30 parts keep their name)' + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S, then re-run the DRC.');
End;


Procedure ShowAllDesignators;
Var
    N : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        N := SetDesignators(False, True);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - every designator shown again' + #13#10 + #13#10 +
                '   components changed: ' + IntToStr(N));
End;



{ RECOVERY -- closes an undo transaction that was left open.

  The first run of AddX3MaskRule raised inside its Try block, on the read-only
  IPCB_Rule.Priority. DelphiScript halted the script on that line rather than
  unwinding, so the matching PCBServer.PostProcess in the Finally NEVER RAN and
  PreProcess was left open. From then on Altium answered every Ctrl+S with
  "A command is currently active and save cannot be completed at this time",
  and would not switch documents either. Nothing on the board was wrong; the
  editor was simply still inside a transaction that no longer had an owner.

  Calling PostProcess once closes it. It is wrapped because calling it when no
  transaction is open is itself an error. }

{ The 30 designators that stay visible are still Altium's stock 60 mil high with
  a 10 mil stroke, which is enormous next to a 0402. Hiding the chip passives took
  the silkscreen classes from 1098 violations to 85, and every one of those 85 is
  one of these 30 -- mostly the power block, where L1-L3, Q2 and U5-U8 sit within
  a couple of millimetres of each other.

  This drops them to 31.5 mil high with a 6 mil stroke, which is JLCPCB's stated
  floor for legible silkscreen, and hides the four Creative Commons marks' own
  designators: U$2-U$5 are off-board licence art, so "U$3" printed beside them
  means nothing to anybody and two of them collide with each other. }
Procedure ShrinkVisibleDesignators;
Var
    Iter : IPCB_BoardIterator;
    C    : IPCB_Component;
    NShrunk, NHidden : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    NShrunk := 0;
    NHidden := 0;

    PCBServer.PreProcess;
    Try
        Iter := Brd.BoardIterator_Create;
        Iter.AddFilter_ObjectSet(MkSet(eComponentObject));
        Iter.AddFilter_LayerSet(AllLayers);
        Iter.AddFilter_Method(eProcessAll);
        C := Iter.FirstPCBObject;
        While C <> Nil Do
        Begin
            If C.NameOn Then
            Begin
                If Copy(C.Name.Text, 1, 2) = 'U$' Then
                Begin
                    C.BeginModify;
                    C.NameOn := False;
                    C.EndModify;
                    NHidden := NHidden + 1;
                End
                Else
                Begin
                    C.Name.BeginModify;
                    C.Name.Size  := MilsToCoord(31.5);
                    C.Name.Width := MilsToCoord(6);
                    C.Name.EndModify;
                    NShrunk := NShrunk + 1;
                End;
            End;
            C := Iter.NextPCBObject;
        End;
        Brd.BoardIterator_Destroy(Iter);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - visible designators' + #13#10 + #13#10 +
                '   shrunk to 31.5 mil / 6 mil stroke: ' + IntToStr(NShrunk) + #13#10 +
                '   licence marks hidden: ' + IntToStr(NHidden) + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S, then re-run the DRC.');
End;



{ Turns OFF the Component Clearance rule, and the reason is worth stating because
  switching a design rule off is not normally the answer.

  The rule is Horizontal Gap = 10 mil, COLLISIONCHECKMODE=3, which reduces each
  component to ONE axis-aligned rectangle -- the union of the bounding rectangle
  of every child primitive on every layer, courtyards on the mechanical layers
  included -- and measures rectangle to rectangle. It does not measure copper.

  Checked against the verified placement, all 255 reported pairs have a real
  land-to-land gap between 0.300 mm and 10.10 mm. NOT ONE is closer than the
  0.09 mm electrical Clearance rule, and not one is closer than the 0.300 mm
  minimum place_board.py enforces and verify_copper.py re-checks on the copper
  Altium actually reports. The rule calls U1 and X2 a COLLISION while their
  nearest copper is 5.26 mm apart, and BTN and X2 at 7.85 mm, because X2's
  rectangle is the whole 60.96 x 25.40 mm header footprint and the FPGA sits
  inside it -- which is exactly where the FPGA belongs.

  Left on, it puts 255 lines of noise into every DRC run, which is how a real
  violation gets missed. The assembly criterion this rule is meant to protect is
  already enforced, at 0.300 mm land to land: that is above IPC-7351 Least
  density, which asks 0.10 mm of courtyard excess per side, i.e. 0.20 mm between
  parts.

  What is NOT being claimed: that the courtyards themselves are right. They came
  from the EAGLE import and are generous -- a C0402's ran 0.473 mm past its pad.
  If a true IPC courtyard check is wanted later, re-cut the courtyards in the
  PcbLib and turn this rule back on, rather than trusting it as it stands.

  EnableComponentClearance puts it back.

  WHAT ACTUALLY WORKED, AND WHAT DID NOT. Setting IPCB_Rule.Enabled := False from
  a script reports success and DOES NOT PERSIST: after running it and saving, the
  ComponentClearance record in Rules6 still read ENABLED=TRUE and the next batch
  DRC still produced all 255. The setting that governs the batch run is the BATCH
  checkbox in Tools > Design Rule Check > Rules To Check, which is where the rule
  was found switched OFF in the first place. Unticking it there took the report
  from 905 violations to 650. These procedures are kept because they document the
  finding, but use the dialog. }
Procedure SetComponentClearance(Want : Boolean);
Var
    Iter : IPCB_BoardIterator;
    R    : IPCB_Rule;
    N    : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;
    N := 0;
    PCBServer.PreProcess;
    Try
        Iter := Brd.BoardIterator_Create;
        Iter.AddFilter_ObjectSet(MkSet(eRuleObject));
        Iter.AddFilter_LayerSet(AllLayers);
        Iter.AddFilter_Method(eProcessAll);
        R := Iter.FirstPCBObject;
        While R <> Nil Do
        Begin
            If R.RuleKind = eRule_ComponentClearance Then
            Begin
                R.BeginModify;
                R.Enabled := Want;
                R.EndModify;
                N := N + 1;
            End;
            R := Iter.NextPCBObject;
        End;
        Brd.BoardIterator_Destroy(Iter);
    Finally
        PCBServer.PostProcess;
    End;
    ShowMessage('Zulu A7 - Component Clearance' + #13#10 + #13#10 +
                '   rules set to Enabled = ' + BoolToStr(Want, True) + ': ' + IntToStr(N) +
                #13#10 + #13#10 + 'Nothing is saved yet - press Ctrl+S.');
End;


Procedure DisableComponentClearance;
Begin
    SetComponentClearance(False);
End;


Procedure EnableComponentClearance;
Begin
    SetComponentClearance(True);
End;



{ Takes Q2 and R77 off the BOARD, and their two dead nets with them.

  WHY NOT THE NORMAL ECO. The schematic is already correct: FixPgood in
  ZuluPgood.pas removed Q2, R77 and the PGOOD label from zulu_a7_1.SchDoc and
  renamed LD5_TO_Q2 to GND, and all seven .SchDoc files on disk were then checked
  -- Q2 and R77 appear in NONE of them. But Altium will not propagate it:
  Project > Validate runs, Design > Import Changes and Project > Show Differences
  both answer "No Differences Detected", and a freshly generated Protel netlist
  written at 12:43 STILL lists Q2, R77, PGOOD and LD5_TO_Q2. The compile is
  serving cached data that does not match the files it is compiled from.

  So the board is corrected directly here, to match the verified schematic. The
  stale compile is a separate problem and is worth re-testing after Altium is
  restarted, BEFORE the next schematic change is made -- if the ECO is still
  blind then, no schematic edit can reach the board by the normal route.

  Collect first, remove after -- destroying an object the iterator handed out is
  what broke the first keep-out strip. }
Procedure RemoveQ2R77FromPcb;
Var
    Iter : IPCB_BoardIterator;
    C    : IPCB_Component;
    N    : IPCB_Net;
    Kill : TInterfaceList;
    i, NC, NN : Integer;
    S    : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    Kill := TInterfaceList.Create;
    NC := 0; NN := 0; S := '';

    Iter := Brd.BoardIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eComponentObject));
    Iter.AddFilter_LayerSet(AllLayers);
    Iter.AddFilter_Method(eProcessAll);
    C := Iter.FirstPCBObject;
    While C <> Nil Do
    Begin
        If (C.Name.Text = 'Q2') Or (C.Name.Text = 'R77') Then
        Begin
            Kill.Add(C);
            S := S + '    component ' + C.Name.Text + #13#10;
            NC := NC + 1;
        End;
        C := Iter.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(Iter);

    Iter := Brd.BoardIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eNetObject));
    Iter.AddFilter_LayerSet(AllLayers);
    Iter.AddFilter_Method(eProcessAll);
    N := Iter.FirstPCBObject;
    While N <> Nil Do
    Begin
        If (N.Name = 'PGOOD') Or (N.Name = 'LD5_TO_Q2') Then
        Begin
            Kill.Add(N);
            S := S + '    net ' + N.Name + #13#10;
            NN := NN + 1;
        End;
        N := Iter.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(Iter);

    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do
        Brd.RemovePCBObject(Kill.Items[i]);
    PCBServer.PostProcess;

    Brd.ViewManager_FullUpdate;
    Kill.Free;

    ShowMessage('Zulu A7 - Q2 and R77 off the board' + #13#10 + #13#10 + S +
                #13#10 + 'components removed: ' + IntToStr(NC) + ' (2 expected)' + #13#10 +
                'nets removed: ' + IntToStr(NN) + ' (2 expected)' + #13#10 + #13#10 +
                'Board should now hold 173 components and 177 nets.' + #13#10 +
                'Nothing is saved yet - press Ctrl+S.');
End;



{ Puts R78 pad 1 on GND.

  Removing the LD5_TO_Q2 net took R78-1's net with it, so on the board that pad
  is left connected to nothing while the schematic says GND. The normal ECO would
  have done this; it cannot, because the compile is stale (see
  RemoveQ2R77FromPcb). This closes the gap so the board matches the schematic:
  VCC3V3 - LD5 - R78 - GND. }
Procedure TieR78ToGnd;
Var
    C    : IPCB_Component;
    It   : IPCB_GroupIterator;
    P    : IPCB_Pad;
    NIt  : IPCB_BoardIterator;
    N, G : IPCB_Net;
    Was  : String;
    Done : Boolean;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    G := Nil;
    NIt := Brd.BoardIterator_Create;
    NIt.AddFilter_ObjectSet(MkSet(eNetObject));
    NIt.AddFilter_LayerSet(AllLayers);
    NIt.AddFilter_Method(eProcessAll);
    N := NIt.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = 'GND' Then G := N;
        N := NIt.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(NIt);

    If G = Nil Then
    Begin
        ShowMessage('There is no GND net on this board.');
        Exit;
    End;

    Done := False;
    Was  := '(none)';
    C := Brd.GetPcbComponentByRefDes('R78');
    If C = Nil Then
    Begin
        ShowMessage('R78 is not on the board.');
        Exit;
    End;

    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While (P <> Nil) And (Not Done) Do
    Begin
        If P.Name = '1' Then
        Begin
            If P.Net <> Nil Then Was := P.Net.Name;
            PCBServer.PreProcess;
            P.BeginModify;
            P.Net := G;
            P.EndModify;
            PCBServer.PostProcess;
            Done := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);

    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - R78 pad 1' + #13#10 + #13#10 +
                '   was on net: ' + Was + #13#10 +
                '   now on net: GND' + #13#10 +
                '   changed: ' + BoolToStr(Done, True) + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S.');
End;


Procedure ClosePendingTransaction;
Var
    N : Integer;
Begin
    N := 0;
    Try
        PCBServer.PostProcess;
        N := 1;
    Except
        N := 0;
    End;
    ShowMessage('Zulu A7 - pending transaction' + #13#10 + #13#10 +
                'PostProcess calls that succeeded: ' + IntToStr(N) + #13#10 + #13#10 +
                'Now try Ctrl+S. If it still refuses, run this once more:' + #13#10 +
                'PreProcess/PostProcess can nest, so more than one may be open.');
End;


Procedure AddX3MaskRule;
Var
    Iter    : IPCB_BoardIterator;
    R, Mine : IPCB_Rule;
    Existing, Total : Integer;
    S       : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    { do not add it twice }
    Existing := 0;
    Total    := 0;
    Iter := Brd.BoardIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eRuleObject));
    Iter.AddFilter_LayerSet(AllLayers);
    Iter.AddFilter_Method(eProcessAll);
    R := Iter.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.RuleKind = eRule_SolderMaskExpansion Then
        Begin
            Total := Total + 1;
            If R.Name = 'SolderMaskExpansion_X3' Then Existing := Existing + 1;
        End;
        R := Iter.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(Iter);

    If Existing > 0 Then
    Begin
        ShowMessage('SolderMaskExpansion_X3 already exists - nothing added.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        Mine := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);
        Mine.Name             := 'SolderMaskExpansion_X3';
        Mine.Scope1Expression := 'InComponent(''X3'')';
        Mine.Scope2Expression := 'All';
        Mine.Expansion        := MMsToCoord(0.04);
        Mine.NetScope         := eNetScope_AnyNet;
        Mine.LayerKind        := eRuleLayerKind_SameLayer;
        { IPCB_Rule.Priority is READ-ONLY -- assigning it raises at run time and
          the rule never gets added. Altium owns the ordering; where the new rule
          lands has to be read back out of Rules6 and, if it is outranked by the
          global 0.05 mm rule, moved up in Design > Rules > Priorities. }
        Brd.AddPCBObject(Mine);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    S := 'Zulu A7 - X3 solder-mask expansion' + #13#10 + #13#10 +
         '   SolderMaskExpansion rules before: ' + IntToStr(Total) + #13#10 +
         '   added SolderMaskExpansion_X3, InComponent(''X3''), 0.04 mm' + #13#10 +
         '   priority: whatever Altium assigned - CHECK IT' + #13#10 + #13#10 +
         'It must OUTRANK the global 0.05 mm rule or it will not apply.' + #13#10 +
         'Check Design > Rules > Mask, and read Rules6 back before trusting it.' + #13#10 + #13#10 +
         'Nothing is saved yet - press Ctrl+S, then re-run the DRC.';
    ShowMessage(S);
End;

{ ============================================================================
  THE SIXTEEN ORPHANED DESIGNATORS                              added 2026-09-11

  The DRC leaves 37 Silk To Solder Mask violations. They are not 37 objects --
  they are SIXTEEN designators, each landing on two to five pads that belong to
  a DIFFERENT component. And the reason is not that the board is tight:

      designator   sits at            its own part is at    distance
      U3           (19.218, 19.308)   (28.350, 11.850)      11.791 mm
      J1           (64.508, 21.558)   (66.400, 12.700)       9.058 mm
      U1           (41.582, 18.578)   (46.400, 11.900)       8.234 mm
      X4           (29.003,  8.977)   (32.400,  3.550)       6.402 mm
      U4           (43.900, 23.267)   (47.500, 19.400)       5.284 mm
      ... every one of the sixteen is between 2.1 and 11.8 mm away.

  So the silkscreen currently MISLABELS THE BOARD. The string "U3" is printed
  over R97 and R98, eleven millimetres from the SDRAM it names. Fixing the DRC
  is the smaller half of this; the board is wrong to read.

  These are all parts a human needs labelled -- U1, U3, U4, U6, U7, U8, U10,
  L1, L2, L3, Q1, J1, R4, X4, BTN, LD0 -- so HideChipDesignators, which already
  took the 145 chip passives, is the wrong tool. They go back onto their parts.

  WHY AUTOPOSITION AND NOT COMPUTED COORDINATES. Working out a clear spot
  offline needs the text's true bounding box, and that turned out to be a trap:
  Texts6 says these are ARIAL, not Altium's stroke font, so glyph widths differ
  per character ("L1" is narrow, "BTN" wide); and byte 35 is a MIRROR flag, set
  on every Bottom Overlay string, so a bottom-side designator draws LEFTWARD
  from its anchor. A left-to-right stroke-font model reproduces neither. Altium
  knows its own font metrics; let it place the text.

  CANARY FIRST. ChangeNameAutoposition and the eAutoPos_ enum are new names in
  this project, and an undeclared identifier is fatal here -- Try/Except does
  not catch it. AutoPositionOne touches exactly one component.

  Run:  ReportOrphanDesignators   how far each of the sixteen has strayed
        AutoPositionOne           canary -- L1 only
        AutoPositionOrphans       all sixteen
  Then Ctrl+S and re-run the DRC.
  ============================================================================ }

Const
    ORPHANS = 'U1 U3 U4 U6 U7 U8 U10 L1 L2 L3 Q1 J1 R4 X4 BTN LD0';


Function IsOrphan(Const D : String) : Boolean;
Begin
    Result := Pos(' ' + D + ' ', ' ' + ORPHANS + ' ') > 0;
End;


Procedure ReportOrphanDesignators;
Var
    It  : IPCB_BoardIterator;
    C   : IPCB_Component;
    Log : TStringList;
    DX, DY : Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;
    Log := TStringList.Create;

    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        If IsOrphan(C.Name.Text) Then
        Begin
            DX := CoordToMMs(C.Name.XLocation) - CoordToMMs(C.X);
            DY := CoordToMMs(C.Name.YLocation) - CoordToMMs(C.Y);
            Log.Add('   ' + C.Name.Text + '   designator offset ' +
                    FloatToStr(DX) + ' , ' + FloatToStr(DY) + ' mm');
        End;
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    ShowMessage('Zulu A7 - designator offset from its own component' + #13#10 + #13#10 +
                Log.Text + #13#10 + 'Nothing was changed.');
    Log.Free;
End;


Procedure AutoPositionOne;
Var
    C : IPCB_Component;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    C := Brd.GetPcbComponentByRefDes('L1');
    If C = Nil Then
    Begin
        ShowMessage('L1 not found.');
        Exit;
    End;

    C.BeginModify;
    C.ChangeNameAutoposition(eAutoPos_TopCenter);
    C.EndModify;

    Brd.ViewManager_FullUpdate;
    ShowMessage('Canary flew.' + #13#10 + #13#10 +
                'L1 designator moved to (' +
                FloatToStr(CoordToMMs(C.Name.XLocation)) + ' , ' +
                FloatToStr(CoordToMMs(C.Name.YLocation)) + ') mm,' + #13#10 +
                'against the component at (' +
                FloatToStr(CoordToMMs(C.X)) + ' , ' + FloatToStr(CoordToMMs(C.Y)) + ').' + #13#10 + #13#10 +
                'ChangeNameAutoposition and eAutoPos_TopCenter are real in this build,' + #13#10 +
                'so AutoPositionOrphans is safe to run. Nothing is saved yet.');
End;


Procedure AutoPositionOrphans;
Var
    It  : IPCB_BoardIterator;
    C   : IPCB_Component;
    Log : TStringList;
    N   : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;
    Log := TStringList.Create;
    N := 0;

    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        If IsOrphan(C.Name.Text) Then
        Begin
            C.BeginModify;
            C.ChangeNameAutoposition(eAutoPos_TopCenter);
            C.EndModify;
            Log.Add('   ' + C.Name.Text + '  -> (' +
                    FloatToStr(CoordToMMs(C.Name.XLocation)) + ' , ' +
                    FloatToStr(CoordToMMs(C.Name.YLocation)) + ')');
            N := N + 1;
        End;
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - ' + IntToStr(N) + ' designators put back on their parts' +
                #13#10 + #13#10 + Log.Text + #13#10 +
                'Sixteen expected. Ctrl+S, then re-run the DRC: the 37 Silk To' + #13#10 +
                'Solder Mask violations should fall, and whatever is left is a' + #13#10 +
                'genuinely tight spot rather than an orphan.');
    Log.Free;
End;


End.

{ End of ZuluFixDrc.pas }
