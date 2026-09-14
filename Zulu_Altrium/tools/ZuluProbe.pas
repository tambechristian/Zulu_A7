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


End.

{ End of ZuluProbe.pas }
