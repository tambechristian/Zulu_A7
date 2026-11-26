{ NoPmodPlaceRxTxLed.pas -- 2026-11-25, no-PMOD Rev 4 UART activity LED (tools/rxtx_led_sch.py,
  tools/route/rxtx_led/sites.py site 1, docs/rxtx_led.md).
  PlaceRxTxLed puts the two parts the ECO dropped off the board:
    LD6  (LED0603, yellow) Top, rotation 0 like LD1-LD5 (cathode east), between U2's north edge and X1:
                           pad A at (34.700, 20.000), pad K at (36.300, 20.000).
    R136 (R0201, 1K)       Top, rotation 0, west of the anode: pad 1 (VCC3V3) at (33.050, 20.000),
                           pad 2 (anode net) at (33.650, 20.000).
  Each part: layer and rotation set, then moved so its reference pad lands exactly on target; designators hidden
  (as every chip LED/passive here). Refuses unless both parts exist on the Rev_4 board. Save after. }
Function FBrd : IPCB_Board;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If (Result = Nil) Or (Pos('\Rev_4\', Result.FileName) = 0) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Result.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_4 Zulu_a7_no_pmod.PcbDoc first.');
        Result := Nil;
    End;
End;

Function PadOf(Cm : IPCB_Component; AName : String) : IPCB_Pad;
Var
    It : IPCB_GroupIterator;
    Pd : IPCB_Pad;
Begin
    Result := Nil;
    It := Cm.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    Pd := It.FirstPCBObject;
    While Pd <> Nil Do
    Begin
        If Pd.Name = AName Then Result := Pd;
        Pd := It.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(It);
End;

Function Place(Brd : IPCB_Board; Ref, PadName : String; Rot, X, Y : Double) : String;
Var
    Cm : IPCB_Component;
    Pd : IPCB_Pad;
    It : IPCB_GroupIterator;
    dx, dy : Integer;
Begin
    Result := '';
    Cm := Brd.GetPcbComponentByRefDes(Ref);
    If Cm = Nil Then Begin Result := 'MISSING ' + Ref; Exit; End;
    PCBServer.PreProcess;
    Cm.BeginModify;
    If Cm.Layer <> eTopLayer Then Cm.Layer := eTopLayer;
    Cm.Rotation := Rot;
    Cm.EndModify;
    Pd := PadOf(Cm, PadName);
    If Pd = Nil Then Begin PCBServer.PostProcess; Result := 'NO PAD ' + Ref + '-' + PadName; Exit; End;
    dx := Brd.XOrigin + MMsToCoord(X) - Pd.X;
    dy := Brd.YOrigin + MMsToCoord(Y) - Pd.Y;
    Cm.BeginModify;
    Cm.MoveByXY(dx, dy);
    Cm.NameOn := False;
    Cm.EndModify;
    PCBServer.PostProcess;
    Result := Ref + ' rot ' + FormatFloat('0', Cm.Rotation) + ':';
    It := Cm.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    Pd := It.FirstPCBObject;
    While Pd <> Nil Do
    Begin
        Result := Result + ' ' + Pd.Name + '(' + Pd.Net.Name + ') ' + FormatFloat('0.000', CoordToMMs(Pd.X - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Pd.Y - Brd.YOrigin)) + ';';
        Pd := It.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(It);
End;

Procedure PlaceRxTxLed;
Var
    Brd : IPCB_Board;
    S : String;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    If (Brd.GetPcbComponentByRefDes('LD6') = Nil) Or (Brd.GetPcbComponentByRefDes('R136') = Nil) Then
    Begin
        ShowMessage('Refusing: LD6 / R136 not on the board (run Design > Update PCB first).');
        Exit;
    End;
    S := Place(Brd, 'LD6', 'A', 0, 34.7, 20.0) + #13#10 + Place(Brd, 'R136', '1', 0, 33.05, 20.0);
    Brd.ViewManager_FullUpdate;
    ShowMessage(S + #13#10 + '(expected LD6 A 34.700,20.000 K 36.300,20.000; R136 1 33.050,20.000 2 33.650,20.000)');
End;
