{..............................................................................}
{  ZuluPgood.pas                  DelphiScript for Altium Designer             }
{                                                                              }
{  Removes Q2 and R77 from zulu_a7_1.SchDoc and rewires LD5 straight to GND.   }
{                                                                              }
{  WHY                                                                          }
{  The chain today is VCC3V3 - LD5 - R78 - LD5_TO_Q2 - Q2(D,S) - GND, with Q2's }
{  gate on PGOOD and R77 pulling PGOOD up to VCC3V3. The netlist says PGOOD has }
{  exactly two pads, Q2-G and R77-1: NOTHING DRIVES IT. The schematic's own note }
{  on Q2 says why -- "its gate is on PGOOD, the LTC3569's open-drain output" --  }
{  and the LTC3569 was replaced by the bq24232 (U8) on 2026-09-09. The part that }
{  was meant to pull PGOOD low no longer exists, so Q2 is permanently on and LD5 }
{  is really a 3V3-present indicator wired through three parts and two nets.     }
{                                                                               }
{  The user chose, on 2026-09-11, to delete Q2 and R77 and wire LD5 directly:    }
{  VCC3V3 - LD5 - R78 - GND. Two parts and two nets leave the densest corner of  }
{  the board, where routing them would have been hardest.                       }
{                                                                               }
{  WHAT THIS DOES, EXACTLY                                                      }
{    deletes component Q2 and component R77                                     }
{    deletes every wire with an endpoint on a pin of either                     }
{    deletes the net label PGOOD and the GND power port that fed Q2's source     }
{    renames the net label LD5_TO_Q2 to GND, so R78's free pin becomes GND       }
{                                                                               }
{  Nets PGOOD and LD5_TO_Q2 disappear. LD5_K is untouched. After this, run       }
{  Design > Update PCB Document to take Q2 and R77 off the board.                }
{                                                                               }
{  Collect first, delete after: the same trap as the PCB side, where destroying  }
{  an object the iterator handed out left the traversal unable to find anything  }
{  more. Nothing is destroyed here, only removed.                               }
{                                                                               }
{  Run:  open zulu_a7_1.SchDoc and click in it, then                            }
{        File > Run Script... > ReportPgood     lists what would change          }
{        File > Run Script... > FixPgood        does it                          }
{  Then Ctrl+S.                                                                  }
{..............................................................................}

Const
    TOL = 1;          { schematic units; endpoints are on the grid, this is slack }


Function Doc : ISch_Document;
Begin
    Result := SchServer.GetCurrentSchDocument;
End;


{ helper - is this component one of the two we are removing }
Function IsDoomed(D : String) : Boolean;
Begin
    Result := (D = 'Q2') Or (D = 'R77');
End;


{ helper - collects the absolute pin locations of Q2 and R77 into a string list,
  each as 'x,y'. Also counts the components found. }
Function DoomedPinSpots(S : TStringList) : Integer;
Var
    It, PIt : ISch_Iterator;
    C       : ISch_Component;
    P       : ISch_Pin;
Begin
    Result := 0;
    It := Doc.SchIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eSchComponent));
    C := It.FirstSchObject;
    While C <> Nil Do
    Begin
        If IsDoomed(C.Designator.Text) Then
        Begin
            Result := Result + 1;
            PIt := C.SchIterator_Create;
            PIt.AddFilter_ObjectSet(MkSet(ePin));
            P := PIt.FirstSchObject;
            While P <> Nil Do
            Begin
                S.Add(IntToStr(P.Location.X) + ',' + IntToStr(P.Location.Y));
                P := PIt.NextSchObject;
            End;
            C.SchIterator_Destroy(PIt);
        End;
        C := It.NextSchObject;
    End;
    Doc.SchIterator_Destroy(It);
End;


{ helper - does either end of this wire sit on one of the doomed pin spots }
Function WireTouches(W : ISch_Wire; S : TStringList) : Boolean;
Var
    i, n : Integer;
    V    : TLocation;
Begin
    Result := False;
    n := W.VerticesCount;
    For i := 1 To n Do
    Begin
        V := W.Vertex[i];
        If S.IndexOf(IntToStr(V.X) + ',' + IntToStr(V.Y)) >= 0 Then Result := True;
    End;
End;


Procedure Survey(DoIt : Boolean);
Var
    Spots   : TStringList;
    Log     : TStringList;
    Kill    : TInterfaceList;
    Rename  : TInterfaceList;
    It      : ISch_Iterator;
    O       : ISch_GraphicalObject;
    C       : ISch_Component;
    W       : ISch_Wire;
    NL      : ISch_NetLabel;
    PP      : ISch_PowerObject;
    i, NC, NW, NL2, NP, NR : Integer;
    Tail    : String;
Begin
    If Doc = Nil Then
    Begin
        ShowMessage('No schematic document is focused.' + #13#10 +
                    'Open zulu_a7_1.SchDoc, click in it, and run again.');
        Exit;
    End;
    Spots := TStringList.Create;
    Log   := TStringList.Create;
    Kill  := TInterfaceList.Create;
    Rename := TInterfaceList.Create;
    NC := 0; NW := 0; NL2 := 0; NP := 0; NR := 0;

    NC := DoomedPinSpots(Spots);
    Log.Add('components Q2/R77 found: ' + IntToStr(NC) + ' (2 expected)');
    Log.Add('their pin locations: ' + IntToStr(Spots.Count) + ' (3 + 2 = 5 expected)');

    { one pass, collect everything that has to go }
    It := Doc.SchIterator_Create;
    O := It.FirstSchObject;
    While O <> Nil Do
    Begin
        If O.ObjectId = eSchComponent Then
        Begin
            C := O;
            If IsDoomed(C.Designator.Text) Then
            Begin
                Kill.Add(O);
                Log.Add('  DELETE component ' + C.Designator.Text);
            End;
        End
        Else If O.ObjectId = eWire Then
        Begin
            W := O;
            If WireTouches(W, Spots) Then
            Begin
                Kill.Add(O);
                NW := NW + 1;
            End;
        End
        Else If O.ObjectId = eNetLabel Then
        Begin
            NL := O;
            If NL.Text = 'PGOOD' Then
            Begin
                Kill.Add(O);
                NL2 := NL2 + 1;
                Log.Add('  DELETE net label PGOOD');
            End
            Else If NL.Text = 'LD5_TO_Q2' Then
            Begin
                NR := NR + 1;
                Rename.Add(O);
                Log.Add('  RENAME net label LD5_TO_Q2 -> GND');
            End;
        End
        Else If O.ObjectId = ePowerObject Then
        Begin
            PP := O;
            { match it by SITTING ON one of Q2's pins, not by a coordinate typed
              from a file dump -- the API's units need not be the file's }
            If (PP.Text = 'GND') And
               (Spots.IndexOf(IntToStr(PP.Location.X) + ',' + IntToStr(PP.Location.Y)) >= 0) Then
            Begin
                Kill.Add(O);
                NP := NP + 1;
                Log.Add('  DELETE the GND power port sitting on Q2 source');
            End;
        End;
        O := It.NextSchObject;
    End;
    Doc.SchIterator_Destroy(It);

    Log.Add('  DELETE wires touching those pins: ' + IntToStr(NW));

    If DoIt Then
        Tail := 'Done. Nothing is saved yet - press Ctrl+S, then run' + #13#10 +
                'Design > Update PCB Document zulu_a7.PcbDoc.'
    Else
        Tail := 'REPORT ONLY - nothing was changed.';

    { Everything above only LOOKED. All the mutation happens here, in one block
      that cannot raise: index loops over lists already built, no property that
      might not exist, no arithmetic. That matters -- on the PCB side an exception
      inside a transaction left PreProcess open and Altium refused every save
      afterwards until a bare PostProcess closed it. }
    If DoIt Then
    Begin
        SchServer.ProcessControl.PreProcess(Doc, '');
        For i := 0 To Rename.Count - 1 Do
        Begin
            NL := Rename.Items[i];
            NL.Text := 'GND';
        End;
        For i := 0 To Kill.Count - 1 Do
            Doc.RemoveSchObject(Kill.Items[i]);
        SchServer.ProcessControl.PostProcess(Doc, '');
        Doc.GraphicallyInvalidate;
    End;

    ShowMessage('Zulu A7 - PGOOD' + #13#10 + #13#10 +
                Log.Text + #13#10 +
                'net labels renamed: ' + IntToStr(NR) + ' (1 expected)' + #13#10 +
                'power ports deleted: ' + IntToStr(NP) + ' (1 expected)' + #13#10 +
                'objects removed: ' + IntToStr(Kill.Count) + #13#10 + #13#10 +
                Tail);

    Kill.Free;
    Rename.Free;
    Log.Free;
    Spots.Free;
End;


Procedure ReportPgood;
Begin
    Survey(False);
End;


Procedure FixPgood;
Begin
    Survey(True);
End;

End.

{ End of ZuluPgood.pas }
