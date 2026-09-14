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
    PROBE_X0 = 60.0;      { the probes live in this rectangle, mm }
    PROBE_X1 = 62.0;
    PROBE_Y0 = 1.0;
    PROBE_Y1 = 8.0;


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
    T.Y1    := MMsToCoord(Y);
    T.X2    := MMsToCoord(PROBE_X1 - 0.25);
    T.Y2    := MMsToCoord(Y);
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


End.

{ End of ZuluSetup.pas }
