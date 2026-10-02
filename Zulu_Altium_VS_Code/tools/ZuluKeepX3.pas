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
{  Run, with the PcbDoc focused:                                               }
{        ReportKeepouts     counts first, changes nothing                      }
{        MakeZoneB          x 3.075..5.075, y 10.525..13.025                   }
{  Run, with the PcbLib focused:                                               }
{        ReportLibKeepouts  counts, changes nothing -- RUN THIS FIRST          }
{        StripLibKeepouts   deletes the imported art                           }
{  Then Ctrl+S on whichever document you changed.                              }
{..............................................................................}

Var
    Brd : IPCB_Board;
    Lib : IPCB_Library;


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

{..............................................................................}
{  Strips the EAGLE keep-out art from zulu_a7.PcbLib.                          }
{                                                                              }
{  WHY THIS IS NOT OPTIONAL EVEN THOUGH THE BOARD IS ALREADY CLEAN             }
{  ZuluKeepouts.pas deleted 584 keep-out tracks and one keep-out region from    }
{  the BOARD. It says so at its own line 36: the PcbLib still holds the same    }
{  art, so a re-import or a library update brings it all back. 64 keep-out      }
{  tracks across 13 patterns -- 1X03-NOSILK, 32X25, C0201, C0402, C0603, C0805, }
{  DM3AT-SF-PEJM5, MOLEX-105017-0001, R0201, R0402, SOIC-8_208MIL, TSOPII-54    }
{  at 4 each, ZULU-DIP37 at 8 Top plus 8 Bottom -- plus one keep-out region in  }
{  742C083. 144 of the 173 components resolve to one of those patterns, and the }
{  PcbLib is a document of this project. One Update PCB Document From PCB       }
{  Libraries, one new 0402 placed by ECO, or one accepted Component Link report }
{  reinstates 584 copper obstacles: 76 on Top, 508 on Bottom. The arithmetic    }
{  reproduces exactly, 142 x 4 + 1 x 16.                                       }
{                                                                              }
{  In EAGLE these lived on layers 39/40, tKeepout/bKeepout, which are a         }
{  PLACEMENT keep-out -- they stop another COMPONENT being put there and say    }
{  nothing about copper. Altium has no placement-keep-out concept, so the       }
{  Import Wizard mapped them to the nearest thing it does have, a ROUTING       }
{  keep-out on Top and Bottom Layer, and the meaning changed from "no part      }
{  here" to "no copper here".                                                   }
{                                                                              }
{  THE CANARY RULE APPLIES. Every API name below is used for the first time in  }
{  this project -- GetCurrentPCBLibrary, LibraryIterator_Create,                }
{  SetState_FilterAll, GroupIterator_Create, RemovePCBObject on a footprint --  }
{  and an undeclared identifier is fatal in this interpreter: Try/Except does   }
{  not catch it, the script halts on a modal error, and the scripting system    }
{  then refuses to start anything until Run > Stop. So ReportLibKeepouts runs   }
{  FIRST. It touches every one of those names and changes nothing. Only if it   }
{  prints a count is StripLibKeepouts safe to run.                             }
{                                                                              }
{  COLLECT THEN REMOVE, never remove inside the traversal. ZuluKeepouts.pas     }
{  learned this the hard way on the board: destroying an object the iterator    }
{  had handed out removed exactly ONE primitive and then reported nothing left  }
{  to do, while the file still held 583 tracks.                                 }
{                                                                              }
{  Run with zulu_a7.PcbLib FOCUSED, not the PcbDoc:                             }
{        ReportLibKeepouts   counts, changes nothing                            }
{        StripLibKeepouts    deletes them                                       }
{  Then Ctrl+S on the library. The BOARD does not change either way.           }
{..............................................................................}

Function LibOrNil : IPCB_Library;
Begin
    Result := PCBServer.GetCurrentPCBLibrary;
    If Result = Nil Then
        ShowMessage('No PCB LIBRARY is focused.' + #13#10 +
                    'Open zulu_a7.PcbLib, click in the footprint window, and run again.' +
                    #13#10 + 'This is the library script, not the board one.');
End;


Procedure ReportLibKeepouts;
Var
    FIt  : IPCB_LibraryIterator;
    Fp   : IPCB_LibComponent;
    GIt  : IPCB_GroupIterator;
    P    : IPCB_Primitive;
    Log  : TStringList;
    N, Total, Pats : Integer;
Begin
    Lib := LibOrNil;
    If Lib = Nil Then Exit;

    Log := TStringList.Create;
    Total := 0; Pats := 0;

    FIt := Lib.LibraryIterator_Create;
    FIt.SetState_FilterAll;
    Fp := FIt.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        N := 0;
        GIt := Fp.GroupIterator_Create;
        GIt.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eFillObject, eRegionObject));
        P := GIt.FirstPCBObject;
        While P <> Nil Do
        Begin
            If P.IsKeepout Then N := N + 1;
            P := GIt.NextPCBObject;
        End;
        Fp.GroupIterator_Destroy(GIt);

        If N > 0 Then
        Begin
            Log.Add('   ' + Fp.Name + '   ' + IntToStr(N));
            Total := Total + N;
            Pats := Pats + 1;
        End;
        Fp := FIt.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(FIt);

    ShowMessage('Zulu A7 - keep-out primitives in the PcbLib' + #13#10 + #13#10 +
                Log.Text + #13#10 +
                '   patterns ' + IntToStr(Pats) + '   primitives ' + IntToStr(Total) + #13#10 + #13#10 +
                'Reading the file says 13 patterns and 65 primitives.' + #13#10 +
                'Nothing was changed.');
    Log.Free;
End;


Procedure StripLibKeepouts;
Var
    FIt   : IPCB_LibraryIterator;
    Fp    : IPCB_LibComponent;
    GIt   : IPCB_GroupIterator;
    P     : IPCB_Primitive;
    Kill  : TInterfaceList;
    i, Total, Pats : Integer;
    Log   : TStringList;
Begin
    Lib := LibOrNil;
    If Lib = Nil Then Exit;

    Log := TStringList.Create;
    Total := 0; Pats := 0;

    FIt := Lib.LibraryIterator_Create;
    FIt.SetState_FilterAll;
    Fp := FIt.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        Kill := TInterfaceList.Create;
        Try
            GIt := Fp.GroupIterator_Create;
            GIt.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eFillObject, eRegionObject));
            P := GIt.FirstPCBObject;
            While P <> Nil Do
            Begin
                If P.IsKeepout Then Kill.Add(P);
                P := GIt.NextPCBObject;
            End;
            Fp.GroupIterator_Destroy(GIt);

            If Kill.Count > 0 Then
            Begin
                For i := 0 To Kill.Count - 1 Do
                    Fp.RemovePCBObject(Kill.Items[i]);
                Log.Add('   ' + Fp.Name + '   ' + IntToStr(Kill.Count));
                Total := Total + Kill.Count;
                Pats := Pats + 1;
            End;
        Finally
            Kill.Free;
        End;
        Fp := FIt.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(FIt);

    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - PcbLib keep-out art stripped' + #13#10 + #13#10 +
                Log.Text + #13#10 +
                '   patterns ' + IntToStr(Pats) + '   removed ' + IntToStr(Total) + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S on the LIBRARY.' + #13#10 +
                'Then re-run ReportLibKeepouts; it should print zero.');
    Log.Free;
End;

End.

{ End of ZuluKeepX3.pas }
