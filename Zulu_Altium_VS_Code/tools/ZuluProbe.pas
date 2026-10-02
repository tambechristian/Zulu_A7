{..............................................................................}
{  ZuluProbe.pas                   DelphiScript for Altium Designer            }
{                                                                              }
{  ReportSetup died on "Undeclared identifier: PreferedLimit". The IPCB_Rule    }
{  property names in this build are not the ones the Rules6 stream uses, and    }
{  guessing them one GUI round-trip at a time is slow. This script asks the     }
{  interpreter directly: every candidate name is read inside its own            }
{  Try/Except, so the ones that do not exist are reported rather than fatal.    }
{                                                                              }
{  It also proves the premise -- BOGUS_NOT_A_PROPERTY must come back "--". If   }
{  it does not appear at all, Try/Except is NOT catching undeclared identifiers }
{  and every later line is unreachable.                                         }
{                                                                              }
{  Rules are found BY NAME, not by TRuleKind constant, so a wrong enum name     }
{  cannot take the script down either.                                          }
{                                                                              }
{  Changes nothing.  Run: ProbeNames                                            }
{..............................................................................}

Var
    Brd : IPCB_Board;
    Log : TStringList;


Function MM(C : TCoord) : String;
Begin
    Result := FloatToStr(CoordToMMs(C)) + ' mm';
End;


Function FindRuleByName(Const N : String) : IPCB_Rule;
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
        If (Result = Nil) And (R.Name = N) Then Result := R;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;


Procedure ProbeNames;
Var
    R : IPCB_Rule;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;
    Log := TStringList.Create;

    Log.Add('--- Width ---');
    R := FindRuleByName('Width');
    If R = Nil Then Log.Add('  RULE NOT FOUND')
    Else
    Begin
        Try Log.Add('  MinLimit         ' + MM(R.MinLimit));         Except Log.Add('  MinLimit         --'); End;
        Try Log.Add('  MaxLimit         ' + MM(R.MaxLimit));         Except Log.Add('  MaxLimit         --'); End;
        Try Log.Add('  FavoredLimit     ' + MM(R.FavoredLimit));     Except Log.Add('  FavoredLimit     --'); End;
        Try Log.Add('  PreferedWidth    ' + MM(R.PreferedWidth));    Except Log.Add('  PreferedWidth    --'); End;
        Try Log.Add('  PreferredWidth   ' + MM(R.PreferredWidth));   Except Log.Add('  PreferredWidth   --'); End;
        Try Log.Add('  FavoredWidth     ' + MM(R.FavoredWidth));     Except Log.Add('  FavoredWidth     --'); End;
        Try Log.Add('  BOGUS_NOT_A_PROP ' + MM(R.Bogus_Not_A_Prop)); Except Log.Add('  BOGUS_NOT_A_PROP --  (good: Try works)'); End;
    End;

    Log.Add('');
    Log.Add('--- PolygonConnect ---');
    R := FindRuleByName('PolygonConnect');
    If R = Nil Then Log.Add('  RULE NOT FOUND')
    Else
    Begin
        Try Log.Add('  ReliefConductorWidth ' + MM(R.ReliefConductorWidth)); Except Log.Add('  ReliefConductorWidth --'); End;
        Try Log.Add('  ReliefAirGap         ' + MM(R.ReliefAirGap));         Except Log.Add('  ReliefAirGap         --'); End;
        Try Log.Add('  AirGapWidth          ' + MM(R.AirGapWidth));          Except Log.Add('  AirGapWidth          --'); End;
        Try Log.Add('  ReliefEntries        ' + IntToStr(R.ReliefEntries));  Except Log.Add('  ReliefEntries        --'); End;
    End;

    Log.Add('');
    Log.Add('--- RoutingCorners ---');
    R := FindRuleByName('RoutingCorners');
    If R = Nil Then Log.Add('  RULE NOT FOUND')
    Else
    Begin
        Try Log.Add('  MinSetback       ' + MM(R.MinSetback));       Except Log.Add('  MinSetback       --'); End;
        Try Log.Add('  MaxSetback       ' + MM(R.MaxSetback));       Except Log.Add('  MaxSetback       --'); End;
    End;

    Log.Add('');
    Log.Add('--- DiffPairsRouting ---');
    R := FindRuleByName('DiffPairsRouting');
    If R = Nil Then Log.Add('  RULE NOT FOUND')
    Else
    Begin
        Try Log.Add('  MinGap             ' + MM(R.MinGap));             Except Log.Add('  MinGap             --'); End;
        Try Log.Add('  MaxGap             ' + MM(R.MaxGap));             Except Log.Add('  MaxGap             --'); End;
        Try Log.Add('  Gap                ' + MM(R.Gap));                Except Log.Add('  Gap                --'); End;
        Try Log.Add('  MinLimit           ' + MM(R.MinLimit));           Except Log.Add('  MinLimit           --'); End;
        Try Log.Add('  MaxLimit           ' + MM(R.MaxLimit));           Except Log.Add('  MaxLimit           --'); End;
        Try Log.Add('  MostFreqGap        ' + MM(R.MostFreqGap));        Except Log.Add('  MostFreqGap        --'); End;
        Try Log.Add('  MaxUncoupledLength ' + MM(R.MaxUncoupledLength)); Except Log.Add('  MaxUncoupledLength --'); End;
    End;

    Log.Add('');
    Log.Add('--- board grids ---');
    Try Log.Add('  SnapGridSize      ' + MM(Brd.SnapGridSize));      Except Log.Add('  SnapGridSize      --'); End;
    Try Log.Add('  SnapGridSizeX     ' + MM(Brd.SnapGridSizeX));     Except Log.Add('  SnapGridSizeX     --'); End;
    Try Log.Add('  ComponentGridSize ' + MM(Brd.ComponentGridSize)); Except Log.Add('  ComponentGridSize --'); End;

    ShowMessage('Zulu A7 - property probe' + #13#10 + #13#10 + Log.Text +
                #13#10 + 'Nothing was changed.');
    Log.Free;
End;



{ ---------------------------------------------------------------------------
  2026-09-15: is the solder-mask TENTING flag reachable from a script?

  The Rules6 record of a SolderMaskExpansion rule carries ISTENTINGTOP (and,
  when set, ISTENTINGBOTTOM). The property name that writes it has never been
  used in this project. An UNDECLARED name halts the script with a modal error
  and Try/Except never runs -- so this canary uses the name once, on a rule
  object that is created by the factory and NEVER added to the board. If it
  halts: dismiss the error, Run > Stop (Ctrl+F3), and set the checkbox in the
  Rules dialog instead. If it runs: SetViaTenting in ZuluSetup.pas may use it.

  Changes nothing.  Run: ProbeTenting
  --------------------------------------------------------------------------- }

Procedure ProbeTenting;
Var
    R : IPCB_Rule;
Begin
    R := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);
    R.IsTentingTop    := True;
    R.IsTentingBottom := True;
    If R.IsTentingTop And R.IsTentingBottom Then
        ShowMessage('Zulu A7 - tenting probe' + #13#10 + #13#10 +
                    'IsTentingTop and IsTentingBottom are DECLARED and read back True.' + #13#10 +
                    'The rule object was never added to the board. Nothing was changed.' + #13#10 + #13#10 +
                    'SetViaTenting in ZuluSetup.pas may now be run.')
    Else
        ShowMessage('Zulu A7 - tenting probe' + #13#10 + #13#10 +
                    'The names are declared but read back FALSE after a True write.' + #13#10 +
                    'Do NOT run SetViaTenting; set the checkboxes in the Rules dialog.');
End;




{ ---------------------------------------------------------------------------
  2026-09-15: can a script create a VIA with the obvious names?

  The fan-out needs ~100 vias placed by script. Track creation is proven
  (ZuluBoardOutline.pas); via creation is not. This canary uses each name
  once on a via object that is created by the factory and NEVER added to the
  board, and reads every value back. If it halts with "Undeclared identifier"
  the editor jumps to the line that names the culprit; dismiss, Ctrl+F3.

  Changes nothing.  Run: ProbeVia
  --------------------------------------------------------------------------- }

Procedure ProbeVia;
Var
    V : IPCB_Via;
Begin
    V := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    V.X         := MMsToCoord(1.0);
    V.Y         := MMsToCoord(2.0);
    V.Size      := MMsToCoord(0.35);
    V.HoleSize  := MMsToCoord(0.20);
    V.LowLayer  := eTopLayer;
    V.HighLayer := eBottomLayer;
    ShowMessage('Zulu A7 - via probe' + #13#10 + #13#10 +
                'eViaObject / IPCB_Via / X / Y / Size / HoleSize / LowLayer / HighLayer are all declared.' + #13#10 +
                'read back: X ' + MM(V.X) + '  Y ' + MM(V.Y) + '  Size ' + MM(V.Size) + '  Hole ' + MM(V.HoleSize) + #13#10 +
                'The via was never added to the board. Nothing was changed.');
End;


{ ---------------------------------------------------------------------------
  ProbeR78Net (2026-09-15).  R78 pad 1 is written with net -1 in Pads6 after
  EVERY attempt to put it on GND: TieR78ToGnd (119e15b), the Import Changes ECO
  (0a7bdda) and BlkPadNet in PlaceRegBlock (2026-09-15) all reported success and
  none survived a save.  This reads what the live board holds: each R78 pad's
  net, how many R78 pads a board-wide pad iterator sees, and whether that
  iterator reports R78-1 on GND.  Changes nothing.
  --------------------------------------------------------------------------- }

Procedure ProbeR78Net;
Var
    C   : IPCB_Component;
    It  : IPCB_GroupIterator;
    BIt, NIt : IPCB_BoardIterator;
    P, Hit : IPCB_Pad;
    N   : IPCB_Net;
    S, nm : String;
    K, NG, NAll, Same : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    S := '';
    C := Brd.GetPcbComponentByRefDes('R78');
    If C = Nil Then
    Begin
        ShowMessage('R78 not found');
        Exit;
    End;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        nm := '(no net)';
        If P.Net <> Nil Then nm := P.Net.Name;
        S := S + 'group iterator: R78-' + P.Name + ' at ' + MM(P.X) + ', ' + MM(P.Y) + '  net ' + nm + #13#10;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    K := 0;
    BIt := Brd.BoardIterator_Create;
    BIt.AddFilter_ObjectSet(MkSet(ePadObject));
    BIt.AddFilter_LayerSet(AllLayers);
    BIt.AddFilter_Method(eProcessAll);
    P := BIt.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (Abs(CoordToMMs(P.X) - 6.2) < 0.01) And (Abs(CoordToMMs(P.Y) - 3.9) < 0.01) Then
        Begin
            K := K + 1;
            nm := '(no net)';
            If P.Net <> Nil Then nm := P.Net.Name;
            S := S + 'board iterator: pad ' + P.Name + ' at R78-1''s centre (6.2, 3.9)  net ' + nm + #13#10;
        End;
        P := BIt.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(BIt);
    { how many net objects are called GND, and is R78-1's net object one of them? }
    Hit := Nil;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = '1' Then Hit := P;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    NG := 0; NAll := 0; Same := 0;
    NIt := Brd.BoardIterator_Create;
    NIt.AddFilter_ObjectSet(MkSet(eNetObject));
    NIt.AddFilter_LayerSet(AllLayers);
    NIt.AddFilter_Method(eProcessAll);
    N := NIt.FirstPCBObject;
    While N <> Nil Do
    Begin
        NAll := NAll + 1;
        If N.Name = 'GND' Then
        Begin
            NG := NG + 1;
            If Hit <> Nil Then
                If Hit.Net = N Then Same := Same + 1;
        End;
        N := NIt.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(NIt);
    S := S + #13#10 + 'net objects on the board: ' + IntToStr(NAll) + ', named GND: ' + IntToStr(NG) +
         ', of them the one R78-1 points at: ' + IntToStr(Same);
    ShowMessage('Zulu A7 - R78 net probe' + #13#10 + #13#10 + S + #13#10 + 'pads at R78-1''s centre seen by the board iterator: ' + IntToStr(K) + #13#10 + 'Nothing was changed.');
End;


{ ---------------------------------------------------------------------------
  JoinR78ToGndNet: if R78-1's Net already reads GND but the file still writes
  -1, the pad may be missing from the net's own member list.  Adds it with
  IPCB_Net.AddPCBObject inside Try/Except (a rejected call is reported; an
  undeclared name would halt -- no transaction is open, so nothing strands).
  --------------------------------------------------------------------------- }

Procedure JoinR78ToGndNet;
Var
    C   : IPCB_Component;
    It  : IPCB_GroupIterator;
    NIt : IPCB_BoardIterator;
    P, Hit : IPCB_Pad;
    N, G : IPCB_Net;
    S   : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    G := Nil;
    NIt := Brd.BoardIterator_Create;
    NIt.AddFilter_ObjectSet(MkSet(eNetObject));
    NIt.AddFilter_LayerSet(AllLayers);
    NIt.AddFilter_Method(eProcessAll);
    N := NIt.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = 'GND' Then G := N;
        N := NIt.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(NIt);
    C := Brd.GetPcbComponentByRefDes('R78');
    If (C = Nil) Or (G = Nil) Then Exit;
    Hit := Nil;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = '1' Then Hit := P;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Hit = Nil Then Exit;
    S := '';
    Try
        Hit.BeginModify;
        Hit.Net := G;
        G.AddPCBObject(Hit);
        Hit.EndModify;
        S := 'AddPCBObject accepted.';
    Except
        S := 'AddPCBObject raised.';
    End;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Zulu A7 - R78-1 join to GND: ' + S + #13#10 + 'Now save and re-read Pads6.');
End;


End.

{ End of ZuluProbe.pas }
