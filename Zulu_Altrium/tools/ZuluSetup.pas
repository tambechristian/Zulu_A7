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
{        10 mil is 0.254 mm, wider than the 0.225 mm BGA land and the 0.240 mm }
{        0201 lands it connects: a starved thermal by construction.            }
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
{  Then Ctrl+S.                                                                }
{..............................................................................}

Var
    Brd : IPCB_Board;


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

End.

{ End of ZuluSetup.pas }
