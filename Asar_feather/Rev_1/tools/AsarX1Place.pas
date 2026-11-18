{ AsarX1Place.pas -- 2026-11-17, X1 USB-C -> micro-B (docs/x1_microb.md).
  After the ECO has added X1 with AMPHENOL-10118193-0001LF (footprint origin = pin 3): puts X1 on the west edge, mouth
  facing -x, pin 3 (D+) at (4.125, 11.43) so the maker's PCB-edge line sits on the board edge x = 0 and the 5 contacts'
  inner ends are at x 4.80; hides X1's designator and comment (the board's free "X1" text stays). Moves Q1 (12 MHz
  oscillator) 1.46 mm east, pad 1 (14.15, 15.4) -> (15.61, 15.4), to clear X4's east rear leg by 0.26 mm.
  Every pad is checked within 0.005 mm. Refuses unless X1 carries the micro-B footprint and Q1 pad 1 is at (14.15, 15.4).
  Copper is not touched: the copper plan (tools/route/x1microb) follows. }

Var
    Brd : IPCB_Board;
    Report : String;
    NBad : Integer;

Function PadAt(D, PN : String; Var X, Y : Double) : Boolean;
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
Begin
    Result := False;
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then Exit;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = PN Then
        Begin
            X := CoordToMMs(P.X - Brd.XOrigin);
            Y := CoordToMMs(P.Y - Brd.YOrigin);
            Result := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Procedure Check(D, PN : String; PX, PY : Double);
Var
    x, y : Double;
Begin
    If Not PadAt(D, PN, x, y) Then
    Begin
        NBad := NBad + 1;
        Report := Report + D + '-' + PN + ' missing; ';
        Exit;
    End;
    If (Abs(x - PX) > 0.005) Or (Abs(y - PY) > 0.005) Then
    Begin
        NBad := NBad + 1;
        Report := Report + D + '-' + PN + ' at ' + FormatFloat('0.000', x) + ',' + FormatFloat('0.000', y) + '; ';
    End;
End;

Procedure AsarX1Place;
Var
    C : IPCB_Component;
    x, y : Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then
    Begin ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.'); Exit; End;
    C := Brd.GetPcbComponentByRefDes('X1');
    If C = Nil Then Begin ShowMessage('Refusing: X1 is not on the board (run the ECO first).'); Exit; End;
    If C.Pattern <> 'AMPHENOL-10118193-0001LF' Then
    Begin ShowMessage('Refusing: X1 footprint is ' + C.Pattern + '.'); Exit; End;
    If Not PadAt('Q1', '1', x, y) Then Begin ShowMessage('Refusing: Q1 pad 1 not found.'); Exit; End;
    If (Abs(x - 14.15) > 0.005) Or (Abs(y - 15.4) > 0.005) Then
    Begin ShowMessage('Refusing: Q1 pad 1 is at ' + FormatFloat('0.000', x) + ',' + FormatFloat('0.000', y) + ', not (14.15, 15.4); nothing changed.'); Exit; End;
    Report := ''; NBad := 0;
    PCBServer.PreProcess;
    C.BeginModify;
    If C.Layer <> eTopLayer Then C.Layer := eTopLayer;
    C.Rotation := 0;
    C.EndModify;
    PadAt('X1', '3', x, y);
    C.BeginModify;
    C.X := C.X + MMsToCoord(4.125 - x);
    C.Y := C.Y + MMsToCoord(11.43 - y);
    C.NameOn := False;
    C.CommentOn := False;
    C.EndModify;
    C := Brd.GetPcbComponentByRefDes('Q1');
    C.BeginModify;
    C.X := C.X + MMsToCoord(1.46);
    C.EndModify;
    PCBServer.PostProcess;
    Check('X1', '1', 4.125, 12.73);
    Check('X1', '2', 4.125, 12.08);
    Check('X1', '3', 4.125, 11.43);
    Check('X1', '4', 4.125, 10.78);
    Check('X1', '5', 4.125, 10.13);
    Check('X1', 'MP1', 3.90, 14.63);
    Check('X1', 'MP2', 3.90, 8.23);
    Check('X1', 'MP3', 1.45, 12.63);
    Check('X1', 'MP4', 1.45, 10.23);
    Check('X1', 'MH1', 1.45, 14.73);
    Check('X1', 'MH2', 1.45, 8.13);
    Check('Q1', '1', 15.61, 15.4);
    Brd.ViewManager_FullUpdate;
    ShowMessage('X1 and Q1 placed. Pads off plan: ' + IntToStr(NBad) + ' ' + Report + 'Undo if anything is off; else save and dump.');
End;
