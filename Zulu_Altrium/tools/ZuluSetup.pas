{..............................................................................}
{  ZuluSetup.pas                  DelphiScript for Altium Designer             }
{                                                                              }
{  The pre-routing setup pass. Everything here was measured against the files   }
{  before it was written -- see docs/routing_readiness.md.                     }
{                                                                              }
{  1. THE WIDTH RULE IS THE BLOCKER.                                            }
{     Its PREFERRED width is 3.937 mil = 0.100000 mm. The gap between two       }
{     CPG236 lands is 0.4999 pitch - 0.225044 land = 0.274856 mm, and at the    }
{     0.09 mm Clearance rule that admits 0.094856 mm of copper. EVERY ESCAPE    }
{     TRACE THE ROUTER STARTS INSIDE THE BALL FIELD IS 0.005144 mm TOO WIDE.    }
{     Preferred drops to 3 mil. MIN stays 3 mil and MAX stays 19.685 mil --     }
{     never narrow MAX globally, VCC1V0 carries 367 mA and needs real copper.   }
{                                                                               }
{  2. THE GRIDS ARE IMPERIAL ON A METRIC PART.                                  }
{     Snap is 5 mil and the track and via grids are 20 mil, on a 0.5 mm ball    }
{     pitch. A 3 mil trace has 0.00932 mm of play per side in a 0.275 mm ball   }
{     gap, and the measured worst centreline error across the 36 real ball gaps }
{     is 0.06195 mm on a 5 mil grid (violates) against 0.00007 mm on a 0.025 mm }
{     metric grid (legal). The hazard is imperial-against-metric, not coarse-   }
{     against-fine; finer than 0.025 mm buys nothing and slows hand routing.    }
{                                                                               }
{  3. THE POLYGON RELIEF SPOKE IS WIDER THAN THE PADS IT CONNECTS.              }
{     10 mil = 0.254 mm, against a 0.225 mm BGA land and 0.240 mm 0201 lands.   }
{     That is a starved thermal by construction on every under-die cap. Spoke   }
{     drops to 0.15 mm with a 0.20 mm air gap.                                  }
{                                                                               }
{  4. ROUTING CORNERS ARE SET TO A 100 mil SETBACK.                             }
{     2.540 mm on a board whose tightest channel is 0.22 mm. Minimum setback    }
{     drops to 0.10 mm.                                                         }
{                                                                               }
{  5. THE DIFFERENTIAL PAIR RULE CANNOT BIND TO ANYTHING.                       }
{     DifferentialPairs6 is 0 BYTES -- no pair object exists -- so USB_D_P and  }
{     USB_D_N would route as two unrelated nets. Its values are set here; the   }
{     pair object itself is CreateUsbPair. MaxUncoupled goes to 2 mm, not 1:    }
{     the forced break-out from a 0.30 mm coupled pitch onto U2's 0.5 mm pins   }
{     is itself 1.5-2 mm uncoupled and no legal route avoids it.                }
{                                                                               }
{  EVERY WRITE IS IN ITS OWN Try/Except. That is not defensive habit: a raise   }
{  inside PCBServer.PreProcess leaves the transaction open and Altium then      }
{  refuses every save until a bare PostProcess closes it. This script must      }
{  never be the thing that does that.                                           }
{                                                                               }
{  Run:  ReportSetup    reads back every value, changes nothing                 }
{        ApplyRules     1, 3, 4, 5                                              }
{        ApplyGrids     2                                                       }
{  Then Ctrl+S.                                                                  }
{..............................................................................}

Var
    Brd : IPCB_Board;
    Log : TStringList;


Function MM(C : TCoord) : String;
Begin
    Result := FloatToStr(CoordToMMs(C)) + ' mm';
End;


Function FindRule(K : TRuleKind) : IPCB_Rule;
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
        If (R.RuleKind = K) And (Result = Nil) Then Result := R;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;


Function Start : Boolean;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    Result := Brd <> Nil;
    If Not Result Then
        ShowMessage('No PCB document is focused.' + #13#10 +
                    'Open zulu_a7.PcbDoc, click in the board window, and run again.');
    Log := TStringList.Create;
End;


Procedure Finish(Title : String);
Begin
    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - ' + Title + #13#10 + #13#10 + Log.Text + #13#10 +
                'Nothing is saved yet - press Ctrl+S.');
    Log.Free;
End;


Procedure ReportSetup;
Var
    R : IPCB_Rule;
Begin
    If Not Start Then Exit;

    R := FindRule(eRule_MaxMinWidth);
    If R <> Nil Then
        Log.Add('Width           min ' + MM(R.MinLimit) + '   preferred ' + MM(R.PreferedLimit) +
                '   max ' + MM(R.MaxLimit));

    R := FindRule(eRule_PolygonConnectStyle);
    If R <> Nil Then
        Log.Add('PolygonConnect  spoke ' + MM(R.ReliefConductorWidth) +
                '   air gap ' + MM(R.ReliefAirGap) + '   entries ' + IntToStr(R.ReliefEntries));

    R := FindRule(eRule_RoutingCorners);
    If R <> Nil Then
        Log.Add('RoutingCorners  min setback ' + MM(R.MinSetback) + '   max ' + MM(R.MaxSetback));

    R := FindRule(eRule_DiffPairsRouting);
    If R <> Nil Then
        Log.Add('DiffPairs       gap ' + MM(R.Gap) + '   max uncoupled ' + MM(R.MaxUncoupledLength));

    Log.Add('');
    Log.Add('snap grid       ' + MM(Brd.SnapGridSize));
    Log.Add('component grid  ' + MM(Brd.ComponentGridSize));
    Log.Add('');
    Log.Add('WANTED: preferred width 0.0762, spoke 0.15 / gap 0.20,');
    Log.Add('        corner setback 0.10, diff gap 0.15, uncoupled 2.0,');
    Log.Add('        snap grid 0.025 -- all mm.');
    Log.Add('');
    Log.Add('REPORT ONLY - nothing was changed.');
    Finish('setup, as it stands');
End;


Procedure ApplyRules;
Var
    R : IPCB_Rule;
Begin
    If Not Start Then Exit;

    PCBServer.PreProcess;

    R := FindRule(eRule_MaxMinWidth);
    If R <> Nil Then
    Begin
        Try
            R.BeginModify;
            R.PreferedLimit := MilsToCoord(3);
            R.EndModify;
            Log.Add('Width preferred  -> ' + MM(R.PreferedLimit) + '  (was 0.1 mm, which does');
            Log.Add('                    not fit between two CPG236 lands)');
        Except
            Log.Add('Width preferred  FAILED');
        End;
    End
    Else Log.Add('Width rule NOT FOUND');

    R := FindRule(eRule_PolygonConnectStyle);
    If R <> Nil Then
    Begin
        Try
            R.BeginModify;
            R.ReliefConductorWidth := MMsToCoord(0.15);
            R.ReliefAirGap         := MMsToCoord(0.20);
            R.EndModify;
            Log.Add('Polygon spoke    -> ' + MM(R.ReliefConductorWidth) +
                    '  air gap ' + MM(R.ReliefAirGap));
        Except
            Log.Add('Polygon spoke    FAILED');
        End;
    End
    Else Log.Add('PolygonConnect rule NOT FOUND');

    R := FindRule(eRule_RoutingCorners);
    If R <> Nil Then
    Begin
        Try
            R.BeginModify;
            R.MinSetback := MMsToCoord(0.10);
            R.EndModify;
            Log.Add('Corner setback   -> ' + MM(R.MinSetback) + '  (was 2.54 mm)');
        Except
            Log.Add('Corner setback   FAILED');
        End;
    End
    Else Log.Add('RoutingCorners rule NOT FOUND');

    R := FindRule(eRule_DiffPairsRouting);
    If R <> Nil Then
    Begin
        Try
            R.BeginModify;
            R.Gap                := MMsToCoord(0.150);
            R.MinGap             := MMsToCoord(0.150);
            R.MaxGap             := MMsToCoord(0.150);
            R.MinWidth           := MMsToCoord(0.150);
            R.PreferedWidth      := MMsToCoord(0.150);
            R.MaxWidth           := MMsToCoord(0.150);
            R.MaxUncoupledLength := MMsToCoord(2.0);
            R.EndModify;
            Log.Add('DiffPairs        -> gap ' + MM(R.Gap) +
                    '  uncoupled ' + MM(R.MaxUncoupledLength));
        Except
            Log.Add('DiffPairs        PARTIAL or FAILED - check Design > Rules');
        End;
    End
    Else Log.Add('DiffPairsRouting rule NOT FOUND');

    PCBServer.PostProcess;
    Finish('rules');
End;


Procedure ApplyGrids;
Begin
    If Not Start Then Exit;

    PCBServer.PreProcess;

    Try
        Brd.BeginModify;
        Brd.SnapGridSize := MMsToCoord(0.025);
        Brd.EndModify;
        Log.Add('snap grid       -> ' + MM(Brd.SnapGridSize));
    Except
        Log.Add('snap grid       FAILED');
    End;

    Try
        Brd.BeginModify;
        Brd.SnapGridSizeX := MMsToCoord(0.025);
        Brd.SnapGridSizeY := MMsToCoord(0.025);
        Brd.EndModify;
        Log.Add('snap grid X/Y   -> 0.025 mm');
    Except
        Log.Add('snap grid X/Y   not settable through this property');
    End;

    Try
        Brd.BeginModify;
        Brd.ComponentGridSize := MMsToCoord(0.025);
        Brd.EndModify;
        Log.Add('component grid  -> ' + MM(Brd.ComponentGridSize));
    Except
        Log.Add('component grid  FAILED');
    End;

    PCBServer.PostProcess;

    Log.Add('');
    Log.Add('The TRACK and VIA grids are 0.508 mm and are not exposed as board');
    Log.Add('properties in this build. If they are still imperial after this,');
    Log.Add('set them in the Properties panel with nothing selected.');
    Finish('grids');
End;

End.

{ End of ZuluSetup.pas }
