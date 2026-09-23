{..............................................................................}
{  ZuluPlaneNets.pas             DelphiScript for Altium Designer              }
{                                                                              }
{  Assigns the nets of the two internal plane layers of zulu_a7.PcbDoc.        }
{     AssignPlaneNetsToGND    both planes GND   (the original stack)          }
{     AssignL5ToVCC3V3        PLANE1 GND, PLANE2 VCC3V3  (stage 5, 2026-09-23)}
{     ReportPlaneNets         read them back                                  }
{                                                                              }
{  WHY A SCRIPT, AND WHY THE POLYGON RATHER THAN THE LAYER                     }
{  Altium Designer 26 does not expose a plane net in the Layer Stack Manager.  }
{  Selecting L2-GND there gives Name, Manufacturer, Material, Process, Weight, }
{  Thickness, Copper Orientation, Pullback distance, Description, Note and     }
{  Comment -- and no net, in the Properties panel or as a grid column. The net }
{  belongs to the SPLIT PLANE POLYGON that lives on the layer. Reading the     }
{  PcbDoc confirms it: Polygons6 holds two POLYGONTYPE=Split Plane polygons,   }
{  one on LAYER=PLANE1 and one on PLANE2, both with no net, while Board6 reads }
{  PLANE1NETNAME=(No Net) and PLANE2NETNAME=(No Net). Setting the polygons'    }
{  net is what updates those.                                                  }
{                                                                              }
{  This could not be done before Design > Import Changes, because GND did not  }
{  exist on the board until the netlist came across. It does now, one of 179.  }
{                                                                              }
{  A plane layer whose polygon carries no net is floating copper: every GND    }
{  pad and every stitch via on it would connect to nothing, and the two plane  }
{  rules (PlaneClearance, PlaneConnect) would have nothing to act on.          }
{                                                                              }
{  Objects are matched by LAYER, not by type. The first attempt asked only for }
{  ePolyObject and found NOTHING: in this build the plane copper comes back as }
{  ObjectId 11, a REGION, even though the file stores it under Polygons6 with  }
{  POLYGONTYPE=Split Plane. The iterator therefore asks for polygons, split    }
{  planes and regions together and filters on the layer, which is the one      }
{  property that is unambiguous. 606 such objects exist once components are    }
{  placed -- the rest are footprint courtyards on Mechanical 3 and 8 -- and    }
{  exactly four sit on the two internal planes.                                }
{                                                                              }
{  Run:  File > Run Script... > AssignPlaneNetsToGND                           }
{        File > Run Script... > ReportPlaneNets     to read them back          }
{  Then Ctrl+S. Only parameterless procedures appear in the picker.            }
{..............................................................................}

Const
    WANTED_NET = 'GND';


{ helper - takes parameters, so it stays out of the Run Script list }
Function IsInternalPlane(L : TLayer) : Boolean;
Begin
    { The six-layer stack puts its two planes on the first two internal plane
      layers, which is what LAYER=PLANE1 and LAYER=PLANE2 in the file mean.
      The rest are listed so the script still does the right thing if the
      stack ever grows another plane.                                        }
    Result := (L = eInternalPlane1) Or (L = eInternalPlane2) Or
              (L = eInternalPlane3) Or (L = eInternalPlane4);
End;


Function FindNetByName(Board : IPCB_Board; AName : String) : IPCB_Net;
Var
    Iter : IPCB_BoardIterator;
    Obj  : IPCB_Net;
Begin
    Result := Nil;
    Iter := Board.BoardIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eNetObject));
    Iter.AddFilter_LayerSet(AllLayers);
    Iter.AddFilter_Method(eProcessAll);
    Obj := Iter.FirstPCBObject;
    While Obj <> Nil Do
    Begin
        If Obj.Name = AName Then Result := Obj;
        Obj := Iter.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iter);
End;


Procedure AssignPlaneNetsToGND;
Var
    Board : IPCB_Board;
    Iter  : IPCB_BoardIterator;
    Poly  : IPCB_Polygon;
    GND   : IPCB_Net;
    N, Seen : Integer;
    S     : String;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.' + #13#10 +
                    'Open zulu_a7.PcbDoc, click in the board window, and run again.');
        Exit;
    End;

    GND := FindNetByName(Board, WANTED_NET);
    If GND = Nil Then
    Begin
        ShowMessage('There is no net called ' + WANTED_NET + ' on this board.' + #13#10 +
                    'Run Design > Import Changes first - the nets come from the schematic.');
        Exit;
    End;

    N := 0;
    Seen := 0;
    S := '';

    PCBServer.PreProcess;
    Try
        Iter := Board.BoardIterator_Create;
        Iter.AddFilter_ObjectSet(MkSet(ePolyObject, eSplitPlaneObject, eRegionObject));
        Iter.AddFilter_LayerSet(AllLayers);
        Iter.AddFilter_Method(eProcessAll);

        Poly := Iter.FirstPCBObject;
        While Poly <> Nil Do
        Begin
            Seen := Seen + 1;
            If IsInternalPlane(Poly.Layer) Then
            Begin
                Poly.BeginModify;
                Poly.Net := GND;
                Poly.EndModify;
                N := N + 1;
                S := S + '    ' + Layer2String(Poly.Layer) + '  ->  ' + WANTED_NET + #13#10;
            End;
            Poly := Iter.NextPCBObject;
        End;

        Board.BoardIterator_Destroy(Iter);
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - internal plane nets' + #13#10 + #13#10 +
                S +
                'Planes assigned: ' + IntToStr(N) + ' (two expected)' + #13#10 +
                'Polygons examined: ' + IntToStr(Seen) + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S.' + #13#10 +
                'Then re-run Tools > Design Rule Check: PlaneConnect and' + #13#10 +
                'PlaneClearance finally have a net to act on.');
End;


{..............................................................................}
{  STAGE 5, 2026-09-23 -- L5 STOPS BEING A SECOND GROUND AND BECOMES THE 3.3 V }
{  PLANE.                                                                      }
{                                                                              }
{  WHY.  Stage 4b ran out of routing room: our planners closed 92 of the last  }
{  140 signal connections and Altium's own Situs closed 90, failing a DIFFERENT }
{  50 -- a global shortage, not one blockage.  VCC3V3's routed trunks block     }
{  370 mm2 of a 1774 mm2 board, 213 mm of it inside the U1 surround and 88 mm   }
{  in the north band, which is exactly where the open flash, LED, SD and CHANx  }
{  lines have to pass.  Moving VCC3V3 onto L5 returns that area.                }
{                                                                              }
{  WHY IT IS ELECTRICALLY SOUND HERE.  The stack is                             }
{  Top / L2-GND / L3-SIG / L4-SIG / L5 / Bottom with gaps 0.0994 / 0.1000 /     }
{  1.1208 / 0.1000 / 0.0994 mm, so Top and L3 reference L2 and L4 and Bottom    }
{  reference L5.  Every I/O bank on this board is 3.3 V -- U1's only other      }
{  rails are VCC1V0 on 8 balls, VCC1V8 on 3 (C9/H13/J13, the CPG236 VCCAUX      }
{  pins) and VCCADC on one -- and U3, the SDRAM, runs on VCC3V3 and GND alone.  }
{  L4 and Bottom therefore end up referenced to the same potential as the I/O   }
{  supply of the signals on them, which is the textbook arrangement as long as  }
{  the VCC3V3-to-GND decoupling is distributed, and 48 capacitor pads are.      }
{  L2 stays GND: measured from the file it is one island of 1514 mm2 with all   }
{  211 GND pads over it, and it stays one island under the full stage-4b via    }
{  load.  L5 carrying VCC3V3 is likewise one island (1477.9 mm2 today, 1403.9   }
{  with 213 more vias) with all 128 VCC3V3 pads over it --                      }
{  tools/stage5/plane_islands.py proves both.                                   }
{                                                                              }
{  WHAT THIS SCRIPT DOES NOT DO.  It changes the two plane polygons' nets and   }
{  nothing else.  The routed VCC3V3 trunk must be removed and the VCC3V3 pads   }
{  tied to the plane by via in the same edit -- that is the stage-5 route plan, }
{  placed by PlaceStage5 in ZuluSetup.pas.  Renaming the L5-GND layer and       }
{  re-checking Width_PWR_VCC3V3 are separate manual steps; see docs/stage5.     }
{                                                                              }
{  Run:  File > Run Script... > AssignL5ToVCC3V3    then Ctrl+S.                }
{..............................................................................}

Procedure AssignL5ToVCC3V3;
Var
    Board : IPCB_Board;
    Iter  : IPCB_BoardIterator;
    Poly  : IPCB_Polygon;
    GND, PWR, Want : IPCB_Net;
    N, Seen : Integer;
    S     : String;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.' + #13#10 +
                    'Open zulu_a7.PcbDoc, click in the board window, and run again.');
        Exit;
    End;

    GND := FindNetByName(Board, 'GND');
    PWR := FindNetByName(Board, 'VCC3V3');
    If (GND = Nil) Or (PWR = Nil) Then
    Begin
        ShowMessage('This board is missing GND or VCC3V3 - nothing was changed.');
        Exit;
    End;

    N := 0;
    Seen := 0;
    S := '';

    PCBServer.PreProcess;
    Try
        Iter := Board.BoardIterator_Create;
        { the plane copper comes back as ObjectId 11, a region, in this build -- ask for
          all three kinds and filter on the layer, the one unambiguous property }
        Iter.AddFilter_ObjectSet(MkSet(ePolyObject, eSplitPlaneObject, eRegionObject));
        Iter.AddFilter_LayerSet(AllLayers);
        Iter.AddFilter_Method(eProcessAll);

        Poly := Iter.FirstPCBObject;
        While Poly <> Nil Do
        Begin
            Seen := Seen + 1;
            If IsInternalPlane(Poly.Layer) Then
            Begin
                If Poly.Layer = eInternalPlane2 Then Want := PWR Else Want := GND;
                Poly.BeginModify;
                Poly.Net := Want;
                Poly.EndModify;
                N := N + 1;
                S := S + '    ' + Layer2String(Poly.Layer) + '  ->  ' + Want.Name + #13#10;
            End;
            Poly := Iter.NextPCBObject;
        End;

        Board.BoardIterator_Destroy(Iter);
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - stage 5 plane nets' + #13#10 + #13#10 +
                S +
                'Planes assigned: ' + IntToStr(N) + ' (two expected)' + #13#10 +
                'Polygons examined: ' + IntToStr(Seen) + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S, then run ReportPlaneNets' + #13#10 +
                'to read the two nets back out of the board.');
End;


Procedure ReportPlaneNets;
Var
    Board : IPCB_Board;
    Iter  : IPCB_BoardIterator;
    Poly  : IPCB_Polygon;
    S     : String;
    N     : Integer;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    S := '';
    N := 0;
    Iter := Board.BoardIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(ePolyObject, eSplitPlaneObject, eRegionObject));
    Iter.AddFilter_LayerSet(AllLayers);
    Iter.AddFilter_Method(eProcessAll);

    Poly := Iter.FirstPCBObject;
    While Poly <> Nil Do
    Begin
        N := N + 1;
        S := S + '    kind ' + IntToStr(Poly.ObjectId) +
                 '  layer ' + Layer2String(Poly.Layer) + '  net = ';
        If Poly.Net = Nil Then
            S := S + '(none)' + #13#10
        Else
            S := S + Poly.Net.Name + #13#10;
        Poly := Iter.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iter);

    ShowMessage('Poly / split-plane / region objects: ' + IntToStr(N) + #13#10 +
                '(this build reports the plane copper as ObjectId 11, a region)' + #13#10 +
                #13#10 + S);
End;

End.

{ End of ZuluPlaneNets.pas }
