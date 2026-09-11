{..............................................................................}
{  ZuluKeepouts.pas               DelphiScript for Altium Designer             }
{                                                                              }
{  Removes the copper-layer KEEPOUT primitives the EAGLE import created.       }
{                                                                              }
{  WHAT THEY ARE AND WHY THEY MUST GO                                          }
{  The source board C:\...\Zulu_A7\zulu_a7.brd carries art on EAGLE layer 39    }
{  (tKeepout) in fourteen packages and on layer 40 (bKeepout) in ZULU-DIP37.    }
{  In EAGLE those layers are a PLACEMENT keepout: they stop another COMPONENT   }
{  being placed there. They say nothing about copper.                           }
{                                                                               }
{  Altium has no placement-keepout concept, so the Import Wizard mapped them    }
{  onto the nearest thing it does have -- a ROUTING keepout on Top Layer and    }
{  Bottom Layer. The meaning changed from "no part here" to "no copper here",   }
{  and the outlines sit around, and in three footprints straight through, the   }
{  lands of the parts they belong to.                                           }
{                                                                               }
{  Counted from the saved PcbDoc before this script runs:                       }
{      584 keepout TRACKS   76 on Top Layer, 508 on Bottom Layer                }
{                           2 mil wide, no net, component index -1 (free        }
{                           primitives, so Update From Libraries will NOT       }
{                           remove them -- they have to be deleted here)        }
{        1 keepout REGION   KEEPOUTRESTRICTIONS=31, around R34 on the bottom,   }
{                           from package 742C083's layer-39 rectangle. This one }
{                           is already live: it is 8 of the board's 11          }
{                           Clearance violations, one per R34 pad.              }
{                                                                               }
{  143 of the 175 components are enclosed by one. Left in place they would      }
{  obstruct routing to the very pads they surround.                            }
{                                                                               }
{  The four tracks on each internal plane are NOT keepouts (they are the plane  }
{  outline, which is how a plane is bounded) and are left alone. Nothing on a   }
{  mechanical or overlay layer is touched. Only Top Layer and Bottom Layer are  }
{  considered, and only primitives whose IsKeepout is already True.            }
{                                                                               }
{  The PcbLib still contains the same art, so a future re-import or a library   }
{  update would bring it back. That is a separate cleanup.                     }
{                                                                               }
{  Run:  File > Run Script... > ReportCopperKeepouts    count first, change     }
{                                                        nothing                }
{        File > Run Script... > StripCopperKeepouts     delete them             }
{  Then Ctrl+S.                                                                 }
{..............................................................................}

Var
    Brd : IPCB_Board;


{ helper - is this one of the two outer copper layers }
Function IsOuterCopper(L : TLayer) : Boolean;
Begin
    Result := (L = eTopLayer) Or (L = eBottomLayer);
End;


{ helper - counts keepout primitives on the outer copper layers.
  Returns the total and fills the per-kind counters. }
Function CountKeepouts(Var NTrack, NArc, NFill, NRegion, NOther : Integer) : Integer;
Var
    Iter : IPCB_BoardIterator;
    P    : IPCB_Primitive;
Begin
    NTrack := 0; NArc := 0; NFill := 0; NRegion := 0; NOther := 0;
    Iter := Brd.BoardIterator_Create;
    Iter.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eFillObject,
                                   eRegionObject, ePolyObject));
    Iter.AddFilter_LayerSet(AllLayers);
    Iter.AddFilter_Method(eProcessAll);
    P := Iter.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.IsKeepout And IsOuterCopper(P.Layer) Then
        Begin
            Case P.ObjectId Of
                eTrackObject  : NTrack  := NTrack  + 1;
                eArcObject    : NArc    := NArc    + 1;
                eFillObject   : NFill   := NFill   + 1;
                eRegionObject : NRegion := NRegion + 1;
            Else
                NOther := NOther + 1;
            End;
        End;
        P := Iter.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(Iter);
    Result := NTrack + NArc + NFill + NRegion + NOther;
End;


Procedure ReportCopperKeepouts;
Var
    NT, NA, NF, NR, NO, Total : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    Total := CountKeepouts(NT, NA, NF, NR, NO);

    ShowMessage('Zulu A7 - keepout primitives on Top Layer and Bottom Layer' + #13#10 + #13#10 +
                '   tracks   ' + IntToStr(NT) + #13#10 +
                '   arcs     ' + IntToStr(NA) + #13#10 +
                '   fills    ' + IntToStr(NF) + #13#10 +
                '   regions  ' + IntToStr(NR) + #13#10 +
                '   other    ' + IntToStr(NO) + #13#10 +
                '   TOTAL    ' + IntToStr(Total) + #13#10 + #13#10 +
                'Reading the saved file says 584 tracks and 1 region.' + #13#10 +
                'Nothing has been changed by this report.');
End;


{ The first version of this deleted one object per pass, re-creating the iterator
  each time, and called PCBServer.DestroyPCBObject after Brd.RemovePCBObject. It
  removed exactly ONE object and then reported nothing left to do, while the file
  still held 583 tracks and the region. Destroying an object the board iterator
  had handed out evidently leaves the traversal unable to find anything further.

  So: ONE pass collects every victim into a list, the iterator is closed, and only
  then is anything removed. RemovePCBObject alone is enough -- it takes the object
  off the board, and nothing else holds a reference. }
Procedure StripCopperKeepouts;
Var
    Iter : IPCB_BoardIterator;
    P    : IPCB_Primitive;
    List : TInterfaceList;
    i, Before, After, Killed : Integer;
    NT, NA, NF, NR, NO : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.' + #13#10 +
                    'Open zulu_a7.PcbDoc, click in the board window, and run again.');
        Exit;
    End;

    Before := CountKeepouts(NT, NA, NF, NR, NO);
    Killed := 0;

    List := TInterfaceList.Create;
    Try
        Iter := Brd.BoardIterator_Create;
        Iter.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eFillObject,
                                       eRegionObject, ePolyObject));
        Iter.AddFilter_LayerSet(AllLayers);
        Iter.AddFilter_Method(eProcessAll);
        P := Iter.FirstPCBObject;
        While P <> Nil Do
        Begin
            If P.IsKeepout And IsOuterCopper(P.Layer) Then List.Add(P);
            P := Iter.NextPCBObject;
        End;
        Brd.BoardIterator_Destroy(Iter);

        PCBServer.PreProcess;
        Try
            For i := 0 To List.Count - 1 Do
            Begin
                Brd.RemovePCBObject(List.Items[i]);
                Killed := Killed + 1;
            End;
        Finally
            PCBServer.PostProcess;
        End;
    Finally
        List.Free;
    End;

    After := CountKeepouts(NT, NA, NF, NR, NO);
    Brd.ViewManager_FullUpdate;

    ShowMessage('Zulu A7 - copper keepouts stripped' + #13#10 + #13#10 +
                '   before   ' + IntToStr(Before) + #13#10 +
                '   collected' + IntToStr(Killed) + #13#10 +
                '   left     ' + IntToStr(After) + #13#10 + #13#10 +
                'The file held 583 tracks and 1 region before this run.' + #13#10 + #13#10 +
                'Nothing is saved yet - press Ctrl+S, then re-run the DRC.');
End;

End.

{ End of ZuluKeepouts.pas }
