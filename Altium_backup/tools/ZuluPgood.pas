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



{ Puts LD5's anode back on VCC3V3.

  COLLATERAL DAMAGE FROM FixPgood, caught by board_preflight.py: unconnected pads
  went from 39 across 7 components to 40 across 8, and the new one was LD5-A.
  FixPgood deletes every wire with an endpoint on a Q2 or R77 pin. One of those
  two wires ran from the VCC3V3 power port to R77-2 -- and the same branch fed
  LD5's anode, so deleting it took LD5-A off VCC3V3 as well. LD5-K and R78 were
  unaffected; only the anode floated.

  The fix is a VCC3V3 power port placed directly ON the anode pin. A power port
  sitting on a pin connects to it without a wire, so this cannot be severed again
  by anything that deletes wires, and it does not depend on finding the old port's
  coordinates.

  Run ReportLD5Anode first: it says whether the anode already has a port on it. }
Procedure LD5Anode(DoIt : Boolean);
Var
    It, PIt : ISch_Iterator;
    C       : ISch_Component;
    P, Anode: ISch_Pin;
    O       : ISch_GraphicalObject;
    PP      : ISch_PowerObject;
    Found, Already : Boolean;
    AX, AY  : Integer;
    Msg     : String;
Begin
    If Doc = Nil Then
    Begin
        ShowMessage('No schematic document is focused.' + #13#10 +
                    'Open zulu_a7_1.SchDoc, click in it, and run again.');
        Exit;
    End;

    Found := False; Already := False; AX := 0; AY := 0;

    It := Doc.SchIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eSchComponent));
    C := It.FirstSchObject;
    While (C <> Nil) And (Not Found) Do
    Begin
        If C.Designator.Text = 'LD5' Then
        Begin
            PIt := C.SchIterator_Create;
            PIt.AddFilter_ObjectSet(MkSet(ePin));
            P := PIt.FirstSchObject;
            While P <> Nil Do
            Begin
                If P.Designator = 'A' Then
                Begin
                    AX := P.Location.X;
                    AY := P.Location.Y;
                    Found := True;
                End;
                P := PIt.NextSchObject;
            End;
            C.SchIterator_Destroy(PIt);
        End;
        C := It.NextSchObject;
    End;
    Doc.SchIterator_Destroy(It);

    If Not Found Then
    Begin
        ShowMessage('LD5 pin A was not found on this sheet.');
        Exit;
    End;

    { is something already sitting on it }
    It := Doc.SchIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePowerObject));
    O := It.FirstSchObject;
    While O <> Nil Do
    Begin
        PP := O;
        If (PP.Location.X = AX) And (PP.Location.Y = AY) Then Already := True;
        O := It.NextSchObject;
    End;
    Doc.SchIterator_Destroy(It);

    Msg := 'Zulu A7 - LD5 anode' + #13#10 + #13#10 +
           '   LD5 pin A at ' + IntToStr(AX) + ',' + IntToStr(AY) + #13#10 +
           '   power port already on it: ' + BoolToStr(Already, True) + #13#10;

    If DoIt And (Not Already) Then
    Begin
        { Build the object FULLY before opening the transaction, and put only the
          register call inside it. ISch_PowerObject.OwnerDocument is READ-ONLY --
          assigning it raises "Property does not exist or is readonly", and the
          first version of this did that from inside PreProcess, which leaves the
          transaction open exactly as the PCB side did. RegisterSchObjectInContainer
          sets ownership; nothing else needs to. }
        PP := SchServer.SchObjectFactory(ePowerObject, eCreate_Default);
        PP.Location    := Point(AX, AY);
        PP.Text        := 'VCC3V3';
        PP.Style       := ePowerBar;
        PP.Orientation := eRotate90;

        SchServer.ProcessControl.PreProcess(Doc, '');
        Doc.RegisterSchObjectInContainer(PP);
        SchServer.ProcessControl.PostProcess(Doc, '');
        Doc.GraphicallyInvalidate;
        Msg := Msg + '   ADDED a VCC3V3 power port on the pin' + #13#10 + #13#10 +
               'Nothing is saved yet - press Ctrl+S, then Validate and regenerate' + #13#10 +
               'the netlist to confirm LD5-A is on VCC3V3.';
    End
    Else If Already Then
        Msg := Msg + #13#10 + 'Nothing to do.'
    Else
        Msg := Msg + #13#10 + 'REPORT ONLY - nothing was changed.';

    ShowMessage(Msg);
End;



{ RECOVERY, the schematic twin of ClosePendingTransaction in ZuluFixDrc.pas.
  A script that raises between SchServer.ProcessControl.PreProcess and its
  matching PostProcess leaves the transaction open, and Altium then refuses to
  save the document. One PostProcess closes it. }
Procedure CloseSchTransaction;
Var
    N : Integer;
Begin
    If Doc = Nil Then
    Begin
        ShowMessage('No schematic document is focused.');
        Exit;
    End;
    N := 0;
    Try
        SchServer.ProcessControl.PostProcess(Doc, '');
        N := 1;
    Except
        N := 0;
    End;
    ShowMessage('Zulu A7 - schematic transaction' + #13#10 + #13#10 +
                'PostProcess calls that succeeded: ' + IntToStr(N) + #13#10 + #13#10 +
                'Now try Ctrl+S.');
End;


Procedure ReportLD5Anode;
Begin
    LD5Anode(False);
End;


Procedure FixLD5Anode;
Begin
    LD5Anode(True);
End;


Procedure ReportPgood;
Begin
    Survey(False);
End;


Procedure FixPgood;
Begin
    Survey(True);
End;

{ ==========================================================================
  SHEET 1 LEFTOVERS, removed 2026-09-16 at the user's request
  ("clean up sheet 1 power supplies and remove unconnected wires, unconnected
  VCC3V3 source component, and unconnected GND component at the bottom right").

  Everything here is debris from FixPgood / FixLD5Anode in the LD5-R78 corner,
  identified from the file by tools/sheet1_orphans.py (file units):
    wires  (785,247)-(805,247)  (735,247)-(785,247)        an island at y 247
           (845,357)-(845,367)  (845,367)-(845,377)
           (740,377)-(785,377)  (785,377)-(845,377)        a chain off LD5's anode, dead-ending at (740,377)
           (845,277)-(845,287)                             a stub under R78-1
           (845,207)-(845,217)  (735,207)-(845,207)        an island carrying the GND port below
    power port VCC3V3 at (785,341)   -- on nothing
    power port GND    at (748,207)   -- on the y 207 island, reaches no pin
    junctions at (785,247) (845,367) (785,377) (785,341) (748,207)
  KEPT: the VCC3V3 port ON LD5-A (845,367), the LD5_K label and wire, and the
  GND net label on R78-1 (845,287).

  Positions are matched through the API's own units: LD5 pin A (file 845,367)
  and R78 pin 1 (file 845,287) are read back and give the scale and origin,
  so no file coordinate is ever compared with an API coordinate directly.
  Junctions are found by kind COUNT (37 on this sheet) inside a single iterator pass.
  Collect first, then delete in one block that cannot raise; nothing is
  deleted unless all 16 objects are found exactly once.

  Run:  open zulu_a7_1.SchDoc, click in it, File > Run Script... >
        ReportSheet1Leftovers, then CleanSheet1Leftovers, then Ctrl+S.
  ========================================================================== }

Function S1Pin(Des, PinName : String; Var X, Y : Integer) : Boolean;
Var
    It, PIt : ISch_Iterator;
    C       : ISch_Component;
    P       : ISch_Pin;
Begin
    Result := False;
    It := Doc.SchIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eSchComponent));
    C := It.FirstSchObject;
    While C <> Nil Do
    Begin
        If C.Designator.Text = Des Then
        Begin
            PIt := C.SchIterator_Create;
            PIt.AddFilter_ObjectSet(MkSet(ePin));
            P := PIt.FirstSchObject;
            While P <> Nil Do
            Begin
                If P.Designator = PinName Then
                Begin
                    X := P.Location.X;
                    Y := P.Location.Y;
                    Result := True;
                End;
                P := PIt.NextSchObject;
            End;
            C.SchIterator_Destroy(PIt);
        End;
        C := It.NextSchObject;
    End;
    Doc.SchIterator_Destroy(It);
End;

Function S1At(AX, AY : Integer; FX, FY, S, X0, Y0 : Double) : Boolean;
Begin
    Result := (Abs(AX - (X0 + FX * S)) <= Abs(S) * 0.5) And (Abs(AY - (Y0 + FY * S)) <= Abs(S) * 0.5);
End;

Function S1Seg(W : ISch_Wire; X1, Y1, X2, Y2, S, X0, Y0 : Double) : Boolean;
Var
    A, B : TLocation;
Begin
    Result := False;
    If W.VerticesCount <> 2 Then Exit;
    A := W.Vertex[1];
    B := W.Vertex[2];
    Result := (S1At(A.X, A.Y, X1, Y1, S, X0, Y0) And S1At(B.X, B.Y, X2, Y2, S, X0, Y0)) Or
              (S1At(A.X, A.Y, X2, Y2, S, X0, Y0) And S1At(B.X, B.Y, X1, Y1, S, X0, Y0));
End;

Function S1WireIndex(W : ISch_Wire; S, X0, Y0 : Double) : Integer;
Begin
    Result := -1;
    If S1Seg(W, 785, 247, 805, 247, S, X0, Y0) Then Result := 0;
    If S1Seg(W, 735, 247, 785, 247, S, X0, Y0) Then Result := 1;
    If S1Seg(W, 845, 357, 845, 367, S, X0, Y0) Then Result := 2;
    If S1Seg(W, 845, 367, 845, 377, S, X0, Y0) Then Result := 3;
    If S1Seg(W, 740, 377, 785, 377, S, X0, Y0) Then Result := 4;
    If S1Seg(W, 785, 377, 845, 377, S, X0, Y0) Then Result := 5;
    If S1Seg(W, 845, 277, 845, 287, S, X0, Y0) Then Result := 6;
    If S1Seg(W, 845, 207, 845, 217, S, X0, Y0) Then Result := 7;
    If S1Seg(W, 735, 207, 845, 207, S, X0, Y0) Then Result := 8;
End;

Function S1JunctionIndex(X, Y : Integer; S, X0, Y0 : Double) : Integer;
Begin
    Result := -1;
    If S1At(X, Y, 785, 247, S, X0, Y0) Then Result := 0;
    If S1At(X, Y, 845, 367, S, X0, Y0) Then Result := 1;
    If S1At(X, Y, 785, 377, S, X0, Y0) Then Result := 2;
    If S1At(X, Y, 785, 341, S, X0, Y0) Then Result := 3;
    If S1At(X, Y, 748, 207, S, X0, Y0) Then Result := 4;
End;

Procedure Sheet1Leftovers(DoIt : Boolean);
Var
    Log   : TStringList;
    Ids   : TStringList;
    Kill  : TInterfaceList;
    Other : TInterfaceList;
    It    : ISch_Iterator;
    O     : ISch_GraphicalObject;
    W     : ISch_Wire;
    PP    : ISch_PowerObject;
    AX, AY, RX, RY, i, k, n, v, NKinds : Integer;
    Key, JKind : String;
    S1s, S1x0, S1y0 : Double;
    W0, W1, W2, W3, W4, W5, W6, W7, W8 : Integer;
    J0, J1, J2, J3, J4 : Integer;
    NP3, NPG : Integer;
    Ok : Boolean;
Begin
    If Doc = Nil Then
    Begin
        ShowMessage('No schematic document is focused.' + #13#10 + 'Open zulu_a7_1.SchDoc, click in it, and run again.');
        Exit;
    End;
    If Not (S1Pin('LD5', 'A', AX, AY) And S1Pin('R78', '1', RX, RY)) Then
    Begin
        ShowMessage('LD5 pin A or R78 pin 1 not found - is this zulu_a7_1.SchDoc? Nothing changed.');
        Exit;
    End;
    S1s := (AY - RY) / 80.0;
    S1x0 := AX - 845 * S1s;
    S1y0 := AY - 367 * S1s;
    Log := TStringList.Create;
    Ids := TStringList.Create;
    Kill := TInterfaceList.Create;
    Other := TInterfaceList.Create;
    W0 := 0; W1 := 0; W2 := 0; W3 := 0; W4 := 0; W5 := 0; W6 := 0; W7 := 0; W8 := 0;
    J0 := 0; J1 := 0; J2 := 0; J3 := 0; J4 := 0;
    NP3 := 0; NPG := 0;
    Log.Add('scale ' + FloatToStr(S1s) + ' API units per file unit (LD5-A x ' + IntToStr(AX) + ', R78-1 x ' + IntToStr(RX) + ')');

    { ONE iterator pass only.  Every earlier attempt that opened a second iterator in this
      procedure stopped at the second loop with Error in declaration block.  Objects that are
      not components, wires, net labels or power ports are kept aside without touching their
      Location (not every kind has one), and every object's kind is tallied as kind#n. }
    It := Doc.SchIterator_Create;
    O := It.FirstSchObject;
    While O <> Nil Do
    Begin
        Key := IntToStr(O.ObjectId);
        n := 1;
        While Ids.IndexOf(Key + '#' + IntToStr(n)) >= 0 Do n := n + 1;
        Ids.Add(Key + '#' + IntToStr(n));
        If O.ObjectId = eWire Then
        Begin
            W := O;
            k := S1WireIndex(W, S1s, S1x0, S1y0);
            If k >= 0 Then Kill.Add(O);
            If k = 0 Then W0 := W0 + 1;
            If k = 1 Then W1 := W1 + 1;
            If k = 2 Then W2 := W2 + 1;
            If k = 3 Then W3 := W3 + 1;
            If k = 4 Then W4 := W4 + 1;
            If k = 5 Then W5 := W5 + 1;
            If k = 6 Then W6 := W6 + 1;
            If k = 7 Then W7 := W7 + 1;
            If k = 8 Then W8 := W8 + 1;
        End
        Else If O.ObjectId = ePowerObject Then
        Begin
            PP := O;
            If (PP.Text = 'VCC3V3') And S1At(PP.Location.X, PP.Location.Y, 785, 341, S1s, S1x0, S1y0) Then
            Begin
                NP3 := NP3 + 1;
                Kill.Add(O);
            End;
            If (PP.Text = 'GND') And S1At(PP.Location.X, PP.Location.Y, 748, 207, S1s, S1x0, S1y0) Then
            Begin
                NPG := NPG + 1;
                Kill.Add(O);
            End;
        End
        Else If (O.ObjectId <> eSchComponent) And (O.ObjectId <> eNetLabel) Then
            Other.Add(O);
        O := It.NextSchObject;
    End;
    Doc.SchIterator_Destroy(It);

    { Junctions: this build has no eJunction name, so the junction kind is the one with
      exactly 37 members -- sheet 1 holds 37 junction records (RECORD=29 in the file) and no
      other top-level kind has 37.  Only objects of that kind have their Location read. }
    JKind := '';
    NKinds := 0;
    For v := 0 To 200 Do
        If (Ids.IndexOf(IntToStr(v) + '#37') >= 0) And (Ids.IndexOf(IntToStr(v) + '#38') < 0) Then
        Begin
            JKind := IntToStr(v);
            NKinds := NKinds + 1;
        End;
    Log.Add('object kinds with exactly 37 members: ' + IntToStr(NKinds) + ' (kind ' + JKind + ')');
    If NKinds = 1 Then
        For i := 0 To Other.Count - 1 Do
        Begin
            O := Other.Items[i];
            If IntToStr(O.ObjectId) = JKind Then
            Begin
                k := S1JunctionIndex(O.Location.X, O.Location.Y, S1s, S1x0, S1y0);
                If k >= 0 Then Kill.Add(O);
                If k = 0 Then J0 := J0 + 1;
                If k = 1 Then J1 := J1 + 1;
                If k = 2 Then J2 := J2 + 1;
                If k = 3 Then J3 := J3 + 1;
                If k = 4 Then J4 := J4 + 1;
            End;
        End;

    Ok := (NP3 = 1) And (NPG = 1) And (W0 = 1) And (W1 = 1) And (W2 = 1) And (W3 = 1) And (W4 = 1) And
          (W5 = 1) And (W6 = 1) And (W7 = 1) And (W8 = 1) And (J0 = 1) And (J1 = 1) And (J2 = 1) And
          (J3 = 1) And (J4 = 1) And (Kill.Count = 16);
    Log.Add('wires found, each should be 1: ' + IntToStr(W0) + ' ' + IntToStr(W1) + ' ' + IntToStr(W2) + ' ' + IntToStr(W3) + ' ' +
            IntToStr(W4) + ' ' + IntToStr(W5) + ' ' + IntToStr(W6) + ' ' + IntToStr(W7) + ' ' + IntToStr(W8));
    Log.Add('junction points found, each should be 1: ' + IntToStr(J0) + ' ' + IntToStr(J1) + ' ' + IntToStr(J2) + ' ' + IntToStr(J3) + ' ' + IntToStr(J4));
    Log.Add('VCC3V3 port at (785,341): ' + IntToStr(NP3) + '   GND port at (748,207): ' + IntToStr(NPG));
    Log.Add('objects collected: ' + IntToStr(Kill.Count) + ' (16 expected)');

    If DoIt And Ok Then
    Begin
        SchServer.ProcessControl.PreProcess(Doc, '');
        For i := 0 To Kill.Count - 1 Do
            Doc.RemoveSchObject(Kill.Items[i]);
        SchServer.ProcessControl.PostProcess(Doc, '');
        Doc.GraphicallyInvalidate;
        Log.Add('');
        Log.Add('REMOVED 16 objects. Press Ctrl+S.');
    End
    Else If DoIt Then
        Log.Add('NOT every object was found exactly once - NOTHING was changed.')
    Else
        Log.Add('REPORT ONLY - nothing was changed.');
    ShowMessage('Zulu A7 - sheet 1 leftovers' + #13#10 + #13#10 + Log.Text);
    Kill.Free;
    Other.Free;
    Ids.Free;
    Log.Free;
End;


Procedure ReportSheet1Leftovers;
Begin
    Sheet1Leftovers(False);
End;


Procedure CleanSheet1Leftovers;
Begin
    Sheet1Leftovers(True);
End;

End.

{ End of ZuluPgood.pas }
