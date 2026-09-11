{..............................................................................}
{  ZuluKeepX3.pas                  DelphiScript for Altium Designer            }
{                                                                              }
{  The two Hirose keep-outs under X3, as TOP-LAYER keep-out FILLS.             }
{                                                                              }
{  WHY                                                                          }
{  X3 is a DM3D-SF microSD socket at (8.800, 12.475), rotation 90, Top -- read  }
{  out of Components6, not from a drawing. Two areas under its body must stay   }
{  free of top copper and of through vias. See docs/routing_readiness.md item   }
{  1: docs/drc_triage.md and footprint_lands.md both say these zones are "on    }
{  all layers" and BOTH ARE WRONG -- 17 pads fall inside them and every one is  }
{  on the Bottom Layer (all three U7 lands, L2-1, C147-2, C148-1/2, C149-1,     }
{  C150-1/2, C151-1, R103-1/2, R104-1, R108-2). Zero Top pads are inside. A     }
{  keep-out on all layers would bury the entire 1.0 V buck.                     }
{                                                                              }
{  So: Top Layer only. That still bars THROUGH vias inside the rectangles, so   }
{  the seven bottom-side buck GND pads pick up about 0.3 mm of extra stub to    }
{  reach a plane via outside them. That cost is known and accepted.             }
{                                                                              }
{  AN AREA, NOT AN OUTLINE -- and that is the real lesson, not "region vs fill".}
{  The board's own DRC evidence is that 155 keep-out TRACKS from the EAGLE      }
{  import produced zero violations while the single keep-out REGION in 742C083  }
{  produced 8. Those tracks were package outlines: thin lines that ran AROUND   }
{  their parts and crossed nothing. The region was a filled rectangle that      }
{  covered R34's lands. The distinguishing property is area, not primitive      }
{  class, and a Fill is an area.                                                }
{                                                                              }
{  Zone A was placed by hand through Place > Keepout > Fill and then given      }
{  exact numbers in the Properties panel; it is already in the file at          }
{  (7.2750, 7.5750)-(9.2750, 16.0750) on layer 1 with the keep-out flag set,    }
{  and all five restrictions (Via, Track, Copper, SMD Pad, TH Pad) ticked.      }
{  That menu command then refused to start again -- three attempts, no fill --  }
{  so zone B is made here instead, as the SAME primitive type so the pair is    }
{  consistent.                                                                  }
{                                                                              }
{  No PCBServer.PreProcess: an undeclared identifier is fatal in this           }
{  interpreter (Try/Except does not catch it) and a halt inside a transaction   }
{  strands it, after which Altium refuses every save. One undo step is cheap    }
{  by comparison. If this script dies on a name, nothing is half-built.         }
{                                                                              }
{  Run:  ReportKeepouts   counts first, changes nothing                        }
{        MakeZoneB        x 3.075..5.075, y 10.525..13.025                     }
{  Then Ctrl+S. Two keep-out fills and nothing else is the wanted state.       }
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


Procedure MakeZoneB;
Var
    F : IPCB_Fill;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    F := PCBServer.PCBObjectFactory(eFillObject, eNoDimension, eCreate_Default);
    F.X1Location := MMsToCoord(3.075);
    F.Y1Location := MMsToCoord(10.525);
    F.X2Location := MMsToCoord(5.075);
    F.Y2Location := MMsToCoord(13.025);
    F.Rotation   := 0;
    F.Layer      := eTopLayer;
    F.IsKeepout  := True;
    Brd.AddPCBObject(F);

    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - zone B placed.' + #13#10 + #13#10 +
                'Top Layer keep-out fill' + #13#10 +
                '  x 3.075 .. 5.075' + #13#10 +
                '  y 10.525 .. 13.025' + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S.');
End;


Procedure ReportKeepouts;
Var
    It : IPCB_BoardIterator;
    P  : IPCB_Primitive;
    NT, NF, NR, NO : Integer;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;

    NT := 0; NF := 0; NR := 0; NO := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eFillObject, eRegionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.IsKeepout Then
        Begin
            If P.ObjectId = eFillObject Then NF := NF + 1
            Else If P.ObjectId = eRegionObject Then NR := NR + 1
            Else If P.ObjectId = eTrackObject Then NT := NT + 1
            Else NO := NO + 1;
        End;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    ShowMessage('Zulu A7 - keep-out primitives on the board' + #13#10 + #13#10 +
                '   fills    ' + IntToStr(NF) + #13#10 +
                '   regions  ' + IntToStr(NR) + #13#10 +
                '   tracks   ' + IntToStr(NT) + #13#10 +
                '   other    ' + IntToStr(NO) + #13#10 + #13#10 +
                'Two fills and nothing else is the wanted state.');
End;

End.

{ End of ZuluKeepX3.pas }
