{..............................................................................}
{  ZuluSetup.pas                   DelphiScript for Altium Designer            }
{                                                                              }
{  THE PRE-ROUTING SETUP PASS.  Read this before adding anything to it.        }
{                                                                              }
{  WHY THE RULE-WRITING CODE THAT USED TO LIVE HERE IS GONE                    }
{  The first version set the four rules through IPCB_Rule properties. It died  }
{  on "Undeclared identifier: PreferedLimit", and the follow-up probe died the }
{  same way on FavoredLimit. Two things were learned and both matter:          }
{                                                                              }
{    1. The IPCB_Rule property names in this build are NOT the Rules6 stream   }
{       keys (PREFEREDWIDTH, AIRGAPWIDTH, MINSETBACK, MAXUNCOUPLEDLENGTH) and  }
{       not the names in the commonly-circulated scripts either.               }
{    2. Try/Except does NOT catch an undeclared identifier. It is raised by    }
{       the interpreter as a modal Error dialog and the script HALTS -- the    }
{       handler never runs. So a name cannot be probed by trying it, and one   }
{       wrong name takes the whole script down. Worse, if it halts after       }
{       PCBServer.PreProcess the transaction is left open and Altium refuses   }
{       every save until a bare PostProcess closes it.                         }
{                                                                              }
{  A halted script also stays "executing" as far as the scripting system is    }
{  concerned -- the next run fails with "Another script executing now". Clear  }
{  it with Run > Stop (Ctrl+F3) before running anything else.                  }
{                                                                              }
{  So the four rules and the grids were set in the GUI instead, and verified   }
{  by re-reading the saved file rather than by trusting the dialog:            }
{                                                                              }
{    Design > Rules > Routing > Width                                          }
{        PREFEREDWIDTH  3.937mil -> 3mil      MINLIMIT 3mil, MAXLIMIT 19.685   }
{        The blocker. 3.937mil is 0.1 mm; the gap between two CPG236 lands is  }
{        0.4999 pitch - 0.225044 land = 0.274856 mm, and at the 0.09 mm        }
{        Clearance rule that admits 0.094856 mm. Every escape trace inside the }
{        ball field was 0.005144 mm too wide. MAX stays 19.685mil -- never     }
{        narrow it globally, VCC1V0 carries 367 mA.                            }
{                                                                              }
{    Design > Rules > Plane > Polygon Connect Style                            }
{        RELIEFCONDUCTORWIDTH 10mil -> 5.9055mil (0.15 mm)                     }
{        AIRGAPWIDTH          10mil -> 7.874mil  (0.20 mm)                     }
{        10 mil is 0.254 mm, wider than the 0.225 mm BGA land and close to the   }
{        0.300 mm 0201 lands it connects: a starved thermal by construction.   }
{                                                                              }
{    Design > Rules > Routing > Routing Corners                                }
{        MINSETBACK 100mil -> 3.937mil (0.10 mm).  MAXSETBACK left at 100mil.  }
{        2.54 mm of setback on a board whose tightest channel is 0.22 mm.      }
{                                                                              }
{    Design > Rules > Routing > Differential Pairs Routing                     }
{        all six of min/preferred/max width and gap -> 5.9055mil (0.15 mm)     }
{        MAXUNCOUPLEDLENGTH 500mil -> 118.1102mil (3 mm)                       }
{        0.15/0.15 is not a guess. The stack in Board6 puts Top Layer          }
{        3.9134 mil (0.0994 mm) over the L2 GND plane on PP-006, er 4.100.     }
{        50 ohm single-ended there is w = 0.148 mm, and an edge-coupled pair   }
{        at w = s = 0.15 mm gives Zdiff = 2*50*(1 - 0.48*exp(-0.96*s/h))       }
{        = 88.7 ohm, against USB 90. The 3 mm uncoupled budget covers TWO      }
{        breakouts, not one: U2 0.5 mm LQFP pitch at one end and X1 0.65 mm    }
{        connector pitch at the other, ~1.5 mm each.                           }
{                                                                              }
{    View > Grids > Set Global Snap Grid (Shift+Ctrl+G)                        }
{        0.127 mm (5 mil) -> 0.025 mm.  COMPONENTGRIDSIZE followed it.         }
{        The hazard was imperial-against-metric, not coarse-against-fine: the  }
{        worst centreline error across the 36 real ball gaps is 0.06195 mm on  }
{        a 5 mil grid (violates) against 0.00007 mm on 0.025 mm (legal).       }
{        TRACKGRIDSIZE and VIAGRIDSIZE are still 0.508 mm in the file. They    }
{        are AD6-era fields with no control in this build and the interactive  }
{        router uses the snap grid; they are left alone deliberately.          }
{                                                                              }
{  WHAT IS LEFT, AND HOW TO ADD IT SAFELY                                      }
{  Net classes are still worth scripting -- ten classes by hand is a lot of    }
{  clicking. But given (2) above, NEVER add a new API name straight into a     }
{  long procedure. Run MakeOneTestClass first: it touches exactly one name set }
{  and creates one throwaway class. If it reports success the names are real   }
{  and MakeNetClasses can run; if it dies, only a canary was lost.             }
{                                                                              }
{  Note the deliberate absence of PCBServer.PreProcess/PostProcess around the  }
{  class creation. That costs a single undo step and buys immunity from the    }
{  stranded-transaction failure described above.                               }
{                                                                              }
{  Run:  MakeOneTestClass    canary -- one class named ZULU_CANARY             }
{        MakeNetClasses      the real ten                                      }
{        ReportNetClasses    lists what is on the board, changes nothing       }
{        ReportShift         where the seven movable parts are now             }
{        ShiftWest           U2 1.475 mm west, LD0-LD5 1.250 mm west           }
{  Then Ctrl+S.                                                                }
{..............................................................................}

Var
    Brd     : IPCB_Board;
    Log     : TStringList;
    Missing : String;


Function BoardOrNil : IPCB_Board;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If Result = Nil Then
        ShowMessage('No PCB document is focused.' + #13#10 +
                    'Open zulu_a7.PcbDoc, click in the board window, and run again.');
End;


{ One class, one member, no transaction. If this survives, every name it uses
  is real: PCBClassFactoryByClassMember, eClassMemberKind_Net, SuperClass,
  Name, AddMemberByName, AddPCBObject. }
Procedure MakeOneTestClass;
Var
    Cls : IPCB_ObjectClass;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    Cls := PCBServer.PCBClassFactoryByClassMember(eClassMemberKind_Net);
    Cls.SuperClass := False;
    Cls.Name       := 'ZULU_CANARY';
    Cls.AddMemberByName('GND');
    Brd.AddPCBObject(Cls);

    Brd.ViewManager_FullUpdate;
    ShowMessage('Canary flew.' + #13#10 + #13#10 +
                'A net class ZULU_CANARY now exists with GND in it, so every' + #13#10 +
                'API name MakeNetClasses needs is real in this build.' + #13#10 + #13#10 +
                'Delete it in Design > Classes, then run MakeNetClasses.' + #13#10 +
                'Nothing is saved yet.');
End;


Procedure AddClass(Const AName : String; Const Members : String);
Var
    Cls  : IPCB_ObjectClass;
    List : TStringList;
    i    : Integer;
Begin
    List := TStringList.Create;
    Try
        List.Delimiter     := ' ';
        List.DelimitedText := Members;

        Cls := PCBServer.PCBClassFactoryByClassMember(eClassMemberKind_Net);
        Cls.SuperClass := False;
        Cls.Name       := AName;
        For i := 0 To List.Count - 1 Do
            If List[i] <> '' Then Cls.AddMemberByName(List[i]);
        Brd.AddPCBObject(Cls);
    Finally
        List.Free;
    End;
End;


{ The ten classes. Every member name was read out of Nets6 -- none of them is
  typed from memory or from a schematic drawing. }
Procedure MakeNetClasses;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    { carries real current: VCC1V0 alone is 367 mA, and 3 mil of 1 oz copper
      is good for only ~379 mA at a 10 C rise. These must not route at the
      3 mil preferred width. }
    AddClass('PWR_RAILS',
             'VCC1V0 VCC1V8 VCC3V3 VCCADC VU VBATT USB5V0 FT-VCORE FT-VPHY FT-VPLL');

    { buck switching nodes -- small loops, wide copper, keep them off the
      analog and off the SDRAM }
    AddClass('PWR_SWITCH', 'NODE_P0 NODE_P1 NetL1_1 NetL2_1 NetL3_1');

    AddClass('SDRAM_ADDR',
             'A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 BS0 BS1');
    AddClass('SDRAM_DATA',
             'D0 D1 D2 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D13 D14 D15');
    AddClass('SDRAM_CTRL',
             'CAS# RAS# WE# CKE LDQM UDQM SDRAM-CS# SDRAM-CLK');

    AddClass('USB_DATA', 'USB_D_P USB_D_N');

    AddClass('CLOCKS', 'CLK-12M-FPGA CLK-12M-FT CLK-12M-SHARED SDRAM-CLK CHAN-CLK');

    AddClass('CFG_FLASH',
             'FLASH-CS# FLASH-D00 FLASH-D01 FLASH-D02 FLASH-D03 ' +
             'FPGA-CCLK FPGA-INIT# FPGA-DONE DONE DONE-PU PROG# ' +
             'CFG-M0 CFG-M1 CFG-M2 PUDC_B');

    AddClass('JTAG', 'TCK TDI TDO TMS FPGA-TCK FPGA-TDI FPGA-TDO FPGA-TMS');

    AddClass('SDCARD', 'SD-CLK SD-CMD SD-DAT0 SD-DAT1 SD-DAT2 SD-DAT3');

    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - ten net classes added.' + #13#10 + #13#10 +
                'Check them in Design > Classes, then Ctrl+S.' + #13#10 +
                'Run ReportNetClasses to see the members the board actually kept.');
End;


Procedure ReportNetClasses;
Var
    It  : IPCB_BoardIterator;
    Cls : IPCB_ObjectClass;
    Log : TStringList;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    Log := TStringList.Create;
    It  := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eClassObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Cls := It.FirstPCBObject;
    While Cls <> Nil Do
    Begin
        If Not Cls.SuperClass Then Log.Add(Cls.Name);
        Cls := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    ShowMessage('Zulu A7 - user classes on the board' + #13#10 + #13#10 +
                Log.Text + #13#10 + 'Nothing was changed.');
    Log.Free;
End;

{..............................................................................}
{  U2 AND THE LED ROW GO WEST.                                                 }
{                                                                              }
{  WHY                                                                          }
{  This is the one measured regression against the six-layer board that died   }
{  at 26 airwires. The FT2232 went from a QFN64 to an LQFP64, so the north-     }
{  south corridor between U2's east face and U1's west lands fell from 3.680 mm }
{  to 2.2625 mm, while routing layers fell from six to four. North-south        }
{  capacity at the exact x where the old router built its via wall went from    }
{  21 lanes x 6 to 13 lanes x 4 -- a 59 per cent cut, and the only budget       }
{  number on this board that got worse. See docs/routing_readiness.md item 5.   }
{                                                                              }
{  THE DISTANCES ARE NOT THE ONES THE REVIEW ASKED FOR, AND THAT IS DELIBERATE. }
{  It asked for U2 1.600 and the LEDs 1.300. Re-measured from the board as it   }
{  stands -- after Q2 and R77 were deleted and the packer re-flowed that corner }
{  -- BTN's east edge is 21.750 and the LED row's west edge is 23.300, so the   }
{  slack is 1.550 mm, not the 1.650 the review had. At a 1.300 shift the LEDs   }
{  would sit 0.250 mm from BTN, and Altium's own ComponentClearance rule is     }
{  GAP = 10mil = 0.254 mm, scope All/All. It would fail DRC by four microns.    }
{                                                                              }
{  So the pair is scaled back to the largest shift that holds every neighbour   }
{  at 0.300 mm or better:                                                       }
{                                                                              }
{      U2    1.475 mm west     LED row -> U2 becomes exactly 0.300             }
{      LEDs  1.250 mm west     BTN -> LED row becomes exactly 0.300            }
{                                                                              }
{  and the corridor goes 2.2625 -> 3.7375 mm. That is 92 per cent of the gain   }
{  the review wanted, for none of the DRC risk. Both distances are exact        }
{  multiples of the new 0.025 mm snap grid.                                     }
{                                                                              }
{  NOTHING ELSE MOVES, AND THAT IS A FINDING, NOT AN OMISSION. The review       }
{  priced this at "eight parts plus U2, plus U2's bottom-side decoupling        }
{  following it". There is no bottom-side decoupling under U2: the only         }
{  bottom parts wholly inside U2's outline are R80-R83, and the area beneath    }
{  it belongs to U3, which must not move. Checked with tools/shift_u2_leds.py   }
{  against tools/placement_report.txt regenerated from the live board.          }
{                                                                              }
{  Land-to-land clearance was re-checked on every pad pair at these distances   }
{  (place_board.check, 0.30 mm): 0 off-board, 0 pairs under the rule.           }
{                                                                              }
{  Run:  ReportShift    prints where the seven parts are, changes nothing      }
{        ShiftWest      moves them                                              }
{  Then Ctrl+S, re-run ReportPlacement, and re-run tools/verify_copper.py.     }
{..............................................................................}

Procedure MoveWest(D : String; DX : Double);
Var
    C : IPCB_Component;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then
    Begin
        Missing := Missing + D + ' ';
        Exit;
    End;
    C.BeginModify;
    C.X := C.X - MMsToCoord(DX);
    C.EndModify;
    Log.Add('   ' + D + '  -> ' + FloatToStr(CoordToMMs(C.X)) + ' mm');
End;


Procedure ReportShift;
Var
    It : IPCB_BoardIterator;
    C  : IPCB_Component;
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
        If (C.Name.Text = 'U2') Or (C.Name.Text = 'LD0') Or (C.Name.Text = 'LD1') Or
           (C.Name.Text = 'LD2') Or (C.Name.Text = 'LD3') Or (C.Name.Text = 'LD4') Or
           (C.Name.Text = 'LD5') Or (C.Name.Text = 'BTN') Then
            Log.Add('   ' + C.Name.Text + '  x ' + FloatToStr(CoordToMMs(C.X)) +
                    '   y ' + FloatToStr(CoordToMMs(C.Y)));
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    ShowMessage('Zulu A7 - component origins now' + #13#10 + #13#10 + Log.Text + #13#10 +
                'BTN does not move. Nothing was changed.');
    Log.Free;
End;


Procedure ShiftWest;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.' + #13#10 +
                    'Open zulu_a7.PcbDoc, click in the board window, and run again.');
        Exit;
    End;
    Log := TStringList.Create;
    Missing := '';

    MoveWest('U2',  1.475);
    MoveWest('LD0', 1.250);
    MoveWest('LD1', 1.250);
    MoveWest('LD2', 1.250);
    MoveWest('LD3', 1.250);
    MoveWest('LD4', 1.250);
    MoveWest('LD5', 1.250);

    Brd.ViewManager_FullUpdate;
    If Missing <> '' Then Log.Add('   NOT FOUND: ' + Missing);
    ShowMessage('Zulu A7 - U2 1.475 mm west, LD0-LD5 1.250 mm west' + #13#10 + #13#10 +
                Log.Text + #13#10 +
                'Corridor U2 east -> U1 west lands: 2.2625 -> 3.7375 mm.' + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S, then re-run ReportPlacement.');
    Log.Free;
End;



{ ============================================================================
  POWER-RAIL WIDTH RULES -- 2026-09-14

  WHAT.  The single Width_PWR_RAILS rule (3 mil / 0.4 / 1.0 mm, uniform on
  every layer) becomes four rules with PER-LAYER tables. Altium's Width rule
  DRC-checks only min and max -- the preferred width is router guidance -- so
  the thermal floor a rail needs on L3/L4 has to be a per-layer MIN, and it
  cannot be the same min on Top, where VCC3V3 must neck to 3 mil between BGA
  balls. Every number below traces to the files:

      inner copper 0.0152 mm, outer 0.035 mm      tools/verify_stack.py
      rail currents (MAX column)                  tools/power_budget.py
      which balls are boxed by foreign nets       Pads6, U1's 238 lands
      IPC-2221  I = k * dT^0.44 * A^0.725         k 0.024 inner / 0.048 outer

  Only VCC3V3 keeps the 3 mil Top neck: its balls C18, V6, V9 and V11 are the
  ONLY rail balls with a foreign net on all four sides. VCC1V0's eight balls
  each touch a same-net or empty position (K10 is unpopulated), VCC1V8's C9,
  H13, J13 and VCCADC's C13 all face an empty position, so none of them needs
  a neck and none gets the 3 mil hole in DRC.

      rule                 nets                       Top            L3/L4          Bottom
      Width_PWR_VCC3V3     VCC3V3           662 mA    0.0762/0.2/1.5 1.05/1.05/1.5  0.2/0.3/1.5
      Width_PWR_U8         VU USB5V0 VBATT  697 mA    0.2/0.3/1.5    1.10/1.10/1.5  0.2/0.2/1.5
      Width_PWR_VCC1V0     VCC1V0           367 mA    0.15/0.2/1.5   0.50/0.50/1.5  0.15/0.3/1.5
      Width_PWR_RAILS      the five light rails       0.15/0.2/1.0   0.15/0.2/1.0   0.15/0.3/1.0
                                                      (min / preferred / max, mm)

  Inner mins are the 10 C widths rounded UP to 0.05: VCC3V3 1.0187 -> 1.05
  (1.00 would be 10.3 C), VU 1.0937 -> 1.10, VCC1V0 0.4515 -> 0.50. Outer mins
  are the 10 C outer widths (0.170, 0.183 -> 0.20) or the 0.15 etch floor.
  Preferred is pad entry: 0.20 under the 0.225 U1 land and the 0.28 LQFP pad
  (0.50 into a 0.28 pad on 0.5 mm pitch fails JLC's 0.09 mask-to-trace), 0.30
  at the 0.300 mm 0201 pads, 0.20 at U8's 0.24 mm VQFN pads. Inner preferred
  equals inner min so the router never lays 1.5 mm on a signal layer by
  accident. Max 1.5 lets 1.05 and 1.10 exist; 1.0 on the light rails flags a
  mistyped width.

  PRIORITY.  IPCB_Rule.Priority is READ-ONLY (assigning it raises and the
  rule is never added). A new rule lands at priority 1 and pushes the rest
  down, so the three are created in the order VCC1V0, U8, VCC3V3 to end at
  VCC3V3 1, U8 2, VCC1V0 3, Width_PWR_SWITCH 4, Width_PWR_RAILS 5, Width 6.
  Their scopes are disjoint so their mutual order is cosmetic; all three must
  outrank Width_PWR_RAILS, and that is read back from Rules6 afterwards.

  WRITE ORDER, both matter:
    - MaxWidth(L) before MinWidth(L) before FavoredWidth(L): a new rule starts
      at 10/10/10 mil and a 1.05 mm min written before the max is 1.5 mm gets
      clamped (tools/ZuluRules.pas, ApplyWidthOnLayer).
    - The scalar MaxLimit / MinLimit / PreferedWidth are the UNIFORM
      write-through: written AFTER the layer values they erase the table.
      ZuluRules.pas does exactly that and is now guarded to touch only the
      global rule named 'Width'. Here the scalars go first, as the base.

  Every value is read back through the same property right after the write
  and the run FAILS on any mismatch; the file is then checked independently
  by tools/verify_widths.py, which also discovers the per-layer keys -- no
  Width rule on this board had ever carried a non-uniform table before, so
  persistence is proven by that dump, not assumed.

  DRC PROOF.  PlaceWidthProbes puts thirteen short tracks in a spare corner,
  each on a rail at a width chosen to sit just inside or just outside its
  layer's min; run the DRC and exactly the seven marked VIOL must appear as
  Width Constraint violations. RemoveWidthProbes deletes them again.

  Run:  SetPwrRailWidths          then Ctrl+S, python tools/verify_widths.py
        PlaceWidthProbes          then Tools > Design Rule Check > Run
        RemoveWidthProbes         then Ctrl+S and run the DRC once more
        ReportWidthRules          any time, read-only
  ============================================================================ }

Function WMm(C : TCoord) : String;
Begin
    Result := FloatToStr(Round(CoordToMMs(C) * 10000) / 10000);
End;


{ one layer of one rule: max first, then min, then preferred; read back all three }
Procedure SetLayerWidths(R : IPCB_Rule; L : TLayer; LName : String;
                         AMin, APref, AMax : Double; Log : TStringList; Var Bad : Integer);
Var
    GMin, GPref, GMax : Double;
    Ok : Boolean;
Begin
    R.MaxWidth(L)     := MMsToCoord(AMax);
    R.MinWidth(L)     := MMsToCoord(AMin);
    R.FavoredWidth(L) := MMsToCoord(APref);

    GMin  := CoordToMMs(R.MinWidth(L));
    GPref := CoordToMMs(R.FavoredWidth(L));
    GMax  := CoordToMMs(R.MaxWidth(L));
    Ok := (Abs(GMin - AMin) < 0.0005) And (Abs(GPref - APref) < 0.0005) And (Abs(GMax - AMax) < 0.0005);
    If Not Ok Then Bad := Bad + 1;
    If Ok Then
        Log.Add('      ' + LName + '  ' + WMm(R.MinWidth(L)) + ' / ' + WMm(R.FavoredWidth(L)) +
                ' / ' + WMm(R.MaxWidth(L)) + '  ok')
    Else
        Log.Add('      ' + LName + '  ' + WMm(R.MinWidth(L)) + ' / ' + WMm(R.FavoredWidth(L)) +
                ' / ' + WMm(R.MaxWidth(L)) + '  MISMATCH wanted ' + FloatToStr(AMin) + ' / ' +
                FloatToStr(APref) + ' / ' + FloatToStr(AMax));
End;


{ the whole table of one rule; scalars first as the uniform base }
Procedure SetRuleTable(R : IPCB_Rule; RName : String;
                       TMin, TPref, TMax, MMin, MPref, MMax, BMin, BPref, BMax : Double;
                       Log : TStringList; Var Bad : Integer);
Var
    Lo, Hi : Double;
Begin
    Lo := TMin;
    If MMin < Lo Then Lo := MMin;
    If BMin < Lo Then Lo := BMin;
    Hi := TMax;
    If MMax > Hi Then Hi := MMax;
    If BMax > Hi Then Hi := BMax;

    R.MaxLimit      := MMsToCoord(Hi);
    R.MinLimit      := MMsToCoord(Lo);
    R.PreferedWidth := MMsToCoord(TPref);

    Log.Add('   ' + RName + '   scalar base ' + WMm(R.MinLimit) + ' / ' +
            WMm(R.PreferedWidth) + ' / ' + WMm(R.MaxLimit));
    SetLayerWidths(R, eTopLayer,    'Top   ', TMin, TPref, TMax, Log, Bad);
    SetLayerWidths(R, eMidLayer1,   'L3-SIG', MMin, MPref, MMax, Log, Bad);
    SetLayerWidths(R, eMidLayer2,   'L4-SIG', MMin, MPref, MMax, Log, Bad);
    SetLayerWidths(R, eBottomLayer, 'Bottom', BMin, BPref, BMax, Log, Bad);
End;


Function FindRuleByName(AName : String) : IPCB_Rule;
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


{ a new Width rule, not yet added; the caller sets its table then adds it }
Function NewWidthRule(AName, AScope : String) : IPCB_Rule;
Begin
    Result := PCBServer.PCBRuleFactory(eRule_MaxMinWidth);
    Result.Name             := AName;
    Result.Scope1Expression := AScope;
    Result.Scope2Expression := 'All';
    Result.NetScope         := eNetScope_AnyNet;
    Result.LayerKind        := eRuleLayerKind_SameLayer;
End;


Procedure SetPwrRailWidths;
Var
    R   : IPCB_Rule;
    Bad : Integer;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    If (FindRuleByName('Width_PWR_VCC3V3') <> Nil) Or
       (FindRuleByName('Width_PWR_U8')     <> Nil) Or
       (FindRuleByName('Width_PWR_VCC1V0') <> Nil) Then
    Begin
        ShowMessage('The power-rail width rules already exist - nothing changed.' + #13#10 +
                    'Run ReportWidthRules to see them.');
        Exit;
    End;
    If FindRuleByName('Width_PWR_RAILS') = Nil Then
    Begin
        ShowMessage('Width_PWR_RAILS is missing - nothing changed.');
        Exit;
    End;

    Log := TStringList.Create;
    Bad := 0;

    PCBServer.PreProcess;
    Try
        { the existing class rule, edited in place: the five light rails }
        R := FindRuleByName('Width_PWR_RAILS');
        R.BeginModify;
        SetRuleTable(R, 'Width_PWR_RAILS ',
                     0.15, 0.20, 1.00,   0.15, 0.20, 1.00,   0.15, 0.30, 1.00, Log, Bad);
        R.EndModify;

        { created in this order so that they land VCC3V3 1, U8 2, VCC1V0 3 }
        R := NewWidthRule('Width_PWR_VCC1V0', 'InNet(''VCC1V0'')');
        SetRuleTable(R, 'Width_PWR_VCC1V0',
                     0.15, 0.20, 1.50,   0.50, 0.50, 1.50,   0.15, 0.30, 1.50, Log, Bad);
        Brd.AddPCBObject(R);

        R := NewWidthRule('Width_PWR_U8', 'InNet(''VU'') Or InNet(''USB5V0'') Or InNet(''VBATT'')');
        SetRuleTable(R, 'Width_PWR_U8    ',
                     0.20, 0.30, 1.50,   1.10, 1.10, 1.50,   0.20, 0.20, 1.50, Log, Bad);
        Brd.AddPCBObject(R);

        R := NewWidthRule('Width_PWR_VCC3V3', 'InNet(''VCC3V3'')');
        SetRuleTable(R, 'Width_PWR_VCC3V3',
                     0.0762, 0.20, 1.50,  1.05, 1.05, 1.50,   0.20, 0.30, 1.50, Log, Bad);
        Brd.AddPCBObject(R);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    Log.SaveToFile('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/widths_report.txt');
    If Bad = 0 Then
        ShowMessage('Zulu A7 - power-rail width rules written, every value read back OK' + #13#10 + #13#10 +
                    Log.Text + #13#10 +
                    'Nothing is saved yet - press Ctrl+S, then' + #13#10 +
                    'python tools/verify_widths.py --dump   to learn the per-layer keys,' + #13#10 +
                    'python tools/verify_widths.py          to check the saved file.')
    Else
        ShowMessage('Zulu A7 - power-rail width rules: ' + IntToStr(Bad) + ' LAYER(S) READ BACK WRONG' + #13#10 + #13#10 +
                    Log.Text + #13#10 +
                    'Do NOT save. Close the document discarding changes and read the log.');
    Log.Free;
End;


Procedure ReportWidthRules;
Var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Log := TStringList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.RuleKind = eRule_MaxMinWidth Then
        Begin
            Log.Add(R.Name + '   priority ' + IntToStr(R.Priority) + '   ' + R.Scope1Expression);
            Log.Add('      scalar ' + WMm(R.MinLimit) + ' / ' + WMm(R.PreferedWidth) + ' / ' + WMm(R.MaxLimit));
            Log.Add('      Top    ' + WMm(R.MinWidth(eTopLayer))    + ' / ' + WMm(R.FavoredWidth(eTopLayer))    + ' / ' + WMm(R.MaxWidth(eTopLayer)));
            Log.Add('      L3-SIG ' + WMm(R.MinWidth(eMidLayer1))   + ' / ' + WMm(R.FavoredWidth(eMidLayer1))   + ' / ' + WMm(R.MaxWidth(eMidLayer1)));
            Log.Add('      L4-SIG ' + WMm(R.MinWidth(eMidLayer2))   + ' / ' + WMm(R.FavoredWidth(eMidLayer2))   + ' / ' + WMm(R.MaxWidth(eMidLayer2)));
            Log.Add('      Bottom ' + WMm(R.MinWidth(eBottomLayer)) + ' / ' + WMm(R.FavoredWidth(eBottomLayer)) + ' / ' + WMm(R.MaxWidth(eBottomLayer)));
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Log.SaveToFile('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/widths_report.txt');
    ShowMessage('Zulu A7 - Width rules as Altium holds them (min / preferred / max, mm)' + #13#10 + #13#10 + Log.Text);
    Log.Free;
End;


{ ---- the DRC proof --------------------------------------------------------- }

Const
    { 2026-09-15: moved under U1 (x 41.79..51.01, y 7.29..16.51). L3/L4 carry no
      copper there, so the inner-layer rules see only the probe pairs; the old
      corner at x 60..62 had JP4-1's through-hole pad in it and every probe run
      picked up clearance noise against it. Probe() adds PROBE_Y0 - 1 to y.   }
    PROBE_X0 = 43.0;      { the probes live in this rectangle, mm }
    PROBE_X1 = 45.0;
    PROBE_Y0 = 9.0;
    PROBE_Y1 = 16.0;


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


Procedure Probe(NetName : String; L : TLayer; LName : String; W : Double; Y : Double;
                Expect : String; Log : TStringList; Var Missing : String);
Var
    T : IPCB_Track;
    N : IPCB_Net;
Begin
    N := NetByName(NetName);
    If N = Nil Then
    Begin
        Missing := Missing + ' ' + NetName;
        Exit;
    End;
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1    := MMsToCoord(PROBE_X0 + 0.25);
    T.Y1    := MMsToCoord(Y + PROBE_Y0 - 1.0);
    T.X2    := MMsToCoord(PROBE_X1 - 0.25);
    T.Y2    := MMsToCoord(Y + PROBE_Y0 - 1.0);
    T.Layer := L;
    T.Width := MMsToCoord(W);
    T.Net   := N;
    Brd.AddPCBObject(T);
    Log.Add('   y=' + FloatToStr(Y) + '  ' + NetName + '  ' + LName + '  ' + FloatToStr(W) + ' mm   expect ' + Expect);
End;


Procedure PlaceWidthProbes;
Var
    Missing : String;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Log := TStringList.Create;
    Missing := '';

    PCBServer.PreProcess;
    Try
        Probe('VCC3V3',   eMidLayer1,   'L3-SIG', 0.30,   1.5, 'VIOL  (min 1.05)',            Log, Missing);
        Probe('VCC3V3',   eTopLayer,    'Top   ', 0.0762, 2.0, 'pass  (min 0.0762)',          Log, Missing);
        Probe('VCC3V3',   eMidLayer2,   'L4-SIG', 1.00,   2.5, 'VIOL  (min 1.05)',            Log, Missing);
        Probe('VCC1V0',   eTopLayer,    'Top   ', 0.0762, 3.0, 'VIOL  (min 0.15)',            Log, Missing);
        Probe('VCC1V0',   eMidLayer1,   'L3-SIG', 0.45,   3.5, 'VIOL  (min 0.50)',            Log, Missing);
        Probe('VCC1V0',   eMidLayer1,   'L3-SIG', 0.50,   4.0, 'pass  (min 0.50)',            Log, Missing);
        Probe('VU',       eBottomLayer, 'Bottom', 0.15,   4.5, 'VIOL  (min 0.20)',            Log, Missing);
        Probe('VU',       eBottomLayer, 'Bottom', 0.20,   5.0, 'pass  (min 0.20)',            Log, Missing);
        Probe('VU',       eMidLayer2,   'L4-SIG', 1.10,   5.5, 'pass  (min 1.10)',            Log, Missing);
        Probe('FT-VCORE', eMidLayer1,   'L3-SIG', 0.10,   6.0, 'VIOL  (min 0.15)',            Log, Missing);
        Probe('FT-VCORE', eMidLayer1,   'L3-SIG', 0.15,   6.5, 'pass  (min 0.15)',            Log, Missing);
        Probe('VCC1V8',   eTopLayer,    'Top   ', 0.15,   7.0, 'pass  (min 0.15)',            Log, Missing);
        Probe('NODE_P0',  eTopLayer,    'Top   ', 0.15,   7.5, 'VIOL  (PWR_SWITCH min 0.20)', Log, Missing);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    Log.SaveToFile('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/widths_report.txt');
    If Missing <> '' Then Log.Add('   NET NOT FOUND:' + Missing);
    ShowMessage('Zulu A7 - 13 width probes placed at x ' + FloatToStr(PROBE_X0) + '..' + FloatToStr(PROBE_X1) + ' mm' + #13#10 + #13#10 +
                Log.Text + #13#10 +
                'Now Tools > Design Rule Check > Run. Exactly the seven VIOL lines must' + #13#10 +
                'appear as Width Constraint violations; then run RemoveWidthProbes.');
    Log.Free;
End;


Procedure RemoveWidthProbes;
Var
    It   : IPCB_BoardIterator;
    T    : IPCB_Track;
    Kill : TInterfaceList;
    i    : Integer;
    x1, y1, x2, y2 : Double;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Kill := TInterfaceList.Create;

    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        x1 := CoordToMMs(T.X1);
        y1 := CoordToMMs(T.Y1);
        x2 := CoordToMMs(T.X2);
        y2 := CoordToMMs(T.Y2);
        If (x1 >= PROBE_X0) And (x1 <= PROBE_X1) And (x2 >= PROBE_X0) And (x2 <= PROBE_X1) And
           (y1 >= PROBE_Y0) And (y1 <= PROBE_Y1) And (y2 >= PROBE_Y0) And (y2 <= PROBE_Y1) And
           ((T.Layer = eTopLayer) Or (T.Layer = eMidLayer1) Or (T.Layer = eMidLayer2) Or (T.Layer = eBottomLayer)) Then
            Kill.Add(T);
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    PCBServer.PreProcess;
    Try
        For i := 0 To Kill.Count - 1 Do
            Brd.RemovePCBObject(Kill.Items[i]);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - removed ' + IntToStr(Kill.Count) + ' probe track(s) from the ' +
                FloatToStr(PROBE_X0) + '..' + FloatToStr(PROBE_X1) + ' x ' +
                FloatToStr(PROBE_Y0) + '..' + FloatToStr(PROBE_Y1) + ' mm rectangle.' + #13#10 +
                'Expected 13. Press Ctrl+S and re-run the DRC.');
    Kill.Free;
End;




{ ============================================================================
  VIA LAND 0.30 -> 0.35 mm, 2026-09-14 (user decision, docs/via_land_decision.md)

  JLCPCB's engineering reply recommended a 0.075 mm annular ring -- a 0.20 mm
  drill on a 0.35 mm land -- and teardrops on every via. Pads6 shows the
  CPG236 never needs an interstitial via (rings 0-2 full, rings 3-5 a vacant
  moat, the 7x7 core all GND/power), so nothing forces the 0.30 land anywhere:
  0.35 fits every moat cell with +0.122 mm to the 0.09 rule. Cost: the binding
  via pitch goes 0.40 -> 0.44 mm; plane anti-pads (hole-referenced) and the
  JLC price tier do not move. Hole stays 0.20. Min = max = preferred, as
  before, so the routers cannot invent a second via size.

  Write order: MaxWidth first (the rule holds 0.30/0.30/0.30, so raising the
  min before the max would be clamped), then MinWidth, then PreferedWidth;
  read all six back. ZuluRules.pas ApplyRoutingVias now writes 0.35 too.

  Teardrops are NOT a rule: Tools > Teardrops after routing, before Gerbers.

  Run:  SetViaLand035    then Ctrl+S and read Rules6 back (RoutingVias
                         WIDTH / MINWIDTH / MAXWIDTH = 13.7795mil)
  ============================================================================ }

Procedure SetViaLand035;
Var
    R   : IPCB_Rule;
    Bad : Integer;
    GMin, GPref, GMax, HMin, HPref, HMax : Double;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    R := FindRuleByName('RoutingVias');
    If R = Nil Then
    Begin
        ShowMessage('No rule named RoutingVias - nothing changed.');
        Exit;
    End;
    Log := TStringList.Create;

    PCBServer.PreProcess;
    Try
        R.BeginModify;
        R.MaxWidth      := MMsToCoord(0.35);
        R.MinWidth      := MMsToCoord(0.35);
        R.PreferedWidth := MMsToCoord(0.35);
        R.EndModify;
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    GMin  := CoordToMMs(R.MinWidth);
    GPref := CoordToMMs(R.PreferedWidth);
    GMax  := CoordToMMs(R.MaxWidth);
    HMin  := CoordToMMs(R.MinHoleWidth);
    HPref := CoordToMMs(R.PreferedHoleWidth);
    HMax  := CoordToMMs(R.MaxHoleWidth);
    Bad := 0;
    If Abs(GMin - 0.35) > 0.0005 Then Bad := Bad + 1;
    If Abs(GPref - 0.35) > 0.0005 Then Bad := Bad + 1;
    If Abs(GMax - 0.35) > 0.0005 Then Bad := Bad + 1;
    If Abs(HMin - 0.20) > 0.0005 Then Bad := Bad + 1;
    If Abs(HPref - 0.20) > 0.0005 Then Bad := Bad + 1;
    If Abs(HMax - 0.20) > 0.0005 Then Bad := Bad + 1;
    Log.Add('RoutingVias  land min/pref/max = ' + WMm(R.MinWidth) + ' / ' + WMm(R.PreferedWidth) + ' / ' + WMm(R.MaxWidth) + ' mm');
    Log.Add('             hole min/pref/max = ' + WMm(R.MinHoleWidth) + ' / ' + WMm(R.PreferedHoleWidth) + ' / ' + WMm(R.MaxHoleWidth) + ' mm');
    Log.SaveToFile('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/widths_report.txt');
    If Bad = 0 Then
        ShowMessage('Zulu A7 - via land 0.30 -> 0.35 mm, read back OK' + #13#10 + #13#10 + Log.Text + #13#10 +
                    'Nothing is saved yet - press Ctrl+S.')
    Else
        ShowMessage('Zulu A7 - via land: ' + IntToStr(Bad) + ' value(s) READ BACK WRONG' + #13#10 + #13#10 + Log.Text + #13#10 +
                    'Do NOT save.');
    Log.Free;
End;




{ ============================================================================
  SDRAM BUS RULES, 2026-09-14 -- docs/sdram_bus_widths.md

  The 39 SDRAM nets need no 50 ohm: an unterminated 3.3 V LVTTL bus of
  9-33 mm with an 8 mA (~50 ohm) driver cannot tell 45 from 60 ohm, and
  overshoot is set by the FPGA DRIVE setting, not by width. So the width is
  chosen on driver match, etch tolerance and yield: 0.125 mm on L3/L4 is
  49-50 ohm (+-4.4 ohm at JLC's +-0.5 mil), 0.10 is the neck (54 ohm) and
  0.15 the cap (45 ohm). Top keeps the 3 mil escape with PREFERRED = MIN,
  because the router lays the preferred and never necks by itself.

      Width_SDRAM   Top 0.0762/0.0762/0.15   L3,L4 0.10/0.125/0.15   Bottom 0.10/0.125/0.15
      Clearance_SDRAM_INNER 0.10 mm  the three classes, L3/L4 ONLY  (yield: tooled space
                                     0.080-0.087 instead of 0.070-0.077 after etch comp.)
      Clearance_SDRAM_CLK   0.20 mm  SDRAM-CLK, L3/L4 ONLY  (halves the coupling on the
                                     one net whose edge IS the timing)

  Neither clearance touches Top or Bottom: the ring-1 escape has 0.0994 mm
  to its neighbouring lands and any bus clearance >= 0.10 there closes it.

  Clearance rules are created INNER first, CLK second, so that CLK lands at
  priority 1, INNER 2, the global 0.09 rule 3 (a CLK-to-data pair matches
  both SDRAM rules and the higher priority must be the 0.20). NetScope is
  left at the factory default and read back from Rules6 afterwards (the
  file spells it DifferentNets). Width_SDRAM lands at Width priority 1 and
  pushes the five power rules and the global Width down one -- their
  scopes are disjoint, so that is cosmetic; verify_widths.py expects it.

  Precondition outside the board: XDC DRIVE 8 (SLOW or FAST) or 12 SLOW on
  all 39 outputs; never 12/16 FAST without a series resistor.

  Run:  SetSdramRules       then Ctrl+S, python tools/verify_widths.py
        PlaceSdramProbes    then Tools > DRC > Run: exactly 5 VIOL lines
        RemoveWidthProbes   (same rectangle), Ctrl+S, DRC once more
  ============================================================================ }

Function NewClearanceRule(AName, AScope : String; AGap : Double) : IPCB_Rule;
Begin
    Result := PCBServer.PCBRuleFactory(eRule_Clearance);
    Result.Name             := AName;
    Result.Scope1Expression := AScope;
    Result.Scope2Expression := 'All';
    Result.LayerKind        := eRuleLayerKind_SameLayer;
    Result.Gap              := MMsToCoord(AGap);
End;


Procedure SetSdramRules;
Var
    R   : IPCB_Rule;
    Bad : Integer;
    G   : Double;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    If (FindRuleByName('Width_SDRAM') <> Nil) Or (FindRuleByName('Clearance_SDRAM_INNER') <> Nil) Or
       (FindRuleByName('Clearance_SDRAM_CLK') <> Nil) Then
    Begin
        ShowMessage('The SDRAM rules already exist - nothing changed.');
        Exit;
    End;
    Log := TStringList.Create;
    Bad := 0;

    PCBServer.PreProcess;
    Try
        R := NewClearanceRule('Clearance_SDRAM_INNER',
             '(InNetClass(''SDRAM_DATA'') Or InNetClass(''SDRAM_ADDR'') Or InNetClass(''SDRAM_CTRL'')) And (OnLayer(''L3-SIG'') Or OnLayer(''L4-SIG''))', 0.10);
        Brd.AddPCBObject(R);
        G := CoordToMMs(R.Gap);
        If Abs(G - 0.10) > 0.0005 Then Bad := Bad + 1;
        Log.Add('   Clearance_SDRAM_INNER  gap ' + WMm(R.Gap) + '   ' + R.Scope1Expression);

        R := NewClearanceRule('Clearance_SDRAM_CLK',
             'InNet(''SDRAM-CLK'') And (OnLayer(''L3-SIG'') Or OnLayer(''L4-SIG''))', 0.20);
        Brd.AddPCBObject(R);
        G := CoordToMMs(R.Gap);
        If Abs(G - 0.20) > 0.0005 Then Bad := Bad + 1;
        Log.Add('   Clearance_SDRAM_CLK    gap ' + WMm(R.Gap) + '   ' + R.Scope1Expression);

        R := NewWidthRule('Width_SDRAM', 'InNetClass(''SDRAM_DATA'') Or InNetClass(''SDRAM_ADDR'') Or InNetClass(''SDRAM_CTRL'')');
        SetRuleTable(R, 'Width_SDRAM     ',
                     0.0762, 0.0762, 0.15,   0.10, 0.125, 0.15,   0.10, 0.125, 0.15, Log, Bad);
        Brd.AddPCBObject(R);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;
    Log.SaveToFile('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/widths_report.txt');
    If Bad = 0 Then
        ShowMessage('Zulu A7 - SDRAM rules written, every value read back OK' + #13#10 + #13#10 + Log.Text + #13#10 +
                    'Nothing is saved yet - press Ctrl+S, then python tools/verify_widths.py')
    Else
        ShowMessage('Zulu A7 - SDRAM rules: ' + IntToStr(Bad) + ' value(s) READ BACK WRONG' + #13#10 + #13#10 + Log.Text + #13#10 +
                    'Do NOT save.');
    Log.Free;
End;


Procedure PlaceSdramProbes;
Var
    Missing : String;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Log := TStringList.Create;
    Missing := '';
    PCBServer.PreProcess;
    Try
        { pairs: second track at y + width + gap }
        Probe('D0',        eMidLayer1,   'L3-SIG', 0.125,  1.0,    'pair A (gap 0.095) -> VIOL Clearance_SDRAM_INNER', Log, Missing);
        Probe('D1',        eMidLayer1,   'L3-SIG', 0.125,  1.22,   '   ... second of pair A', Log, Missing);
        Probe('D2',        eMidLayer1,   'L3-SIG', 0.125,  1.7,    'pair B (gap 0.105) -> pass', Log, Missing);
        Probe('D3',        eMidLayer1,   'L3-SIG', 0.125,  1.93,   '   ... second of pair B', Log, Missing);
        Probe('SDRAM-CLK', eMidLayer2,   'L4-SIG', 0.125,  2.4,    'pair C (gap 0.15)  -> VIOL Clearance_SDRAM_CLK', Log, Missing);
        Probe('D4',        eMidLayer2,   'L4-SIG', 0.125,  2.675,  '   ... second of pair C', Log, Missing);
        Probe('SDRAM-CLK', eMidLayer2,   'L4-SIG', 0.125,  3.2,    'pair D (gap 0.21)  -> pass', Log, Missing);
        Probe('D5',        eMidLayer2,   'L4-SIG', 0.125,  3.535,  '   ... second of pair D', Log, Missing);
        Probe('D6',        eTopLayer,    'Top   ', 0.0762, 4.0,    'pair E Top (gap 0.09) -> pass (no SDRAM clearance on Top)', Log, Missing);
        Probe('D7',        eTopLayer,    'Top   ', 0.0762, 4.1662, '   ... second of pair E', Log, Missing);
        Probe('D8',        eMidLayer1,   'L3-SIG', 0.095,  4.6,    'VIOL Width_SDRAM (L3 min 0.10)', Log, Missing);
        Probe('D9',        eTopLayer,    'Top   ', 0.0762, 5.0,    'pass (Top min 0.0762)', Log, Missing);
        Probe('D10',       eMidLayer1,   'L3-SIG', 0.16,   5.4,    'VIOL Width_SDRAM (max 0.15)', Log, Missing);
        Probe('A0',        eBottomLayer, 'Bottom', 0.095,  5.8,    'VIOL Width_SDRAM (Bottom min 0.10)', Log, Missing);
        Probe('A1',        eMidLayer2,   'L4-SIG', 0.125,  6.2,    'pass (L4 pref 0.125)', Log, Missing);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;
    If Missing <> '' Then Log.Add('   NET NOT FOUND:' + Missing);
    ShowMessage('Zulu A7 - 15 SDRAM probe tracks placed at x 60..62 mm' + #13#10 + #13#10 + Log.Text + #13#10 +
                'Tools > Design Rule Check > Run: exactly 2 Clearance + 3 Width violations.' + #13#10 +
                'Then RemoveWidthProbes (same rectangle), Ctrl+S, DRC again.');
    Log.Free;
End;




{ ============================================================================
  VIA TENTING, 2026-09-15 -- docs/via_land_decision.md, step 3

  Every via on the board is tented, top and bottom: a SolderMaskExpansion rule
  scoped IsVia with both tenting flags set. Why a rule and not the global
  expansion: with the global 0.05 mm opening, two 0.35 mm via lands on
  adjacent 0.5 mm moat cells under U1 leave a 0.0499 mm mask web against the
  0.100 mm sliver rule, and two vias at the 0.44 mm binding pitch leave none
  at all. A 0 mm expansion would still open the land (0.09 mm web at 0.44
  pitch, still under the sliver rule); tenting removes the opening, which is
  also what keeps solder from wicking into vias beside the BGA lands and the
  0201 pads. No via on this board is a test point.

  The rule lands at priority 1 above SolderMaskExpansion_U1 (InComponent, which
  never matches a via) and the global rule, so it applies to every via. It is
  only exercised once vias exist -- the fan-out's first vias are the DRC proof.

  ProbeTenting in ZuluProbe.pas (2026-09-15) showed that IsTentingTop is NOT
  a declared property in this build, so the two Tented checkboxes are set in
  the Rules dialog after this script has made the rule with the proven names;
  verify_widths.py checks ISTENTINGTOP / ISTENTINGBOTTOM = TRUE in the file.

  Run:  SetViaTenting    then tick Tented top + bottom in Design > Rules, Ctrl+S,
                         python tools/verify_widths.py
  ============================================================================ }

Procedure SetViaTenting;
Var
    R : IPCB_Rule;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    If FindRuleByName('SolderMaskExpansion_Vias') <> Nil Then
    Begin
        ShowMessage('SolderMaskExpansion_Vias already exists - nothing changed.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        R := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);
        R.Name             := 'SolderMaskExpansion_Vias';
        R.Scope1Expression := 'IsVia';
        R.Scope2Expression := 'All';
        R.Expansion        := MMsToCoord(0);
        R.NetScope         := eNetScope_AnyNet;
        R.LayerKind        := eRuleLayerKind_SameLayer;
        Brd.AddPCBObject(R);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    If R.Scope1Expression = 'IsVia' Then
        ShowMessage('Zulu A7 - SolderMaskExpansion_Vias written: scope IsVia, expansion 0, read back OK.' + #13#10 + #13#10 +
                    'The TENTING flags cannot be set by script (IsTentingTop is not declared,' + #13#10 +
                    'ProbeTenting 2026-09-15). Now: Design > Rules > Mask > Solder Mask Expansion >' + #13#10 +
                    'SolderMaskExpansion_Vias, tick Tented for Top and Bottom, OK, then Ctrl+S and' + #13#10 +
                    'python tools/verify_widths.py')
    Else
        ShowMessage('Zulu A7 - SolderMaskExpansion_Vias READ BACK WRONG: scope ' + R.Scope1Expression + #13#10 + 'Do NOT save.');
End;



{ ==== FANOUT BLOCK, generated by tools/fanout_emit.py -- do not edit by hand ==== }

{ Generated 2026-09-15 from tools/fanout_plan.json: 107 vias, 318 tracks. }

Function FanNet(AName : String) : IPCB_Net;
Begin
    Result := NetByName(AName);
End;

Procedure FanVia(N : IPCB_Net; X, Y : Double);
Var
    V : IPCB_Via;
Begin
    V := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    V.X         := MMsToCoord(X);
    V.Y         := MMsToCoord(Y);
    V.Size      := MMsToCoord(0.35);
    V.HoleSize  := MMsToCoord(0.20);
    V.LowLayer  := eTopLayer;
    V.HighLayer := eBottomLayer;
    V.Net       := N;
    Brd.AddPCBObject(V);
End;

Procedure FanTrk(N : IPCB_Net; L : TLayer; W, X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1    := MMsToCoord(X1);
    T.Y1    := MMsToCoord(Y1);
    T.X2    := MMsToCoord(X2);
    T.Y2    := MMsToCoord(Y2);
    T.Layer := L;
    T.Width := MMsToCoord(W);
    T.Net   := N;
    Brd.AddPCBObject(T);
End;

Procedure PlaceFanout;
Var
    N : IPCB_Net;
    Missing : String;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Missing := '';
    PCBServer.PreProcess;
    Try
        N := FanNet('A0');
        If N = Nil Then Missing := Missing + ' A0' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 8.4000, 42.1501, 8.1500);
            FanTrk(N, eTopLayer, 0.0762, 42.1501, 8.1500, 41.6875, 8.1500);
        End;
        N := FanNet('A1');
        If N = Nil Then Missing := Missing + ' A1' Else
        Begin
            FanVia(N, 43.4001, 9.4000);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 8.8999, 43.4001, 9.4000);
        End;
        N := FanNet('A10');
        If N = Nil Then Missing := Missing + ' A10' Else
        Begin
            FanVia(N, 41.4000, 8.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 8.4000, 42.6501, 8.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.6501, 8.6500, 41.4000, 8.6500);
        End;
        N := FanNet('A12');
        If N = Nil Then Missing := Missing + ' A12' Else
        Begin
            FanVia(N, 43.4001, 11.4000);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 10.8999, 43.4001, 11.4000);
        End;
        N := FanNet('A2');
        If N = Nil Then Missing := Missing + ' A2' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 8.8999, 42.1501, 9.1500);
            FanTrk(N, eTopLayer, 0.0762, 42.1501, 9.1500, 41.6875, 9.1500);
        End;
        N := FanNet('A4');
        If N = Nil Then Missing := Missing + ' A4' Else
        Begin
            FanVia(N, 43.4001, 9.8999);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 9.4000, 43.4001, 9.8999);
        End;
        N := FanNet('A5');
        If N = Nil Then Missing := Missing + ' A5' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 9.4000, 42.1502, 9.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.1502, 9.6500, 41.6875, 9.6500);
        End;
        N := FanNet('A6');
        If N = Nil Then Missing := Missing + ' A6' Else
        Begin
            FanVia(N, 43.4001, 10.4000);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 9.8999, 43.4001, 10.4000);
        End;
        N := FanNet('A8');
        If N = Nil Then Missing := Missing + ' A8' Else
        Begin
            FanVia(N, 43.4001, 10.8999);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 10.4000, 43.4001, 10.8999);
        End;
        N := FanNet('A9');
        If N = Nil Then Missing := Missing + ' A9' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 10.4000, 42.1502, 10.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.1502, 10.6500, 41.6875, 10.6500);
        End;
        N := FanNet('AIN15_N');
        If N = Nil Then Missing := Missing + ' AIN15_N' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 13.4000, 42.1502, 13.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.1502, 13.6500, 41.6875, 13.6500);
        End;
        N := FanNet('AIN15_P');
        If N = Nil Then Missing := Missing + ' AIN15_P' Else
        Begin
            FanVia(N, 43.4001, 13.8999);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 13.4000, 43.4001, 13.8999);
        End;
        N := FanNet('AIN16_N');
        If N = Nil Then Missing := Missing + ' AIN16_N' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 12.4000, 42.1502, 12.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.1502, 12.6500, 41.6875, 12.6500);
        End;
        N := FanNet('AIN16_P');
        If N = Nil Then Missing := Missing + ' AIN16_P' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 12.8999, 42.1501, 13.1500);
            FanTrk(N, eTopLayer, 0.0762, 42.1501, 13.1500, 41.6875, 13.1500);
        End;
        N := FanNet('BS0');
        If N = Nil Then Missing := Missing + ' BS0' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 7.8999, 42.1502, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.1502, 7.6500, 41.6875, 7.6500);
        End;
        N := FanNet('BTN');
        If N = Nil Then Missing := Missing + ' BTN' Else
        Begin
            FanVia(N, 49.4001, 10.4000);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 10.4000, 49.4001, 10.4000);
        End;
        N := FanNet('CFG-M0');
        If N = Nil Then Missing := Missing + ' CFG-M0' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 47.4001, 7.8999, 47.1501, 7.6498);
            FanTrk(N, eTopLayer, 0.0762, 47.1501, 7.6498, 47.1501, 7.1875);
        End;
        N := FanNet('CFG-M2');
        If N = Nil Then Missing := Missing + ' CFG-M2' Else
        Begin
            FanVia(N, 46.4001, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 46.4001, 8.4000, 46.4001, 8.8999);
        End;
        N := FanNet('CHAN-CLK');
        If N = Nil Then Missing := Missing + ' CHAN-CLK' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 9.8999, 50.6502, 10.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.6502, 10.1500, 51.1125, 10.1500);
        End;
        N := FanNet('CHAN0');
        If N = Nil Then Missing := Missing + ' CHAN0' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 15.8999, 50.6501, 16.1499);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 16.1499, 50.6501, 16.6125);
        End;
        N := FanNet('CHAN11');
        If N = Nil Then Missing := Missing + ' CHAN11' Else
        Begin
            FanVia(N, 49.4001, 11.8999);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 11.8999, 49.4001, 11.8999);
        End;
        N := FanNet('CHAN15');
        If N = Nil Then Missing := Missing + ' CHAN15' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 7.8999, 50.1501, 7.6498);
            FanTrk(N, eTopLayer, 0.0762, 50.1501, 7.6498, 50.1501, 7.1875);
        End;
        N := FanNet('CHAN17');
        If N = Nil Then Missing := Missing + ' CHAN17' Else
        Begin
            FanVia(N, 49.6501, 7.0200);
            FanTrk(N, eTopLayer, 0.0762, 49.4001, 8.4000, 49.6501, 8.1501);
            FanTrk(N, eTopLayer, 0.0762, 49.6501, 8.1501, 49.6501, 7.0200);
        End;
        N := FanNet('CHAN18');
        If N = Nil Then Missing := Missing + ' CHAN18' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 49.4001, 7.8999, 49.1501, 7.6498);
            FanTrk(N, eTopLayer, 0.0762, 49.1501, 7.6498, 49.1501, 7.1875);
        End;
        N := FanNet('CHAN2');
        If N = Nil Then Missing := Missing + ' CHAN2' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 15.8999, 49.6501, 16.1499);
            FanTrk(N, eTopLayer, 0.0762, 49.6501, 16.1499, 49.6501, 16.6125);
        End;
        N := FanNet('CHAN20');
        If N = Nil Then Missing := Missing + ' CHAN20' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 48.9000, 7.8999, 48.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 48.6501, 7.6500, 48.6501, 7.1875);
        End;
        N := FanNet('CHAN21');
        If N = Nil Then Missing := Missing + ' CHAN21' Else
        Begin
            FanVia(N, 48.9000, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 48.9000, 8.4000, 48.9000, 8.8999);
        End;
        N := FanNet('CHAN23');
        If N = Nil Then Missing := Missing + ' CHAN23' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 48.4001, 7.8999, 48.1501, 7.6498);
            FanTrk(N, eTopLayer, 0.0762, 48.1501, 7.6498, 48.1501, 7.1875);
        End;
        N := FanNet('CHAN24');
        If N = Nil Then Missing := Missing + ' CHAN24' Else
        Begin
            FanVia(N, 48.4001, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 48.4001, 8.4000, 48.4001, 8.8999);
        End;
        N := FanNet('CHAN26');
        If N = Nil Then Missing := Missing + ' CHAN26' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 47.9000, 7.8999, 47.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 47.6501, 7.6500, 47.6501, 7.1875);
        End;
        N := FanNet('CHAN27');
        If N = Nil Then Missing := Missing + ' CHAN27' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 8.8999, 50.6502, 9.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.6502, 9.1500, 51.1125, 9.1500);
        End;
        N := FanNet('CHAN4');
        If N = Nil Then Missing := Missing + ' CHAN4' Else
        Begin
            FanVia(N, 48.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.0762, 49.4001, 15.4000, 48.9000, 14.8999);
        End;
        N := FanNet('CHAN5');
        If N = Nil Then Missing := Missing + ' CHAN5' Else
        Begin
            FanVia(N, 49.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 14.8999, 49.4001, 14.8999);
        End;
        N := FanNet('CHAN6');
        If N = Nil Then Missing := Missing + ' CHAN6' Else
        Begin
            FanVia(N, 49.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 12.8999, 49.4001, 12.8999);
        End;
        N := FanNet('CHAN8');
        If N = Nil Then Missing := Missing + ' CHAN8' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 12.4000, 50.6501, 12.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 12.6500, 51.1125, 12.6500);
        End;
        N := FanNet('CHAN9');
        If N = Nil Then Missing := Missing + ' CHAN9' Else
        Begin
            FanVia(N, 49.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 12.4000, 49.4001, 12.4000);
        End;
        N := FanNet('CKE');
        If N = Nil Then Missing := Missing + ' CKE' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 10.8999, 42.1501, 11.1500);
            FanTrk(N, eTopLayer, 0.0762, 42.1501, 11.1500, 41.6875, 11.1500);
        End;
        N := FanNet('CLK-12M-FPGA');
        If N = Nil Then Missing := Missing + ' CLK-12M-FPGA' Else
        Begin
            FanVia(N, 48.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 11.4000, 49.4001, 11.4000);
            FanTrk(N, eTopLayer, 0.0762, 49.4001, 11.4000, 48.9000, 11.8999);
        End;
        N := FanNet('D0');
        If N = Nil Then Missing := Missing + ' D0' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 45.4001, 7.8999, 45.1501, 7.6498);
            FanTrk(N, eTopLayer, 0.0762, 45.1501, 7.6498, 45.1501, 7.1875);
        End;
        N := FanNet('D1');
        If N = Nil Then Missing := Missing + ' D1' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 44.9000, 7.8999, 44.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 44.6501, 7.6500, 44.6501, 7.1875);
        End;
        N := FanNet('D10');
        If N = Nil Then Missing := Missing + ' D10' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 11.8999, 42.1501, 12.1500);
            FanTrk(N, eTopLayer, 0.0762, 42.1501, 12.1500, 41.6875, 12.1500);
        End;
        N := FanNet('D12');
        If N = Nil Then Missing := Missing + ' D12' Else
        Begin
            FanVia(N, 43.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 12.4000, 43.4001, 12.8999);
        End;
        N := FanNet('D4');
        If N = Nil Then Missing := Missing + ' D4' Else
        Begin
            FanVia(N, 43.9000, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 43.9000, 8.4000, 43.9000, 8.8999);
        End;
        N := FanNet('D6');
        If N = Nil Then Missing := Missing + ' D6' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 43.9000, 7.8999, 43.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 43.6501, 7.6500, 43.6501, 7.1875);
        End;
        N := FanNet('D7');
        If N = Nil Then Missing := Missing + ' D7' Else
        Begin
            FanVia(N, 43.4001, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 43.4001, 8.4000, 43.4001, 8.8999);
        End;
        N := FanNet('D9');
        If N = Nil Then Missing := Missing + ' D9' Else
        Begin
            FanVia(N, 43.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 11.8999, 43.4001, 12.4000);
        End;
        N := FanNet('FLASH-D00');
        If N = Nil Then Missing := Missing + ' FLASH-D00' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 14.8999, 50.6502, 15.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.6502, 15.1500, 51.1125, 15.1500);
        End;
        N := FanNet('FLASH-D02');
        If N = Nil Then Missing := Missing + ' FLASH-D02' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 13.4000, 50.6501, 13.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 13.6500, 51.1125, 13.6500);
        End;
        N := FanNet('FLASH-D03');
        If N = Nil Then Missing := Missing + ' FLASH-D03' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 13.8999, 50.6502, 14.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.6502, 14.1500, 51.1125, 14.1500);
        End;
        N := FanNet('FPGA-CCLK');
        If N = Nil Then Missing := Missing + ' FPGA-CCLK' Else
        Begin
            FanVia(N, 46.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.0762, 46.9000, 15.4000, 46.4001, 14.8999);
        End;
        N := FanNet('FPGA-DONE');
        If N = Nil Then Missing := Missing + ' FPGA-DONE' Else
        Begin
            FanVia(N, 47.4001, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 47.4001, 8.4000, 47.4001, 8.8999);
        End;
        N := FanNet('FPGA-INIT#');
        If N = Nil Then Missing := Missing + ' FPGA-INIT#' Else
        Begin
            FanVia(N, 46.9000, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 46.9000, 8.4000, 46.9000, 8.8999);
        End;
        N := FanNet('FPGA-TCK');
        If N = Nil Then Missing := Missing + ' FPGA-TCK' Else
        Begin
            FanVia(N, 44.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.0762, 45.4001, 15.4000, 44.9000, 14.8999);
        End;
        N := FanNet('FT-PWREN#');
        If N = Nil Then Missing := Missing + ' FT-PWREN#' Else
        Begin
            FanVia(N, 49.4001, 9.8999);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 9.8999, 49.4001, 9.8999);
        End;
        N := FanNet('GND');
        If N = Nil Then Missing := Missing + ' GND' Else
        Begin
            FanVia(N, 43.4001, 14.8999);
            FanVia(N, 43.9000, 14.8999);
            FanVia(N, 44.4001, 14.8999);
            FanVia(N, 43.4001, 14.4000);
            FanVia(N, 45.9000, 14.8999);
            FanVia(N, 44.4001, 8.8999);
            FanVia(N, 45.9000, 8.8999);
            FanVia(N, 48.9000, 13.8999);
            FanVia(N, 44.9000, 13.8999);
            FanVia(N, 45.4001, 13.8999);
            FanVia(N, 45.9000, 13.8999);
            FanVia(N, 46.9000, 13.8999);
            FanVia(N, 44.4001, 13.8999);
            FanVia(N, 44.4001, 13.4000);
            FanVia(N, 44.4001, 12.8999);
            FanVia(N, 45.9000, 9.8999);
            FanVia(N, 47.4001, 9.8999);
            FanVia(N, 47.9000, 9.8999);
            FanVia(N, 48.4001, 9.8999);
            FanVia(N, 48.4001, 10.4000);
            FanVia(N, 45.9000, 11.8999);
            FanVia(N, 46.9000, 11.8999);
            FanVia(N, 44.4001, 10.4000);
            FanVia(N, 48.4001, 11.4000);
            FanVia(N, 41.4000, 16.4000);
            FanVia(N, 41.4000, 15.8999);
            FanVia(N, 41.4000, 15.4000);
            FanVia(N, 41.4000, 14.4000);
            FanVia(N, 41.4000, 13.8999);
            FanVia(N, 40.9000, 13.4000);
            FanVia(N, 41.4000, 6.9000);
            FanVia(N, 51.4000, 16.4000);
            FanVia(N, 51.4000, 15.4000);
            FanVia(N, 51.4000, 13.8999);
            FanVia(N, 51.4000, 11.4000);
            FanVia(N, 51.9000, 8.8999);
            FanVia(N, 51.9000, 13.1500);
            FanVia(N, 47.4001, 6.2500);
            FanVia(N, 50.6501, 6.3500);
            FanVia(N, 40.9000, 10.1500);
            FanTrk(N, eTopLayer, 0.1500, 42.9000, 15.4000, 43.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 43.4001, 15.4000, 43.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 14.8999, 43.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 43.9000, 15.4000, 43.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.4001, 15.4000, 44.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 15.4000, 44.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 14.4000, 43.4001, 14.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 13.8999, 42.9000, 14.4000);
            FanTrk(N, eTopLayer, 0.1500, 46.4001, 15.4000, 45.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.4001, 8.4000, 44.4001, 8.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 8.4000, 45.9000, 8.8999);
            FanTrk(N, eTopLayer, 0.2000, 49.9000, 14.4000, 49.4001, 14.4000);
            FanTrk(N, eTopLayer, 0.1500, 49.4001, 14.4000, 48.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 13.4000, 45.4001, 13.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 13.4000, 45.9000, 13.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 13.4000, 44.9000, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 13.4000, 45.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 13.4000, 45.9000, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 12.8999, 45.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 12.8999, 45.9000, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 12.8999, 45.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 12.8999, 45.9000, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 12.4000, 45.9000, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 12.4000, 45.4001, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 11.8999, 45.4001, 11.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 11.4000, 45.9000, 11.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 11.4000, 45.9000, 10.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 10.8999, 45.9000, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 13.4000, 46.9000, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 12.8999, 46.9000, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 12.8999, 47.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 12.4000, 47.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 12.8999, 47.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 10.8999, 47.9000, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 10.4000, 47.9000, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 13.4000, 44.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 13.4000, 45.4001, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 13.4000, 45.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 13.4000, 46.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.1500, 44.9000, 13.4000, 44.4001, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 13.4000, 44.4001, 13.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 12.8999, 44.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 10.4000, 45.9000, 9.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 10.4000, 47.4001, 9.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 10.4000, 47.9000, 9.8999);
            FanTrk(N, eTopLayer, 0.1500, 47.9000, 10.4000, 48.4001, 9.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 10.4000, 48.4001, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 12.4000, 45.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 11.4000, 45.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 12.4000, 46.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 11.4000, 46.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 16.4000, 41.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 15.8999, 41.9000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 15.4000, 42.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.4001, 15.4000, 42.9000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 15.4000, 43.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 43.4001, 15.4000, 43.9000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 43.9000, 15.4000, 44.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.4001, 15.4000, 44.9000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 16.4000, 42.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 15.8999, 42.9000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 43.4001, 16.4000, 43.4001, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 43.4001, 15.8999, 43.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 43.9000, 16.4000, 43.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 43.9000, 15.8999, 43.9000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.4001, 16.4000, 44.4001, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.4001, 15.8999, 44.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 16.4000, 44.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 15.8999, 44.9000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 16.4000, 43.4001, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 43.4001, 16.4000, 43.9000, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 43.9000, 16.4000, 44.4001, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.4001, 16.4000, 44.9000, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 15.8999, 43.4001, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 43.4001, 15.8999, 43.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 43.9000, 15.8999, 44.4001, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.4001, 15.8999, 44.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 15.4000, 42.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 14.8999, 42.9000, 14.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.9000, 14.4000, 42.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 14.4000, 42.4001, 14.4000);
            FanTrk(N, eTopLayer, 0.2000, 42.4001, 14.4000, 42.9000, 14.4000);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 13.8999, 42.4001, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 42.4001, 13.8999, 42.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 14.4000, 41.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 16.4000, 41.4000, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 15.8999, 41.4000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 15.4000, 41.4000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 14.4000, 41.4000, 14.4000);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 13.8999, 41.4000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 13.4000, 40.9000, 13.4000);
            FanTrk(N, eTopLayer, 0.1500, 41.9000, 7.4000, 41.4000, 6.9000);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 16.4000, 45.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 16.4000, 46.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.9000, 15.8999, 46.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 15.8999, 46.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.0762, 48.4001, 15.8999, 48.1501, 16.1499);
            FanTrk(N, eTopLayer, 0.0762, 48.1501, 16.1499, 48.1501, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 48.1501, 16.6500, 47.1501, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 47.1501, 16.6500, 46.9000, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 50.9000, 16.4000, 51.4000, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 50.9000, 15.4000, 51.4000, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 50.9000, 13.8999, 51.4000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 50.9000, 11.4000, 51.4000, 11.4000);
            FanTrk(N, eTopLayer, 0.2000, 50.9000, 8.8999, 51.9000, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 12.8999, 50.6501, 13.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 13.1500, 51.9000, 13.1500);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 7.4000, 47.4001, 6.2500);
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 7.8999, 50.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 7.6500, 50.6501, 6.3500);
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 9.8999, 42.1501, 10.1500);
            FanTrk(N, eTopLayer, 0.0762, 42.1501, 10.1500, 40.9000, 10.1500);
            FanTrk(N, eBottomLayer, 0.1500, 44.9000, 13.8999, 44.9699, 14.4500);
            FanTrk(N, eBottomLayer, 0.1500, 46.9000, 13.8999, 47.1899, 14.4500);
            FanTrk(N, eBottomLayer, 0.1500, 48.9000, 13.8999, 49.4099, 14.4500);
            FanTrk(N, eBottomLayer, 0.1500, 44.4001, 10.4000, 44.9699, 10.4000);
            FanTrk(N, eBottomLayer, 0.1500, 44.9699, 10.4000, 44.9699, 11.0500);
            FanTrk(N, eBottomLayer, 0.1500, 47.1899, 11.0500, 47.4001, 10.8398);
            FanTrk(N, eBottomLayer, 0.1500, 47.4001, 10.8398, 47.4001, 9.8999);
            FanTrk(N, eBottomLayer, 0.1500, 48.4001, 11.4000, 49.4099, 11.4000);
            FanTrk(N, eBottomLayer, 0.1500, 49.4099, 11.4000, 49.4099, 11.0500);
        End;
        N := FanNet('GNDADC');
        If N = Nil Then Missing := Missing + ' GNDADC' Else
        Begin
            FanVia(N, 46.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.1500, 47.4001, 15.4000, 46.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 16.4000, 47.4001, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 15.8999, 47.4001, 15.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 16.4000, 47.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 16.4000, 47.9000, 16.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 15.8999, 47.9000, 15.8999);
        End;
        N := FanNet('JA1');
        If N = Nil Then Missing := Missing + ' JA1' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 8.4000, 50.6501, 8.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 8.6500, 51.1125, 8.6500);
        End;
        N := FanNet('JA10');
        If N = Nil Then Missing := Missing + ' JA10' Else
        Begin
            FanVia(N, 51.4000, 8.1500);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 8.4000, 50.1501, 8.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.1501, 8.1500, 51.4000, 8.1500);
        End;
        N := FanNet('JA3');
        If N = Nil Then Missing := Missing + ' JA3' Else
        Begin
            FanVia(N, 49.4001, 13.4000);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 13.4000, 49.4001, 13.4000);
        End;
        N := FanNet('JA4');
        If N = Nil Then Missing := Missing + ' JA4' Else
        Begin
            FanVia(N, 50.1501, 16.7800);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 15.4000, 50.1501, 15.6501);
            FanTrk(N, eTopLayer, 0.0762, 50.1501, 15.6501, 50.1501, 16.7800);
        End;
        N := FanNet('JA7');
        If N = Nil Then Missing := Missing + ' JA7' Else
        Begin
            FanVia(N, 49.4001, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 49.9000, 8.8999, 49.4001, 8.8999);
        End;
        N := FanNet('LED0_G');
        If N = Nil Then Missing := Missing + ' LED0_G' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 9.4000, 50.6501, 9.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 9.6500, 51.1125, 9.6500);
        End;
        N := FanNet('LED1');
        If N = Nil Then Missing := Missing + ' LED1' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 10.4000, 50.6501, 10.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 10.6500, 51.1125, 10.6500);
        End;
        N := FanNet('PUDC_B');
        If N = Nil Then Missing := Missing + ' PUDC_B' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 14.4000, 50.6501, 14.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 14.6500, 51.1125, 14.6500);
        End;
        N := FanNet('RAS#');
        If N = Nil Then Missing := Missing + ' RAS#' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 7.8999, 42.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.6501, 7.6500, 42.6501, 7.1875);
        End;
        N := FanNet('RST#');
        If N = Nil Then Missing := Missing + ' RST#' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 46.4001, 7.8999, 46.1501, 7.6498);
            FanTrk(N, eTopLayer, 0.0762, 46.1501, 7.6498, 46.1501, 7.1875);
        End;
        N := FanNet('SD-CLK');
        If N = Nil Then Missing := Missing + ' SD-CLK' Else
        Begin
            FanVia(N, 45.4001, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 45.4001, 8.4000, 45.4001, 8.8999);
        End;
        N := FanNet('SD-CMD');
        If N = Nil Then Missing := Missing + ' SD-CMD' Else
        Begin
            FanVia(N, 44.9000, 8.8999);
            FanTrk(N, eTopLayer, 0.0762, 44.9000, 8.4000, 44.9000, 8.8999);
        End;
        N := FanNet('SD-DAT0');
        If N = Nil Then Missing := Missing + ' SD-DAT0' Else
        Begin
            FanVia(N, 48.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.0762, 48.9000, 15.4000, 48.4001, 14.8999);
        End;
        N := FanNet('SD-DAT1');
        If N = Nil Then Missing := Missing + ' SD-DAT1' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 48.9000, 15.8999, 48.6501, 16.1499);
            FanTrk(N, eTopLayer, 0.0762, 48.6501, 16.1499, 48.6501, 16.6125);
        End;
        N := FanNet('SD-DAT2');
        If N = Nil Then Missing := Missing + ' SD-DAT2' Else
        Begin
            FanVia(N, 43.4001, 11.8999);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 11.4000, 43.4001, 11.8999);
        End;
        N := FanNet('UART_FT_CTS#');
        If N = Nil Then Missing := Missing + ' UART_FT_CTS#' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 49.4001, 15.8999, 49.1501, 16.1500);
            FanTrk(N, eTopLayer, 0.0762, 49.1501, 16.1500, 49.1501, 16.6125);
        End;
        N := FanNet('UART_FT_DTR#');
        If N = Nil Then Missing := Missing + ' UART_FT_DTR#' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 10.8999, 50.6502, 11.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.6502, 11.1500, 51.1125, 11.1500);
        End;
        N := FanNet('UART_FT_RTS#');
        If N = Nil Then Missing := Missing + ' UART_FT_RTS#' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 11.4000, 50.6501, 11.6500);
            FanTrk(N, eTopLayer, 0.0762, 50.6501, 11.6500, 51.1125, 11.6500);
        End;
        N := FanNet('UART_FT_TXD');
        If N = Nil Then Missing := Missing + ' UART_FT_TXD' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 50.4001, 11.8999, 50.6502, 12.1500);
            FanTrk(N, eTopLayer, 0.0762, 50.6502, 12.1500, 51.1125, 12.1500);
        End;
        N := FanNet('UDQM');
        If N = Nil Then Missing := Missing + ' UDQM' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 11.4000, 42.1502, 11.6500);
            FanTrk(N, eTopLayer, 0.0762, 42.1502, 11.6500, 41.6875, 11.6500);
        End;
        N := FanNet('VCC1V0');
        If N = Nil Then Missing := Missing + ' VCC1V0' Else
        Begin
            FanVia(N, 46.4001, 13.8999);
            FanVia(N, 46.4001, 9.8999);
            FanVia(N, 46.9000, 9.8999);
            FanVia(N, 46.4001, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 13.4000, 46.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 12.8999, 46.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 11.4000, 46.4001, 10.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 10.8999, 46.4001, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 10.8999, 46.9000, 10.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 10.4000, 46.9000, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 10.8999, 46.9000, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 13.4000, 46.4001, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 10.4000, 46.4001, 9.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.9000, 10.4000, 46.9000, 9.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 12.4000, 46.4001, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 46.4001, 11.4000, 46.4001, 11.8999);
            FanTrk(N, eBottomLayer, 0.1500, 46.4001, 13.8999, 46.5900, 14.4500);
            FanTrk(N, eBottomLayer, 0.1500, 46.4001, 11.8999, 46.5900, 11.0500);
            FanTrk(N, eBottomLayer, 0.1500, 46.5900, 11.0500, 46.5900, 11.4500);
            FanTrk(N, eBottomLayer, 0.1500, 46.5900, 11.4500, 44.3700, 11.4500);
            FanTrk(N, eBottomLayer, 0.1500, 44.3700, 11.4500, 44.3700, 11.0500);
            FanTrk(N, eBottomLayer, 0.1500, 46.5900, 11.0500, 46.5900, 11.4500);
            FanTrk(N, eBottomLayer, 0.1500, 46.5900, 11.4500, 47.5000, 11.4500);
            FanTrk(N, eBottomLayer, 0.1500, 47.5000, 11.4500, 47.9000, 11.0500);
            FanTrk(N, eBottomLayer, 0.1500, 47.9000, 11.0500, 48.8100, 11.0500);
        End;
        N := FanNet('VCC1V8');
        If N = Nil Then Missing := Missing + ' VCC1V8' Else
        Begin
            FanVia(N, 45.4001, 14.8999);
            FanVia(N, 48.4001, 12.8999);
            FanVia(N, 48.4001, 12.4000);
            FanVia(N, 48.4001, 13.4000);
            FanVia(N, 43.9000, 14.4000);
            FanTrk(N, eTopLayer, 0.1500, 45.9000, 15.4000, 45.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 12.8999, 47.9000, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 12.8999, 48.4001, 12.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 12.4000, 48.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.1500, 47.9000, 12.8999, 48.4001, 13.4000);
            FanTrk(N, eBottomLayer, 0.1500, 48.4001, 13.4000, 48.4001, 13.8999);
            FanTrk(N, eBottomLayer, 0.1500, 48.4001, 13.8999, 48.8100, 14.4500);
            FanTrk(N, eBottomLayer, 0.1500, 43.9000, 14.4000, 44.3700, 14.4500);
            FanTrk(N, eMidLayer1, 0.1500, 45.4001, 14.8999, 45.4001, 14.4000);
            FanTrk(N, eMidLayer1, 0.1500, 45.4001, 14.4000, 43.9000, 14.4000);
        End;
        N := FanNet('VCC3V3');
        If N = Nil Then Missing := Missing + ' VCC3V3' Else
        Begin
            FanVia(N, 47.9000, 14.8999);
            FanVia(N, 43.4001, 13.4000);
            FanVia(N, 47.9000, 8.8999);
            FanVia(N, 49.4001, 13.8999);
            FanVia(N, 49.4001, 9.4000);
            FanVia(N, 48.9000, 10.4000);
            FanVia(N, 47.4001, 13.8999);
            FanVia(N, 47.9000, 13.8999);
            FanVia(N, 44.4001, 12.4000);
            FanVia(N, 44.4001, 11.8999);
            FanVia(N, 44.9000, 9.8999);
            FanVia(N, 45.4001, 9.8999);
            FanVia(N, 44.4001, 9.8999);
            FanVia(N, 48.4001, 11.8999);
            FanVia(N, 51.4000, 15.8999);
            FanVia(N, 40.9000, 11.8999);
            FanVia(N, 40.4000, 9.4000);
            FanVia(N, 40.9000, 7.8999);
            FanVia(N, 44.1501, 6.9000);
            FanVia(N, 45.6501, 6.9000);
            FanVia(N, 46.6501, 6.9000);
            FanTrk(N, eTopLayer, 0.1500, 48.4001, 15.4000, 47.9000, 14.8999);
            FanTrk(N, eTopLayer, 0.1500, 42.9000, 12.8999, 43.4001, 13.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 8.4000, 47.9000, 8.8999);
            FanTrk(N, eTopLayer, 0.2000, 49.9000, 13.8999, 49.4001, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 49.9000, 9.4000, 49.4001, 9.4000);
            FanTrk(N, eTopLayer, 0.2000, 49.9000, 10.8999, 49.4001, 10.8999);
            FanTrk(N, eTopLayer, 0.1500, 49.4001, 10.8999, 48.9000, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 12.4000, 44.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 11.8999, 44.9000, 11.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 11.4000, 44.9000, 10.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 10.8999, 44.9000, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 10.8999, 45.4001, 10.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 10.4000, 45.4001, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 10.8999, 45.4001, 10.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 13.4000, 47.9000, 13.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 11.8999, 47.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 11.4000, 47.9000, 11.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 11.8999, 47.4001, 11.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 11.8999, 47.9000, 11.4000);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 11.4000, 47.4001, 10.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.4001, 13.4000, 47.4001, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 13.4000, 47.9000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 12.4000, 44.4001, 12.4000);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 11.8999, 44.4001, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 44.9000, 10.4000, 44.9000, 9.8999);
            FanTrk(N, eTopLayer, 0.2000, 45.4001, 10.4000, 45.4001, 9.8999);
            FanTrk(N, eTopLayer, 0.1500, 44.9000, 10.4000, 44.4001, 9.8999);
            FanTrk(N, eTopLayer, 0.2000, 47.9000, 11.8999, 48.4001, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 50.9000, 15.8999, 51.4000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 50.4001, 15.4000, 50.9000, 15.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 11.8999, 40.9000, 11.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 9.4000, 40.4000, 9.4000);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 7.8999, 40.9000, 7.8999);
            FanTrk(N, eTopLayer, 0.0762, 44.4001, 7.8999, 44.1501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 44.1501, 7.6500, 44.1501, 6.9000);
            FanTrk(N, eTopLayer, 0.0762, 45.9000, 7.8999, 45.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 45.6501, 7.6500, 45.6501, 6.9000);
            FanTrk(N, eTopLayer, 0.0762, 46.9000, 7.8999, 46.6501, 7.6500);
            FanTrk(N, eTopLayer, 0.0762, 46.6501, 7.6500, 46.6501, 6.9000);
        End;
        N := FanNet('VCCADC');
        If N = Nil Then Missing := Missing + ' VCCADC' Else
        Begin
            FanVia(N, 47.4001, 14.8999);
            FanTrk(N, eTopLayer, 0.1500, 47.9000, 15.4000, 47.4001, 14.8999);
        End;
        N := FanNet('WE#');
        If N = Nil Then Missing := Missing + ' WE#' Else
        Begin
            FanTrk(N, eTopLayer, 0.0762, 43.4001, 7.8999, 43.1501, 7.6498);
            FanTrk(N, eTopLayer, 0.0762, 43.1501, 7.6498, 43.1501, 7.1875);
        End;
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;
    If Missing <> '' Then
        ShowMessage('Zulu A7 - fan-out placed, but these nets were NOT found:' + Missing + #13#10 + 'Their primitives were skipped. Do not save until this is understood.')
    Else
        ShowMessage('Zulu A7 - fan-out placed: 107 vias, 318 tracks.' + #13#10 + #13#10 +
                    'Now Tools > Design Rule Check > Run, then Ctrl+S if it is clean.');
End;


Procedure RemoveFanout;
Var
    It   : IPCB_BoardIterator;
    P    : IPCB_Primitive;
    Kill : TInterfaceList;
    i    : Integer;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.ObjectId = eViaObject) Or ((P.ObjectId = eTrackObject) And
           ((P.Layer = eTopLayer) Or (P.Layer = eMidLayer1) Or (P.Layer = eMidLayer2) Or (P.Layer = eBottomLayer))) Then
            Kill.Add(P);
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Kill.Count > 430 Then
    Begin
        ShowMessage('RemoveFanout would delete ' + IntToStr(Kill.Count) + ' objects, more than the fan-out placed - there is other routing on the board now. Nothing removed.');
        Kill.Free;
        Exit;
    End;
    PCBServer.PreProcess;
    Try
        For i := 0 To Kill.Count - 1 Do
            Brd.RemovePCBObject(Kill.Items[i]);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - removed ' + IntToStr(Kill.Count) + ' fan-out object(s). Press Ctrl+S.');
    Kill.Free;
End;

{ ==== END FANOUT BLOCK ==== }


{ ==== COROUTE BLOCK, generated by tools/route_emit.py -- do not edit by hand ==== }

Procedure PlaceCoRoute;
Var
    N    : IPCB_Net;
    V    : IPCB_Via;
    T    : IPCB_Track;
    It   : IPCB_BoardIterator;
    Kill : TInterfaceList;
    i    : Integer;
    x, y, x2, y2 : Double;
    nm   : String;
    Missing : String;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Missing := '';
    Kill := TInterfaceList.Create;
    { the existing copper this plan replaces: all of it, or nothing happens }
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        nm := ''; If V.Net <> Nil Then nm := V.Net.Name;
        x := CoordToMMs(V.X); y := CoordToMMs(V.Y);
        If ((nm = 'GND') And (Abs(x - 41.4000) < 0.001) And (Abs(y - 13.8999) < 0.001)) Then Kill.Add(V);
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        nm := ''; If T.Net <> Nil Then nm := T.Net.Name;
        x := CoordToMMs(T.X1); y := CoordToMMs(T.Y1); x2 := CoordToMMs(T.X2); y2 := CoordToMMs(T.Y2);
        If ((nm = 'GND') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 13.8999) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 13.8999) < 0.001)) Or ((Abs(x - 41.4000) < 0.001) And (Abs(y - 13.8999) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 13.8999) < 0.001)))) Then Kill.Add(T);
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Kill.Count <> 2 Then
    Begin
        ShowMessage('Zulu A7 - CoRoute: found ' + IntToStr(Kill.Count) + ' of the 2 objects it must replace. Nothing changed.');
        Kill.Free;
        Exit;
    End;
    PCBServer.PreProcess;
    Try
        For i := 0 To Kill.Count - 1 Do
            Brd.RemovePCBObject(Kill.Items[i]);
        N := FanNet('A0');
        If N = Nil Then Missing := Missing + ' A0' Else
        Begin
            FanVia(N, 40.2500, 8.1000);
            FanVia(N, 21.1500, 7.0500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 8.1500, 41.3500, 8.1500);
            FanTrk(N, eTopLayer, 0.0762, 41.3500, 8.1500, 40.9000, 8.2100);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 8.2100, 40.5000, 8.2100);
            FanTrk(N, eTopLayer, 0.0762, 40.5000, 8.2100, 40.2500, 8.1000);
            FanTrk(N, eMidLayer1, 0.1250, 40.2500, 8.1000, 39.9750, 7.9000);
            FanTrk(N, eMidLayer1, 0.1250, 39.9750, 7.9000, 37.7250, 7.9000);
            FanTrk(N, eMidLayer1, 0.1250, 37.7250, 7.9000, 35.9000, 9.7250);
            FanTrk(N, eMidLayer1, 0.1250, 35.9000, 9.7250, 35.8250, 9.7500);
            FanTrk(N, eMidLayer1, 0.1250, 35.8250, 9.7500, 27.1750, 9.7500);
            FanTrk(N, eMidLayer1, 0.1250, 27.1750, 9.7500, 21.8750, 8.4500);
            FanTrk(N, eMidLayer1, 0.1250, 21.8750, 8.4500, 21.8500, 8.4500);
            FanTrk(N, eMidLayer1, 0.1250, 21.8500, 8.4500, 21.8500, 8.4250);
            FanTrk(N, eMidLayer1, 0.1250, 21.8500, 8.4250, 21.1500, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 21.1500, 7.0500, 21.1501, 6.1701);
        End;
        N := FanNet('A1');
        If N = Nil Then Missing := Missing + ' A1' Else
        Begin
            FanVia(N, 20.3500, 7.0500);
            FanTrk(N, eMidLayer1, 0.1250, 43.4001, 9.4000, 40.2750, 8.9500);
            FanTrk(N, eMidLayer1, 0.1250, 40.2750, 8.9500, 39.2500, 8.3500);
            FanTrk(N, eMidLayer1, 0.1250, 39.2500, 8.3500, 37.6250, 8.3500);
            FanTrk(N, eMidLayer1, 0.1250, 37.6250, 8.3500, 36.0000, 9.9500);
            FanTrk(N, eMidLayer1, 0.1250, 36.0000, 9.9500, 35.8500, 10.0000);
            FanTrk(N, eMidLayer1, 0.1250, 35.8500, 10.0000, 27.1500, 10.0000);
            FanTrk(N, eMidLayer1, 0.1250, 27.1500, 10.0000, 21.7500, 8.6750);
            FanTrk(N, eMidLayer1, 0.1250, 21.7500, 8.6750, 21.0500, 8.4500);
            FanTrk(N, eMidLayer1, 0.1250, 21.0500, 8.4500, 20.3500, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 20.3500, 7.0500, 20.3500, 6.1701);
        End;
        N := FanNet('A10');
        If N = Nil Then Missing := Missing + ' A10' Else
        Begin
            FanVia(N, 21.9500, 7.0500);
            FanTrk(N, eMidLayer2, 0.1250, 41.4000, 8.6500, 40.9250, 8.4750);
            FanTrk(N, eMidLayer2, 0.1250, 40.9250, 8.4750, 40.0250, 8.4750);
            FanTrk(N, eMidLayer2, 0.1250, 40.0250, 8.4750, 39.8500, 8.6000);
            FanTrk(N, eMidLayer2, 0.1250, 39.8500, 8.6000, 39.5500, 8.6000);
            FanTrk(N, eMidLayer2, 0.1250, 39.5500, 8.6000, 39.3000, 8.3750);
            FanTrk(N, eMidLayer2, 0.1250, 39.3000, 8.3750, 39.2500, 8.3500);
            FanTrk(N, eMidLayer2, 0.1250, 39.2500, 8.3500, 38.0750, 8.4000);
            FanTrk(N, eMidLayer2, 0.1250, 38.0750, 8.4000, 36.3250, 10.0000);
            FanTrk(N, eMidLayer2, 0.1250, 36.3250, 10.0000, 36.1000, 10.1750);
            FanTrk(N, eMidLayer2, 0.1250, 36.1000, 10.1750, 30.9000, 10.2500);
            FanTrk(N, eMidLayer2, 0.1250, 30.9000, 10.2500, 27.0000, 9.7000);
            FanTrk(N, eMidLayer2, 0.1250, 27.0000, 9.7000, 23.3500, 8.6750);
            FanTrk(N, eMidLayer2, 0.1250, 23.3500, 8.6750, 22.6500, 8.4500);
            FanTrk(N, eMidLayer2, 0.1250, 22.6500, 8.4500, 21.9500, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 21.9500, 7.0500, 21.9499, 6.1701);
        End;
        N := FanNet('A11');
        If N = Nil Then Missing := Missing + ' A11' Else
        Begin
            FanVia(N, 38.5000, 11.5000);
            FanVia(N, 23.3500, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 10.4000, 41.5000, 10.4600);
            FanTrk(N, eTopLayer, 0.0762, 41.5000, 10.4600, 40.9000, 10.4600);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 10.4600, 38.9795, 10.4600);
            FanTrk(N, eTopLayer, 0.0762, 38.9795, 10.4600, 38.9795, 11.5000);
            FanTrk(N, eTopLayer, 0.0762, 38.9795, 11.5000, 38.5000, 11.5000);
            FanTrk(N, eMidLayer2, 0.1250, 38.5000, 11.5000, 24.2250, 13.9000);
            FanTrk(N, eMidLayer2, 0.1250, 24.2250, 13.9000, 23.7250, 16.3000);
            FanTrk(N, eMidLayer2, 0.1250, 23.7250, 16.3000, 23.3500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 23.3500, 16.6500, 23.5499, 17.5300);
        End;
        N := FanNet('A12');
        If N = Nil Then Missing := Missing + ' A12' Else
        Begin
            FanVia(N, 23.3500, 16.1750);
            FanTrk(N, eMidLayer1, 0.1250, 43.4001, 11.4000, 39.5500, 11.4000);
            FanTrk(N, eMidLayer1, 0.1250, 39.5500, 11.4000, 38.7000, 12.2500);
            FanTrk(N, eMidLayer1, 0.1250, 38.7000, 12.2500, 32.3750, 13.8750);
            FanTrk(N, eMidLayer1, 0.1250, 32.3750, 13.8750, 25.8750, 13.8750);
            FanTrk(N, eMidLayer1, 0.1250, 25.8750, 13.8750, 23.3500, 16.1750);
            FanTrk(N, eBottomLayer, 0.1250, 23.3500, 16.1750, 23.6500, 16.4750);
            FanTrk(N, eBottomLayer, 0.1250, 23.6500, 16.4750, 23.9500, 16.9000);
            FanTrk(N, eBottomLayer, 0.1250, 23.9500, 16.9000, 24.3500, 17.5300);
        End;
        N := FanNet('A2');
        If N = Nil Then Missing := Missing + ' A2' Else
        Begin
            FanVia(N, 38.6000, 8.9500);
            FanVia(N, 19.5500, 7.0500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 9.1500, 41.4000, 9.1400);
            FanTrk(N, eTopLayer, 0.0762, 41.4000, 9.1400, 40.9000, 9.1200);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 9.1200, 40.5000, 9.0800);
            FanTrk(N, eTopLayer, 0.0762, 40.5000, 9.0800, 40.1000, 9.0800);
            FanTrk(N, eTopLayer, 0.0762, 40.1000, 9.0800, 39.8000, 9.2000);
            FanTrk(N, eTopLayer, 0.0762, 39.8000, 9.2000, 38.6000, 8.9500);
            FanTrk(N, eMidLayer2, 0.1250, 38.6000, 8.9500, 36.1250, 10.4250);
            FanTrk(N, eMidLayer2, 0.1250, 36.1250, 10.4250, 29.0500, 10.5000);
            FanTrk(N, eMidLayer2, 0.1250, 29.0500, 10.5000, 20.2500, 8.4500);
            FanTrk(N, eMidLayer2, 0.1250, 20.2500, 8.4500, 19.5500, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 19.5500, 7.0500, 19.5499, 6.1701);
        End;
        N := FanNet('A3');
        If N = Nil Then Missing := Missing + ' A3' Else
        Begin
            FanVia(N, 39.1500, 8.7000);
            FanVia(N, 18.7500, 7.0500);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 8.8999, 41.7000, 8.9200);
            FanTrk(N, eTopLayer, 0.0762, 41.7000, 8.9200, 41.4000, 8.9600);
            FanTrk(N, eTopLayer, 0.0762, 41.4000, 8.9600, 40.9000, 8.9300);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 8.9300, 40.5000, 8.9000);
            FanTrk(N, eTopLayer, 0.0762, 40.5000, 8.9000, 39.1500, 8.7000);
            FanTrk(N, eMidLayer1, 0.1250, 39.1500, 8.7000, 38.7000, 8.6000);
            FanTrk(N, eMidLayer1, 0.1250, 38.7000, 8.6000, 38.4000, 8.6000);
            FanTrk(N, eMidLayer1, 0.1250, 38.4000, 8.6000, 36.1000, 10.1750);
            FanTrk(N, eMidLayer1, 0.1250, 36.1000, 10.1750, 35.8750, 10.2500);
            FanTrk(N, eMidLayer1, 0.1250, 35.8750, 10.2500, 27.1250, 10.2500);
            FanTrk(N, eMidLayer1, 0.1250, 27.1250, 10.2500, 19.4500, 8.4500);
            FanTrk(N, eMidLayer1, 0.1250, 19.4500, 8.4500, 18.7500, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 18.7500, 7.0500, 18.7500, 6.1701);
        End;
        N := FanNet('A4');
        If N = Nil Then Missing := Missing + ' A4' Else
        Begin
            FanVia(N, 18.7500, 16.6500);
            FanTrk(N, eMidLayer2, 0.1250, 43.4001, 9.8999, 40.6750, 8.7500);
            FanTrk(N, eMidLayer2, 0.1250, 40.6750, 8.7500, 40.0000, 8.7750);
            FanTrk(N, eMidLayer2, 0.1250, 40.0000, 8.7750, 39.8750, 8.8500);
            FanTrk(N, eMidLayer2, 0.1250, 39.8750, 8.8500, 37.6750, 9.8250);
            FanTrk(N, eMidLayer2, 0.1250, 37.6750, 9.8250, 36.8750, 10.3250);
            FanTrk(N, eMidLayer2, 0.1250, 36.8750, 10.3250, 36.1750, 10.7250);
            FanTrk(N, eMidLayer2, 0.1250, 36.1750, 10.7250, 22.3250, 13.5250);
            FanTrk(N, eMidLayer2, 0.1250, 22.3250, 13.5250, 21.7750, 13.6750);
            FanTrk(N, eMidLayer2, 0.1250, 21.7750, 13.6750, 19.4250, 15.3000);
            FanTrk(N, eMidLayer2, 0.1250, 19.4250, 15.3000, 18.7500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 18.7500, 16.6500, 18.7500, 17.5300);
        End;
        N := FanNet('A5');
        If N = Nil Then Missing := Missing + ' A5' Else
        Begin
            FanVia(N, 38.5000, 10.6000);
            FanVia(N, 19.5500, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 9.6500, 40.9000, 9.6500);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 9.6500, 40.4000, 9.7100);
            FanTrk(N, eTopLayer, 0.0762, 40.4000, 9.7100, 38.6465, 9.7100);
            FanTrk(N, eTopLayer, 0.0762, 38.6465, 9.7100, 38.6465, 10.6000);
            FanTrk(N, eTopLayer, 0.0762, 38.6465, 10.6000, 38.5000, 10.6000);
            FanTrk(N, eMidLayer1, 0.1250, 38.5000, 10.6000, 23.1250, 13.1750);
            FanTrk(N, eMidLayer1, 0.1250, 23.1250, 13.1750, 22.0500, 13.6750);
            FanTrk(N, eMidLayer1, 0.1250, 22.0500, 13.6750, 20.2250, 15.3000);
            FanTrk(N, eMidLayer1, 0.1250, 20.2250, 15.3000, 19.5500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 19.5500, 16.6500, 19.5499, 17.5300);
        End;
        N := FanNet('A6');
        If N = Nil Then Missing := Missing + ' A6' Else
        Begin
            FanVia(N, 20.3500, 16.6500);
            FanTrk(N, eMidLayer2, 0.1250, 43.4001, 10.4000, 40.5000, 9.0500);
            FanTrk(N, eMidLayer2, 0.1250, 40.5000, 9.0500, 40.2250, 9.0500);
            FanTrk(N, eMidLayer2, 0.1250, 40.2250, 9.0500, 40.0250, 9.2500);
            FanTrk(N, eMidLayer2, 0.1250, 40.0250, 9.2500, 38.0750, 9.9000);
            FanTrk(N, eMidLayer2, 0.1250, 38.0750, 9.9000, 36.6750, 10.7500);
            FanTrk(N, eMidLayer2, 0.1250, 36.6750, 10.7500, 36.2750, 10.9750);
            FanTrk(N, eMidLayer2, 0.1250, 36.2750, 10.9750, 36.1750, 11.0250);
            FanTrk(N, eMidLayer2, 0.1250, 36.1750, 11.0250, 22.8500, 13.6500);
            FanTrk(N, eMidLayer2, 0.1250, 22.8500, 13.6500, 21.8750, 13.9000);
            FanTrk(N, eMidLayer2, 0.1250, 21.8750, 13.9000, 21.0500, 15.3000);
            FanTrk(N, eMidLayer2, 0.1250, 21.0500, 15.3000, 20.3500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 20.3500, 16.6500, 20.3500, 17.5300);
        End;
        N := FanNet('A7');
        If N = Nil Then Missing := Missing + ' A7' Else
        Begin
            FanVia(N, 38.5000, 11.0500);
            FanVia(N, 21.1000, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 9.8999, 41.4000, 9.8700);
            FanTrk(N, eTopLayer, 0.0762, 41.4000, 9.8700, 40.9000, 9.8300);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 9.8300, 40.4000, 9.8800);
            FanTrk(N, eTopLayer, 0.0762, 40.4000, 9.8800, 38.8130, 9.8800);
            FanTrk(N, eTopLayer, 0.0762, 38.8130, 9.8800, 38.8130, 11.0500);
            FanTrk(N, eTopLayer, 0.0762, 38.8130, 11.0500, 38.5000, 11.0500);
            FanTrk(N, eMidLayer1, 0.1250, 38.5000, 11.0500, 23.2250, 13.4000);
            FanTrk(N, eMidLayer1, 0.1250, 23.2250, 13.4000, 22.1500, 13.9000);
            FanTrk(N, eMidLayer1, 0.1250, 22.1500, 13.9000, 21.1000, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 21.1000, 16.6500, 21.1501, 17.5300);
        End;
        N := FanNet('A8');
        If N = Nil Then Missing := Missing + ' A8' Else
        Begin
            FanVia(N, 21.6250, 16.6750);
            FanTrk(N, eMidLayer2, 0.1250, 43.4001, 10.8999, 41.0000, 9.8000);
            FanTrk(N, eMidLayer2, 0.1250, 41.0000, 9.8000, 38.3000, 10.0750);
            FanTrk(N, eMidLayer2, 0.1250, 38.3000, 10.0750, 36.2750, 11.3000);
            FanTrk(N, eMidLayer2, 0.1250, 36.2750, 11.3000, 30.4250, 12.6250);
            FanTrk(N, eMidLayer2, 0.1250, 30.4250, 12.6250, 22.9500, 13.8750);
            FanTrk(N, eMidLayer2, 0.1250, 22.9500, 13.8750, 21.4750, 16.1500);
            FanTrk(N, eMidLayer2, 0.1250, 21.4750, 16.1500, 21.5000, 16.5500);
            FanTrk(N, eMidLayer2, 0.1250, 21.5000, 16.5500, 21.6250, 16.6750);
            FanTrk(N, eBottomLayer, 0.1250, 21.6250, 16.6750, 21.9499, 17.5300);
        End;
        N := FanNet('A9');
        If N = Nil Then Missing := Missing + ' A9' Else
        Begin
            FanVia(N, 38.5000, 11.9500);
            FanVia(N, 21.8250, 16.2500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 10.6500, 41.5000, 10.6800);
            FanTrk(N, eTopLayer, 0.0762, 41.5000, 10.6800, 40.9000, 10.6800);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 10.6800, 39.1460, 10.6800);
            FanTrk(N, eTopLayer, 0.0762, 39.1460, 10.6800, 39.1460, 11.9500);
            FanTrk(N, eTopLayer, 0.0762, 39.1460, 11.9500, 38.5000, 11.9500);
            FanTrk(N, eMidLayer1, 0.1250, 38.5000, 11.9500, 23.3250, 13.6250);
            FanTrk(N, eMidLayer1, 0.1250, 23.3250, 13.6250, 23.2250, 13.7500);
            FanTrk(N, eMidLayer1, 0.1250, 23.2250, 13.7500, 21.8250, 16.2500);
            FanTrk(N, eBottomLayer, 0.1250, 21.8250, 16.2500, 22.3500, 16.9000);
            FanTrk(N, eBottomLayer, 0.1250, 22.3500, 16.9000, 22.7500, 17.5300);
        End;
        N := FanNet('AIN15_N');
        If N = Nil Then Missing := Missing + ' AIN15_N' Else
        Begin
            FanVia(N, 40.6000, 14.0500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 13.6500, 41.3500, 13.7200);
            FanTrk(N, eTopLayer, 0.0762, 41.3500, 13.7200, 40.6000, 14.0500);
            FanTrk(N, eBottomLayer, 0.0762, 40.4500, 4.6000, 40.4500, 4.3000);
            FanTrk(N, eBottomLayer, 0.0762, 40.4500, 4.3000, 40.4500, 3.6000);
            FanTrk(N, eBottomLayer, 0.0762, 40.4500, 3.6000, 40.3500, 3.0500);
            FanTrk(N, eBottomLayer, 0.0762, 40.4500, 4.3000, 41.3500, 4.3000);
            FanTrk(N, eBottomLayer, 0.0762, 41.3500, 4.3000, 41.3500, 3.9500);
            FanTrk(N, eBottomLayer, 0.0762, 40.6000, 14.0500, 40.2000, 14.1000);
            FanTrk(N, eBottomLayer, 0.0762, 40.2000, 14.1000, 40.0066, 13.5582);
            FanTrk(N, eBottomLayer, 0.0762, 40.0066, 13.5582, 39.9942, 13.5233);
            FanTrk(N, eBottomLayer, 0.0762, 39.9942, 13.5233, 39.9805, 13.4503);
            FanTrk(N, eBottomLayer, 0.0762, 39.9805, 13.4503, 39.9794, 13.4131);
            FanTrk(N, eBottomLayer, 0.0762, 39.9794, 13.4131, 39.9614, 12.7678);
            FanTrk(N, eBottomLayer, 0.0762, 39.9614, 12.7678, 39.9612, 12.7620);
            FanTrk(N, eBottomLayer, 0.0762, 39.9612, 12.7620, 39.9612, 12.7561);
            FanTrk(N, eBottomLayer, 0.0762, 39.9612, 12.7561, 39.9293, 9.4045);
            FanTrk(N, eBottomLayer, 0.0762, 39.9293, 9.4045, 39.9289, 9.3647);
            FanTrk(N, eBottomLayer, 0.0762, 39.9289, 9.3647, 39.9415, 9.2862);
            FanTrk(N, eBottomLayer, 0.0762, 39.9415, 9.2862, 39.9671, 9.2109);
            FanTrk(N, eBottomLayer, 0.0762, 39.9671, 9.2109, 40.0049, 9.1409);
            FanTrk(N, eBottomLayer, 0.0762, 40.0049, 9.1409, 40.0540, 9.0783);
            FanTrk(N, eBottomLayer, 0.0762, 40.0540, 9.0783, 40.0834, 9.0516);
            FanTrk(N, eBottomLayer, 0.0762, 40.0834, 9.0516, 41.1040, 8.1244);
            FanTrk(N, eBottomLayer, 0.0762, 41.1040, 8.1244, 41.1233, 8.1068);
            FanTrk(N, eBottomLayer, 0.0762, 41.1233, 8.1068, 41.1554, 8.0656);
            FanTrk(N, eBottomLayer, 0.0762, 41.1554, 8.0656, 41.1799, 8.0196);
            FanTrk(N, eBottomLayer, 0.0762, 41.1799, 8.0196, 41.1963, 7.9700);
            FanTrk(N, eBottomLayer, 0.0762, 41.1963, 7.9700, 41.2039, 7.9183);
            FanTrk(N, eBottomLayer, 0.0762, 41.2039, 7.9183, 41.2025, 7.8661);
            FanTrk(N, eBottomLayer, 0.0762, 41.2025, 7.8661, 41.1923, 7.8149);
            FanTrk(N, eBottomLayer, 0.0762, 41.1923, 7.8149, 41.1829, 7.7905);
            FanTrk(N, eBottomLayer, 0.0762, 41.1829, 7.7905, 40.8000, 6.8000);
            FanTrk(N, eBottomLayer, 0.0762, 40.8000, 6.8000, 40.4500, 4.6000);
        End;
        N := FanNet('AIN15_P');
        If N = Nil Then Missing := Missing + ' AIN15_P' Else
        Begin
            FanVia(N, 41.5000, 4.6600);
            FanVia(N, 39.6500, 3.8500);
            FanTrk(N, eBottomLayer, 0.0762, 41.5000, 4.6600, 41.6200, 4.2600);
            FanTrk(N, eBottomLayer, 0.0762, 41.6200, 4.2600, 41.6500, 4.0500);
            FanTrk(N, eBottomLayer, 0.0762, 41.6500, 4.0500, 41.6500, 3.0500);
            FanTrk(N, eTopLayer, 0.0762, 41.5000, 4.6600, 39.6500, 3.8500);
            FanTrk(N, eBottomLayer, 0.0762, 39.6500, 3.8500, 40.1500, 3.9500);
            FanTrk(N, eBottomLayer, 0.0762, 43.4001, 13.8999, 40.4299, 13.7026);
            FanTrk(N, eBottomLayer, 0.0762, 40.4299, 13.7026, 40.4050, 13.7010);
            FanTrk(N, eBottomLayer, 0.0762, 40.4050, 13.7010, 40.3564, 13.6896);
            FanTrk(N, eBottomLayer, 0.0762, 40.3564, 13.6896, 40.3103, 13.6704);
            FanTrk(N, eBottomLayer, 0.0762, 40.3103, 13.6704, 40.2680, 13.6439);
            FanTrk(N, eBottomLayer, 0.0762, 40.2680, 13.6439, 40.2306, 13.6109);
            FanTrk(N, eBottomLayer, 0.0762, 40.2306, 13.6109, 40.1991, 13.5722);
            FanTrk(N, eBottomLayer, 0.0762, 40.1991, 13.5722, 40.1743, 13.5289);
            FanTrk(N, eBottomLayer, 0.0762, 40.1743, 13.5289, 40.1570, 13.4821);
            FanTrk(N, eBottomLayer, 0.0762, 40.1570, 13.4821, 40.1475, 13.4331);
            FanTrk(N, eBottomLayer, 0.0762, 40.1475, 13.4331, 40.1468, 13.4082);
            FanTrk(N, eBottomLayer, 0.0762, 40.1468, 13.4082, 40.1294, 12.7627);
            FanTrk(N, eBottomLayer, 0.0762, 40.1294, 12.7627, 40.1293, 12.7586);
            FanTrk(N, eBottomLayer, 0.0762, 40.1293, 12.7586, 40.1293, 12.7546);
            FanTrk(N, eBottomLayer, 0.0762, 40.1293, 12.7546, 40.0967, 9.4029);
            FanTrk(N, eBottomLayer, 0.0762, 40.0967, 9.4029, 40.0965, 9.3773);
            FanTrk(N, eBottomLayer, 0.0762, 40.0965, 9.3773, 40.1046, 9.3267);
            FanTrk(N, eBottomLayer, 0.0762, 40.1046, 9.3267, 40.1211, 9.2782);
            FanTrk(N, eBottomLayer, 0.0762, 40.1211, 9.2782, 40.1455, 9.2331);
            FanTrk(N, eBottomLayer, 0.0762, 40.1455, 9.2331, 40.1771, 9.1927);
            FanTrk(N, eBottomLayer, 0.0762, 40.1771, 9.1927, 40.1960, 9.1755);
            FanTrk(N, eBottomLayer, 0.0762, 40.1960, 9.1755, 41.2166, 8.2483);
            FanTrk(N, eBottomLayer, 0.0762, 41.2166, 8.2483, 41.2449, 8.2226);
            FanTrk(N, eBottomLayer, 0.0762, 41.2449, 8.2226, 41.2924, 8.1628);
            FanTrk(N, eBottomLayer, 0.0762, 41.2924, 8.1628, 41.3297, 8.0960);
            FanTrk(N, eBottomLayer, 0.0762, 41.3297, 8.0960, 41.3557, 8.0241);
            FanTrk(N, eBottomLayer, 0.0762, 41.3557, 8.0241, 41.3698, 7.9489);
            FanTrk(N, eBottomLayer, 0.0762, 41.3698, 7.9489, 41.3715, 7.8725);
            FanTrk(N, eBottomLayer, 0.0762, 41.3715, 7.8725, 41.3609, 7.7968);
            FanTrk(N, eBottomLayer, 0.0762, 41.3609, 7.7968, 41.3496, 7.7603);
            FanTrk(N, eBottomLayer, 0.0762, 41.3496, 7.7603, 41.1103, 6.9900);
            FanTrk(N, eBottomLayer, 0.0762, 41.1103, 6.9900, 41.1031, 6.9667);
            FanTrk(N, eBottomLayer, 0.0762, 41.1031, 6.9667, 41.0963, 6.9184);
            FanTrk(N, eBottomLayer, 0.0762, 41.0963, 6.9184, 41.0972, 6.8696);
            FanTrk(N, eBottomLayer, 0.0762, 41.0972, 6.8696, 41.1016, 6.8456);
            FanTrk(N, eBottomLayer, 0.0762, 41.1016, 6.8456, 41.5000, 4.6600);
        End;
        N := FanNet('AIN16_N');
        If N = Nil Then Missing := Missing + ' AIN16_N' Else
        Begin
            FanVia(N, 41.3000, 12.6650);
            FanVia(N, 46.1500, 3.3500);
            FanVia(N, 43.3000, 3.2000);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 12.6500, 41.3000, 12.6650);
            FanTrk(N, eBottomLayer, 0.0762, 46.0160, 5.0000, 46.0200, 4.6000);
            FanTrk(N, eBottomLayer, 0.0762, 46.0200, 4.6000, 46.1500, 3.9500);
            FanTrk(N, eBottomLayer, 0.0762, 46.1500, 3.9500, 46.1500, 3.3500);
            FanTrk(N, eTopLayer, 0.0762, 46.1500, 3.3500, 43.3000, 3.2000);
            FanTrk(N, eBottomLayer, 0.0762, 43.3000, 3.2000, 42.6500, 3.0500);
            FanTrk(N, eBottomLayer, 0.0762, 41.3000, 12.6650, 40.6977, 12.1259);
            FanTrk(N, eBottomLayer, 0.0762, 40.6977, 12.1259, 40.6787, 12.1088);
            FanTrk(N, eBottomLayer, 0.0762, 40.6787, 12.1088, 40.6468, 12.0689);
            FanTrk(N, eBottomLayer, 0.0762, 40.6468, 12.0689, 40.6221, 12.0241);
            FanTrk(N, eBottomLayer, 0.0762, 40.6221, 12.0241, 40.6053, 11.9759);
            FanTrk(N, eBottomLayer, 0.0762, 40.6053, 11.9759, 40.5967, 11.9255);
            FanTrk(N, eBottomLayer, 0.0762, 40.5967, 11.9255, 40.5967, 11.8999);
            FanTrk(N, eBottomLayer, 0.0762, 40.5967, 11.8999, 40.5967, 10.1500);
            FanTrk(N, eBottomLayer, 0.0762, 40.5967, 10.1500, 40.5967, 10.1247);
            FanTrk(N, eBottomLayer, 0.0762, 40.5967, 10.1247, 40.6051, 10.0747);
            FanTrk(N, eBottomLayer, 0.0762, 40.6051, 10.0747, 40.6217, 10.0268);
            FanTrk(N, eBottomLayer, 0.0762, 40.6217, 10.0268, 40.6460, 9.9824);
            FanTrk(N, eBottomLayer, 0.0762, 40.6460, 9.9824, 40.6773, 9.9425);
            FanTrk(N, eBottomLayer, 0.0762, 40.6773, 9.9425, 40.6961, 9.9255);
            FanTrk(N, eBottomLayer, 0.0762, 40.6961, 9.9255, 41.7165, 8.9984);
            FanTrk(N, eBottomLayer, 0.0762, 41.7165, 8.9984, 41.7456, 8.9720);
            FanTrk(N, eBottomLayer, 0.0762, 41.7456, 8.9720, 41.7942, 8.9103);
            FanTrk(N, eBottomLayer, 0.0762, 41.7942, 8.9103, 41.8319, 8.8414);
            FanTrk(N, eBottomLayer, 0.0762, 41.8319, 8.8414, 41.8576, 8.7671);
            FanTrk(N, eBottomLayer, 0.0762, 41.8576, 8.7671, 41.8707, 8.6897);
            FanTrk(N, eBottomLayer, 0.0762, 41.8707, 8.6897, 41.8708, 8.6504);
            FanTrk(N, eBottomLayer, 0.0762, 41.8708, 8.6504, 41.8717, 7.4999);
            FanTrk(N, eBottomLayer, 0.0762, 41.8717, 7.4999, 41.8717, 7.4887);
            FanTrk(N, eBottomLayer, 0.0762, 41.8717, 7.4887, 41.8756, 7.4668);
            FanTrk(N, eBottomLayer, 0.0762, 41.8756, 7.4668, 41.8832, 7.4458);
            FanTrk(N, eBottomLayer, 0.0762, 41.8832, 7.4458, 41.8943, 7.4265);
            FanTrk(N, eBottomLayer, 0.0762, 41.8943, 7.4265, 41.9085, 7.4093);
            FanTrk(N, eBottomLayer, 0.0762, 41.9085, 7.4093, 41.9256, 7.3949);
            FanTrk(N, eBottomLayer, 0.0762, 41.9256, 7.3949, 41.9352, 7.3893);
            FanTrk(N, eBottomLayer, 0.0762, 41.9352, 7.3893, 46.0160, 5.0000);
        End;
        N := FanNet('AIN16_P');
        If N = Nil Then Missing := Missing + ' AIN16_P' Else
        Begin
            FanVia(N, 40.4500, 13.4000);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 13.1500, 41.2000, 13.1500);
            FanTrk(N, eTopLayer, 0.0762, 41.2000, 13.1500, 40.9000, 13.0900);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 13.0900, 40.6000, 13.0900);
            FanTrk(N, eTopLayer, 0.0762, 40.6000, 13.0900, 40.4500, 13.4000);
            FanTrk(N, eBottomLayer, 0.0762, 45.8500, 4.9000, 45.8500, 3.6500);
            FanTrk(N, eBottomLayer, 0.0762, 45.8500, 3.6500, 45.1500, 3.6500);
            FanTrk(N, eBottomLayer, 0.0762, 45.1500, 3.6500, 44.9500, 3.9500);
            FanTrk(N, eBottomLayer, 0.0762, 44.9500, 3.9500, 43.9500, 3.0500);
            FanTrk(N, eBottomLayer, 0.0762, 40.4500, 13.4000, 40.3058, 12.8236);
            FanTrk(N, eBottomLayer, 0.0762, 40.3058, 12.8236, 40.3003, 12.8018);
            FanTrk(N, eBottomLayer, 0.0762, 40.3003, 12.8018, 40.2959, 12.7570);
            FanTrk(N, eBottomLayer, 0.0762, 40.2959, 12.7570, 40.2971, 12.7346);
            FanTrk(N, eBottomLayer, 0.0762, 40.2971, 12.7346, 40.4298, 10.1261);
            FanTrk(N, eBottomLayer, 0.0762, 40.4298, 10.1261, 40.4317, 10.0892);
            FanTrk(N, eBottomLayer, 0.0762, 40.4317, 10.0892, 40.4469, 10.0170);
            FanTrk(N, eBottomLayer, 0.0762, 40.4469, 10.0170, 40.4732, 9.9480);
            FanTrk(N, eBottomLayer, 0.0762, 40.4732, 9.9480, 40.5099, 9.8839);
            FanTrk(N, eBottomLayer, 0.0762, 40.5099, 9.8839, 40.5561, 9.8264);
            FanTrk(N, eBottomLayer, 0.0762, 40.5561, 9.8264, 40.5835, 9.8016);
            FanTrk(N, eBottomLayer, 0.0762, 40.5835, 9.8016, 41.6039, 8.8745);
            FanTrk(N, eBottomLayer, 0.0762, 41.6039, 8.8745, 41.6227, 8.8575);
            FanTrk(N, eBottomLayer, 0.0762, 41.6227, 8.8575, 41.6540, 8.8177);
            FanTrk(N, eBottomLayer, 0.0762, 41.6540, 8.8177, 41.6782, 8.7734);
            FanTrk(N, eBottomLayer, 0.0762, 41.6782, 8.7734, 41.6948, 8.7256);
            FanTrk(N, eBottomLayer, 0.0762, 41.6948, 8.7256, 41.7033, 8.6757);
            FanTrk(N, eBottomLayer, 0.0762, 41.7033, 8.6757, 41.7033, 8.6504);
            FanTrk(N, eBottomLayer, 0.0762, 41.7033, 8.6504, 41.7049, 7.4996);
            FanTrk(N, eBottomLayer, 0.0762, 41.7049, 7.4996, 41.7049, 7.4740);
            FanTrk(N, eBottomLayer, 0.0762, 41.7049, 7.4740, 41.7138, 7.4235);
            FanTrk(N, eBottomLayer, 0.0762, 41.7138, 7.4235, 41.7313, 7.3754);
            FanTrk(N, eBottomLayer, 0.0762, 41.7313, 7.3754, 41.7568, 7.3309);
            FanTrk(N, eBottomLayer, 0.0762, 41.7568, 7.3309, 41.7896, 7.2916);
            FanTrk(N, eBottomLayer, 0.0762, 41.7896, 7.2916, 41.8286, 7.2584);
            FanTrk(N, eBottomLayer, 0.0762, 41.8286, 7.2584, 41.8507, 7.2455);
            FanTrk(N, eBottomLayer, 0.0762, 41.8507, 7.2455, 45.8500, 4.9000);
        End;
        N := FanNet('BS0');
        If N = Nil Then Missing := Missing + ' BS0' Else
        Begin
            FanVia(N, 40.2000, 7.5500);
            FanVia(N, 23.5500, 7.0500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 7.6500, 40.9000, 7.5600);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 7.5600, 40.5000, 7.5600);
            FanTrk(N, eTopLayer, 0.0762, 40.5000, 7.5600, 40.2000, 7.5500);
            FanTrk(N, eMidLayer1, 0.1250, 40.2000, 7.5500, 39.8750, 7.4000);
            FanTrk(N, eMidLayer1, 0.1250, 39.8750, 7.4000, 37.9000, 7.4000);
            FanTrk(N, eMidLayer1, 0.1250, 37.9000, 7.4000, 35.8000, 9.5000);
            FanTrk(N, eMidLayer1, 0.1250, 35.8000, 9.5000, 27.2000, 9.5000);
            FanTrk(N, eMidLayer1, 0.1250, 27.2000, 9.5000, 24.2500, 8.4500);
            FanTrk(N, eMidLayer1, 0.1250, 24.2500, 8.4500, 23.5500, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 23.5500, 7.0500, 23.5499, 6.1701);
        End;
        N := FanNet('BS1');
        If N = Nil Then Missing := Missing + ' BS1' Else
        Begin
            FanVia(N, 39.7500, 8.2500);
            FanVia(N, 22.7500, 7.0500);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 8.4000, 41.7000, 8.3300);
            FanTrk(N, eTopLayer, 0.0762, 41.7000, 8.3300, 41.4000, 8.3300);
            FanTrk(N, eTopLayer, 0.0762, 41.4000, 8.3300, 40.9000, 8.3800);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 8.3800, 40.5000, 8.3800);
            FanTrk(N, eTopLayer, 0.0762, 40.5000, 8.3800, 40.0000, 8.4500);
            FanTrk(N, eTopLayer, 0.0762, 40.0000, 8.4500, 39.7500, 8.2500);
            FanTrk(N, eMidLayer2, 0.1250, 39.7500, 8.2500, 39.5250, 7.9500);
            FanTrk(N, eMidLayer2, 0.1250, 39.5250, 7.9500, 38.2000, 7.9750);
            FanTrk(N, eMidLayer2, 0.1250, 38.2000, 7.9750, 36.4500, 9.5750);
            FanTrk(N, eMidLayer2, 0.1250, 36.4500, 9.5750, 36.0000, 9.9500);
            FanTrk(N, eMidLayer2, 0.1250, 36.0000, 9.9500, 31.1500, 10.0000);
            FanTrk(N, eMidLayer2, 0.1250, 31.1500, 10.0000, 27.2000, 9.5000);
            FanTrk(N, eMidLayer2, 0.1250, 27.2000, 9.5000, 23.4500, 8.4500);
            FanTrk(N, eMidLayer2, 0.1250, 23.4500, 8.4500, 22.7500, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 22.7500, 7.0500, 22.7500, 6.1701);
        End;
        N := FanNet('CAS#');
        If N = Nil Then Missing := Missing + ' CAS#' Else
        Begin
            FanVia(N, 39.8000, 4.4000);
            FanVia(N, 26.3500, 6.9750);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 7.4000, 42.9000, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 42.9000, 6.5500, 42.4000, 6.0500);
            FanTrk(N, eTopLayer, 0.0762, 42.4000, 6.0500, 39.8000, 4.4000);
            FanTrk(N, eMidLayer2, 0.1250, 39.8000, 4.4000, 39.2500, 4.7500);
            FanTrk(N, eMidLayer2, 0.1250, 39.2500, 4.7500, 27.5750, 5.5000);
            FanTrk(N, eMidLayer2, 0.1250, 27.5750, 5.5000, 26.3500, 6.7250);
            FanTrk(N, eMidLayer2, 0.1250, 26.3500, 6.7250, 26.3500, 6.9750);
            FanTrk(N, eBottomLayer, 0.1250, 26.3500, 6.9750, 25.9499, 6.1701);
        End;
        N := FanNet('CKE');
        If N = Nil Then Missing := Missing + ' CKE' Else
        Begin
            FanVia(N, 38.5000, 13.1500);
            FanVia(N, 26.8500, 15.6000);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 11.1500, 41.5000, 11.1300);
            FanTrk(N, eTopLayer, 0.0762, 41.5000, 11.1300, 40.9000, 11.1300);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 11.1300, 39.4790, 11.1300);
            FanTrk(N, eTopLayer, 0.0762, 39.4790, 11.1300, 39.4790, 13.1500);
            FanTrk(N, eTopLayer, 0.0762, 39.4790, 13.1500, 38.5000, 13.1500);
            FanTrk(N, eMidLayer1, 0.1250, 38.5000, 13.1500, 26.8500, 15.6000);
            FanTrk(N, eBottomLayer, 0.1250, 26.8500, 15.6000, 25.5750, 16.8500);
            FanTrk(N, eBottomLayer, 0.1250, 25.5750, 16.8500, 25.1501, 17.5300);
        End;
        N := FanNet('D0');
        If N = Nil Then Missing := Missing + ' D0' Else
        Begin
            FanVia(N, 45.2500, 4.4000);
            FanVia(N, 38.0250, 7.0500);
            FanTrk(N, eTopLayer, 0.0762, 45.1501, 7.1875, 45.1500, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 45.1500, 6.5500, 45.2500, 4.4000);
            FanTrk(N, eMidLayer2, 0.1250, 45.2500, 4.4000, 44.9250, 4.7500);
            FanTrk(N, eMidLayer2, 0.1250, 44.9250, 4.7500, 41.7000, 5.7500);
            FanTrk(N, eMidLayer2, 0.1250, 41.7000, 5.7500, 39.0000, 6.0750);
            FanTrk(N, eMidLayer2, 0.1250, 39.0000, 6.0750, 38.0250, 7.0500);
            FanTrk(N, eBottomLayer, 0.1250, 38.0250, 7.0500, 37.9499, 6.1701);
        End;
        N := FanNet('D1');
        If N = Nil Then Missing := Missing + ' D1' Else
        Begin
            FanVia(N, 44.3000, 4.4000);
            FanVia(N, 36.7500, 7.0250);
            FanTrk(N, eTopLayer, 0.0762, 44.6501, 7.1875, 44.6500, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 44.6500, 6.5500, 44.3000, 4.4000);
            FanTrk(N, eMidLayer2, 0.1250, 44.3000, 4.4000, 43.9750, 4.7500);
            FanTrk(N, eMidLayer2, 0.1250, 43.9750, 4.7500, 41.6750, 5.5000);
            FanTrk(N, eMidLayer2, 0.1250, 41.6750, 5.5000, 37.4750, 6.0250);
            FanTrk(N, eMidLayer2, 0.1250, 37.4750, 6.0250, 36.7500, 6.7500);
            FanTrk(N, eMidLayer2, 0.1250, 36.7500, 6.7500, 36.7500, 7.0250);
            FanTrk(N, eBottomLayer, 0.1250, 36.7500, 7.0250, 36.3500, 6.1701);
        End;
        N := FanNet('D10');
        If N = Nil Then Missing := Missing + ' D10' Else
        Begin
            FanVia(N, 38.5000, 14.5000);
            FanVia(N, 31.6500, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 12.1500, 41.2000, 12.1400);
            FanTrk(N, eTopLayer, 0.0762, 41.2000, 12.1400, 40.9500, 12.2050);
            FanTrk(N, eTopLayer, 0.0762, 40.9500, 12.2050, 40.9000, 12.2100);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 12.2100, 39.9785, 12.2100);
            FanTrk(N, eTopLayer, 0.0762, 39.9785, 12.2100, 39.9785, 14.5000);
            FanTrk(N, eTopLayer, 0.0762, 39.9785, 14.5000, 38.5000, 14.5000);
            FanTrk(N, eMidLayer1, 0.1250, 38.5000, 14.5000, 32.2750, 16.0250);
            FanTrk(N, eMidLayer1, 0.1250, 32.2750, 16.0250, 31.6500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 31.6500, 16.6500, 31.5501, 17.5300);
        End;
        N := FanNet('D11');
        If N = Nil Then Missing := Missing + ' D11' Else
        Begin
            FanVia(N, 38.5000, 14.9500);
            FanVia(N, 33.2500, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 12.4000, 41.6000, 12.3300);
            FanTrk(N, eTopLayer, 0.0762, 41.6000, 12.3300, 41.2000, 12.3300);
            FanTrk(N, eTopLayer, 0.0762, 41.2000, 12.3300, 40.9500, 12.3800);
            FanTrk(N, eTopLayer, 0.0762, 40.9500, 12.3800, 40.1450, 12.3800);
            FanTrk(N, eTopLayer, 0.0762, 40.1450, 12.3800, 40.1450, 14.9500);
            FanTrk(N, eTopLayer, 0.0762, 40.1450, 14.9500, 38.5000, 14.9500);
            FanTrk(N, eMidLayer1, 0.1250, 38.5000, 14.9500, 33.8750, 16.0250);
            FanTrk(N, eMidLayer1, 0.1250, 33.8750, 16.0250, 33.2500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 33.2500, 16.6500, 33.1501, 17.5300);
        End;
        N := FanNet('D12');
        If N = Nil Then Missing := Missing + ' D12' Else
        Begin
            FanVia(N, 34.0250, 16.6500);
            FanTrk(N, eMidLayer2, 0.1250, 43.4001, 12.8999, 43.2250, 13.0000);
            FanTrk(N, eMidLayer2, 0.1250, 43.2250, 13.0000, 42.6000, 13.6250);
            FanTrk(N, eMidLayer2, 0.1250, 42.6000, 13.6250, 42.6000, 14.9250);
            FanTrk(N, eMidLayer2, 0.1250, 42.6000, 14.9250, 42.5750, 14.9500);
            FanTrk(N, eMidLayer2, 0.1250, 42.5750, 14.9500, 40.9000, 15.1000);
            FanTrk(N, eMidLayer2, 0.1250, 40.9000, 15.1000, 37.2500, 16.0250);
            FanTrk(N, eMidLayer2, 0.1250, 37.2500, 16.0250, 34.6500, 16.0250);
            FanTrk(N, eMidLayer2, 0.1250, 34.6500, 16.0250, 34.0250, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 34.0250, 16.6500, 33.9499, 17.5300);
        End;
        N := FanNet('D13');
        If N = Nil Then Missing := Missing + ' D13' Else
        Begin
            FanVia(N, 40.6000, 12.7500);
            FanVia(N, 35.6250, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 12.8999, 41.3500, 12.9700);
            FanTrk(N, eTopLayer, 0.0762, 41.3500, 12.9700, 41.1500, 12.9700);
            FanTrk(N, eTopLayer, 0.0762, 41.1500, 12.9700, 40.9000, 12.9200);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 12.9200, 40.6000, 12.7500);
            FanTrk(N, eMidLayer1, 0.1250, 40.6000, 12.7500, 38.8500, 14.5000);
            FanTrk(N, eMidLayer1, 0.1250, 38.8500, 14.5000, 38.8500, 15.0500);
            FanTrk(N, eMidLayer1, 0.1250, 38.8500, 15.0500, 38.8000, 15.1500);
            FanTrk(N, eMidLayer1, 0.1250, 38.8000, 15.1500, 38.6500, 15.3000);
            FanTrk(N, eMidLayer1, 0.1250, 38.6500, 15.3000, 36.2750, 16.0250);
            FanTrk(N, eMidLayer1, 0.1250, 36.2750, 16.0250, 35.6250, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 35.6250, 16.6500, 35.5501, 17.5300);
        End;
        N := FanNet('D14');
        If N = Nil Then Missing := Missing + ' D14' Else
        Begin
            FanVia(N, 47.9000, 17.1500);
            FanVia(N, 36.1250, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 48.4001, 16.4000, 48.3250, 16.7250);
            FanTrk(N, eTopLayer, 0.0762, 48.3250, 16.7250, 47.9000, 17.1500);
            FanTrk(N, eMidLayer2, 0.1250, 47.9000, 17.1500, 38.0000, 17.2500);
            FanTrk(N, eMidLayer2, 0.1250, 38.0000, 17.2500, 36.7250, 17.2500);
            FanTrk(N, eMidLayer2, 0.1250, 36.7250, 17.2500, 36.1250, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 36.1250, 16.6500, 36.3500, 17.5300);
        End;
        N := FanNet('D15');
        If N = Nil Then Missing := Missing + ' D15' Else
        Begin
            FanVia(N, 48.9000, 16.8000);
            FanVia(N, 38.3500, 16.7250);
            FanTrk(N, eTopLayer, 0.0762, 48.9000, 16.4000, 48.9000, 16.8000);
            FanTrk(N, eMidLayer2, 0.1250, 48.9000, 16.8000, 38.3500, 16.7250);
            FanTrk(N, eBottomLayer, 0.1250, 38.3500, 16.7250, 37.9499, 17.5300);
        End;
        N := FanNet('D2');
        If N = Nil Then Missing := Missing + ' D2' Else
        Begin
            FanVia(N, 44.7750, 4.4000);
            FanVia(N, 35.6500, 7.0750);
            FanTrk(N, eTopLayer, 0.0762, 44.9000, 7.4000, 44.9000, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 44.9000, 6.5500, 44.7750, 4.4000);
            FanTrk(N, eMidLayer1, 0.1250, 44.7750, 4.4000, 44.4500, 4.7500);
            FanTrk(N, eMidLayer1, 0.1250, 44.4500, 4.7500, 43.1250, 5.3250);
            FanTrk(N, eMidLayer1, 0.1250, 43.1250, 5.3250, 36.2750, 6.4250);
            FanTrk(N, eMidLayer1, 0.1250, 36.2750, 6.4250, 35.6500, 7.0750);
            FanTrk(N, eBottomLayer, 0.1250, 35.6500, 7.0750, 35.5501, 6.1701);
        End;
        N := FanNet('D3');
        If N = Nil Then Missing := Missing + ' D3' Else
        Begin
            FanVia(N, 43.8250, 4.4000);
            FanVia(N, 33.9750, 8.9250);
            FanTrk(N, eTopLayer, 0.0762, 44.4001, 7.4000, 44.4750, 7.1500);
            FanTrk(N, eTopLayer, 0.0762, 44.4750, 7.1500, 44.4750, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 44.4750, 6.5500, 43.8250, 4.4000);
            FanTrk(N, eMidLayer1, 0.1250, 43.8250, 4.4000, 43.1000, 5.0750);
            FanTrk(N, eMidLayer1, 0.1250, 43.1000, 5.0750, 34.6250, 6.4500);
            FanTrk(N, eMidLayer1, 0.1250, 34.6250, 6.4500, 33.9750, 8.9250);
            FanTrk(N, eBottomLayer, 0.1250, 33.9750, 8.9250, 33.9499, 6.1701);
        End;
        N := FanNet('D4');
        If N = Nil Then Missing := Missing + ' D4' Else
        Begin
            FanVia(N, 33.3250, 8.9500);
            FanTrk(N, eMidLayer2, 0.1250, 43.9000, 8.8999, 43.7000, 7.3250);
            FanTrk(N, eMidLayer2, 0.1250, 43.7000, 7.3250, 43.6750, 7.3000);
            FanTrk(N, eMidLayer2, 0.1250, 43.6750, 7.3000, 40.9750, 7.3000);
            FanTrk(N, eMidLayer2, 0.1250, 40.9750, 7.3000, 40.5750, 6.9000);
            FanTrk(N, eMidLayer2, 0.1250, 40.5750, 6.9000, 38.6750, 6.9000);
            FanTrk(N, eMidLayer2, 0.1250, 38.6750, 6.9000, 38.1750, 7.3750);
            FanTrk(N, eMidLayer2, 0.1250, 38.1750, 7.3750, 35.8000, 9.5000);
            FanTrk(N, eMidLayer2, 0.1250, 35.8000, 9.5000, 33.8750, 9.5000);
            FanTrk(N, eMidLayer2, 0.1250, 33.8750, 9.5000, 33.3250, 9.5000);
            FanTrk(N, eMidLayer2, 0.1250, 33.3250, 9.5000, 33.3250, 8.9500);
            FanTrk(N, eBottomLayer, 0.1250, 33.3250, 8.9500, 33.1501, 6.1701);
        End;
        N := FanNet('D5');
        If N = Nil Then Missing := Missing + ' D5' Else
        Begin
            FanVia(N, 43.3250, 4.4000);
            FanVia(N, 31.5500, 8.9500);
            FanTrk(N, eTopLayer, 0.0762, 43.9000, 7.4000, 43.8250, 7.1500);
            FanTrk(N, eTopLayer, 0.0762, 43.8250, 7.1500, 43.8250, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 43.8250, 6.5500, 43.3250, 4.4000);
            FanTrk(N, eMidLayer2, 0.1250, 43.3250, 4.4000, 43.0000, 4.7500);
            FanTrk(N, eMidLayer2, 0.1250, 43.0000, 4.7500, 41.6500, 5.2500);
            FanTrk(N, eMidLayer2, 0.1250, 41.6500, 5.2500, 32.2500, 6.4500);
            FanTrk(N, eMidLayer2, 0.1250, 32.2500, 6.4500, 31.5500, 8.9500);
            FanTrk(N, eBottomLayer, 0.1250, 31.5500, 8.9500, 31.5501, 6.1701);
        End;
        N := FanNet('D6');
        If N = Nil Then Missing := Missing + ' D6' Else
        Begin
            FanVia(N, 42.8500, 4.4000);
            FanVia(N, 30.9750, 8.9250);
            FanTrk(N, eTopLayer, 0.0762, 43.6501, 7.1875, 43.6500, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 43.6500, 6.5500, 42.8500, 4.4000);
            FanTrk(N, eMidLayer1, 0.1250, 42.8500, 4.4000, 42.5250, 4.7500);
            FanTrk(N, eMidLayer1, 0.1250, 42.5250, 4.7500, 41.5000, 5.0250);
            FanTrk(N, eMidLayer1, 0.1250, 41.5000, 5.0250, 31.4250, 6.4500);
            FanTrk(N, eMidLayer1, 0.1250, 31.4250, 6.4500, 30.9750, 8.9250);
            FanTrk(N, eBottomLayer, 0.1250, 30.9750, 8.9250, 30.7500, 6.1701);
        End;
        N := FanNet('D7');
        If N = Nil Then Missing := Missing + ' D7' Else
        Begin
            FanVia(N, 29.3250, 8.9500);
            FanTrk(N, eMidLayer2, 0.1250, 43.4001, 8.8999, 41.0000, 7.5500);
            FanTrk(N, eMidLayer2, 0.1250, 41.0000, 7.5500, 40.8250, 7.5500);
            FanTrk(N, eMidLayer2, 0.1250, 40.8250, 7.5500, 40.4750, 7.2000);
            FanTrk(N, eMidLayer2, 0.1250, 40.4750, 7.2000, 38.7000, 7.2000);
            FanTrk(N, eMidLayer2, 0.1250, 38.7000, 7.2000, 36.8250, 8.9250);
            FanTrk(N, eMidLayer2, 0.1250, 36.8250, 8.9250, 35.9000, 9.7250);
            FanTrk(N, eMidLayer2, 0.1250, 35.9000, 9.7250, 33.3000, 9.7500);
            FanTrk(N, eMidLayer2, 0.1250, 33.3000, 9.7500, 29.8750, 9.5000);
            FanTrk(N, eMidLayer2, 0.1250, 29.8750, 9.5000, 29.3250, 9.5000);
            FanTrk(N, eMidLayer2, 0.1250, 29.3250, 9.5000, 29.3250, 8.9500);
            FanTrk(N, eBottomLayer, 0.1250, 29.3250, 8.9500, 29.1501, 6.1701);
        End;
        N := FanNet('D8');
        If N = Nil Then Missing := Missing + ' D8' Else
        Begin
            FanVia(N, 38.5000, 13.6000);
            FanVia(N, 29.2500, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 11.4000, 41.5000, 11.3600);
            FanTrk(N, eTopLayer, 0.0762, 41.5000, 11.3600, 40.9000, 11.3600);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 11.3600, 39.6455, 11.3600);
            FanTrk(N, eTopLayer, 0.0762, 39.6455, 11.3600, 39.6455, 13.6000);
            FanTrk(N, eTopLayer, 0.0762, 39.6455, 13.6000, 38.5000, 13.6000);
            FanTrk(N, eMidLayer2, 0.1250, 38.5000, 13.6000, 29.8750, 16.0250);
            FanTrk(N, eMidLayer2, 0.1250, 29.8750, 16.0250, 29.2500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 29.2500, 16.6500, 29.1501, 17.5300);
        End;
        N := FanNet('D9');
        If N = Nil Then Missing := Missing + ' D9' Else
        Begin
            FanVia(N, 30.8250, 16.6500);
            FanTrk(N, eMidLayer2, 0.1250, 43.4001, 12.4000, 42.4250, 12.6000);
            FanTrk(N, eMidLayer2, 0.1250, 42.4250, 12.6000, 41.7500, 13.2750);
            FanTrk(N, eMidLayer2, 0.1250, 41.7500, 13.2750, 41.7500, 14.5000);
            FanTrk(N, eMidLayer2, 0.1250, 41.7500, 14.5000, 41.6000, 14.7000);
            FanTrk(N, eMidLayer2, 0.1250, 41.6000, 14.7000, 41.5000, 14.7500);
            FanTrk(N, eMidLayer2, 0.1250, 41.5000, 14.7500, 38.6000, 15.3000);
            FanTrk(N, eMidLayer2, 0.1250, 38.6000, 15.3000, 31.8750, 15.7750);
            FanTrk(N, eMidLayer2, 0.1250, 31.8750, 15.7750, 31.4500, 16.0250);
            FanTrk(N, eMidLayer2, 0.1250, 31.4500, 16.0250, 30.8250, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 30.8250, 16.6500, 30.7500, 17.5300);
        End;
        N := FanNet('LDQM');
        If N = Nil Then Missing := Missing + ' LDQM' Else
        Begin
            FanVia(N, 42.3750, 4.4000);
            FanVia(N, 27.3000, 7.4000);
            FanTrk(N, eTopLayer, 0.0762, 43.4001, 7.4000, 43.4000, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 43.4000, 6.5500, 42.3750, 4.4000);
            FanTrk(N, eMidLayer2, 0.1250, 42.3750, 4.4000, 42.0500, 4.7500);
            FanTrk(N, eMidLayer2, 0.1250, 42.0500, 4.7500, 41.6250, 5.0000);
            FanTrk(N, eMidLayer2, 0.1250, 41.6250, 5.0000, 29.0500, 5.6500);
            FanTrk(N, eMidLayer2, 0.1250, 29.0500, 5.6500, 27.3000, 7.4000);
            FanTrk(N, eBottomLayer, 0.1250, 27.3000, 7.4000, 27.5000, 7.0250);
            FanTrk(N, eBottomLayer, 0.1250, 27.5000, 7.0250, 27.5501, 6.1701);
        End;
        N := FanNet('RAS#');
        If N = Nil Then Missing := Missing + ' RAS#' Else
        Begin
            FanVia(N, 39.1500, 4.4000);
            FanVia(N, 25.5500, 6.9750);
            FanTrk(N, eTopLayer, 0.0762, 42.6501, 7.1875, 42.6500, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 42.6500, 6.5500, 42.3250, 6.2250);
            FanTrk(N, eTopLayer, 0.0762, 42.3250, 6.2250, 39.1500, 4.4000);
            FanTrk(N, eMidLayer1, 0.1250, 39.1500, 4.4000, 38.6000, 4.7500);
            FanTrk(N, eMidLayer1, 0.1250, 38.6000, 4.7500, 26.9500, 5.3500);
            FanTrk(N, eMidLayer1, 0.1250, 26.9500, 5.3500, 25.5500, 6.7500);
            FanTrk(N, eMidLayer1, 0.1250, 25.5500, 6.7500, 25.5500, 6.9750);
            FanTrk(N, eBottomLayer, 0.1250, 25.5500, 6.9750, 25.1501, 6.1701);
        End;
        N := FanNet('SDRAM-CLK');
        If N = Nil Then Missing := Missing + ' SDRAM-CLK' Else
        Begin
            FanVia(N, 38.8500, 12.7000);
            FanVia(N, 27.1250, 16.1000);
            FanTrk(N, eTopLayer, 0.0762, 41.9000, 10.8999, 41.5000, 10.9000);
            FanTrk(N, eTopLayer, 0.0762, 41.5000, 10.9000, 40.9000, 10.9000);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 10.9000, 39.3125, 10.9000);
            FanTrk(N, eTopLayer, 0.0762, 39.3125, 10.9000, 39.3125, 12.7000);
            FanTrk(N, eTopLayer, 0.0762, 39.3125, 12.7000, 38.8500, 12.7000);
            FanTrk(N, eMidLayer2, 0.1250, 38.8500, 12.7000, 34.8250, 12.7000);
            FanTrk(N, eMidLayer2, 0.1250, 34.8250, 12.7000, 27.1250, 16.1000);
            FanTrk(N, eBottomLayer, 0.1250, 27.1250, 16.1000, 26.3750, 16.8500);
            FanTrk(N, eBottomLayer, 0.1250, 26.3750, 16.8500, 25.9499, 17.5300);
        End;
        N := FanNet('SDRAM-CS#');
        If N = Nil Then Missing := Missing + ' SDRAM-CS#' Else
        Begin
            FanVia(N, 38.5000, 4.4000);
            FanVia(N, 24.7500, 6.9750);
            FanTrk(N, eTopLayer, 0.0762, 42.4001, 7.4000, 42.4000, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 42.4000, 6.5500, 38.5000, 4.4000);
            FanTrk(N, eMidLayer2, 0.1250, 38.5000, 4.4000, 26.1000, 5.3750);
            FanTrk(N, eMidLayer2, 0.1250, 26.1000, 5.3750, 24.7500, 6.7250);
            FanTrk(N, eMidLayer2, 0.1250, 24.7500, 6.7250, 24.7500, 6.9750);
            FanTrk(N, eBottomLayer, 0.1250, 24.7500, 6.9750, 24.3500, 6.1701);
        End;
        N := FanNet('UDQM');
        If N = Nil Then Missing := Missing + ' UDQM' Else
        Begin
            FanVia(N, 38.5000, 14.0500);
            FanVia(N, 27.0500, 16.6500);
            FanTrk(N, eTopLayer, 0.0762, 41.6875, 11.6500, 41.5000, 11.5900);
            FanTrk(N, eTopLayer, 0.0762, 41.5000, 11.5900, 40.9000, 11.5900);
            FanTrk(N, eTopLayer, 0.0762, 40.9000, 11.5900, 39.8120, 11.5900);
            FanTrk(N, eTopLayer, 0.0762, 39.8120, 11.5900, 39.8120, 14.0500);
            FanTrk(N, eTopLayer, 0.0762, 39.8120, 14.0500, 38.5000, 14.0500);
            FanTrk(N, eMidLayer1, 0.1250, 38.5000, 14.0500, 28.8500, 16.0250);
            FanTrk(N, eMidLayer1, 0.1250, 28.8500, 16.0250, 27.0500, 16.6500);
            FanTrk(N, eBottomLayer, 0.1250, 27.0500, 16.6500, 26.7500, 17.5300);
        End;
        N := FanNet('WE#');
        If N = Nil Then Missing := Missing + ' WE#' Else
        Begin
            FanVia(N, 41.9000, 4.4000);
            FanVia(N, 27.1500, 6.9750);
            FanTrk(N, eTopLayer, 0.0762, 43.1501, 7.1875, 43.1500, 6.5500);
            FanTrk(N, eTopLayer, 0.0762, 43.1500, 6.5500, 41.9000, 4.4000);
            FanTrk(N, eMidLayer1, 0.1250, 41.9000, 4.4000, 41.5500, 4.3000);
            FanTrk(N, eMidLayer1, 0.1250, 41.5500, 4.3000, 40.1750, 4.5250);
            FanTrk(N, eMidLayer1, 0.1250, 40.1750, 4.5250, 39.9500, 4.7250);
            FanTrk(N, eMidLayer1, 0.1250, 39.9500, 4.7250, 38.6250, 5.0000);
            FanTrk(N, eMidLayer1, 0.1250, 38.6250, 5.0000, 28.3500, 5.5250);
            FanTrk(N, eMidLayer1, 0.1250, 28.3500, 5.5250, 27.1500, 6.7250);
            FanTrk(N, eMidLayer1, 0.1250, 27.1500, 6.7250, 27.1500, 6.9750);
            FanTrk(N, eBottomLayer, 0.1250, 27.1500, 6.9750, 26.7500, 6.1701);
        End;
    Finally
        PCBServer.PostProcess;
    End;
    Kill.Free;
    Brd.ViewManager_FullUpdate;
    If Missing <> '' Then
        ShowMessage('Zulu A7 - CoRoute placed, but these nets were NOT found:' + Missing + #13#10 + 'Their primitives were skipped. Do not save until this is understood.')
    Else
        ShowMessage('Zulu A7 - CoRoute placed: removed 2, added 75 vias and 508 tracks.' + #13#10 + 'Now Tools > Design Rule Check > Run, then Ctrl+S if it is clean.');
End;


Procedure RemoveCoRoute;
Var
    N    : IPCB_Net;
    V    : IPCB_Via;
    T    : IPCB_Track;
    It   : IPCB_BoardIterator;
    Kill : TInterfaceList;
    i    : Integer;
    x, y, x2, y2 : Double;
    nm   : String;
    Missing : String;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    Missing := '';
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        nm := ''; If V.Net <> Nil Then nm := V.Net.Name;
        x := CoordToMMs(V.X); y := CoordToMMs(V.Y);
        If ((nm = 'AIN15_N') And (Abs(x - 40.6000) < 0.001) And (Abs(y - 14.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'AIN16_P') And (Abs(x - 40.4500) < 0.001) And (Abs(y - 13.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'AIN16_N') And (Abs(x - 41.3000) < 0.001) And (Abs(y - 12.6650) < 0.001)) Then Kill.Add(V);
        If ((nm = 'AIN15_P') And (Abs(x - 41.5000) < 0.001) And (Abs(y - 4.6600) < 0.001)) Then Kill.Add(V);
        If ((nm = 'AIN15_P') And (Abs(x - 39.6500) < 0.001) And (Abs(y - 3.8500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'AIN16_N') And (Abs(x - 46.1500) < 0.001) And (Abs(y - 3.3500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'AIN16_N') And (Abs(x - 43.3000) < 0.001) And (Abs(y - 3.2000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'SDRAM-CS#') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'SDRAM-CS#') And (Abs(x - 24.7500) < 0.001) And (Abs(y - 6.9750) < 0.001)) Then Kill.Add(V);
        If ((nm = 'RAS#') And (Abs(x - 39.1500) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'RAS#') And (Abs(x - 25.5500) < 0.001) And (Abs(y - 6.9750) < 0.001)) Then Kill.Add(V);
        If ((nm = 'CAS#') And (Abs(x - 39.8000) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'CAS#') And (Abs(x - 26.3500) < 0.001) And (Abs(y - 6.9750) < 0.001)) Then Kill.Add(V);
        If ((nm = 'WE#') And (Abs(x - 41.9000) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'WE#') And (Abs(x - 27.1500) < 0.001) And (Abs(y - 6.9750) < 0.001)) Then Kill.Add(V);
        If ((nm = 'LDQM') And (Abs(x - 42.3750) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'LDQM') And (Abs(x - 27.3000) < 0.001) And (Abs(y - 7.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D6') And (Abs(x - 42.8500) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D6') And (Abs(x - 30.9750) < 0.001) And (Abs(y - 8.9250) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D5') And (Abs(x - 43.3250) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D5') And (Abs(x - 31.5500) < 0.001) And (Abs(y - 8.9500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D3') And (Abs(x - 43.8250) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D3') And (Abs(x - 33.9750) < 0.001) And (Abs(y - 8.9250) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D1') And (Abs(x - 44.3000) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D1') And (Abs(x - 36.7500) < 0.001) And (Abs(y - 7.0250) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D2') And (Abs(x - 44.7750) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D2') And (Abs(x - 35.6500) < 0.001) And (Abs(y - 7.0750) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D0') And (Abs(x - 45.2500) < 0.001) And (Abs(y - 4.4000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D0') And (Abs(x - 38.0250) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D14') And (Abs(x - 47.9000) < 0.001) And (Abs(y - 17.1500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D14') And (Abs(x - 36.1250) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D15') And (Abs(x - 48.9000) < 0.001) And (Abs(y - 16.8000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D15') And (Abs(x - 38.3500) < 0.001) And (Abs(y - 16.7250) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D4') And (Abs(x - 33.3250) < 0.001) And (Abs(y - 8.9500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D7') And (Abs(x - 29.3250) < 0.001) And (Abs(y - 8.9500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'BS0') And (Abs(x - 40.2000) < 0.001) And (Abs(y - 7.5500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'BS0') And (Abs(x - 23.5500) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'BS1') And (Abs(x - 39.7500) < 0.001) And (Abs(y - 8.2500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'BS1') And (Abs(x - 22.7500) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A0') And (Abs(x - 40.2500) < 0.001) And (Abs(y - 8.1000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A0') And (Abs(x - 21.1500) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A10') And (Abs(x - 21.9500) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A1') And (Abs(x - 20.3500) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A3') And (Abs(x - 39.1500) < 0.001) And (Abs(y - 8.7000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A3') And (Abs(x - 18.7500) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A2') And (Abs(x - 38.6000) < 0.001) And (Abs(y - 8.9500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A2') And (Abs(x - 19.5500) < 0.001) And (Abs(y - 7.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D9') And (Abs(x - 30.8250) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D12') And (Abs(x - 34.0250) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D13') And (Abs(x - 40.6000) < 0.001) And (Abs(y - 12.7500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D13') And (Abs(x - 35.6250) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D11') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 14.9500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D11') And (Abs(x - 33.2500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D10') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 14.5000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D10') And (Abs(x - 31.6500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'UDQM') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 14.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'UDQM') And (Abs(x - 27.0500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D8') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 13.6000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'D8') And (Abs(x - 29.2500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'CKE') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 13.1500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'CKE') And (Abs(x - 26.8500) < 0.001) And (Abs(y - 15.6000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'SDRAM-CLK') And (Abs(x - 38.8500) < 0.001) And (Abs(y - 12.7000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'SDRAM-CLK') And (Abs(x - 27.1250) < 0.001) And (Abs(y - 16.1000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A9') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 11.9500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A9') And (Abs(x - 21.8250) < 0.001) And (Abs(y - 16.2500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A11') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 11.5000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A11') And (Abs(x - 23.3500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A7') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 11.0500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A7') And (Abs(x - 21.1000) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A5') And (Abs(x - 38.5000) < 0.001) And (Abs(y - 10.6000) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A5') And (Abs(x - 19.5500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A12') And (Abs(x - 23.3500) < 0.001) And (Abs(y - 16.1750) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A8') And (Abs(x - 21.6250) < 0.001) And (Abs(y - 16.6750) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A6') And (Abs(x - 20.3500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        If ((nm = 'A4') And (Abs(x - 18.7500) < 0.001) And (Abs(y - 16.6500) < 0.001)) Then Kill.Add(V);
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        nm := ''; If T.Net <> Nil Then nm := T.Net.Name;
        x := CoordToMMs(T.X1); y := CoordToMMs(T.Y1); x2 := CoordToMMs(T.X2); y2 := CoordToMMs(T.Y2);
        If ((nm = 'AIN15_N') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 13.6500) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 13.7200) < 0.001)) Or ((Abs(x - 41.3500) < 0.001) And (Abs(y - 13.7200) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 13.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eTopLayer) And (((Abs(x - 41.3500) < 0.001) And (Abs(y - 13.7200) < 0.001) And (Abs(x2 - 40.6000) < 0.001) And (Abs(y2 - 14.0500) < 0.001)) Or ((Abs(x - 40.6000) < 0.001) And (Abs(y - 14.0500) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 13.7200) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 13.1500) < 0.001) And (Abs(x2 - 41.2000) < 0.001) And (Abs(y2 - 13.1500) < 0.001)) Or ((Abs(x - 41.2000) < 0.001) And (Abs(y - 13.1500) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 13.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eTopLayer) And (((Abs(x - 41.2000) < 0.001) And (Abs(y - 13.1500) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 13.0900) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 13.0900) < 0.001) And (Abs(x2 - 41.2000) < 0.001) And (Abs(y2 - 13.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 13.0900) < 0.001) And (Abs(x2 - 40.6000) < 0.001) And (Abs(y2 - 13.0900) < 0.001)) Or ((Abs(x - 40.6000) < 0.001) And (Abs(y - 13.0900) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 13.0900) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eTopLayer) And (((Abs(x - 40.6000) < 0.001) And (Abs(y - 13.0900) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 13.4000) < 0.001)) Or ((Abs(x - 40.4500) < 0.001) And (Abs(y - 13.4000) < 0.001) And (Abs(x2 - 40.6000) < 0.001) And (Abs(y2 - 13.0900) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 12.6500) < 0.001) And (Abs(x2 - 41.3000) < 0.001) And (Abs(y2 - 12.6650) < 0.001)) Or ((Abs(x - 41.3000) < 0.001) And (Abs(y - 12.6650) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 12.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4500) < 0.001) And (Abs(y - 4.6000) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 4.3000) < 0.001)) Or ((Abs(x - 40.4500) < 0.001) And (Abs(y - 4.3000) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 4.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4500) < 0.001) And (Abs(y - 4.3000) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 3.6000) < 0.001)) Or ((Abs(x - 40.4500) < 0.001) And (Abs(y - 3.6000) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 4.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4500) < 0.001) And (Abs(y - 3.6000) < 0.001) And (Abs(x2 - 40.3500) < 0.001) And (Abs(y2 - 3.0500) < 0.001)) Or ((Abs(x - 40.3500) < 0.001) And (Abs(y - 3.0500) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 3.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4500) < 0.001) And (Abs(y - 4.3000) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 4.3000) < 0.001)) Or ((Abs(x - 41.3500) < 0.001) And (Abs(y - 4.3000) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 4.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3500) < 0.001) And (Abs(y - 4.3000) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 3.9500) < 0.001)) Or ((Abs(x - 41.3500) < 0.001) And (Abs(y - 3.9500) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 4.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 4.6600) < 0.001) And (Abs(x2 - 41.6200) < 0.001) And (Abs(y2 - 4.2600) < 0.001)) Or ((Abs(x - 41.6200) < 0.001) And (Abs(y - 4.2600) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 4.6600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.6200) < 0.001) And (Abs(y - 4.2600) < 0.001) And (Abs(x2 - 41.6500) < 0.001) And (Abs(y2 - 4.0500) < 0.001)) Or ((Abs(x - 41.6500) < 0.001) And (Abs(y - 4.0500) < 0.001) And (Abs(x2 - 41.6200) < 0.001) And (Abs(y2 - 4.2600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.6500) < 0.001) And (Abs(y - 4.0500) < 0.001) And (Abs(x2 - 41.6500) < 0.001) And (Abs(y2 - 3.0500) < 0.001)) Or ((Abs(x - 41.6500) < 0.001) And (Abs(y - 3.0500) < 0.001) And (Abs(x2 - 41.6500) < 0.001) And (Abs(y2 - 4.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eTopLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 4.6600) < 0.001) And (Abs(x2 - 39.6500) < 0.001) And (Abs(y2 - 3.8500) < 0.001)) Or ((Abs(x - 39.6500) < 0.001) And (Abs(y - 3.8500) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 4.6600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 39.6500) < 0.001) And (Abs(y - 3.8500) < 0.001) And (Abs(x2 - 40.1500) < 0.001) And (Abs(y2 - 3.9500) < 0.001)) Or ((Abs(x - 40.1500) < 0.001) And (Abs(y - 3.9500) < 0.001) And (Abs(x2 - 39.6500) < 0.001) And (Abs(y2 - 3.8500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 45.8500) < 0.001) And (Abs(y - 4.9000) < 0.001) And (Abs(x2 - 45.8500) < 0.001) And (Abs(y2 - 3.6500) < 0.001)) Or ((Abs(x - 45.8500) < 0.001) And (Abs(y - 3.6500) < 0.001) And (Abs(x2 - 45.8500) < 0.001) And (Abs(y2 - 4.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 45.8500) < 0.001) And (Abs(y - 3.6500) < 0.001) And (Abs(x2 - 45.1500) < 0.001) And (Abs(y2 - 3.6500) < 0.001)) Or ((Abs(x - 45.1500) < 0.001) And (Abs(y - 3.6500) < 0.001) And (Abs(x2 - 45.8500) < 0.001) And (Abs(y2 - 3.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 45.1500) < 0.001) And (Abs(y - 3.6500) < 0.001) And (Abs(x2 - 44.9500) < 0.001) And (Abs(y2 - 3.9500) < 0.001)) Or ((Abs(x - 44.9500) < 0.001) And (Abs(y - 3.9500) < 0.001) And (Abs(x2 - 45.1500) < 0.001) And (Abs(y2 - 3.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 44.9500) < 0.001) And (Abs(y - 3.9500) < 0.001) And (Abs(x2 - 43.9500) < 0.001) And (Abs(y2 - 3.0500) < 0.001)) Or ((Abs(x - 43.9500) < 0.001) And (Abs(y - 3.0500) < 0.001) And (Abs(x2 - 44.9500) < 0.001) And (Abs(y2 - 3.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 46.0160) < 0.001) And (Abs(y - 5.0000) < 0.001) And (Abs(x2 - 46.0200) < 0.001) And (Abs(y2 - 4.6000) < 0.001)) Or ((Abs(x - 46.0200) < 0.001) And (Abs(y - 4.6000) < 0.001) And (Abs(x2 - 46.0160) < 0.001) And (Abs(y2 - 5.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 46.0200) < 0.001) And (Abs(y - 4.6000) < 0.001) And (Abs(x2 - 46.1500) < 0.001) And (Abs(y2 - 3.9500) < 0.001)) Or ((Abs(x - 46.1500) < 0.001) And (Abs(y - 3.9500) < 0.001) And (Abs(x2 - 46.0200) < 0.001) And (Abs(y2 - 4.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 46.1500) < 0.001) And (Abs(y - 3.9500) < 0.001) And (Abs(x2 - 46.1500) < 0.001) And (Abs(y2 - 3.3500) < 0.001)) Or ((Abs(x - 46.1500) < 0.001) And (Abs(y - 3.3500) < 0.001) And (Abs(x2 - 46.1500) < 0.001) And (Abs(y2 - 3.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eTopLayer) And (((Abs(x - 46.1500) < 0.001) And (Abs(y - 3.3500) < 0.001) And (Abs(x2 - 43.3000) < 0.001) And (Abs(y2 - 3.2000) < 0.001)) Or ((Abs(x - 43.3000) < 0.001) And (Abs(y - 3.2000) < 0.001) And (Abs(x2 - 46.1500) < 0.001) And (Abs(y2 - 3.3500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 43.3000) < 0.001) And (Abs(y - 3.2000) < 0.001) And (Abs(x2 - 42.6500) < 0.001) And (Abs(y2 - 3.0500) < 0.001)) Or ((Abs(x - 42.6500) < 0.001) And (Abs(y - 3.0500) < 0.001) And (Abs(x2 - 43.3000) < 0.001) And (Abs(y2 - 3.2000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 13.8999) < 0.001) And (Abs(x2 - 40.4299) < 0.001) And (Abs(y2 - 13.7026) < 0.001)) Or ((Abs(x - 40.4299) < 0.001) And (Abs(y - 13.7026) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 13.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4299) < 0.001) And (Abs(y - 13.7026) < 0.001) And (Abs(x2 - 40.4050) < 0.001) And (Abs(y2 - 13.7010) < 0.001)) Or ((Abs(x - 40.4050) < 0.001) And (Abs(y - 13.7010) < 0.001) And (Abs(x2 - 40.4299) < 0.001) And (Abs(y2 - 13.7026) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4050) < 0.001) And (Abs(y - 13.7010) < 0.001) And (Abs(x2 - 40.3564) < 0.001) And (Abs(y2 - 13.6896) < 0.001)) Or ((Abs(x - 40.3564) < 0.001) And (Abs(y - 13.6896) < 0.001) And (Abs(x2 - 40.4050) < 0.001) And (Abs(y2 - 13.7010) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.3564) < 0.001) And (Abs(y - 13.6896) < 0.001) And (Abs(x2 - 40.3103) < 0.001) And (Abs(y2 - 13.6704) < 0.001)) Or ((Abs(x - 40.3103) < 0.001) And (Abs(y - 13.6704) < 0.001) And (Abs(x2 - 40.3564) < 0.001) And (Abs(y2 - 13.6896) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.3103) < 0.001) And (Abs(y - 13.6704) < 0.001) And (Abs(x2 - 40.2680) < 0.001) And (Abs(y2 - 13.6439) < 0.001)) Or ((Abs(x - 40.2680) < 0.001) And (Abs(y - 13.6439) < 0.001) And (Abs(x2 - 40.3103) < 0.001) And (Abs(y2 - 13.6704) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.2680) < 0.001) And (Abs(y - 13.6439) < 0.001) And (Abs(x2 - 40.2306) < 0.001) And (Abs(y2 - 13.6109) < 0.001)) Or ((Abs(x - 40.2306) < 0.001) And (Abs(y - 13.6109) < 0.001) And (Abs(x2 - 40.2680) < 0.001) And (Abs(y2 - 13.6439) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.2306) < 0.001) And (Abs(y - 13.6109) < 0.001) And (Abs(x2 - 40.1991) < 0.001) And (Abs(y2 - 13.5722) < 0.001)) Or ((Abs(x - 40.1991) < 0.001) And (Abs(y - 13.5722) < 0.001) And (Abs(x2 - 40.2306) < 0.001) And (Abs(y2 - 13.6109) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1991) < 0.001) And (Abs(y - 13.5722) < 0.001) And (Abs(x2 - 40.1743) < 0.001) And (Abs(y2 - 13.5289) < 0.001)) Or ((Abs(x - 40.1743) < 0.001) And (Abs(y - 13.5289) < 0.001) And (Abs(x2 - 40.1991) < 0.001) And (Abs(y2 - 13.5722) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1743) < 0.001) And (Abs(y - 13.5289) < 0.001) And (Abs(x2 - 40.1570) < 0.001) And (Abs(y2 - 13.4821) < 0.001)) Or ((Abs(x - 40.1570) < 0.001) And (Abs(y - 13.4821) < 0.001) And (Abs(x2 - 40.1743) < 0.001) And (Abs(y2 - 13.5289) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1570) < 0.001) And (Abs(y - 13.4821) < 0.001) And (Abs(x2 - 40.1475) < 0.001) And (Abs(y2 - 13.4331) < 0.001)) Or ((Abs(x - 40.1475) < 0.001) And (Abs(y - 13.4331) < 0.001) And (Abs(x2 - 40.1570) < 0.001) And (Abs(y2 - 13.4821) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1475) < 0.001) And (Abs(y - 13.4331) < 0.001) And (Abs(x2 - 40.1468) < 0.001) And (Abs(y2 - 13.4082) < 0.001)) Or ((Abs(x - 40.1468) < 0.001) And (Abs(y - 13.4082) < 0.001) And (Abs(x2 - 40.1475) < 0.001) And (Abs(y2 - 13.4331) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1468) < 0.001) And (Abs(y - 13.4082) < 0.001) And (Abs(x2 - 40.1294) < 0.001) And (Abs(y2 - 12.7627) < 0.001)) Or ((Abs(x - 40.1294) < 0.001) And (Abs(y - 12.7627) < 0.001) And (Abs(x2 - 40.1468) < 0.001) And (Abs(y2 - 13.4082) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1294) < 0.001) And (Abs(y - 12.7627) < 0.001) And (Abs(x2 - 40.1293) < 0.001) And (Abs(y2 - 12.7586) < 0.001)) Or ((Abs(x - 40.1293) < 0.001) And (Abs(y - 12.7586) < 0.001) And (Abs(x2 - 40.1294) < 0.001) And (Abs(y2 - 12.7627) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1293) < 0.001) And (Abs(y - 12.7586) < 0.001) And (Abs(x2 - 40.1293) < 0.001) And (Abs(y2 - 12.7546) < 0.001)) Or ((Abs(x - 40.1293) < 0.001) And (Abs(y - 12.7546) < 0.001) And (Abs(x2 - 40.1293) < 0.001) And (Abs(y2 - 12.7586) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1293) < 0.001) And (Abs(y - 12.7546) < 0.001) And (Abs(x2 - 40.0967) < 0.001) And (Abs(y2 - 9.4029) < 0.001)) Or ((Abs(x - 40.0967) < 0.001) And (Abs(y - 9.4029) < 0.001) And (Abs(x2 - 40.1293) < 0.001) And (Abs(y2 - 12.7546) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.0967) < 0.001) And (Abs(y - 9.4029) < 0.001) And (Abs(x2 - 40.0965) < 0.001) And (Abs(y2 - 9.3773) < 0.001)) Or ((Abs(x - 40.0965) < 0.001) And (Abs(y - 9.3773) < 0.001) And (Abs(x2 - 40.0967) < 0.001) And (Abs(y2 - 9.4029) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.0965) < 0.001) And (Abs(y - 9.3773) < 0.001) And (Abs(x2 - 40.1046) < 0.001) And (Abs(y2 - 9.3267) < 0.001)) Or ((Abs(x - 40.1046) < 0.001) And (Abs(y - 9.3267) < 0.001) And (Abs(x2 - 40.0965) < 0.001) And (Abs(y2 - 9.3773) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1046) < 0.001) And (Abs(y - 9.3267) < 0.001) And (Abs(x2 - 40.1211) < 0.001) And (Abs(y2 - 9.2782) < 0.001)) Or ((Abs(x - 40.1211) < 0.001) And (Abs(y - 9.2782) < 0.001) And (Abs(x2 - 40.1046) < 0.001) And (Abs(y2 - 9.3267) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1211) < 0.001) And (Abs(y - 9.2782) < 0.001) And (Abs(x2 - 40.1455) < 0.001) And (Abs(y2 - 9.2331) < 0.001)) Or ((Abs(x - 40.1455) < 0.001) And (Abs(y - 9.2331) < 0.001) And (Abs(x2 - 40.1211) < 0.001) And (Abs(y2 - 9.2782) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1455) < 0.001) And (Abs(y - 9.2331) < 0.001) And (Abs(x2 - 40.1771) < 0.001) And (Abs(y2 - 9.1927) < 0.001)) Or ((Abs(x - 40.1771) < 0.001) And (Abs(y - 9.1927) < 0.001) And (Abs(x2 - 40.1455) < 0.001) And (Abs(y2 - 9.2331) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1771) < 0.001) And (Abs(y - 9.1927) < 0.001) And (Abs(x2 - 40.1960) < 0.001) And (Abs(y2 - 9.1755) < 0.001)) Or ((Abs(x - 40.1960) < 0.001) And (Abs(y - 9.1755) < 0.001) And (Abs(x2 - 40.1771) < 0.001) And (Abs(y2 - 9.1927) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.1960) < 0.001) And (Abs(y - 9.1755) < 0.001) And (Abs(x2 - 41.2166) < 0.001) And (Abs(y2 - 8.2483) < 0.001)) Or ((Abs(x - 41.2166) < 0.001) And (Abs(y - 8.2483) < 0.001) And (Abs(x2 - 40.1960) < 0.001) And (Abs(y2 - 9.1755) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.2166) < 0.001) And (Abs(y - 8.2483) < 0.001) And (Abs(x2 - 41.2449) < 0.001) And (Abs(y2 - 8.2226) < 0.001)) Or ((Abs(x - 41.2449) < 0.001) And (Abs(y - 8.2226) < 0.001) And (Abs(x2 - 41.2166) < 0.001) And (Abs(y2 - 8.2483) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.2449) < 0.001) And (Abs(y - 8.2226) < 0.001) And (Abs(x2 - 41.2924) < 0.001) And (Abs(y2 - 8.1628) < 0.001)) Or ((Abs(x - 41.2924) < 0.001) And (Abs(y - 8.1628) < 0.001) And (Abs(x2 - 41.2449) < 0.001) And (Abs(y2 - 8.2226) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.2924) < 0.001) And (Abs(y - 8.1628) < 0.001) And (Abs(x2 - 41.3297) < 0.001) And (Abs(y2 - 8.0960) < 0.001)) Or ((Abs(x - 41.3297) < 0.001) And (Abs(y - 8.0960) < 0.001) And (Abs(x2 - 41.2924) < 0.001) And (Abs(y2 - 8.1628) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3297) < 0.001) And (Abs(y - 8.0960) < 0.001) And (Abs(x2 - 41.3557) < 0.001) And (Abs(y2 - 8.0241) < 0.001)) Or ((Abs(x - 41.3557) < 0.001) And (Abs(y - 8.0241) < 0.001) And (Abs(x2 - 41.3297) < 0.001) And (Abs(y2 - 8.0960) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3557) < 0.001) And (Abs(y - 8.0241) < 0.001) And (Abs(x2 - 41.3698) < 0.001) And (Abs(y2 - 7.9489) < 0.001)) Or ((Abs(x - 41.3698) < 0.001) And (Abs(y - 7.9489) < 0.001) And (Abs(x2 - 41.3557) < 0.001) And (Abs(y2 - 8.0241) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3698) < 0.001) And (Abs(y - 7.9489) < 0.001) And (Abs(x2 - 41.3715) < 0.001) And (Abs(y2 - 7.8725) < 0.001)) Or ((Abs(x - 41.3715) < 0.001) And (Abs(y - 7.8725) < 0.001) And (Abs(x2 - 41.3698) < 0.001) And (Abs(y2 - 7.9489) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3715) < 0.001) And (Abs(y - 7.8725) < 0.001) And (Abs(x2 - 41.3609) < 0.001) And (Abs(y2 - 7.7968) < 0.001)) Or ((Abs(x - 41.3609) < 0.001) And (Abs(y - 7.7968) < 0.001) And (Abs(x2 - 41.3715) < 0.001) And (Abs(y2 - 7.8725) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3609) < 0.001) And (Abs(y - 7.7968) < 0.001) And (Abs(x2 - 41.3496) < 0.001) And (Abs(y2 - 7.7603) < 0.001)) Or ((Abs(x - 41.3496) < 0.001) And (Abs(y - 7.7603) < 0.001) And (Abs(x2 - 41.3609) < 0.001) And (Abs(y2 - 7.7968) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3496) < 0.001) And (Abs(y - 7.7603) < 0.001) And (Abs(x2 - 41.1103) < 0.001) And (Abs(y2 - 6.9900) < 0.001)) Or ((Abs(x - 41.1103) < 0.001) And (Abs(y - 6.9900) < 0.001) And (Abs(x2 - 41.3496) < 0.001) And (Abs(y2 - 7.7603) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1103) < 0.001) And (Abs(y - 6.9900) < 0.001) And (Abs(x2 - 41.1031) < 0.001) And (Abs(y2 - 6.9667) < 0.001)) Or ((Abs(x - 41.1031) < 0.001) And (Abs(y - 6.9667) < 0.001) And (Abs(x2 - 41.1103) < 0.001) And (Abs(y2 - 6.9900) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1031) < 0.001) And (Abs(y - 6.9667) < 0.001) And (Abs(x2 - 41.0963) < 0.001) And (Abs(y2 - 6.9184) < 0.001)) Or ((Abs(x - 41.0963) < 0.001) And (Abs(y - 6.9184) < 0.001) And (Abs(x2 - 41.1031) < 0.001) And (Abs(y2 - 6.9667) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.0963) < 0.001) And (Abs(y - 6.9184) < 0.001) And (Abs(x2 - 41.0972) < 0.001) And (Abs(y2 - 6.8696) < 0.001)) Or ((Abs(x - 41.0972) < 0.001) And (Abs(y - 6.8696) < 0.001) And (Abs(x2 - 41.0963) < 0.001) And (Abs(y2 - 6.9184) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.0972) < 0.001) And (Abs(y - 6.8696) < 0.001) And (Abs(x2 - 41.1016) < 0.001) And (Abs(y2 - 6.8456) < 0.001)) Or ((Abs(x - 41.1016) < 0.001) And (Abs(y - 6.8456) < 0.001) And (Abs(x2 - 41.0972) < 0.001) And (Abs(y2 - 6.8696) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1016) < 0.001) And (Abs(y - 6.8456) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 4.6600) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 4.6600) < 0.001) And (Abs(x2 - 41.1016) < 0.001) And (Abs(y2 - 6.8456) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6000) < 0.001) And (Abs(y - 14.0500) < 0.001) And (Abs(x2 - 40.2000) < 0.001) And (Abs(y2 - 14.1000) < 0.001)) Or ((Abs(x - 40.2000) < 0.001) And (Abs(y - 14.1000) < 0.001) And (Abs(x2 - 40.6000) < 0.001) And (Abs(y2 - 14.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.2000) < 0.001) And (Abs(y - 14.1000) < 0.001) And (Abs(x2 - 40.0066) < 0.001) And (Abs(y2 - 13.5582) < 0.001)) Or ((Abs(x - 40.0066) < 0.001) And (Abs(y - 13.5582) < 0.001) And (Abs(x2 - 40.2000) < 0.001) And (Abs(y2 - 14.1000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.0066) < 0.001) And (Abs(y - 13.5582) < 0.001) And (Abs(x2 - 39.9942) < 0.001) And (Abs(y2 - 13.5233) < 0.001)) Or ((Abs(x - 39.9942) < 0.001) And (Abs(y - 13.5233) < 0.001) And (Abs(x2 - 40.0066) < 0.001) And (Abs(y2 - 13.5582) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9942) < 0.001) And (Abs(y - 13.5233) < 0.001) And (Abs(x2 - 39.9805) < 0.001) And (Abs(y2 - 13.4503) < 0.001)) Or ((Abs(x - 39.9805) < 0.001) And (Abs(y - 13.4503) < 0.001) And (Abs(x2 - 39.9942) < 0.001) And (Abs(y2 - 13.5233) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9805) < 0.001) And (Abs(y - 13.4503) < 0.001) And (Abs(x2 - 39.9794) < 0.001) And (Abs(y2 - 13.4131) < 0.001)) Or ((Abs(x - 39.9794) < 0.001) And (Abs(y - 13.4131) < 0.001) And (Abs(x2 - 39.9805) < 0.001) And (Abs(y2 - 13.4503) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9794) < 0.001) And (Abs(y - 13.4131) < 0.001) And (Abs(x2 - 39.9614) < 0.001) And (Abs(y2 - 12.7678) < 0.001)) Or ((Abs(x - 39.9614) < 0.001) And (Abs(y - 12.7678) < 0.001) And (Abs(x2 - 39.9794) < 0.001) And (Abs(y2 - 13.4131) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9614) < 0.001) And (Abs(y - 12.7678) < 0.001) And (Abs(x2 - 39.9612) < 0.001) And (Abs(y2 - 12.7620) < 0.001)) Or ((Abs(x - 39.9612) < 0.001) And (Abs(y - 12.7620) < 0.001) And (Abs(x2 - 39.9614) < 0.001) And (Abs(y2 - 12.7678) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9612) < 0.001) And (Abs(y - 12.7620) < 0.001) And (Abs(x2 - 39.9612) < 0.001) And (Abs(y2 - 12.7561) < 0.001)) Or ((Abs(x - 39.9612) < 0.001) And (Abs(y - 12.7561) < 0.001) And (Abs(x2 - 39.9612) < 0.001) And (Abs(y2 - 12.7620) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9612) < 0.001) And (Abs(y - 12.7561) < 0.001) And (Abs(x2 - 39.9293) < 0.001) And (Abs(y2 - 9.4045) < 0.001)) Or ((Abs(x - 39.9293) < 0.001) And (Abs(y - 9.4045) < 0.001) And (Abs(x2 - 39.9612) < 0.001) And (Abs(y2 - 12.7561) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9293) < 0.001) And (Abs(y - 9.4045) < 0.001) And (Abs(x2 - 39.9289) < 0.001) And (Abs(y2 - 9.3647) < 0.001)) Or ((Abs(x - 39.9289) < 0.001) And (Abs(y - 9.3647) < 0.001) And (Abs(x2 - 39.9293) < 0.001) And (Abs(y2 - 9.4045) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9289) < 0.001) And (Abs(y - 9.3647) < 0.001) And (Abs(x2 - 39.9415) < 0.001) And (Abs(y2 - 9.2862) < 0.001)) Or ((Abs(x - 39.9415) < 0.001) And (Abs(y - 9.2862) < 0.001) And (Abs(x2 - 39.9289) < 0.001) And (Abs(y2 - 9.3647) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9415) < 0.001) And (Abs(y - 9.2862) < 0.001) And (Abs(x2 - 39.9671) < 0.001) And (Abs(y2 - 9.2109) < 0.001)) Or ((Abs(x - 39.9671) < 0.001) And (Abs(y - 9.2109) < 0.001) And (Abs(x2 - 39.9415) < 0.001) And (Abs(y2 - 9.2862) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 39.9671) < 0.001) And (Abs(y - 9.2109) < 0.001) And (Abs(x2 - 40.0049) < 0.001) And (Abs(y2 - 9.1409) < 0.001)) Or ((Abs(x - 40.0049) < 0.001) And (Abs(y - 9.1409) < 0.001) And (Abs(x2 - 39.9671) < 0.001) And (Abs(y2 - 9.2109) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.0049) < 0.001) And (Abs(y - 9.1409) < 0.001) And (Abs(x2 - 40.0540) < 0.001) And (Abs(y2 - 9.0783) < 0.001)) Or ((Abs(x - 40.0540) < 0.001) And (Abs(y - 9.0783) < 0.001) And (Abs(x2 - 40.0049) < 0.001) And (Abs(y2 - 9.1409) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.0540) < 0.001) And (Abs(y - 9.0783) < 0.001) And (Abs(x2 - 40.0834) < 0.001) And (Abs(y2 - 9.0516) < 0.001)) Or ((Abs(x - 40.0834) < 0.001) And (Abs(y - 9.0516) < 0.001) And (Abs(x2 - 40.0540) < 0.001) And (Abs(y2 - 9.0783) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.0834) < 0.001) And (Abs(y - 9.0516) < 0.001) And (Abs(x2 - 41.1040) < 0.001) And (Abs(y2 - 8.1244) < 0.001)) Or ((Abs(x - 41.1040) < 0.001) And (Abs(y - 8.1244) < 0.001) And (Abs(x2 - 40.0834) < 0.001) And (Abs(y2 - 9.0516) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1040) < 0.001) And (Abs(y - 8.1244) < 0.001) And (Abs(x2 - 41.1233) < 0.001) And (Abs(y2 - 8.1068) < 0.001)) Or ((Abs(x - 41.1233) < 0.001) And (Abs(y - 8.1068) < 0.001) And (Abs(x2 - 41.1040) < 0.001) And (Abs(y2 - 8.1244) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1233) < 0.001) And (Abs(y - 8.1068) < 0.001) And (Abs(x2 - 41.1554) < 0.001) And (Abs(y2 - 8.0656) < 0.001)) Or ((Abs(x - 41.1554) < 0.001) And (Abs(y - 8.0656) < 0.001) And (Abs(x2 - 41.1233) < 0.001) And (Abs(y2 - 8.1068) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1554) < 0.001) And (Abs(y - 8.0656) < 0.001) And (Abs(x2 - 41.1799) < 0.001) And (Abs(y2 - 8.0196) < 0.001)) Or ((Abs(x - 41.1799) < 0.001) And (Abs(y - 8.0196) < 0.001) And (Abs(x2 - 41.1554) < 0.001) And (Abs(y2 - 8.0656) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1799) < 0.001) And (Abs(y - 8.0196) < 0.001) And (Abs(x2 - 41.1963) < 0.001) And (Abs(y2 - 7.9700) < 0.001)) Or ((Abs(x - 41.1963) < 0.001) And (Abs(y - 7.9700) < 0.001) And (Abs(x2 - 41.1799) < 0.001) And (Abs(y2 - 8.0196) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1963) < 0.001) And (Abs(y - 7.9700) < 0.001) And (Abs(x2 - 41.2039) < 0.001) And (Abs(y2 - 7.9183) < 0.001)) Or ((Abs(x - 41.2039) < 0.001) And (Abs(y - 7.9183) < 0.001) And (Abs(x2 - 41.1963) < 0.001) And (Abs(y2 - 7.9700) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.2039) < 0.001) And (Abs(y - 7.9183) < 0.001) And (Abs(x2 - 41.2025) < 0.001) And (Abs(y2 - 7.8661) < 0.001)) Or ((Abs(x - 41.2025) < 0.001) And (Abs(y - 7.8661) < 0.001) And (Abs(x2 - 41.2039) < 0.001) And (Abs(y2 - 7.9183) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.2025) < 0.001) And (Abs(y - 7.8661) < 0.001) And (Abs(x2 - 41.1923) < 0.001) And (Abs(y2 - 7.8149) < 0.001)) Or ((Abs(x - 41.1923) < 0.001) And (Abs(y - 7.8149) < 0.001) And (Abs(x2 - 41.2025) < 0.001) And (Abs(y2 - 7.8661) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1923) < 0.001) And (Abs(y - 7.8149) < 0.001) And (Abs(x2 - 41.1829) < 0.001) And (Abs(y2 - 7.7905) < 0.001)) Or ((Abs(x - 41.1829) < 0.001) And (Abs(y - 7.7905) < 0.001) And (Abs(x2 - 41.1923) < 0.001) And (Abs(y2 - 7.8149) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.1829) < 0.001) And (Abs(y - 7.7905) < 0.001) And (Abs(x2 - 40.8000) < 0.001) And (Abs(y2 - 6.8000) < 0.001)) Or ((Abs(x - 40.8000) < 0.001) And (Abs(y - 6.8000) < 0.001) And (Abs(x2 - 41.1829) < 0.001) And (Abs(y2 - 7.7905) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN15_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.8000) < 0.001) And (Abs(y - 6.8000) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 4.6000) < 0.001)) Or ((Abs(x - 40.4500) < 0.001) And (Abs(y - 4.6000) < 0.001) And (Abs(x2 - 40.8000) < 0.001) And (Abs(y2 - 6.8000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4500) < 0.001) And (Abs(y - 13.4000) < 0.001) And (Abs(x2 - 40.3058) < 0.001) And (Abs(y2 - 12.8236) < 0.001)) Or ((Abs(x - 40.3058) < 0.001) And (Abs(y - 12.8236) < 0.001) And (Abs(x2 - 40.4500) < 0.001) And (Abs(y2 - 13.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.3058) < 0.001) And (Abs(y - 12.8236) < 0.001) And (Abs(x2 - 40.3003) < 0.001) And (Abs(y2 - 12.8018) < 0.001)) Or ((Abs(x - 40.3003) < 0.001) And (Abs(y - 12.8018) < 0.001) And (Abs(x2 - 40.3058) < 0.001) And (Abs(y2 - 12.8236) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.3003) < 0.001) And (Abs(y - 12.8018) < 0.001) And (Abs(x2 - 40.2959) < 0.001) And (Abs(y2 - 12.7570) < 0.001)) Or ((Abs(x - 40.2959) < 0.001) And (Abs(y - 12.7570) < 0.001) And (Abs(x2 - 40.3003) < 0.001) And (Abs(y2 - 12.8018) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.2959) < 0.001) And (Abs(y - 12.7570) < 0.001) And (Abs(x2 - 40.2971) < 0.001) And (Abs(y2 - 12.7346) < 0.001)) Or ((Abs(x - 40.2971) < 0.001) And (Abs(y - 12.7346) < 0.001) And (Abs(x2 - 40.2959) < 0.001) And (Abs(y2 - 12.7570) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.2971) < 0.001) And (Abs(y - 12.7346) < 0.001) And (Abs(x2 - 40.4298) < 0.001) And (Abs(y2 - 10.1261) < 0.001)) Or ((Abs(x - 40.4298) < 0.001) And (Abs(y - 10.1261) < 0.001) And (Abs(x2 - 40.2971) < 0.001) And (Abs(y2 - 12.7346) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4298) < 0.001) And (Abs(y - 10.1261) < 0.001) And (Abs(x2 - 40.4317) < 0.001) And (Abs(y2 - 10.0892) < 0.001)) Or ((Abs(x - 40.4317) < 0.001) And (Abs(y - 10.0892) < 0.001) And (Abs(x2 - 40.4298) < 0.001) And (Abs(y2 - 10.1261) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4317) < 0.001) And (Abs(y - 10.0892) < 0.001) And (Abs(x2 - 40.4469) < 0.001) And (Abs(y2 - 10.0170) < 0.001)) Or ((Abs(x - 40.4469) < 0.001) And (Abs(y - 10.0170) < 0.001) And (Abs(x2 - 40.4317) < 0.001) And (Abs(y2 - 10.0892) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4469) < 0.001) And (Abs(y - 10.0170) < 0.001) And (Abs(x2 - 40.4732) < 0.001) And (Abs(y2 - 9.9480) < 0.001)) Or ((Abs(x - 40.4732) < 0.001) And (Abs(y - 9.9480) < 0.001) And (Abs(x2 - 40.4469) < 0.001) And (Abs(y2 - 10.0170) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.4732) < 0.001) And (Abs(y - 9.9480) < 0.001) And (Abs(x2 - 40.5099) < 0.001) And (Abs(y2 - 9.8839) < 0.001)) Or ((Abs(x - 40.5099) < 0.001) And (Abs(y - 9.8839) < 0.001) And (Abs(x2 - 40.4732) < 0.001) And (Abs(y2 - 9.9480) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.5099) < 0.001) And (Abs(y - 9.8839) < 0.001) And (Abs(x2 - 40.5561) < 0.001) And (Abs(y2 - 9.8264) < 0.001)) Or ((Abs(x - 40.5561) < 0.001) And (Abs(y - 9.8264) < 0.001) And (Abs(x2 - 40.5099) < 0.001) And (Abs(y2 - 9.8839) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.5561) < 0.001) And (Abs(y - 9.8264) < 0.001) And (Abs(x2 - 40.5835) < 0.001) And (Abs(y2 - 9.8016) < 0.001)) Or ((Abs(x - 40.5835) < 0.001) And (Abs(y - 9.8016) < 0.001) And (Abs(x2 - 40.5561) < 0.001) And (Abs(y2 - 9.8264) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 40.5835) < 0.001) And (Abs(y - 9.8016) < 0.001) And (Abs(x2 - 41.6039) < 0.001) And (Abs(y2 - 8.8745) < 0.001)) Or ((Abs(x - 41.6039) < 0.001) And (Abs(y - 8.8745) < 0.001) And (Abs(x2 - 40.5835) < 0.001) And (Abs(y2 - 9.8016) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.6039) < 0.001) And (Abs(y - 8.8745) < 0.001) And (Abs(x2 - 41.6227) < 0.001) And (Abs(y2 - 8.8575) < 0.001)) Or ((Abs(x - 41.6227) < 0.001) And (Abs(y - 8.8575) < 0.001) And (Abs(x2 - 41.6039) < 0.001) And (Abs(y2 - 8.8745) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.6227) < 0.001) And (Abs(y - 8.8575) < 0.001) And (Abs(x2 - 41.6540) < 0.001) And (Abs(y2 - 8.8177) < 0.001)) Or ((Abs(x - 41.6540) < 0.001) And (Abs(y - 8.8177) < 0.001) And (Abs(x2 - 41.6227) < 0.001) And (Abs(y2 - 8.8575) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.6540) < 0.001) And (Abs(y - 8.8177) < 0.001) And (Abs(x2 - 41.6782) < 0.001) And (Abs(y2 - 8.7734) < 0.001)) Or ((Abs(x - 41.6782) < 0.001) And (Abs(y - 8.7734) < 0.001) And (Abs(x2 - 41.6540) < 0.001) And (Abs(y2 - 8.8177) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.6782) < 0.001) And (Abs(y - 8.7734) < 0.001) And (Abs(x2 - 41.6948) < 0.001) And (Abs(y2 - 8.7256) < 0.001)) Or ((Abs(x - 41.6948) < 0.001) And (Abs(y - 8.7256) < 0.001) And (Abs(x2 - 41.6782) < 0.001) And (Abs(y2 - 8.7734) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.6948) < 0.001) And (Abs(y - 8.7256) < 0.001) And (Abs(x2 - 41.7033) < 0.001) And (Abs(y2 - 8.6757) < 0.001)) Or ((Abs(x - 41.7033) < 0.001) And (Abs(y - 8.6757) < 0.001) And (Abs(x2 - 41.6948) < 0.001) And (Abs(y2 - 8.7256) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7033) < 0.001) And (Abs(y - 8.6757) < 0.001) And (Abs(x2 - 41.7033) < 0.001) And (Abs(y2 - 8.6504) < 0.001)) Or ((Abs(x - 41.7033) < 0.001) And (Abs(y - 8.6504) < 0.001) And (Abs(x2 - 41.7033) < 0.001) And (Abs(y2 - 8.6757) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7033) < 0.001) And (Abs(y - 8.6504) < 0.001) And (Abs(x2 - 41.7049) < 0.001) And (Abs(y2 - 7.4996) < 0.001)) Or ((Abs(x - 41.7049) < 0.001) And (Abs(y - 7.4996) < 0.001) And (Abs(x2 - 41.7033) < 0.001) And (Abs(y2 - 8.6504) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7049) < 0.001) And (Abs(y - 7.4996) < 0.001) And (Abs(x2 - 41.7049) < 0.001) And (Abs(y2 - 7.4740) < 0.001)) Or ((Abs(x - 41.7049) < 0.001) And (Abs(y - 7.4740) < 0.001) And (Abs(x2 - 41.7049) < 0.001) And (Abs(y2 - 7.4996) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7049) < 0.001) And (Abs(y - 7.4740) < 0.001) And (Abs(x2 - 41.7138) < 0.001) And (Abs(y2 - 7.4235) < 0.001)) Or ((Abs(x - 41.7138) < 0.001) And (Abs(y - 7.4235) < 0.001) And (Abs(x2 - 41.7049) < 0.001) And (Abs(y2 - 7.4740) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7138) < 0.001) And (Abs(y - 7.4235) < 0.001) And (Abs(x2 - 41.7313) < 0.001) And (Abs(y2 - 7.3754) < 0.001)) Or ((Abs(x - 41.7313) < 0.001) And (Abs(y - 7.3754) < 0.001) And (Abs(x2 - 41.7138) < 0.001) And (Abs(y2 - 7.4235) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7313) < 0.001) And (Abs(y - 7.3754) < 0.001) And (Abs(x2 - 41.7568) < 0.001) And (Abs(y2 - 7.3309) < 0.001)) Or ((Abs(x - 41.7568) < 0.001) And (Abs(y - 7.3309) < 0.001) And (Abs(x2 - 41.7313) < 0.001) And (Abs(y2 - 7.3754) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7568) < 0.001) And (Abs(y - 7.3309) < 0.001) And (Abs(x2 - 41.7896) < 0.001) And (Abs(y2 - 7.2916) < 0.001)) Or ((Abs(x - 41.7896) < 0.001) And (Abs(y - 7.2916) < 0.001) And (Abs(x2 - 41.7568) < 0.001) And (Abs(y2 - 7.3309) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7896) < 0.001) And (Abs(y - 7.2916) < 0.001) And (Abs(x2 - 41.8286) < 0.001) And (Abs(y2 - 7.2584) < 0.001)) Or ((Abs(x - 41.8286) < 0.001) And (Abs(y - 7.2584) < 0.001) And (Abs(x2 - 41.7896) < 0.001) And (Abs(y2 - 7.2916) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8286) < 0.001) And (Abs(y - 7.2584) < 0.001) And (Abs(x2 - 41.8507) < 0.001) And (Abs(y2 - 7.2455) < 0.001)) Or ((Abs(x - 41.8507) < 0.001) And (Abs(y - 7.2455) < 0.001) And (Abs(x2 - 41.8286) < 0.001) And (Abs(y2 - 7.2584) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_P') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8507) < 0.001) And (Abs(y - 7.2455) < 0.001) And (Abs(x2 - 45.8500) < 0.001) And (Abs(y2 - 4.9000) < 0.001)) Or ((Abs(x - 45.8500) < 0.001) And (Abs(y - 4.9000) < 0.001) And (Abs(x2 - 41.8507) < 0.001) And (Abs(y2 - 7.2455) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.3000) < 0.001) And (Abs(y - 12.6650) < 0.001) And (Abs(x2 - 40.6977) < 0.001) And (Abs(y2 - 12.1259) < 0.001)) Or ((Abs(x - 40.6977) < 0.001) And (Abs(y - 12.1259) < 0.001) And (Abs(x2 - 41.3000) < 0.001) And (Abs(y2 - 12.6650) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6977) < 0.001) And (Abs(y - 12.1259) < 0.001) And (Abs(x2 - 40.6787) < 0.001) And (Abs(y2 - 12.1088) < 0.001)) Or ((Abs(x - 40.6787) < 0.001) And (Abs(y - 12.1088) < 0.001) And (Abs(x2 - 40.6977) < 0.001) And (Abs(y2 - 12.1259) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6787) < 0.001) And (Abs(y - 12.1088) < 0.001) And (Abs(x2 - 40.6468) < 0.001) And (Abs(y2 - 12.0689) < 0.001)) Or ((Abs(x - 40.6468) < 0.001) And (Abs(y - 12.0689) < 0.001) And (Abs(x2 - 40.6787) < 0.001) And (Abs(y2 - 12.1088) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6468) < 0.001) And (Abs(y - 12.0689) < 0.001) And (Abs(x2 - 40.6221) < 0.001) And (Abs(y2 - 12.0241) < 0.001)) Or ((Abs(x - 40.6221) < 0.001) And (Abs(y - 12.0241) < 0.001) And (Abs(x2 - 40.6468) < 0.001) And (Abs(y2 - 12.0689) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6221) < 0.001) And (Abs(y - 12.0241) < 0.001) And (Abs(x2 - 40.6053) < 0.001) And (Abs(y2 - 11.9759) < 0.001)) Or ((Abs(x - 40.6053) < 0.001) And (Abs(y - 11.9759) < 0.001) And (Abs(x2 - 40.6221) < 0.001) And (Abs(y2 - 12.0241) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6053) < 0.001) And (Abs(y - 11.9759) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 11.9255) < 0.001)) Or ((Abs(x - 40.5967) < 0.001) And (Abs(y - 11.9255) < 0.001) And (Abs(x2 - 40.6053) < 0.001) And (Abs(y2 - 11.9759) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.5967) < 0.001) And (Abs(y - 11.9255) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 11.8999) < 0.001)) Or ((Abs(x - 40.5967) < 0.001) And (Abs(y - 11.8999) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 11.9255) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.5967) < 0.001) And (Abs(y - 11.8999) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 10.1500) < 0.001)) Or ((Abs(x - 40.5967) < 0.001) And (Abs(y - 10.1500) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 11.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.5967) < 0.001) And (Abs(y - 10.1500) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 10.1247) < 0.001)) Or ((Abs(x - 40.5967) < 0.001) And (Abs(y - 10.1247) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 10.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.5967) < 0.001) And (Abs(y - 10.1247) < 0.001) And (Abs(x2 - 40.6051) < 0.001) And (Abs(y2 - 10.0747) < 0.001)) Or ((Abs(x - 40.6051) < 0.001) And (Abs(y - 10.0747) < 0.001) And (Abs(x2 - 40.5967) < 0.001) And (Abs(y2 - 10.1247) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6051) < 0.001) And (Abs(y - 10.0747) < 0.001) And (Abs(x2 - 40.6217) < 0.001) And (Abs(y2 - 10.0268) < 0.001)) Or ((Abs(x - 40.6217) < 0.001) And (Abs(y - 10.0268) < 0.001) And (Abs(x2 - 40.6051) < 0.001) And (Abs(y2 - 10.0747) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6217) < 0.001) And (Abs(y - 10.0268) < 0.001) And (Abs(x2 - 40.6460) < 0.001) And (Abs(y2 - 9.9824) < 0.001)) Or ((Abs(x - 40.6460) < 0.001) And (Abs(y - 9.9824) < 0.001) And (Abs(x2 - 40.6217) < 0.001) And (Abs(y2 - 10.0268) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6460) < 0.001) And (Abs(y - 9.9824) < 0.001) And (Abs(x2 - 40.6773) < 0.001) And (Abs(y2 - 9.9425) < 0.001)) Or ((Abs(x - 40.6773) < 0.001) And (Abs(y - 9.9425) < 0.001) And (Abs(x2 - 40.6460) < 0.001) And (Abs(y2 - 9.9824) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6773) < 0.001) And (Abs(y - 9.9425) < 0.001) And (Abs(x2 - 40.6961) < 0.001) And (Abs(y2 - 9.9255) < 0.001)) Or ((Abs(x - 40.6961) < 0.001) And (Abs(y - 9.9255) < 0.001) And (Abs(x2 - 40.6773) < 0.001) And (Abs(y2 - 9.9425) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 40.6961) < 0.001) And (Abs(y - 9.9255) < 0.001) And (Abs(x2 - 41.7165) < 0.001) And (Abs(y2 - 8.9984) < 0.001)) Or ((Abs(x - 41.7165) < 0.001) And (Abs(y - 8.9984) < 0.001) And (Abs(x2 - 40.6961) < 0.001) And (Abs(y2 - 9.9255) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7165) < 0.001) And (Abs(y - 8.9984) < 0.001) And (Abs(x2 - 41.7456) < 0.001) And (Abs(y2 - 8.9720) < 0.001)) Or ((Abs(x - 41.7456) < 0.001) And (Abs(y - 8.9720) < 0.001) And (Abs(x2 - 41.7165) < 0.001) And (Abs(y2 - 8.9984) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7456) < 0.001) And (Abs(y - 8.9720) < 0.001) And (Abs(x2 - 41.7942) < 0.001) And (Abs(y2 - 8.9103) < 0.001)) Or ((Abs(x - 41.7942) < 0.001) And (Abs(y - 8.9103) < 0.001) And (Abs(x2 - 41.7456) < 0.001) And (Abs(y2 - 8.9720) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.7942) < 0.001) And (Abs(y - 8.9103) < 0.001) And (Abs(x2 - 41.8319) < 0.001) And (Abs(y2 - 8.8414) < 0.001)) Or ((Abs(x - 41.8319) < 0.001) And (Abs(y - 8.8414) < 0.001) And (Abs(x2 - 41.7942) < 0.001) And (Abs(y2 - 8.9103) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8319) < 0.001) And (Abs(y - 8.8414) < 0.001) And (Abs(x2 - 41.8576) < 0.001) And (Abs(y2 - 8.7671) < 0.001)) Or ((Abs(x - 41.8576) < 0.001) And (Abs(y - 8.7671) < 0.001) And (Abs(x2 - 41.8319) < 0.001) And (Abs(y2 - 8.8414) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8576) < 0.001) And (Abs(y - 8.7671) < 0.001) And (Abs(x2 - 41.8707) < 0.001) And (Abs(y2 - 8.6897) < 0.001)) Or ((Abs(x - 41.8707) < 0.001) And (Abs(y - 8.6897) < 0.001) And (Abs(x2 - 41.8576) < 0.001) And (Abs(y2 - 8.7671) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8707) < 0.001) And (Abs(y - 8.6897) < 0.001) And (Abs(x2 - 41.8708) < 0.001) And (Abs(y2 - 8.6504) < 0.001)) Or ((Abs(x - 41.8708) < 0.001) And (Abs(y - 8.6504) < 0.001) And (Abs(x2 - 41.8707) < 0.001) And (Abs(y2 - 8.6897) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8708) < 0.001) And (Abs(y - 8.6504) < 0.001) And (Abs(x2 - 41.8717) < 0.001) And (Abs(y2 - 7.4999) < 0.001)) Or ((Abs(x - 41.8717) < 0.001) And (Abs(y - 7.4999) < 0.001) And (Abs(x2 - 41.8708) < 0.001) And (Abs(y2 - 8.6504) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8717) < 0.001) And (Abs(y - 7.4999) < 0.001) And (Abs(x2 - 41.8717) < 0.001) And (Abs(y2 - 7.4887) < 0.001)) Or ((Abs(x - 41.8717) < 0.001) And (Abs(y - 7.4887) < 0.001) And (Abs(x2 - 41.8717) < 0.001) And (Abs(y2 - 7.4999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8717) < 0.001) And (Abs(y - 7.4887) < 0.001) And (Abs(x2 - 41.8756) < 0.001) And (Abs(y2 - 7.4668) < 0.001)) Or ((Abs(x - 41.8756) < 0.001) And (Abs(y - 7.4668) < 0.001) And (Abs(x2 - 41.8717) < 0.001) And (Abs(y2 - 7.4887) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8756) < 0.001) And (Abs(y - 7.4668) < 0.001) And (Abs(x2 - 41.8832) < 0.001) And (Abs(y2 - 7.4458) < 0.001)) Or ((Abs(x - 41.8832) < 0.001) And (Abs(y - 7.4458) < 0.001) And (Abs(x2 - 41.8756) < 0.001) And (Abs(y2 - 7.4668) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8832) < 0.001) And (Abs(y - 7.4458) < 0.001) And (Abs(x2 - 41.8943) < 0.001) And (Abs(y2 - 7.4265) < 0.001)) Or ((Abs(x - 41.8943) < 0.001) And (Abs(y - 7.4265) < 0.001) And (Abs(x2 - 41.8832) < 0.001) And (Abs(y2 - 7.4458) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.8943) < 0.001) And (Abs(y - 7.4265) < 0.001) And (Abs(x2 - 41.9085) < 0.001) And (Abs(y2 - 7.4093) < 0.001)) Or ((Abs(x - 41.9085) < 0.001) And (Abs(y - 7.4093) < 0.001) And (Abs(x2 - 41.8943) < 0.001) And (Abs(y2 - 7.4265) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.9085) < 0.001) And (Abs(y - 7.4093) < 0.001) And (Abs(x2 - 41.9256) < 0.001) And (Abs(y2 - 7.3949) < 0.001)) Or ((Abs(x - 41.9256) < 0.001) And (Abs(y - 7.3949) < 0.001) And (Abs(x2 - 41.9085) < 0.001) And (Abs(y2 - 7.4093) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.9256) < 0.001) And (Abs(y - 7.3949) < 0.001) And (Abs(x2 - 41.9352) < 0.001) And (Abs(y2 - 7.3893) < 0.001)) Or ((Abs(x - 41.9352) < 0.001) And (Abs(y - 7.3893) < 0.001) And (Abs(x2 - 41.9256) < 0.001) And (Abs(y2 - 7.3949) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'AIN16_N') And (T.Layer = eBottomLayer) And (((Abs(x - 41.9352) < 0.001) And (Abs(y - 7.3893) < 0.001) And (Abs(x2 - 46.0160) < 0.001) And (Abs(y2 - 5.0000) < 0.001)) Or ((Abs(x - 46.0160) < 0.001) And (Abs(y - 5.0000) < 0.001) And (Abs(x2 - 41.9352) < 0.001) And (Abs(y2 - 7.3893) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.4001) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 42.4000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 42.4000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 42.4001) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.4000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 42.4000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CS#') And (T.Layer = eMidLayer2) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 26.1000) < 0.001) And (Abs(y2 - 5.3750) < 0.001)) Or ((Abs(x - 26.1000) < 0.001) And (Abs(y - 5.3750) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CS#') And (T.Layer = eMidLayer2) And (((Abs(x - 26.1000) < 0.001) And (Abs(y - 5.3750) < 0.001) And (Abs(x2 - 24.7500) < 0.001) And (Abs(y2 - 6.7250) < 0.001)) Or ((Abs(x - 24.7500) < 0.001) And (Abs(y - 6.7250) < 0.001) And (Abs(x2 - 26.1000) < 0.001) And (Abs(y2 - 5.3750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CS#') And (T.Layer = eMidLayer2) And (((Abs(x - 24.7500) < 0.001) And (Abs(y - 6.7250) < 0.001) And (Abs(x2 - 24.7500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)) Or ((Abs(x - 24.7500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 24.7500) < 0.001) And (Abs(y2 - 6.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CS#') And (T.Layer = eBottomLayer) And (((Abs(x - 24.7500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 24.3500) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 24.3500) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 24.7500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.6501) < 0.001) And (Abs(y - 7.1875) < 0.001) And (Abs(x2 - 42.6500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 42.6500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 42.6501) < 0.001) And (Abs(y2 - 7.1875) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.6500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 42.3250) < 0.001) And (Abs(y2 - 6.2250) < 0.001)) Or ((Abs(x - 42.3250) < 0.001) And (Abs(y - 6.2250) < 0.001) And (Abs(x2 - 42.6500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.3250) < 0.001) And (Abs(y - 6.2250) < 0.001) And (Abs(x2 - 39.1500) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 39.1500) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 42.3250) < 0.001) And (Abs(y2 - 6.2250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eMidLayer1) And (((Abs(x - 39.1500) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 38.6000) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 38.6000) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 39.1500) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eMidLayer1) And (((Abs(x - 38.6000) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 26.9500) < 0.001) And (Abs(y2 - 5.3500) < 0.001)) Or ((Abs(x - 26.9500) < 0.001) And (Abs(y - 5.3500) < 0.001) And (Abs(x2 - 38.6000) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eMidLayer1) And (((Abs(x - 26.9500) < 0.001) And (Abs(y - 5.3500) < 0.001) And (Abs(x2 - 25.5500) < 0.001) And (Abs(y2 - 6.7500) < 0.001)) Or ((Abs(x - 25.5500) < 0.001) And (Abs(y - 6.7500) < 0.001) And (Abs(x2 - 26.9500) < 0.001) And (Abs(y2 - 5.3500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eMidLayer1) And (((Abs(x - 25.5500) < 0.001) And (Abs(y - 6.7500) < 0.001) And (Abs(x2 - 25.5500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)) Or ((Abs(x - 25.5500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 25.5500) < 0.001) And (Abs(y2 - 6.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'RAS#') And (T.Layer = eBottomLayer) And (((Abs(x - 25.5500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 25.1501) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 25.1501) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 25.5500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.9000) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 42.9000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 42.9000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 42.9000) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.9000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 42.4000) < 0.001) And (Abs(y2 - 6.0500) < 0.001)) Or ((Abs(x - 42.4000) < 0.001) And (Abs(y - 6.0500) < 0.001) And (Abs(x2 - 42.9000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eTopLayer) And (((Abs(x - 42.4000) < 0.001) And (Abs(y - 6.0500) < 0.001) And (Abs(x2 - 39.8000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 39.8000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 42.4000) < 0.001) And (Abs(y2 - 6.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eMidLayer2) And (((Abs(x - 39.8000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 39.2500) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 39.2500) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 39.8000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eMidLayer2) And (((Abs(x - 39.2500) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 27.5750) < 0.001) And (Abs(y2 - 5.5000) < 0.001)) Or ((Abs(x - 27.5750) < 0.001) And (Abs(y - 5.5000) < 0.001) And (Abs(x2 - 39.2500) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eMidLayer2) And (((Abs(x - 27.5750) < 0.001) And (Abs(y - 5.5000) < 0.001) And (Abs(x2 - 26.3500) < 0.001) And (Abs(y2 - 6.7250) < 0.001)) Or ((Abs(x - 26.3500) < 0.001) And (Abs(y - 6.7250) < 0.001) And (Abs(x2 - 27.5750) < 0.001) And (Abs(y2 - 5.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eMidLayer2) And (((Abs(x - 26.3500) < 0.001) And (Abs(y - 6.7250) < 0.001) And (Abs(x2 - 26.3500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)) Or ((Abs(x - 26.3500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 26.3500) < 0.001) And (Abs(y2 - 6.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CAS#') And (T.Layer = eBottomLayer) And (((Abs(x - 26.3500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 25.9499) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 25.9499) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 26.3500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eTopLayer) And (((Abs(x - 43.1501) < 0.001) And (Abs(y - 7.1875) < 0.001) And (Abs(x2 - 43.1500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 43.1500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 43.1501) < 0.001) And (Abs(y2 - 7.1875) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eTopLayer) And (((Abs(x - 43.1500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 41.9000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 43.1500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eMidLayer1) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 41.5500) < 0.001) And (Abs(y2 - 4.3000) < 0.001)) Or ((Abs(x - 41.5500) < 0.001) And (Abs(y - 4.3000) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eMidLayer1) And (((Abs(x - 41.5500) < 0.001) And (Abs(y - 4.3000) < 0.001) And (Abs(x2 - 40.1750) < 0.001) And (Abs(y2 - 4.5250) < 0.001)) Or ((Abs(x - 40.1750) < 0.001) And (Abs(y - 4.5250) < 0.001) And (Abs(x2 - 41.5500) < 0.001) And (Abs(y2 - 4.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eMidLayer1) And (((Abs(x - 40.1750) < 0.001) And (Abs(y - 4.5250) < 0.001) And (Abs(x2 - 39.9500) < 0.001) And (Abs(y2 - 4.7250) < 0.001)) Or ((Abs(x - 39.9500) < 0.001) And (Abs(y - 4.7250) < 0.001) And (Abs(x2 - 40.1750) < 0.001) And (Abs(y2 - 4.5250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eMidLayer1) And (((Abs(x - 39.9500) < 0.001) And (Abs(y - 4.7250) < 0.001) And (Abs(x2 - 38.6250) < 0.001) And (Abs(y2 - 5.0000) < 0.001)) Or ((Abs(x - 38.6250) < 0.001) And (Abs(y - 5.0000) < 0.001) And (Abs(x2 - 39.9500) < 0.001) And (Abs(y2 - 4.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eMidLayer1) And (((Abs(x - 38.6250) < 0.001) And (Abs(y - 5.0000) < 0.001) And (Abs(x2 - 28.3500) < 0.001) And (Abs(y2 - 5.5250) < 0.001)) Or ((Abs(x - 28.3500) < 0.001) And (Abs(y - 5.5250) < 0.001) And (Abs(x2 - 38.6250) < 0.001) And (Abs(y2 - 5.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eMidLayer1) And (((Abs(x - 28.3500) < 0.001) And (Abs(y - 5.5250) < 0.001) And (Abs(x2 - 27.1500) < 0.001) And (Abs(y2 - 6.7250) < 0.001)) Or ((Abs(x - 27.1500) < 0.001) And (Abs(y - 6.7250) < 0.001) And (Abs(x2 - 28.3500) < 0.001) And (Abs(y2 - 5.5250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eMidLayer1) And (((Abs(x - 27.1500) < 0.001) And (Abs(y - 6.7250) < 0.001) And (Abs(x2 - 27.1500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)) Or ((Abs(x - 27.1500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 27.1500) < 0.001) And (Abs(y2 - 6.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'WE#') And (T.Layer = eBottomLayer) And (((Abs(x - 27.1500) < 0.001) And (Abs(y - 6.9750) < 0.001) And (Abs(x2 - 26.7500) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 26.7500) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 27.1500) < 0.001) And (Abs(y2 - 6.9750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eTopLayer) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 43.4000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 43.4000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eTopLayer) And (((Abs(x - 43.4000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 42.3750) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 42.3750) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 43.4000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eMidLayer2) And (((Abs(x - 42.3750) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 42.0500) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 42.0500) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 42.3750) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eMidLayer2) And (((Abs(x - 42.0500) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 41.6250) < 0.001) And (Abs(y2 - 5.0000) < 0.001)) Or ((Abs(x - 41.6250) < 0.001) And (Abs(y - 5.0000) < 0.001) And (Abs(x2 - 42.0500) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eMidLayer2) And (((Abs(x - 41.6250) < 0.001) And (Abs(y - 5.0000) < 0.001) And (Abs(x2 - 29.0500) < 0.001) And (Abs(y2 - 5.6500) < 0.001)) Or ((Abs(x - 29.0500) < 0.001) And (Abs(y - 5.6500) < 0.001) And (Abs(x2 - 41.6250) < 0.001) And (Abs(y2 - 5.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eMidLayer2) And (((Abs(x - 29.0500) < 0.001) And (Abs(y - 5.6500) < 0.001) And (Abs(x2 - 27.3000) < 0.001) And (Abs(y2 - 7.4000) < 0.001)) Or ((Abs(x - 27.3000) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 29.0500) < 0.001) And (Abs(y2 - 5.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eBottomLayer) And (((Abs(x - 27.3000) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 27.5000) < 0.001) And (Abs(y2 - 7.0250) < 0.001)) Or ((Abs(x - 27.5000) < 0.001) And (Abs(y - 7.0250) < 0.001) And (Abs(x2 - 27.3000) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'LDQM') And (T.Layer = eBottomLayer) And (((Abs(x - 27.5000) < 0.001) And (Abs(y - 7.0250) < 0.001) And (Abs(x2 - 27.5501) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 27.5501) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 27.5000) < 0.001) And (Abs(y2 - 7.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D6') And (T.Layer = eTopLayer) And (((Abs(x - 43.6501) < 0.001) And (Abs(y - 7.1875) < 0.001) And (Abs(x2 - 43.6500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 43.6500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 43.6501) < 0.001) And (Abs(y2 - 7.1875) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D6') And (T.Layer = eTopLayer) And (((Abs(x - 43.6500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 42.8500) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 42.8500) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 43.6500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D6') And (T.Layer = eMidLayer1) And (((Abs(x - 42.8500) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 42.5250) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 42.5250) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 42.8500) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D6') And (T.Layer = eMidLayer1) And (((Abs(x - 42.5250) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 5.0250) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 5.0250) < 0.001) And (Abs(x2 - 42.5250) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D6') And (T.Layer = eMidLayer1) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 5.0250) < 0.001) And (Abs(x2 - 31.4250) < 0.001) And (Abs(y2 - 6.4500) < 0.001)) Or ((Abs(x - 31.4250) < 0.001) And (Abs(y - 6.4500) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 5.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D6') And (T.Layer = eMidLayer1) And (((Abs(x - 31.4250) < 0.001) And (Abs(y - 6.4500) < 0.001) And (Abs(x2 - 30.9750) < 0.001) And (Abs(y2 - 8.9250) < 0.001)) Or ((Abs(x - 30.9750) < 0.001) And (Abs(y - 8.9250) < 0.001) And (Abs(x2 - 31.4250) < 0.001) And (Abs(y2 - 6.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D6') And (T.Layer = eBottomLayer) And (((Abs(x - 30.9750) < 0.001) And (Abs(y - 8.9250) < 0.001) And (Abs(x2 - 30.7500) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 30.7500) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 30.9750) < 0.001) And (Abs(y2 - 8.9250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eTopLayer) And (((Abs(x - 43.9000) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 43.8250) < 0.001) And (Abs(y2 - 7.1500) < 0.001)) Or ((Abs(x - 43.8250) < 0.001) And (Abs(y - 7.1500) < 0.001) And (Abs(x2 - 43.9000) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eTopLayer) And (((Abs(x - 43.8250) < 0.001) And (Abs(y - 7.1500) < 0.001) And (Abs(x2 - 43.8250) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 43.8250) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 43.8250) < 0.001) And (Abs(y2 - 7.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eTopLayer) And (((Abs(x - 43.8250) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 43.3250) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 43.3250) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 43.8250) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eMidLayer2) And (((Abs(x - 43.3250) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 43.0000) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 43.0000) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 43.3250) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eMidLayer2) And (((Abs(x - 43.0000) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 41.6500) < 0.001) And (Abs(y2 - 5.2500) < 0.001)) Or ((Abs(x - 41.6500) < 0.001) And (Abs(y - 5.2500) < 0.001) And (Abs(x2 - 43.0000) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eMidLayer2) And (((Abs(x - 41.6500) < 0.001) And (Abs(y - 5.2500) < 0.001) And (Abs(x2 - 32.2500) < 0.001) And (Abs(y2 - 6.4500) < 0.001)) Or ((Abs(x - 32.2500) < 0.001) And (Abs(y - 6.4500) < 0.001) And (Abs(x2 - 41.6500) < 0.001) And (Abs(y2 - 5.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eMidLayer2) And (((Abs(x - 32.2500) < 0.001) And (Abs(y - 6.4500) < 0.001) And (Abs(x2 - 31.5500) < 0.001) And (Abs(y2 - 8.9500) < 0.001)) Or ((Abs(x - 31.5500) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 32.2500) < 0.001) And (Abs(y2 - 6.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D5') And (T.Layer = eBottomLayer) And (((Abs(x - 31.5500) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 31.5501) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 31.5501) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 31.5500) < 0.001) And (Abs(y2 - 8.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D3') And (T.Layer = eTopLayer) And (((Abs(x - 44.4001) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 44.4750) < 0.001) And (Abs(y2 - 7.1500) < 0.001)) Or ((Abs(x - 44.4750) < 0.001) And (Abs(y - 7.1500) < 0.001) And (Abs(x2 - 44.4001) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D3') And (T.Layer = eTopLayer) And (((Abs(x - 44.4750) < 0.001) And (Abs(y - 7.1500) < 0.001) And (Abs(x2 - 44.4750) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 44.4750) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 44.4750) < 0.001) And (Abs(y2 - 7.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D3') And (T.Layer = eTopLayer) And (((Abs(x - 44.4750) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 43.8250) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 43.8250) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 44.4750) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D3') And (T.Layer = eMidLayer1) And (((Abs(x - 43.8250) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 43.1000) < 0.001) And (Abs(y2 - 5.0750) < 0.001)) Or ((Abs(x - 43.1000) < 0.001) And (Abs(y - 5.0750) < 0.001) And (Abs(x2 - 43.8250) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D3') And (T.Layer = eMidLayer1) And (((Abs(x - 43.1000) < 0.001) And (Abs(y - 5.0750) < 0.001) And (Abs(x2 - 34.6250) < 0.001) And (Abs(y2 - 6.4500) < 0.001)) Or ((Abs(x - 34.6250) < 0.001) And (Abs(y - 6.4500) < 0.001) And (Abs(x2 - 43.1000) < 0.001) And (Abs(y2 - 5.0750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D3') And (T.Layer = eMidLayer1) And (((Abs(x - 34.6250) < 0.001) And (Abs(y - 6.4500) < 0.001) And (Abs(x2 - 33.9750) < 0.001) And (Abs(y2 - 8.9250) < 0.001)) Or ((Abs(x - 33.9750) < 0.001) And (Abs(y - 8.9250) < 0.001) And (Abs(x2 - 34.6250) < 0.001) And (Abs(y2 - 6.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D3') And (T.Layer = eBottomLayer) And (((Abs(x - 33.9750) < 0.001) And (Abs(y - 8.9250) < 0.001) And (Abs(x2 - 33.9499) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 33.9499) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 33.9750) < 0.001) And (Abs(y2 - 8.9250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eTopLayer) And (((Abs(x - 44.6501) < 0.001) And (Abs(y - 7.1875) < 0.001) And (Abs(x2 - 44.6500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 44.6500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 44.6501) < 0.001) And (Abs(y2 - 7.1875) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eTopLayer) And (((Abs(x - 44.6500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 44.3000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 44.3000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 44.6500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eMidLayer2) And (((Abs(x - 44.3000) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 43.9750) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 43.9750) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 44.3000) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eMidLayer2) And (((Abs(x - 43.9750) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 41.6750) < 0.001) And (Abs(y2 - 5.5000) < 0.001)) Or ((Abs(x - 41.6750) < 0.001) And (Abs(y - 5.5000) < 0.001) And (Abs(x2 - 43.9750) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eMidLayer2) And (((Abs(x - 41.6750) < 0.001) And (Abs(y - 5.5000) < 0.001) And (Abs(x2 - 37.4750) < 0.001) And (Abs(y2 - 6.0250) < 0.001)) Or ((Abs(x - 37.4750) < 0.001) And (Abs(y - 6.0250) < 0.001) And (Abs(x2 - 41.6750) < 0.001) And (Abs(y2 - 5.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eMidLayer2) And (((Abs(x - 37.4750) < 0.001) And (Abs(y - 6.0250) < 0.001) And (Abs(x2 - 36.7500) < 0.001) And (Abs(y2 - 6.7500) < 0.001)) Or ((Abs(x - 36.7500) < 0.001) And (Abs(y - 6.7500) < 0.001) And (Abs(x2 - 37.4750) < 0.001) And (Abs(y2 - 6.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eMidLayer2) And (((Abs(x - 36.7500) < 0.001) And (Abs(y - 6.7500) < 0.001) And (Abs(x2 - 36.7500) < 0.001) And (Abs(y2 - 7.0250) < 0.001)) Or ((Abs(x - 36.7500) < 0.001) And (Abs(y - 7.0250) < 0.001) And (Abs(x2 - 36.7500) < 0.001) And (Abs(y2 - 6.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D1') And (T.Layer = eBottomLayer) And (((Abs(x - 36.7500) < 0.001) And (Abs(y - 7.0250) < 0.001) And (Abs(x2 - 36.3500) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 36.3500) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 36.7500) < 0.001) And (Abs(y2 - 7.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D2') And (T.Layer = eTopLayer) And (((Abs(x - 44.9000) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 44.9000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 44.9000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 44.9000) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D2') And (T.Layer = eTopLayer) And (((Abs(x - 44.9000) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 44.7750) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 44.7750) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 44.9000) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D2') And (T.Layer = eMidLayer1) And (((Abs(x - 44.7750) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 44.4500) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 44.4500) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 44.7750) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D2') And (T.Layer = eMidLayer1) And (((Abs(x - 44.4500) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 43.1250) < 0.001) And (Abs(y2 - 5.3250) < 0.001)) Or ((Abs(x - 43.1250) < 0.001) And (Abs(y - 5.3250) < 0.001) And (Abs(x2 - 44.4500) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D2') And (T.Layer = eMidLayer1) And (((Abs(x - 43.1250) < 0.001) And (Abs(y - 5.3250) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 6.4250) < 0.001)) Or ((Abs(x - 36.2750) < 0.001) And (Abs(y - 6.4250) < 0.001) And (Abs(x2 - 43.1250) < 0.001) And (Abs(y2 - 5.3250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D2') And (T.Layer = eMidLayer1) And (((Abs(x - 36.2750) < 0.001) And (Abs(y - 6.4250) < 0.001) And (Abs(x2 - 35.6500) < 0.001) And (Abs(y2 - 7.0750) < 0.001)) Or ((Abs(x - 35.6500) < 0.001) And (Abs(y - 7.0750) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 6.4250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D2') And (T.Layer = eBottomLayer) And (((Abs(x - 35.6500) < 0.001) And (Abs(y - 7.0750) < 0.001) And (Abs(x2 - 35.5501) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 35.5501) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 35.6500) < 0.001) And (Abs(y2 - 7.0750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D0') And (T.Layer = eTopLayer) And (((Abs(x - 45.1501) < 0.001) And (Abs(y - 7.1875) < 0.001) And (Abs(x2 - 45.1500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)) Or ((Abs(x - 45.1500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 45.1501) < 0.001) And (Abs(y2 - 7.1875) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D0') And (T.Layer = eTopLayer) And (((Abs(x - 45.1500) < 0.001) And (Abs(y - 6.5500) < 0.001) And (Abs(x2 - 45.2500) < 0.001) And (Abs(y2 - 4.4000) < 0.001)) Or ((Abs(x - 45.2500) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 45.1500) < 0.001) And (Abs(y2 - 6.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D0') And (T.Layer = eMidLayer2) And (((Abs(x - 45.2500) < 0.001) And (Abs(y - 4.4000) < 0.001) And (Abs(x2 - 44.9250) < 0.001) And (Abs(y2 - 4.7500) < 0.001)) Or ((Abs(x - 44.9250) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 45.2500) < 0.001) And (Abs(y2 - 4.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D0') And (T.Layer = eMidLayer2) And (((Abs(x - 44.9250) < 0.001) And (Abs(y - 4.7500) < 0.001) And (Abs(x2 - 41.7000) < 0.001) And (Abs(y2 - 5.7500) < 0.001)) Or ((Abs(x - 41.7000) < 0.001) And (Abs(y - 5.7500) < 0.001) And (Abs(x2 - 44.9250) < 0.001) And (Abs(y2 - 4.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D0') And (T.Layer = eMidLayer2) And (((Abs(x - 41.7000) < 0.001) And (Abs(y - 5.7500) < 0.001) And (Abs(x2 - 39.0000) < 0.001) And (Abs(y2 - 6.0750) < 0.001)) Or ((Abs(x - 39.0000) < 0.001) And (Abs(y - 6.0750) < 0.001) And (Abs(x2 - 41.7000) < 0.001) And (Abs(y2 - 5.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D0') And (T.Layer = eMidLayer2) And (((Abs(x - 39.0000) < 0.001) And (Abs(y - 6.0750) < 0.001) And (Abs(x2 - 38.0250) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 38.0250) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 39.0000) < 0.001) And (Abs(y2 - 6.0750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D0') And (T.Layer = eBottomLayer) And (((Abs(x - 38.0250) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 37.9499) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 37.9499) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 38.0250) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D14') And (T.Layer = eTopLayer) And (((Abs(x - 48.4001) < 0.001) And (Abs(y - 16.4000) < 0.001) And (Abs(x2 - 48.3250) < 0.001) And (Abs(y2 - 16.7250) < 0.001)) Or ((Abs(x - 48.3250) < 0.001) And (Abs(y - 16.7250) < 0.001) And (Abs(x2 - 48.4001) < 0.001) And (Abs(y2 - 16.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D14') And (T.Layer = eTopLayer) And (((Abs(x - 48.3250) < 0.001) And (Abs(y - 16.7250) < 0.001) And (Abs(x2 - 47.9000) < 0.001) And (Abs(y2 - 17.1500) < 0.001)) Or ((Abs(x - 47.9000) < 0.001) And (Abs(y - 17.1500) < 0.001) And (Abs(x2 - 48.3250) < 0.001) And (Abs(y2 - 16.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D14') And (T.Layer = eMidLayer2) And (((Abs(x - 47.9000) < 0.001) And (Abs(y - 17.1500) < 0.001) And (Abs(x2 - 38.0000) < 0.001) And (Abs(y2 - 17.2500) < 0.001)) Or ((Abs(x - 38.0000) < 0.001) And (Abs(y - 17.2500) < 0.001) And (Abs(x2 - 47.9000) < 0.001) And (Abs(y2 - 17.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D14') And (T.Layer = eMidLayer2) And (((Abs(x - 38.0000) < 0.001) And (Abs(y - 17.2500) < 0.001) And (Abs(x2 - 36.7250) < 0.001) And (Abs(y2 - 17.2500) < 0.001)) Or ((Abs(x - 36.7250) < 0.001) And (Abs(y - 17.2500) < 0.001) And (Abs(x2 - 38.0000) < 0.001) And (Abs(y2 - 17.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D14') And (T.Layer = eMidLayer2) And (((Abs(x - 36.7250) < 0.001) And (Abs(y - 17.2500) < 0.001) And (Abs(x2 - 36.1250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 36.1250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 36.7250) < 0.001) And (Abs(y2 - 17.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D14') And (T.Layer = eBottomLayer) And (((Abs(x - 36.1250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 36.3500) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 36.3500) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 36.1250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D15') And (T.Layer = eTopLayer) And (((Abs(x - 48.9000) < 0.001) And (Abs(y - 16.4000) < 0.001) And (Abs(x2 - 48.9000) < 0.001) And (Abs(y2 - 16.8000) < 0.001)) Or ((Abs(x - 48.9000) < 0.001) And (Abs(y - 16.8000) < 0.001) And (Abs(x2 - 48.9000) < 0.001) And (Abs(y2 - 16.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D15') And (T.Layer = eMidLayer2) And (((Abs(x - 48.9000) < 0.001) And (Abs(y - 16.8000) < 0.001) And (Abs(x2 - 38.3500) < 0.001) And (Abs(y2 - 16.7250) < 0.001)) Or ((Abs(x - 38.3500) < 0.001) And (Abs(y - 16.7250) < 0.001) And (Abs(x2 - 48.9000) < 0.001) And (Abs(y2 - 16.8000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D15') And (T.Layer = eBottomLayer) And (((Abs(x - 38.3500) < 0.001) And (Abs(y - 16.7250) < 0.001) And (Abs(x2 - 37.9499) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 37.9499) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 38.3500) < 0.001) And (Abs(y2 - 16.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 43.9000) < 0.001) And (Abs(y - 8.8999) < 0.001) And (Abs(x2 - 43.7000) < 0.001) And (Abs(y2 - 7.3250) < 0.001)) Or ((Abs(x - 43.7000) < 0.001) And (Abs(y - 7.3250) < 0.001) And (Abs(x2 - 43.9000) < 0.001) And (Abs(y2 - 8.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 43.7000) < 0.001) And (Abs(y - 7.3250) < 0.001) And (Abs(x2 - 43.6750) < 0.001) And (Abs(y2 - 7.3000) < 0.001)) Or ((Abs(x - 43.6750) < 0.001) And (Abs(y - 7.3000) < 0.001) And (Abs(x2 - 43.7000) < 0.001) And (Abs(y2 - 7.3250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 43.6750) < 0.001) And (Abs(y - 7.3000) < 0.001) And (Abs(x2 - 40.9750) < 0.001) And (Abs(y2 - 7.3000) < 0.001)) Or ((Abs(x - 40.9750) < 0.001) And (Abs(y - 7.3000) < 0.001) And (Abs(x2 - 43.6750) < 0.001) And (Abs(y2 - 7.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 40.9750) < 0.001) And (Abs(y - 7.3000) < 0.001) And (Abs(x2 - 40.5750) < 0.001) And (Abs(y2 - 6.9000) < 0.001)) Or ((Abs(x - 40.5750) < 0.001) And (Abs(y - 6.9000) < 0.001) And (Abs(x2 - 40.9750) < 0.001) And (Abs(y2 - 7.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 40.5750) < 0.001) And (Abs(y - 6.9000) < 0.001) And (Abs(x2 - 38.6750) < 0.001) And (Abs(y2 - 6.9000) < 0.001)) Or ((Abs(x - 38.6750) < 0.001) And (Abs(y - 6.9000) < 0.001) And (Abs(x2 - 40.5750) < 0.001) And (Abs(y2 - 6.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 38.6750) < 0.001) And (Abs(y - 6.9000) < 0.001) And (Abs(x2 - 38.1750) < 0.001) And (Abs(y2 - 7.3750) < 0.001)) Or ((Abs(x - 38.1750) < 0.001) And (Abs(y - 7.3750) < 0.001) And (Abs(x2 - 38.6750) < 0.001) And (Abs(y2 - 6.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 38.1750) < 0.001) And (Abs(y - 7.3750) < 0.001) And (Abs(x2 - 35.8000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 35.8000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 38.1750) < 0.001) And (Abs(y2 - 7.3750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 35.8000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 33.8750) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 33.8750) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 35.8000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 33.8750) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 33.3250) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 33.3250) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 33.8750) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eMidLayer2) And (((Abs(x - 33.3250) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 33.3250) < 0.001) And (Abs(y2 - 8.9500) < 0.001)) Or ((Abs(x - 33.3250) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 33.3250) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D4') And (T.Layer = eBottomLayer) And (((Abs(x - 33.3250) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 33.1501) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 33.1501) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 33.3250) < 0.001) And (Abs(y2 - 8.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 8.8999) < 0.001) And (Abs(x2 - 41.0000) < 0.001) And (Abs(y2 - 7.5500) < 0.001)) Or ((Abs(x - 41.0000) < 0.001) And (Abs(y - 7.5500) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 8.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 41.0000) < 0.001) And (Abs(y - 7.5500) < 0.001) And (Abs(x2 - 40.8250) < 0.001) And (Abs(y2 - 7.5500) < 0.001)) Or ((Abs(x - 40.8250) < 0.001) And (Abs(y - 7.5500) < 0.001) And (Abs(x2 - 41.0000) < 0.001) And (Abs(y2 - 7.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 40.8250) < 0.001) And (Abs(y - 7.5500) < 0.001) And (Abs(x2 - 40.4750) < 0.001) And (Abs(y2 - 7.2000) < 0.001)) Or ((Abs(x - 40.4750) < 0.001) And (Abs(y - 7.2000) < 0.001) And (Abs(x2 - 40.8250) < 0.001) And (Abs(y2 - 7.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 40.4750) < 0.001) And (Abs(y - 7.2000) < 0.001) And (Abs(x2 - 38.7000) < 0.001) And (Abs(y2 - 7.2000) < 0.001)) Or ((Abs(x - 38.7000) < 0.001) And (Abs(y - 7.2000) < 0.001) And (Abs(x2 - 40.4750) < 0.001) And (Abs(y2 - 7.2000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 38.7000) < 0.001) And (Abs(y - 7.2000) < 0.001) And (Abs(x2 - 36.8250) < 0.001) And (Abs(y2 - 8.9250) < 0.001)) Or ((Abs(x - 36.8250) < 0.001) And (Abs(y - 8.9250) < 0.001) And (Abs(x2 - 38.7000) < 0.001) And (Abs(y2 - 7.2000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 36.8250) < 0.001) And (Abs(y - 8.9250) < 0.001) And (Abs(x2 - 35.9000) < 0.001) And (Abs(y2 - 9.7250) < 0.001)) Or ((Abs(x - 35.9000) < 0.001) And (Abs(y - 9.7250) < 0.001) And (Abs(x2 - 36.8250) < 0.001) And (Abs(y2 - 8.9250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 35.9000) < 0.001) And (Abs(y - 9.7250) < 0.001) And (Abs(x2 - 33.3000) < 0.001) And (Abs(y2 - 9.7500) < 0.001)) Or ((Abs(x - 33.3000) < 0.001) And (Abs(y - 9.7500) < 0.001) And (Abs(x2 - 35.9000) < 0.001) And (Abs(y2 - 9.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 33.3000) < 0.001) And (Abs(y - 9.7500) < 0.001) And (Abs(x2 - 29.8750) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 29.8750) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 33.3000) < 0.001) And (Abs(y2 - 9.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 29.8750) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 29.3250) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 29.3250) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 29.8750) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eMidLayer2) And (((Abs(x - 29.3250) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 29.3250) < 0.001) And (Abs(y2 - 8.9500) < 0.001)) Or ((Abs(x - 29.3250) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 29.3250) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D7') And (T.Layer = eBottomLayer) And (((Abs(x - 29.3250) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 29.1501) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 29.1501) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 29.3250) < 0.001) And (Abs(y2 - 8.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 7.6500) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 7.5600) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 7.5600) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 7.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 7.5600) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 7.5600) < 0.001)) Or ((Abs(x - 40.5000) < 0.001) And (Abs(y - 7.5600) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 7.5600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eTopLayer) And (((Abs(x - 40.5000) < 0.001) And (Abs(y - 7.5600) < 0.001) And (Abs(x2 - 40.2000) < 0.001) And (Abs(y2 - 7.5500) < 0.001)) Or ((Abs(x - 40.2000) < 0.001) And (Abs(y - 7.5500) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 7.5600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eMidLayer1) And (((Abs(x - 40.2000) < 0.001) And (Abs(y - 7.5500) < 0.001) And (Abs(x2 - 39.8750) < 0.001) And (Abs(y2 - 7.4000) < 0.001)) Or ((Abs(x - 39.8750) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 40.2000) < 0.001) And (Abs(y2 - 7.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eMidLayer1) And (((Abs(x - 39.8750) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 37.9000) < 0.001) And (Abs(y2 - 7.4000) < 0.001)) Or ((Abs(x - 37.9000) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 39.8750) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eMidLayer1) And (((Abs(x - 37.9000) < 0.001) And (Abs(y - 7.4000) < 0.001) And (Abs(x2 - 35.8000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 35.8000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 37.9000) < 0.001) And (Abs(y2 - 7.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eMidLayer1) And (((Abs(x - 35.8000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 27.2000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 27.2000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 35.8000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eMidLayer1) And (((Abs(x - 27.2000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 24.2500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 24.2500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 27.2000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eMidLayer1) And (((Abs(x - 24.2500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 23.5500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 23.5500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 24.2500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS0') And (T.Layer = eBottomLayer) And (((Abs(x - 23.5500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 23.5499) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 23.5499) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 23.5500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 8.4000) < 0.001) And (Abs(x2 - 41.7000) < 0.001) And (Abs(y2 - 8.3300) < 0.001)) Or ((Abs(x - 41.7000) < 0.001) And (Abs(y - 8.3300) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 8.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eTopLayer) And (((Abs(x - 41.7000) < 0.001) And (Abs(y - 8.3300) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 8.3300) < 0.001)) Or ((Abs(x - 41.4000) < 0.001) And (Abs(y - 8.3300) < 0.001) And (Abs(x2 - 41.7000) < 0.001) And (Abs(y2 - 8.3300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eTopLayer) And (((Abs(x - 41.4000) < 0.001) And (Abs(y - 8.3300) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 8.3800) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 8.3800) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 8.3300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 8.3800) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 8.3800) < 0.001)) Or ((Abs(x - 40.5000) < 0.001) And (Abs(y - 8.3800) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 8.3800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eTopLayer) And (((Abs(x - 40.5000) < 0.001) And (Abs(y - 8.3800) < 0.001) And (Abs(x2 - 40.0000) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 40.0000) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 8.3800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eTopLayer) And (((Abs(x - 40.0000) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 39.7500) < 0.001) And (Abs(y2 - 8.2500) < 0.001)) Or ((Abs(x - 39.7500) < 0.001) And (Abs(y - 8.2500) < 0.001) And (Abs(x2 - 40.0000) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 39.7500) < 0.001) And (Abs(y - 8.2500) < 0.001) And (Abs(x2 - 39.5250) < 0.001) And (Abs(y2 - 7.9500) < 0.001)) Or ((Abs(x - 39.5250) < 0.001) And (Abs(y - 7.9500) < 0.001) And (Abs(x2 - 39.7500) < 0.001) And (Abs(y2 - 8.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 39.5250) < 0.001) And (Abs(y - 7.9500) < 0.001) And (Abs(x2 - 38.2000) < 0.001) And (Abs(y2 - 7.9750) < 0.001)) Or ((Abs(x - 38.2000) < 0.001) And (Abs(y - 7.9750) < 0.001) And (Abs(x2 - 39.5250) < 0.001) And (Abs(y2 - 7.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 38.2000) < 0.001) And (Abs(y - 7.9750) < 0.001) And (Abs(x2 - 36.4500) < 0.001) And (Abs(y2 - 9.5750) < 0.001)) Or ((Abs(x - 36.4500) < 0.001) And (Abs(y - 9.5750) < 0.001) And (Abs(x2 - 38.2000) < 0.001) And (Abs(y2 - 7.9750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 36.4500) < 0.001) And (Abs(y - 9.5750) < 0.001) And (Abs(x2 - 36.0000) < 0.001) And (Abs(y2 - 9.9500) < 0.001)) Or ((Abs(x - 36.0000) < 0.001) And (Abs(y - 9.9500) < 0.001) And (Abs(x2 - 36.4500) < 0.001) And (Abs(y2 - 9.5750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 36.0000) < 0.001) And (Abs(y - 9.9500) < 0.001) And (Abs(x2 - 31.1500) < 0.001) And (Abs(y2 - 10.0000) < 0.001)) Or ((Abs(x - 31.1500) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 36.0000) < 0.001) And (Abs(y2 - 9.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 31.1500) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 27.2000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)) Or ((Abs(x - 27.2000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 31.1500) < 0.001) And (Abs(y2 - 10.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 27.2000) < 0.001) And (Abs(y - 9.5000) < 0.001) And (Abs(x2 - 23.4500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 23.4500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 27.2000) < 0.001) And (Abs(y2 - 9.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eMidLayer2) And (((Abs(x - 23.4500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 22.7500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 22.7500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 23.4500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'BS1') And (T.Layer = eBottomLayer) And (((Abs(x - 22.7500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 22.7500) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 22.7500) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 22.7500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 8.1500) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 8.1500) < 0.001)) Or ((Abs(x - 41.3500) < 0.001) And (Abs(y - 8.1500) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 8.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eTopLayer) And (((Abs(x - 41.3500) < 0.001) And (Abs(y - 8.1500) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 8.2100) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 8.2100) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 8.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 8.2100) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 8.2100) < 0.001)) Or ((Abs(x - 40.5000) < 0.001) And (Abs(y - 8.2100) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 8.2100) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eTopLayer) And (((Abs(x - 40.5000) < 0.001) And (Abs(y - 8.2100) < 0.001) And (Abs(x2 - 40.2500) < 0.001) And (Abs(y2 - 8.1000) < 0.001)) Or ((Abs(x - 40.2500) < 0.001) And (Abs(y - 8.1000) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 8.2100) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 40.2500) < 0.001) And (Abs(y - 8.1000) < 0.001) And (Abs(x2 - 39.9750) < 0.001) And (Abs(y2 - 7.9000) < 0.001)) Or ((Abs(x - 39.9750) < 0.001) And (Abs(y - 7.9000) < 0.001) And (Abs(x2 - 40.2500) < 0.001) And (Abs(y2 - 8.1000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 39.9750) < 0.001) And (Abs(y - 7.9000) < 0.001) And (Abs(x2 - 37.7250) < 0.001) And (Abs(y2 - 7.9000) < 0.001)) Or ((Abs(x - 37.7250) < 0.001) And (Abs(y - 7.9000) < 0.001) And (Abs(x2 - 39.9750) < 0.001) And (Abs(y2 - 7.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 37.7250) < 0.001) And (Abs(y - 7.9000) < 0.001) And (Abs(x2 - 35.9000) < 0.001) And (Abs(y2 - 9.7250) < 0.001)) Or ((Abs(x - 35.9000) < 0.001) And (Abs(y - 9.7250) < 0.001) And (Abs(x2 - 37.7250) < 0.001) And (Abs(y2 - 7.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 35.9000) < 0.001) And (Abs(y - 9.7250) < 0.001) And (Abs(x2 - 35.8250) < 0.001) And (Abs(y2 - 9.7500) < 0.001)) Or ((Abs(x - 35.8250) < 0.001) And (Abs(y - 9.7500) < 0.001) And (Abs(x2 - 35.9000) < 0.001) And (Abs(y2 - 9.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 35.8250) < 0.001) And (Abs(y - 9.7500) < 0.001) And (Abs(x2 - 27.1750) < 0.001) And (Abs(y2 - 9.7500) < 0.001)) Or ((Abs(x - 27.1750) < 0.001) And (Abs(y - 9.7500) < 0.001) And (Abs(x2 - 35.8250) < 0.001) And (Abs(y2 - 9.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 27.1750) < 0.001) And (Abs(y - 9.7500) < 0.001) And (Abs(x2 - 21.8750) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 21.8750) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 27.1750) < 0.001) And (Abs(y2 - 9.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 21.8750) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 21.8500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 21.8500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 21.8750) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 21.8500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 21.8500) < 0.001) And (Abs(y2 - 8.4250) < 0.001)) Or ((Abs(x - 21.8500) < 0.001) And (Abs(y - 8.4250) < 0.001) And (Abs(x2 - 21.8500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eMidLayer1) And (((Abs(x - 21.8500) < 0.001) And (Abs(y - 8.4250) < 0.001) And (Abs(x2 - 21.1500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 21.1500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 21.8500) < 0.001) And (Abs(y2 - 8.4250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A0') And (T.Layer = eBottomLayer) And (((Abs(x - 21.1500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 21.1501) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 21.1501) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 21.1500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 41.4000) < 0.001) And (Abs(y - 8.6500) < 0.001) And (Abs(x2 - 40.9250) < 0.001) And (Abs(y2 - 8.4750) < 0.001)) Or ((Abs(x - 40.9250) < 0.001) And (Abs(y - 8.4750) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 8.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 40.9250) < 0.001) And (Abs(y - 8.4750) < 0.001) And (Abs(x2 - 40.0250) < 0.001) And (Abs(y2 - 8.4750) < 0.001)) Or ((Abs(x - 40.0250) < 0.001) And (Abs(y - 8.4750) < 0.001) And (Abs(x2 - 40.9250) < 0.001) And (Abs(y2 - 8.4750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 40.0250) < 0.001) And (Abs(y - 8.4750) < 0.001) And (Abs(x2 - 39.8500) < 0.001) And (Abs(y2 - 8.6000) < 0.001)) Or ((Abs(x - 39.8500) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 40.0250) < 0.001) And (Abs(y2 - 8.4750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 39.8500) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 39.5500) < 0.001) And (Abs(y2 - 8.6000) < 0.001)) Or ((Abs(x - 39.5500) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 39.8500) < 0.001) And (Abs(y2 - 8.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 39.5500) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 39.3000) < 0.001) And (Abs(y2 - 8.3750) < 0.001)) Or ((Abs(x - 39.3000) < 0.001) And (Abs(y - 8.3750) < 0.001) And (Abs(x2 - 39.5500) < 0.001) And (Abs(y2 - 8.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 39.3000) < 0.001) And (Abs(y - 8.3750) < 0.001) And (Abs(x2 - 39.2500) < 0.001) And (Abs(y2 - 8.3500) < 0.001)) Or ((Abs(x - 39.2500) < 0.001) And (Abs(y - 8.3500) < 0.001) And (Abs(x2 - 39.3000) < 0.001) And (Abs(y2 - 8.3750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 39.2500) < 0.001) And (Abs(y - 8.3500) < 0.001) And (Abs(x2 - 38.0750) < 0.001) And (Abs(y2 - 8.4000) < 0.001)) Or ((Abs(x - 38.0750) < 0.001) And (Abs(y - 8.4000) < 0.001) And (Abs(x2 - 39.2500) < 0.001) And (Abs(y2 - 8.3500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 38.0750) < 0.001) And (Abs(y - 8.4000) < 0.001) And (Abs(x2 - 36.3250) < 0.001) And (Abs(y2 - 10.0000) < 0.001)) Or ((Abs(x - 36.3250) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 38.0750) < 0.001) And (Abs(y2 - 8.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 36.3250) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 36.1000) < 0.001) And (Abs(y2 - 10.1750) < 0.001)) Or ((Abs(x - 36.1000) < 0.001) And (Abs(y - 10.1750) < 0.001) And (Abs(x2 - 36.3250) < 0.001) And (Abs(y2 - 10.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 36.1000) < 0.001) And (Abs(y - 10.1750) < 0.001) And (Abs(x2 - 30.9000) < 0.001) And (Abs(y2 - 10.2500) < 0.001)) Or ((Abs(x - 30.9000) < 0.001) And (Abs(y - 10.2500) < 0.001) And (Abs(x2 - 36.1000) < 0.001) And (Abs(y2 - 10.1750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 30.9000) < 0.001) And (Abs(y - 10.2500) < 0.001) And (Abs(x2 - 27.0000) < 0.001) And (Abs(y2 - 9.7000) < 0.001)) Or ((Abs(x - 27.0000) < 0.001) And (Abs(y - 9.7000) < 0.001) And (Abs(x2 - 30.9000) < 0.001) And (Abs(y2 - 10.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 27.0000) < 0.001) And (Abs(y - 9.7000) < 0.001) And (Abs(x2 - 23.3500) < 0.001) And (Abs(y2 - 8.6750) < 0.001)) Or ((Abs(x - 23.3500) < 0.001) And (Abs(y - 8.6750) < 0.001) And (Abs(x2 - 27.0000) < 0.001) And (Abs(y2 - 9.7000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 23.3500) < 0.001) And (Abs(y - 8.6750) < 0.001) And (Abs(x2 - 22.6500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 22.6500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 23.3500) < 0.001) And (Abs(y2 - 8.6750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eMidLayer2) And (((Abs(x - 22.6500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 21.9500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 21.9500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 22.6500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A10') And (T.Layer = eBottomLayer) And (((Abs(x - 21.9500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 21.9499) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 21.9499) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 21.9500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 9.4000) < 0.001) And (Abs(x2 - 40.2750) < 0.001) And (Abs(y2 - 8.9500) < 0.001)) Or ((Abs(x - 40.2750) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 9.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 40.2750) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 39.2500) < 0.001) And (Abs(y2 - 8.3500) < 0.001)) Or ((Abs(x - 39.2500) < 0.001) And (Abs(y - 8.3500) < 0.001) And (Abs(x2 - 40.2750) < 0.001) And (Abs(y2 - 8.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 39.2500) < 0.001) And (Abs(y - 8.3500) < 0.001) And (Abs(x2 - 37.6250) < 0.001) And (Abs(y2 - 8.3500) < 0.001)) Or ((Abs(x - 37.6250) < 0.001) And (Abs(y - 8.3500) < 0.001) And (Abs(x2 - 39.2500) < 0.001) And (Abs(y2 - 8.3500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 37.6250) < 0.001) And (Abs(y - 8.3500) < 0.001) And (Abs(x2 - 36.0000) < 0.001) And (Abs(y2 - 9.9500) < 0.001)) Or ((Abs(x - 36.0000) < 0.001) And (Abs(y - 9.9500) < 0.001) And (Abs(x2 - 37.6250) < 0.001) And (Abs(y2 - 8.3500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 36.0000) < 0.001) And (Abs(y - 9.9500) < 0.001) And (Abs(x2 - 35.8500) < 0.001) And (Abs(y2 - 10.0000) < 0.001)) Or ((Abs(x - 35.8500) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 36.0000) < 0.001) And (Abs(y2 - 9.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 35.8500) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 27.1500) < 0.001) And (Abs(y2 - 10.0000) < 0.001)) Or ((Abs(x - 27.1500) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 35.8500) < 0.001) And (Abs(y2 - 10.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 27.1500) < 0.001) And (Abs(y - 10.0000) < 0.001) And (Abs(x2 - 21.7500) < 0.001) And (Abs(y2 - 8.6750) < 0.001)) Or ((Abs(x - 21.7500) < 0.001) And (Abs(y - 8.6750) < 0.001) And (Abs(x2 - 27.1500) < 0.001) And (Abs(y2 - 10.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 21.7500) < 0.001) And (Abs(y - 8.6750) < 0.001) And (Abs(x2 - 21.0500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 21.0500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 21.7500) < 0.001) And (Abs(y2 - 8.6750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eMidLayer1) And (((Abs(x - 21.0500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 20.3500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 20.3500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 21.0500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A1') And (T.Layer = eBottomLayer) And (((Abs(x - 20.3500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 20.3500) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 20.3500) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 20.3500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 8.8999) < 0.001) And (Abs(x2 - 41.7000) < 0.001) And (Abs(y2 - 8.9200) < 0.001)) Or ((Abs(x - 41.7000) < 0.001) And (Abs(y - 8.9200) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 8.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eTopLayer) And (((Abs(x - 41.7000) < 0.001) And (Abs(y - 8.9200) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 8.9600) < 0.001)) Or ((Abs(x - 41.4000) < 0.001) And (Abs(y - 8.9600) < 0.001) And (Abs(x2 - 41.7000) < 0.001) And (Abs(y2 - 8.9200) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eTopLayer) And (((Abs(x - 41.4000) < 0.001) And (Abs(y - 8.9600) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 8.9300) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 8.9300) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 8.9600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 8.9300) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 8.9000) < 0.001)) Or ((Abs(x - 40.5000) < 0.001) And (Abs(y - 8.9000) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 8.9300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eTopLayer) And (((Abs(x - 40.5000) < 0.001) And (Abs(y - 8.9000) < 0.001) And (Abs(x2 - 39.1500) < 0.001) And (Abs(y2 - 8.7000) < 0.001)) Or ((Abs(x - 39.1500) < 0.001) And (Abs(y - 8.7000) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 8.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eMidLayer1) And (((Abs(x - 39.1500) < 0.001) And (Abs(y - 8.7000) < 0.001) And (Abs(x2 - 38.7000) < 0.001) And (Abs(y2 - 8.6000) < 0.001)) Or ((Abs(x - 38.7000) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 39.1500) < 0.001) And (Abs(y2 - 8.7000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eMidLayer1) And (((Abs(x - 38.7000) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 38.4000) < 0.001) And (Abs(y2 - 8.6000) < 0.001)) Or ((Abs(x - 38.4000) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 38.7000) < 0.001) And (Abs(y2 - 8.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eMidLayer1) And (((Abs(x - 38.4000) < 0.001) And (Abs(y - 8.6000) < 0.001) And (Abs(x2 - 36.1000) < 0.001) And (Abs(y2 - 10.1750) < 0.001)) Or ((Abs(x - 36.1000) < 0.001) And (Abs(y - 10.1750) < 0.001) And (Abs(x2 - 38.4000) < 0.001) And (Abs(y2 - 8.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eMidLayer1) And (((Abs(x - 36.1000) < 0.001) And (Abs(y - 10.1750) < 0.001) And (Abs(x2 - 35.8750) < 0.001) And (Abs(y2 - 10.2500) < 0.001)) Or ((Abs(x - 35.8750) < 0.001) And (Abs(y - 10.2500) < 0.001) And (Abs(x2 - 36.1000) < 0.001) And (Abs(y2 - 10.1750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eMidLayer1) And (((Abs(x - 35.8750) < 0.001) And (Abs(y - 10.2500) < 0.001) And (Abs(x2 - 27.1250) < 0.001) And (Abs(y2 - 10.2500) < 0.001)) Or ((Abs(x - 27.1250) < 0.001) And (Abs(y - 10.2500) < 0.001) And (Abs(x2 - 35.8750) < 0.001) And (Abs(y2 - 10.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eMidLayer1) And (((Abs(x - 27.1250) < 0.001) And (Abs(y - 10.2500) < 0.001) And (Abs(x2 - 19.4500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 19.4500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 27.1250) < 0.001) And (Abs(y2 - 10.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eMidLayer1) And (((Abs(x - 19.4500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 18.7500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 18.7500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 19.4500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A3') And (T.Layer = eBottomLayer) And (((Abs(x - 18.7500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 18.7500) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 18.7500) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 18.7500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 9.1500) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 9.1400) < 0.001)) Or ((Abs(x - 41.4000) < 0.001) And (Abs(y - 9.1400) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 9.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eTopLayer) And (((Abs(x - 41.4000) < 0.001) And (Abs(y - 9.1400) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 9.1200) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 9.1200) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 9.1400) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 9.1200) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 9.0800) < 0.001)) Or ((Abs(x - 40.5000) < 0.001) And (Abs(y - 9.0800) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 9.1200) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eTopLayer) And (((Abs(x - 40.5000) < 0.001) And (Abs(y - 9.0800) < 0.001) And (Abs(x2 - 40.1000) < 0.001) And (Abs(y2 - 9.0800) < 0.001)) Or ((Abs(x - 40.1000) < 0.001) And (Abs(y - 9.0800) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 9.0800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eTopLayer) And (((Abs(x - 40.1000) < 0.001) And (Abs(y - 9.0800) < 0.001) And (Abs(x2 - 39.8000) < 0.001) And (Abs(y2 - 9.2000) < 0.001)) Or ((Abs(x - 39.8000) < 0.001) And (Abs(y - 9.2000) < 0.001) And (Abs(x2 - 40.1000) < 0.001) And (Abs(y2 - 9.0800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eTopLayer) And (((Abs(x - 39.8000) < 0.001) And (Abs(y - 9.2000) < 0.001) And (Abs(x2 - 38.6000) < 0.001) And (Abs(y2 - 8.9500) < 0.001)) Or ((Abs(x - 38.6000) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 39.8000) < 0.001) And (Abs(y2 - 9.2000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eMidLayer2) And (((Abs(x - 38.6000) < 0.001) And (Abs(y - 8.9500) < 0.001) And (Abs(x2 - 36.1250) < 0.001) And (Abs(y2 - 10.4250) < 0.001)) Or ((Abs(x - 36.1250) < 0.001) And (Abs(y - 10.4250) < 0.001) And (Abs(x2 - 38.6000) < 0.001) And (Abs(y2 - 8.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eMidLayer2) And (((Abs(x - 36.1250) < 0.001) And (Abs(y - 10.4250) < 0.001) And (Abs(x2 - 29.0500) < 0.001) And (Abs(y2 - 10.5000) < 0.001)) Or ((Abs(x - 29.0500) < 0.001) And (Abs(y - 10.5000) < 0.001) And (Abs(x2 - 36.1250) < 0.001) And (Abs(y2 - 10.4250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eMidLayer2) And (((Abs(x - 29.0500) < 0.001) And (Abs(y - 10.5000) < 0.001) And (Abs(x2 - 20.2500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)) Or ((Abs(x - 20.2500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 29.0500) < 0.001) And (Abs(y2 - 10.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eMidLayer2) And (((Abs(x - 20.2500) < 0.001) And (Abs(y - 8.4500) < 0.001) And (Abs(x2 - 19.5500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)) Or ((Abs(x - 19.5500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 20.2500) < 0.001) And (Abs(y2 - 8.4500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A2') And (T.Layer = eBottomLayer) And (((Abs(x - 19.5500) < 0.001) And (Abs(y - 7.0500) < 0.001) And (Abs(x2 - 19.5499) < 0.001) And (Abs(y2 - 6.1701) < 0.001)) Or ((Abs(x - 19.5499) < 0.001) And (Abs(y - 6.1701) < 0.001) And (Abs(x2 - 19.5500) < 0.001) And (Abs(y2 - 7.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 12.4000) < 0.001) And (Abs(x2 - 42.4250) < 0.001) And (Abs(y2 - 12.6000) < 0.001)) Or ((Abs(x - 42.4250) < 0.001) And (Abs(y - 12.6000) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 12.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 42.4250) < 0.001) And (Abs(y - 12.6000) < 0.001) And (Abs(x2 - 41.7500) < 0.001) And (Abs(y2 - 13.2750) < 0.001)) Or ((Abs(x - 41.7500) < 0.001) And (Abs(y - 13.2750) < 0.001) And (Abs(x2 - 42.4250) < 0.001) And (Abs(y2 - 12.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 41.7500) < 0.001) And (Abs(y - 13.2750) < 0.001) And (Abs(x2 - 41.7500) < 0.001) And (Abs(y2 - 14.5000) < 0.001)) Or ((Abs(x - 41.7500) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 41.7500) < 0.001) And (Abs(y2 - 13.2750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 41.7500) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 41.6000) < 0.001) And (Abs(y2 - 14.7000) < 0.001)) Or ((Abs(x - 41.6000) < 0.001) And (Abs(y - 14.7000) < 0.001) And (Abs(x2 - 41.7500) < 0.001) And (Abs(y2 - 14.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 41.6000) < 0.001) And (Abs(y - 14.7000) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 14.7500) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 14.7500) < 0.001) And (Abs(x2 - 41.6000) < 0.001) And (Abs(y2 - 14.7000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 14.7500) < 0.001) And (Abs(x2 - 38.6000) < 0.001) And (Abs(y2 - 15.3000) < 0.001)) Or ((Abs(x - 38.6000) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 14.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 38.6000) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 31.8750) < 0.001) And (Abs(y2 - 15.7750) < 0.001)) Or ((Abs(x - 31.8750) < 0.001) And (Abs(y - 15.7750) < 0.001) And (Abs(x2 - 38.6000) < 0.001) And (Abs(y2 - 15.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 31.8750) < 0.001) And (Abs(y - 15.7750) < 0.001) And (Abs(x2 - 31.4500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 31.4500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 31.8750) < 0.001) And (Abs(y2 - 15.7750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eMidLayer2) And (((Abs(x - 31.4500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 30.8250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 30.8250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 31.4500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D9') And (T.Layer = eBottomLayer) And (((Abs(x - 30.8250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 30.7500) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 30.7500) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 30.8250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 12.8999) < 0.001) And (Abs(x2 - 43.2250) < 0.001) And (Abs(y2 - 13.0000) < 0.001)) Or ((Abs(x - 43.2250) < 0.001) And (Abs(y - 13.0000) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 12.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 43.2250) < 0.001) And (Abs(y - 13.0000) < 0.001) And (Abs(x2 - 42.6000) < 0.001) And (Abs(y2 - 13.6250) < 0.001)) Or ((Abs(x - 42.6000) < 0.001) And (Abs(y - 13.6250) < 0.001) And (Abs(x2 - 43.2250) < 0.001) And (Abs(y2 - 13.0000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 42.6000) < 0.001) And (Abs(y - 13.6250) < 0.001) And (Abs(x2 - 42.6000) < 0.001) And (Abs(y2 - 14.9250) < 0.001)) Or ((Abs(x - 42.6000) < 0.001) And (Abs(y - 14.9250) < 0.001) And (Abs(x2 - 42.6000) < 0.001) And (Abs(y2 - 13.6250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 42.6000) < 0.001) And (Abs(y - 14.9250) < 0.001) And (Abs(x2 - 42.5750) < 0.001) And (Abs(y2 - 14.9500) < 0.001)) Or ((Abs(x - 42.5750) < 0.001) And (Abs(y - 14.9500) < 0.001) And (Abs(x2 - 42.6000) < 0.001) And (Abs(y2 - 14.9250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 42.5750) < 0.001) And (Abs(y - 14.9500) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 15.1000) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 15.1000) < 0.001) And (Abs(x2 - 42.5750) < 0.001) And (Abs(y2 - 14.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 15.1000) < 0.001) And (Abs(x2 - 37.2500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 37.2500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 15.1000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 37.2500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 34.6500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 34.6500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 37.2500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eMidLayer2) And (((Abs(x - 34.6500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 34.0250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 34.0250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 34.6500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D12') And (T.Layer = eBottomLayer) And (((Abs(x - 34.0250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 33.9499) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 33.9499) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 34.0250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 12.8999) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 12.9700) < 0.001)) Or ((Abs(x - 41.3500) < 0.001) And (Abs(y - 12.9700) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 12.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eTopLayer) And (((Abs(x - 41.3500) < 0.001) And (Abs(y - 12.9700) < 0.001) And (Abs(x2 - 41.1500) < 0.001) And (Abs(y2 - 12.9700) < 0.001)) Or ((Abs(x - 41.1500) < 0.001) And (Abs(y - 12.9700) < 0.001) And (Abs(x2 - 41.3500) < 0.001) And (Abs(y2 - 12.9700) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eTopLayer) And (((Abs(x - 41.1500) < 0.001) And (Abs(y - 12.9700) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 12.9200) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 12.9200) < 0.001) And (Abs(x2 - 41.1500) < 0.001) And (Abs(y2 - 12.9700) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 12.9200) < 0.001) And (Abs(x2 - 40.6000) < 0.001) And (Abs(y2 - 12.7500) < 0.001)) Or ((Abs(x - 40.6000) < 0.001) And (Abs(y - 12.7500) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 12.9200) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eMidLayer1) And (((Abs(x - 40.6000) < 0.001) And (Abs(y - 12.7500) < 0.001) And (Abs(x2 - 38.8500) < 0.001) And (Abs(y2 - 14.5000) < 0.001)) Or ((Abs(x - 38.8500) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 40.6000) < 0.001) And (Abs(y2 - 12.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eMidLayer1) And (((Abs(x - 38.8500) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 38.8500) < 0.001) And (Abs(y2 - 15.0500) < 0.001)) Or ((Abs(x - 38.8500) < 0.001) And (Abs(y - 15.0500) < 0.001) And (Abs(x2 - 38.8500) < 0.001) And (Abs(y2 - 14.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eMidLayer1) And (((Abs(x - 38.8500) < 0.001) And (Abs(y - 15.0500) < 0.001) And (Abs(x2 - 38.8000) < 0.001) And (Abs(y2 - 15.1500) < 0.001)) Or ((Abs(x - 38.8000) < 0.001) And (Abs(y - 15.1500) < 0.001) And (Abs(x2 - 38.8500) < 0.001) And (Abs(y2 - 15.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eMidLayer1) And (((Abs(x - 38.8000) < 0.001) And (Abs(y - 15.1500) < 0.001) And (Abs(x2 - 38.6500) < 0.001) And (Abs(y2 - 15.3000) < 0.001)) Or ((Abs(x - 38.6500) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 38.8000) < 0.001) And (Abs(y2 - 15.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eMidLayer1) And (((Abs(x - 38.6500) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 36.2750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 38.6500) < 0.001) And (Abs(y2 - 15.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eMidLayer1) And (((Abs(x - 36.2750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 35.6250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 35.6250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D13') And (T.Layer = eBottomLayer) And (((Abs(x - 35.6250) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 35.5501) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 35.5501) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 35.6250) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 12.4000) < 0.001) And (Abs(x2 - 41.6000) < 0.001) And (Abs(y2 - 12.3300) < 0.001)) Or ((Abs(x - 41.6000) < 0.001) And (Abs(y - 12.3300) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 12.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eTopLayer) And (((Abs(x - 41.6000) < 0.001) And (Abs(y - 12.3300) < 0.001) And (Abs(x2 - 41.2000) < 0.001) And (Abs(y2 - 12.3300) < 0.001)) Or ((Abs(x - 41.2000) < 0.001) And (Abs(y - 12.3300) < 0.001) And (Abs(x2 - 41.6000) < 0.001) And (Abs(y2 - 12.3300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eTopLayer) And (((Abs(x - 41.2000) < 0.001) And (Abs(y - 12.3300) < 0.001) And (Abs(x2 - 40.9500) < 0.001) And (Abs(y2 - 12.3800) < 0.001)) Or ((Abs(x - 40.9500) < 0.001) And (Abs(y - 12.3800) < 0.001) And (Abs(x2 - 41.2000) < 0.001) And (Abs(y2 - 12.3300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eTopLayer) And (((Abs(x - 40.9500) < 0.001) And (Abs(y - 12.3800) < 0.001) And (Abs(x2 - 40.1450) < 0.001) And (Abs(y2 - 12.3800) < 0.001)) Or ((Abs(x - 40.1450) < 0.001) And (Abs(y - 12.3800) < 0.001) And (Abs(x2 - 40.9500) < 0.001) And (Abs(y2 - 12.3800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eTopLayer) And (((Abs(x - 40.1450) < 0.001) And (Abs(y - 12.3800) < 0.001) And (Abs(x2 - 40.1450) < 0.001) And (Abs(y2 - 14.9500) < 0.001)) Or ((Abs(x - 40.1450) < 0.001) And (Abs(y - 14.9500) < 0.001) And (Abs(x2 - 40.1450) < 0.001) And (Abs(y2 - 12.3800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eTopLayer) And (((Abs(x - 40.1450) < 0.001) And (Abs(y - 14.9500) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 14.9500) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 14.9500) < 0.001) And (Abs(x2 - 40.1450) < 0.001) And (Abs(y2 - 14.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eMidLayer1) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 14.9500) < 0.001) And (Abs(x2 - 33.8750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 33.8750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 14.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eMidLayer1) And (((Abs(x - 33.8750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 33.2500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 33.2500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 33.8750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D11') And (T.Layer = eBottomLayer) And (((Abs(x - 33.2500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 33.1501) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 33.1501) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 33.2500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 12.1500) < 0.001) And (Abs(x2 - 41.2000) < 0.001) And (Abs(y2 - 12.1400) < 0.001)) Or ((Abs(x - 41.2000) < 0.001) And (Abs(y - 12.1400) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 12.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eTopLayer) And (((Abs(x - 41.2000) < 0.001) And (Abs(y - 12.1400) < 0.001) And (Abs(x2 - 40.9500) < 0.001) And (Abs(y2 - 12.2050) < 0.001)) Or ((Abs(x - 40.9500) < 0.001) And (Abs(y - 12.2050) < 0.001) And (Abs(x2 - 41.2000) < 0.001) And (Abs(y2 - 12.1400) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eTopLayer) And (((Abs(x - 40.9500) < 0.001) And (Abs(y - 12.2050) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 12.2100) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 12.2100) < 0.001) And (Abs(x2 - 40.9500) < 0.001) And (Abs(y2 - 12.2050) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 12.2100) < 0.001) And (Abs(x2 - 39.9785) < 0.001) And (Abs(y2 - 12.2100) < 0.001)) Or ((Abs(x - 39.9785) < 0.001) And (Abs(y - 12.2100) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 12.2100) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eTopLayer) And (((Abs(x - 39.9785) < 0.001) And (Abs(y - 12.2100) < 0.001) And (Abs(x2 - 39.9785) < 0.001) And (Abs(y2 - 14.5000) < 0.001)) Or ((Abs(x - 39.9785) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 39.9785) < 0.001) And (Abs(y2 - 12.2100) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eTopLayer) And (((Abs(x - 39.9785) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 14.5000) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 39.9785) < 0.001) And (Abs(y2 - 14.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eMidLayer1) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 14.5000) < 0.001) And (Abs(x2 - 32.2750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 32.2750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 14.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eMidLayer1) And (((Abs(x - 32.2750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 31.6500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 31.6500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 32.2750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D10') And (T.Layer = eBottomLayer) And (((Abs(x - 31.6500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 31.5501) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 31.5501) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 31.6500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 11.6500) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 11.5900) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 11.5900) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 11.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eTopLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 11.5900) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 11.5900) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 11.5900) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 11.5900) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 11.5900) < 0.001) And (Abs(x2 - 39.8120) < 0.001) And (Abs(y2 - 11.5900) < 0.001)) Or ((Abs(x - 39.8120) < 0.001) And (Abs(y - 11.5900) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 11.5900) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eTopLayer) And (((Abs(x - 39.8120) < 0.001) And (Abs(y - 11.5900) < 0.001) And (Abs(x2 - 39.8120) < 0.001) And (Abs(y2 - 14.0500) < 0.001)) Or ((Abs(x - 39.8120) < 0.001) And (Abs(y - 14.0500) < 0.001) And (Abs(x2 - 39.8120) < 0.001) And (Abs(y2 - 11.5900) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eTopLayer) And (((Abs(x - 39.8120) < 0.001) And (Abs(y - 14.0500) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 14.0500) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 14.0500) < 0.001) And (Abs(x2 - 39.8120) < 0.001) And (Abs(y2 - 14.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eMidLayer1) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 14.0500) < 0.001) And (Abs(x2 - 28.8500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 28.8500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 14.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eMidLayer1) And (((Abs(x - 28.8500) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 27.0500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 27.0500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 28.8500) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'UDQM') And (T.Layer = eBottomLayer) And (((Abs(x - 27.0500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 26.7500) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 26.7500) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 27.0500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 11.4000) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 11.3600) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 11.3600) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 11.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eTopLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 11.3600) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 11.3600) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 11.3600) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 11.3600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 11.3600) < 0.001) And (Abs(x2 - 39.6455) < 0.001) And (Abs(y2 - 11.3600) < 0.001)) Or ((Abs(x - 39.6455) < 0.001) And (Abs(y - 11.3600) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 11.3600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eTopLayer) And (((Abs(x - 39.6455) < 0.001) And (Abs(y - 11.3600) < 0.001) And (Abs(x2 - 39.6455) < 0.001) And (Abs(y2 - 13.6000) < 0.001)) Or ((Abs(x - 39.6455) < 0.001) And (Abs(y - 13.6000) < 0.001) And (Abs(x2 - 39.6455) < 0.001) And (Abs(y2 - 11.3600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eTopLayer) And (((Abs(x - 39.6455) < 0.001) And (Abs(y - 13.6000) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 13.6000) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 13.6000) < 0.001) And (Abs(x2 - 39.6455) < 0.001) And (Abs(y2 - 13.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eMidLayer2) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 13.6000) < 0.001) And (Abs(x2 - 29.8750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)) Or ((Abs(x - 29.8750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 13.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eMidLayer2) And (((Abs(x - 29.8750) < 0.001) And (Abs(y - 16.0250) < 0.001) And (Abs(x2 - 29.2500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 29.2500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 29.8750) < 0.001) And (Abs(y2 - 16.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'D8') And (T.Layer = eBottomLayer) And (((Abs(x - 29.2500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 29.1501) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 29.1501) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 29.2500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 11.1500) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 11.1300) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 11.1300) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 11.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eTopLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 11.1300) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 11.1300) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 11.1300) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 11.1300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 11.1300) < 0.001) And (Abs(x2 - 39.4790) < 0.001) And (Abs(y2 - 11.1300) < 0.001)) Or ((Abs(x - 39.4790) < 0.001) And (Abs(y - 11.1300) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 11.1300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eTopLayer) And (((Abs(x - 39.4790) < 0.001) And (Abs(y - 11.1300) < 0.001) And (Abs(x2 - 39.4790) < 0.001) And (Abs(y2 - 13.1500) < 0.001)) Or ((Abs(x - 39.4790) < 0.001) And (Abs(y - 13.1500) < 0.001) And (Abs(x2 - 39.4790) < 0.001) And (Abs(y2 - 11.1300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eTopLayer) And (((Abs(x - 39.4790) < 0.001) And (Abs(y - 13.1500) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 13.1500) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 13.1500) < 0.001) And (Abs(x2 - 39.4790) < 0.001) And (Abs(y2 - 13.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eMidLayer1) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 13.1500) < 0.001) And (Abs(x2 - 26.8500) < 0.001) And (Abs(y2 - 15.6000) < 0.001)) Or ((Abs(x - 26.8500) < 0.001) And (Abs(y - 15.6000) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 13.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eBottomLayer) And (((Abs(x - 26.8500) < 0.001) And (Abs(y - 15.6000) < 0.001) And (Abs(x2 - 25.5750) < 0.001) And (Abs(y2 - 16.8500) < 0.001)) Or ((Abs(x - 25.5750) < 0.001) And (Abs(y - 16.8500) < 0.001) And (Abs(x2 - 26.8500) < 0.001) And (Abs(y2 - 15.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'CKE') And (T.Layer = eBottomLayer) And (((Abs(x - 25.5750) < 0.001) And (Abs(y - 16.8500) < 0.001) And (Abs(x2 - 25.1501) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 25.1501) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 25.5750) < 0.001) And (Abs(y2 - 16.8500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 10.8999) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 10.9000) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 10.9000) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 10.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eTopLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 10.9000) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 10.9000) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 10.9000) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 10.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 10.9000) < 0.001) And (Abs(x2 - 39.3125) < 0.001) And (Abs(y2 - 10.9000) < 0.001)) Or ((Abs(x - 39.3125) < 0.001) And (Abs(y - 10.9000) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 10.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eTopLayer) And (((Abs(x - 39.3125) < 0.001) And (Abs(y - 10.9000) < 0.001) And (Abs(x2 - 39.3125) < 0.001) And (Abs(y2 - 12.7000) < 0.001)) Or ((Abs(x - 39.3125) < 0.001) And (Abs(y - 12.7000) < 0.001) And (Abs(x2 - 39.3125) < 0.001) And (Abs(y2 - 10.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eTopLayer) And (((Abs(x - 39.3125) < 0.001) And (Abs(y - 12.7000) < 0.001) And (Abs(x2 - 38.8500) < 0.001) And (Abs(y2 - 12.7000) < 0.001)) Or ((Abs(x - 38.8500) < 0.001) And (Abs(y - 12.7000) < 0.001) And (Abs(x2 - 39.3125) < 0.001) And (Abs(y2 - 12.7000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eMidLayer2) And (((Abs(x - 38.8500) < 0.001) And (Abs(y - 12.7000) < 0.001) And (Abs(x2 - 34.8250) < 0.001) And (Abs(y2 - 12.7000) < 0.001)) Or ((Abs(x - 34.8250) < 0.001) And (Abs(y - 12.7000) < 0.001) And (Abs(x2 - 38.8500) < 0.001) And (Abs(y2 - 12.7000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eMidLayer2) And (((Abs(x - 34.8250) < 0.001) And (Abs(y - 12.7000) < 0.001) And (Abs(x2 - 27.1250) < 0.001) And (Abs(y2 - 16.1000) < 0.001)) Or ((Abs(x - 27.1250) < 0.001) And (Abs(y - 16.1000) < 0.001) And (Abs(x2 - 34.8250) < 0.001) And (Abs(y2 - 12.7000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eBottomLayer) And (((Abs(x - 27.1250) < 0.001) And (Abs(y - 16.1000) < 0.001) And (Abs(x2 - 26.3750) < 0.001) And (Abs(y2 - 16.8500) < 0.001)) Or ((Abs(x - 26.3750) < 0.001) And (Abs(y - 16.8500) < 0.001) And (Abs(x2 - 27.1250) < 0.001) And (Abs(y2 - 16.1000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'SDRAM-CLK') And (T.Layer = eBottomLayer) And (((Abs(x - 26.3750) < 0.001) And (Abs(y - 16.8500) < 0.001) And (Abs(x2 - 25.9499) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 25.9499) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 26.3750) < 0.001) And (Abs(y2 - 16.8500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 10.6500) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 10.6800) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 10.6800) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 10.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eTopLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 10.6800) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 10.6800) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 10.6800) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 10.6800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 10.6800) < 0.001) And (Abs(x2 - 39.1460) < 0.001) And (Abs(y2 - 10.6800) < 0.001)) Or ((Abs(x - 39.1460) < 0.001) And (Abs(y - 10.6800) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 10.6800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eTopLayer) And (((Abs(x - 39.1460) < 0.001) And (Abs(y - 10.6800) < 0.001) And (Abs(x2 - 39.1460) < 0.001) And (Abs(y2 - 11.9500) < 0.001)) Or ((Abs(x - 39.1460) < 0.001) And (Abs(y - 11.9500) < 0.001) And (Abs(x2 - 39.1460) < 0.001) And (Abs(y2 - 10.6800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eTopLayer) And (((Abs(x - 39.1460) < 0.001) And (Abs(y - 11.9500) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 11.9500) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 11.9500) < 0.001) And (Abs(x2 - 39.1460) < 0.001) And (Abs(y2 - 11.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eMidLayer1) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 11.9500) < 0.001) And (Abs(x2 - 23.3250) < 0.001) And (Abs(y2 - 13.6250) < 0.001)) Or ((Abs(x - 23.3250) < 0.001) And (Abs(y - 13.6250) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 11.9500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eMidLayer1) And (((Abs(x - 23.3250) < 0.001) And (Abs(y - 13.6250) < 0.001) And (Abs(x2 - 23.2250) < 0.001) And (Abs(y2 - 13.7500) < 0.001)) Or ((Abs(x - 23.2250) < 0.001) And (Abs(y - 13.7500) < 0.001) And (Abs(x2 - 23.3250) < 0.001) And (Abs(y2 - 13.6250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eMidLayer1) And (((Abs(x - 23.2250) < 0.001) And (Abs(y - 13.7500) < 0.001) And (Abs(x2 - 21.8250) < 0.001) And (Abs(y2 - 16.2500) < 0.001)) Or ((Abs(x - 21.8250) < 0.001) And (Abs(y - 16.2500) < 0.001) And (Abs(x2 - 23.2250) < 0.001) And (Abs(y2 - 13.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eBottomLayer) And (((Abs(x - 21.8250) < 0.001) And (Abs(y - 16.2500) < 0.001) And (Abs(x2 - 22.3500) < 0.001) And (Abs(y2 - 16.9000) < 0.001)) Or ((Abs(x - 22.3500) < 0.001) And (Abs(y - 16.9000) < 0.001) And (Abs(x2 - 21.8250) < 0.001) And (Abs(y2 - 16.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A9') And (T.Layer = eBottomLayer) And (((Abs(x - 22.3500) < 0.001) And (Abs(y - 16.9000) < 0.001) And (Abs(x2 - 22.7500) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 22.7500) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 22.3500) < 0.001) And (Abs(y2 - 16.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 10.4000) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 10.4600) < 0.001)) Or ((Abs(x - 41.5000) < 0.001) And (Abs(y - 10.4600) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 10.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eTopLayer) And (((Abs(x - 41.5000) < 0.001) And (Abs(y - 10.4600) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 10.4600) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 10.4600) < 0.001) And (Abs(x2 - 41.5000) < 0.001) And (Abs(y2 - 10.4600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 10.4600) < 0.001) And (Abs(x2 - 38.9795) < 0.001) And (Abs(y2 - 10.4600) < 0.001)) Or ((Abs(x - 38.9795) < 0.001) And (Abs(y - 10.4600) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 10.4600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eTopLayer) And (((Abs(x - 38.9795) < 0.001) And (Abs(y - 10.4600) < 0.001) And (Abs(x2 - 38.9795) < 0.001) And (Abs(y2 - 11.5000) < 0.001)) Or ((Abs(x - 38.9795) < 0.001) And (Abs(y - 11.5000) < 0.001) And (Abs(x2 - 38.9795) < 0.001) And (Abs(y2 - 10.4600) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eTopLayer) And (((Abs(x - 38.9795) < 0.001) And (Abs(y - 11.5000) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 11.5000) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 11.5000) < 0.001) And (Abs(x2 - 38.9795) < 0.001) And (Abs(y2 - 11.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eMidLayer2) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 11.5000) < 0.001) And (Abs(x2 - 24.2250) < 0.001) And (Abs(y2 - 13.9000) < 0.001)) Or ((Abs(x - 24.2250) < 0.001) And (Abs(y - 13.9000) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 11.5000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eMidLayer2) And (((Abs(x - 24.2250) < 0.001) And (Abs(y - 13.9000) < 0.001) And (Abs(x2 - 23.7250) < 0.001) And (Abs(y2 - 16.3000) < 0.001)) Or ((Abs(x - 23.7250) < 0.001) And (Abs(y - 16.3000) < 0.001) And (Abs(x2 - 24.2250) < 0.001) And (Abs(y2 - 13.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eMidLayer2) And (((Abs(x - 23.7250) < 0.001) And (Abs(y - 16.3000) < 0.001) And (Abs(x2 - 23.3500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 23.3500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 23.7250) < 0.001) And (Abs(y2 - 16.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A11') And (T.Layer = eBottomLayer) And (((Abs(x - 23.3500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 23.5499) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 23.5499) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 23.3500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eTopLayer) And (((Abs(x - 41.9000) < 0.001) And (Abs(y - 9.8999) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 9.8700) < 0.001)) Or ((Abs(x - 41.4000) < 0.001) And (Abs(y - 9.8700) < 0.001) And (Abs(x2 - 41.9000) < 0.001) And (Abs(y2 - 9.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eTopLayer) And (((Abs(x - 41.4000) < 0.001) And (Abs(y - 9.8700) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 9.8300) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 9.8300) < 0.001) And (Abs(x2 - 41.4000) < 0.001) And (Abs(y2 - 9.8700) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 9.8300) < 0.001) And (Abs(x2 - 40.4000) < 0.001) And (Abs(y2 - 9.8800) < 0.001)) Or ((Abs(x - 40.4000) < 0.001) And (Abs(y - 9.8800) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 9.8300) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eTopLayer) And (((Abs(x - 40.4000) < 0.001) And (Abs(y - 9.8800) < 0.001) And (Abs(x2 - 38.8130) < 0.001) And (Abs(y2 - 9.8800) < 0.001)) Or ((Abs(x - 38.8130) < 0.001) And (Abs(y - 9.8800) < 0.001) And (Abs(x2 - 40.4000) < 0.001) And (Abs(y2 - 9.8800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eTopLayer) And (((Abs(x - 38.8130) < 0.001) And (Abs(y - 9.8800) < 0.001) And (Abs(x2 - 38.8130) < 0.001) And (Abs(y2 - 11.0500) < 0.001)) Or ((Abs(x - 38.8130) < 0.001) And (Abs(y - 11.0500) < 0.001) And (Abs(x2 - 38.8130) < 0.001) And (Abs(y2 - 9.8800) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eTopLayer) And (((Abs(x - 38.8130) < 0.001) And (Abs(y - 11.0500) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 11.0500) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 11.0500) < 0.001) And (Abs(x2 - 38.8130) < 0.001) And (Abs(y2 - 11.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eMidLayer1) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 11.0500) < 0.001) And (Abs(x2 - 23.2250) < 0.001) And (Abs(y2 - 13.4000) < 0.001)) Or ((Abs(x - 23.2250) < 0.001) And (Abs(y - 13.4000) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 11.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eMidLayer1) And (((Abs(x - 23.2250) < 0.001) And (Abs(y - 13.4000) < 0.001) And (Abs(x2 - 22.1500) < 0.001) And (Abs(y2 - 13.9000) < 0.001)) Or ((Abs(x - 22.1500) < 0.001) And (Abs(y - 13.9000) < 0.001) And (Abs(x2 - 23.2250) < 0.001) And (Abs(y2 - 13.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eMidLayer1) And (((Abs(x - 22.1500) < 0.001) And (Abs(y - 13.9000) < 0.001) And (Abs(x2 - 21.1000) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 21.1000) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 22.1500) < 0.001) And (Abs(y2 - 13.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A7') And (T.Layer = eBottomLayer) And (((Abs(x - 21.1000) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 21.1501) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 21.1501) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 21.1000) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eTopLayer) And (((Abs(x - 41.6875) < 0.001) And (Abs(y - 9.6500) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 9.6500) < 0.001)) Or ((Abs(x - 40.9000) < 0.001) And (Abs(y - 9.6500) < 0.001) And (Abs(x2 - 41.6875) < 0.001) And (Abs(y2 - 9.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eTopLayer) And (((Abs(x - 40.9000) < 0.001) And (Abs(y - 9.6500) < 0.001) And (Abs(x2 - 40.4000) < 0.001) And (Abs(y2 - 9.7100) < 0.001)) Or ((Abs(x - 40.4000) < 0.001) And (Abs(y - 9.7100) < 0.001) And (Abs(x2 - 40.9000) < 0.001) And (Abs(y2 - 9.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eTopLayer) And (((Abs(x - 40.4000) < 0.001) And (Abs(y - 9.7100) < 0.001) And (Abs(x2 - 38.6465) < 0.001) And (Abs(y2 - 9.7100) < 0.001)) Or ((Abs(x - 38.6465) < 0.001) And (Abs(y - 9.7100) < 0.001) And (Abs(x2 - 40.4000) < 0.001) And (Abs(y2 - 9.7100) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eTopLayer) And (((Abs(x - 38.6465) < 0.001) And (Abs(y - 9.7100) < 0.001) And (Abs(x2 - 38.6465) < 0.001) And (Abs(y2 - 10.6000) < 0.001)) Or ((Abs(x - 38.6465) < 0.001) And (Abs(y - 10.6000) < 0.001) And (Abs(x2 - 38.6465) < 0.001) And (Abs(y2 - 9.7100) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eTopLayer) And (((Abs(x - 38.6465) < 0.001) And (Abs(y - 10.6000) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 10.6000) < 0.001)) Or ((Abs(x - 38.5000) < 0.001) And (Abs(y - 10.6000) < 0.001) And (Abs(x2 - 38.6465) < 0.001) And (Abs(y2 - 10.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eMidLayer1) And (((Abs(x - 38.5000) < 0.001) And (Abs(y - 10.6000) < 0.001) And (Abs(x2 - 23.1250) < 0.001) And (Abs(y2 - 13.1750) < 0.001)) Or ((Abs(x - 23.1250) < 0.001) And (Abs(y - 13.1750) < 0.001) And (Abs(x2 - 38.5000) < 0.001) And (Abs(y2 - 10.6000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eMidLayer1) And (((Abs(x - 23.1250) < 0.001) And (Abs(y - 13.1750) < 0.001) And (Abs(x2 - 22.0500) < 0.001) And (Abs(y2 - 13.6750) < 0.001)) Or ((Abs(x - 22.0500) < 0.001) And (Abs(y - 13.6750) < 0.001) And (Abs(x2 - 23.1250) < 0.001) And (Abs(y2 - 13.1750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eMidLayer1) And (((Abs(x - 22.0500) < 0.001) And (Abs(y - 13.6750) < 0.001) And (Abs(x2 - 20.2250) < 0.001) And (Abs(y2 - 15.3000) < 0.001)) Or ((Abs(x - 20.2250) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 22.0500) < 0.001) And (Abs(y2 - 13.6750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eMidLayer1) And (((Abs(x - 20.2250) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 19.5500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 19.5500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 20.2250) < 0.001) And (Abs(y2 - 15.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A5') And (T.Layer = eBottomLayer) And (((Abs(x - 19.5500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 19.5499) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 19.5499) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 19.5500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eMidLayer1) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 11.4000) < 0.001) And (Abs(x2 - 39.5500) < 0.001) And (Abs(y2 - 11.4000) < 0.001)) Or ((Abs(x - 39.5500) < 0.001) And (Abs(y - 11.4000) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 11.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eMidLayer1) And (((Abs(x - 39.5500) < 0.001) And (Abs(y - 11.4000) < 0.001) And (Abs(x2 - 38.7000) < 0.001) And (Abs(y2 - 12.2500) < 0.001)) Or ((Abs(x - 38.7000) < 0.001) And (Abs(y - 12.2500) < 0.001) And (Abs(x2 - 39.5500) < 0.001) And (Abs(y2 - 11.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eMidLayer1) And (((Abs(x - 38.7000) < 0.001) And (Abs(y - 12.2500) < 0.001) And (Abs(x2 - 32.3750) < 0.001) And (Abs(y2 - 13.8750) < 0.001)) Or ((Abs(x - 32.3750) < 0.001) And (Abs(y - 13.8750) < 0.001) And (Abs(x2 - 38.7000) < 0.001) And (Abs(y2 - 12.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eMidLayer1) And (((Abs(x - 32.3750) < 0.001) And (Abs(y - 13.8750) < 0.001) And (Abs(x2 - 25.8750) < 0.001) And (Abs(y2 - 13.8750) < 0.001)) Or ((Abs(x - 25.8750) < 0.001) And (Abs(y - 13.8750) < 0.001) And (Abs(x2 - 32.3750) < 0.001) And (Abs(y2 - 13.8750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eMidLayer1) And (((Abs(x - 25.8750) < 0.001) And (Abs(y - 13.8750) < 0.001) And (Abs(x2 - 23.3500) < 0.001) And (Abs(y2 - 16.1750) < 0.001)) Or ((Abs(x - 23.3500) < 0.001) And (Abs(y - 16.1750) < 0.001) And (Abs(x2 - 25.8750) < 0.001) And (Abs(y2 - 13.8750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eBottomLayer) And (((Abs(x - 23.3500) < 0.001) And (Abs(y - 16.1750) < 0.001) And (Abs(x2 - 23.6500) < 0.001) And (Abs(y2 - 16.4750) < 0.001)) Or ((Abs(x - 23.6500) < 0.001) And (Abs(y - 16.4750) < 0.001) And (Abs(x2 - 23.3500) < 0.001) And (Abs(y2 - 16.1750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eBottomLayer) And (((Abs(x - 23.6500) < 0.001) And (Abs(y - 16.4750) < 0.001) And (Abs(x2 - 23.9500) < 0.001) And (Abs(y2 - 16.9000) < 0.001)) Or ((Abs(x - 23.9500) < 0.001) And (Abs(y - 16.9000) < 0.001) And (Abs(x2 - 23.6500) < 0.001) And (Abs(y2 - 16.4750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A12') And (T.Layer = eBottomLayer) And (((Abs(x - 23.9500) < 0.001) And (Abs(y - 16.9000) < 0.001) And (Abs(x2 - 24.3500) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 24.3500) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 23.9500) < 0.001) And (Abs(y2 - 16.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 10.8999) < 0.001) And (Abs(x2 - 41.0000) < 0.001) And (Abs(y2 - 9.8000) < 0.001)) Or ((Abs(x - 41.0000) < 0.001) And (Abs(y - 9.8000) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 10.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 41.0000) < 0.001) And (Abs(y - 9.8000) < 0.001) And (Abs(x2 - 38.3000) < 0.001) And (Abs(y2 - 10.0750) < 0.001)) Or ((Abs(x - 38.3000) < 0.001) And (Abs(y - 10.0750) < 0.001) And (Abs(x2 - 41.0000) < 0.001) And (Abs(y2 - 9.8000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 38.3000) < 0.001) And (Abs(y - 10.0750) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 11.3000) < 0.001)) Or ((Abs(x - 36.2750) < 0.001) And (Abs(y - 11.3000) < 0.001) And (Abs(x2 - 38.3000) < 0.001) And (Abs(y2 - 10.0750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 36.2750) < 0.001) And (Abs(y - 11.3000) < 0.001) And (Abs(x2 - 30.4250) < 0.001) And (Abs(y2 - 12.6250) < 0.001)) Or ((Abs(x - 30.4250) < 0.001) And (Abs(y - 12.6250) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 11.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 30.4250) < 0.001) And (Abs(y - 12.6250) < 0.001) And (Abs(x2 - 22.9500) < 0.001) And (Abs(y2 - 13.8750) < 0.001)) Or ((Abs(x - 22.9500) < 0.001) And (Abs(y - 13.8750) < 0.001) And (Abs(x2 - 30.4250) < 0.001) And (Abs(y2 - 12.6250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 22.9500) < 0.001) And (Abs(y - 13.8750) < 0.001) And (Abs(x2 - 21.4750) < 0.001) And (Abs(y2 - 16.1500) < 0.001)) Or ((Abs(x - 21.4750) < 0.001) And (Abs(y - 16.1500) < 0.001) And (Abs(x2 - 22.9500) < 0.001) And (Abs(y2 - 13.8750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 21.4750) < 0.001) And (Abs(y - 16.1500) < 0.001) And (Abs(x2 - 21.5000) < 0.001) And (Abs(y2 - 16.5500) < 0.001)) Or ((Abs(x - 21.5000) < 0.001) And (Abs(y - 16.5500) < 0.001) And (Abs(x2 - 21.4750) < 0.001) And (Abs(y2 - 16.1500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eMidLayer2) And (((Abs(x - 21.5000) < 0.001) And (Abs(y - 16.5500) < 0.001) And (Abs(x2 - 21.6250) < 0.001) And (Abs(y2 - 16.6750) < 0.001)) Or ((Abs(x - 21.6250) < 0.001) And (Abs(y - 16.6750) < 0.001) And (Abs(x2 - 21.5000) < 0.001) And (Abs(y2 - 16.5500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A8') And (T.Layer = eBottomLayer) And (((Abs(x - 21.6250) < 0.001) And (Abs(y - 16.6750) < 0.001) And (Abs(x2 - 21.9499) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 21.9499) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 21.6250) < 0.001) And (Abs(y2 - 16.6750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 10.4000) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 9.0500) < 0.001)) Or ((Abs(x - 40.5000) < 0.001) And (Abs(y - 9.0500) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 10.4000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 40.5000) < 0.001) And (Abs(y - 9.0500) < 0.001) And (Abs(x2 - 40.2250) < 0.001) And (Abs(y2 - 9.0500) < 0.001)) Or ((Abs(x - 40.2250) < 0.001) And (Abs(y - 9.0500) < 0.001) And (Abs(x2 - 40.5000) < 0.001) And (Abs(y2 - 9.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 40.2250) < 0.001) And (Abs(y - 9.0500) < 0.001) And (Abs(x2 - 40.0250) < 0.001) And (Abs(y2 - 9.2500) < 0.001)) Or ((Abs(x - 40.0250) < 0.001) And (Abs(y - 9.2500) < 0.001) And (Abs(x2 - 40.2250) < 0.001) And (Abs(y2 - 9.0500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 40.0250) < 0.001) And (Abs(y - 9.2500) < 0.001) And (Abs(x2 - 38.0750) < 0.001) And (Abs(y2 - 9.9000) < 0.001)) Or ((Abs(x - 38.0750) < 0.001) And (Abs(y - 9.9000) < 0.001) And (Abs(x2 - 40.0250) < 0.001) And (Abs(y2 - 9.2500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 38.0750) < 0.001) And (Abs(y - 9.9000) < 0.001) And (Abs(x2 - 36.6750) < 0.001) And (Abs(y2 - 10.7500) < 0.001)) Or ((Abs(x - 36.6750) < 0.001) And (Abs(y - 10.7500) < 0.001) And (Abs(x2 - 38.0750) < 0.001) And (Abs(y2 - 9.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 36.6750) < 0.001) And (Abs(y - 10.7500) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 10.9750) < 0.001)) Or ((Abs(x - 36.2750) < 0.001) And (Abs(y - 10.9750) < 0.001) And (Abs(x2 - 36.6750) < 0.001) And (Abs(y2 - 10.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 36.2750) < 0.001) And (Abs(y - 10.9750) < 0.001) And (Abs(x2 - 36.1750) < 0.001) And (Abs(y2 - 11.0250) < 0.001)) Or ((Abs(x - 36.1750) < 0.001) And (Abs(y - 11.0250) < 0.001) And (Abs(x2 - 36.2750) < 0.001) And (Abs(y2 - 10.9750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 36.1750) < 0.001) And (Abs(y - 11.0250) < 0.001) And (Abs(x2 - 22.8500) < 0.001) And (Abs(y2 - 13.6500) < 0.001)) Or ((Abs(x - 22.8500) < 0.001) And (Abs(y - 13.6500) < 0.001) And (Abs(x2 - 36.1750) < 0.001) And (Abs(y2 - 11.0250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 22.8500) < 0.001) And (Abs(y - 13.6500) < 0.001) And (Abs(x2 - 21.8750) < 0.001) And (Abs(y2 - 13.9000) < 0.001)) Or ((Abs(x - 21.8750) < 0.001) And (Abs(y - 13.9000) < 0.001) And (Abs(x2 - 22.8500) < 0.001) And (Abs(y2 - 13.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 21.8750) < 0.001) And (Abs(y - 13.9000) < 0.001) And (Abs(x2 - 21.0500) < 0.001) And (Abs(y2 - 15.3000) < 0.001)) Or ((Abs(x - 21.0500) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 21.8750) < 0.001) And (Abs(y2 - 13.9000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eMidLayer2) And (((Abs(x - 21.0500) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 20.3500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 20.3500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 21.0500) < 0.001) And (Abs(y2 - 15.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A6') And (T.Layer = eBottomLayer) And (((Abs(x - 20.3500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 20.3500) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 20.3500) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 20.3500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 43.4001) < 0.001) And (Abs(y - 9.8999) < 0.001) And (Abs(x2 - 40.6750) < 0.001) And (Abs(y2 - 8.7500) < 0.001)) Or ((Abs(x - 40.6750) < 0.001) And (Abs(y - 8.7500) < 0.001) And (Abs(x2 - 43.4001) < 0.001) And (Abs(y2 - 9.8999) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 40.6750) < 0.001) And (Abs(y - 8.7500) < 0.001) And (Abs(x2 - 40.0000) < 0.001) And (Abs(y2 - 8.7750) < 0.001)) Or ((Abs(x - 40.0000) < 0.001) And (Abs(y - 8.7750) < 0.001) And (Abs(x2 - 40.6750) < 0.001) And (Abs(y2 - 8.7500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 40.0000) < 0.001) And (Abs(y - 8.7750) < 0.001) And (Abs(x2 - 39.8750) < 0.001) And (Abs(y2 - 8.8500) < 0.001)) Or ((Abs(x - 39.8750) < 0.001) And (Abs(y - 8.8500) < 0.001) And (Abs(x2 - 40.0000) < 0.001) And (Abs(y2 - 8.7750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 39.8750) < 0.001) And (Abs(y - 8.8500) < 0.001) And (Abs(x2 - 37.6750) < 0.001) And (Abs(y2 - 9.8250) < 0.001)) Or ((Abs(x - 37.6750) < 0.001) And (Abs(y - 9.8250) < 0.001) And (Abs(x2 - 39.8750) < 0.001) And (Abs(y2 - 8.8500) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 37.6750) < 0.001) And (Abs(y - 9.8250) < 0.001) And (Abs(x2 - 36.8750) < 0.001) And (Abs(y2 - 10.3250) < 0.001)) Or ((Abs(x - 36.8750) < 0.001) And (Abs(y - 10.3250) < 0.001) And (Abs(x2 - 37.6750) < 0.001) And (Abs(y2 - 9.8250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 36.8750) < 0.001) And (Abs(y - 10.3250) < 0.001) And (Abs(x2 - 36.1750) < 0.001) And (Abs(y2 - 10.7250) < 0.001)) Or ((Abs(x - 36.1750) < 0.001) And (Abs(y - 10.7250) < 0.001) And (Abs(x2 - 36.8750) < 0.001) And (Abs(y2 - 10.3250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 36.1750) < 0.001) And (Abs(y - 10.7250) < 0.001) And (Abs(x2 - 22.3250) < 0.001) And (Abs(y2 - 13.5250) < 0.001)) Or ((Abs(x - 22.3250) < 0.001) And (Abs(y - 13.5250) < 0.001) And (Abs(x2 - 36.1750) < 0.001) And (Abs(y2 - 10.7250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 22.3250) < 0.001) And (Abs(y - 13.5250) < 0.001) And (Abs(x2 - 21.7750) < 0.001) And (Abs(y2 - 13.6750) < 0.001)) Or ((Abs(x - 21.7750) < 0.001) And (Abs(y - 13.6750) < 0.001) And (Abs(x2 - 22.3250) < 0.001) And (Abs(y2 - 13.5250) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 21.7750) < 0.001) And (Abs(y - 13.6750) < 0.001) And (Abs(x2 - 19.4250) < 0.001) And (Abs(y2 - 15.3000) < 0.001)) Or ((Abs(x - 19.4250) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 21.7750) < 0.001) And (Abs(y2 - 13.6750) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eMidLayer2) And (((Abs(x - 19.4250) < 0.001) And (Abs(y - 15.3000) < 0.001) And (Abs(x2 - 18.7500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)) Or ((Abs(x - 18.7500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 19.4250) < 0.001) And (Abs(y2 - 15.3000) < 0.001)))) Then Kill.Add(T);
        If ((nm = 'A4') And (T.Layer = eBottomLayer) And (((Abs(x - 18.7500) < 0.001) And (Abs(y - 16.6500) < 0.001) And (Abs(x2 - 18.7500) < 0.001) And (Abs(y2 - 17.5300) < 0.001)) Or ((Abs(x - 18.7500) < 0.001) And (Abs(y - 17.5300) < 0.001) And (Abs(x2 - 18.7500) < 0.001) And (Abs(y2 - 16.6500) < 0.001)))) Then Kill.Add(T);
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PreProcess;
    Try
        For i := 0 To Kill.Count - 1 Do
            Brd.RemovePCBObject(Kill.Items[i]);
        { put back the copper PlaceCoRoute removed }
        N := FanNet('GND');
        If N = Nil Then Missing := Missing + ' GND' Else
        Begin
            FanVia(N, 41.4000, 13.8999);
            FanTrk(N, eTopLayer, 0.2000, 41.9000, 13.8999, 41.4000, 13.8999);
        End;
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - removed ' + IntToStr(Kill.Count) + ' CoRoute object(s) (expected 583) and restored 2. Press Ctrl+S.');
    Kill.Free;
End;

{ ==== END COROUTE BLOCK ==== }

End.

{ End of ZuluSetup.pas }
