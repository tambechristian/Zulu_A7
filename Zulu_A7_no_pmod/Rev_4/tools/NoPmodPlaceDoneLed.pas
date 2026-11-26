{ NoPmodPlaceDoneLed.pas -- 2026-11-25, no-PMOD Rev 4 DONE LED (tools/done_led_sch.py, docs/done_led.md).
  PlaceDoneLed puts the two parts the ECO dropped off the board:
    LD5  (LED0603, green)  Top, rotation 0 like LD1-LD4, in the LED column's free slot between LD2 (y 12.585) and
                           LD3 (y 15.785): pad A at (21.400, 14.185), pad K at (23.000, 14.185) -- cathode east as
                           every other LED on the board.
    R135 (R0201, 140R)     Top, rotation 90, in the gap between BTN and the LED anodes: pad 1 (FPGA-DONE) at
                           (20.450, 13.885), pad 2 (NetLD5_A) at (20.450, 14.485).
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

Procedure PlaceDoneLed;
Var
    Brd : IPCB_Board;
    S : String;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    If (Brd.GetPcbComponentByRefDes('LD5') = Nil) Or (Brd.GetPcbComponentByRefDes('R135') = Nil) Then
    Begin
        ShowMessage('Refusing: LD5 / R135 not on the board (run Design > Update PCB first).');
        Exit;
    End;
    S := Place(Brd, 'LD5', 'A', 0, 21.4, 14.185) + #13#10 + Place(Brd, 'R135', '1', 90, 20.45, 13.885);
    Brd.ViewManager_FullUpdate;
    ShowMessage(S + #13#10 + '(expected LD5 A 21.400,14.185 K 23.000,14.185; R135 1 20.450,13.885 2 20.450,14.485)');
End;
