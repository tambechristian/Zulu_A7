{..............................................................................}
{  ZuluPlaneNets.pas             DelphiScript for Altium Designer              }
{                                                                              }
{  Assigns GND to the two internal plane layers of zulu_a7.PcbDoc.             }
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
