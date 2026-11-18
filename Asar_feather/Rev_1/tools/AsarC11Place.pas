{ AsarC11Place.pas -- 2026-11-17, C11 back beside U4 pin 8 (docs/c11_move.md, tools/route/c11move).
  The schematic draws C11 (0.1 uF 0402) as the SPI boot flash U4's VCC bypass; the board had it on the bottom under U3.
  Flips C11 to the TOP, horizontal, VCC3V3 pad 2 at (48.30, 17.505) (0.30 mm east of U4-8) and GND pad 1 at
  (49.60, 17.505); hides its designator and comment. Refuses unless C11 is on the bottom with pad 1 at (32.93, 7.23)
  and pad 2 at (34.23, 7.23). Every pad is checked within 0.005 mm and must end on the top layer.
  Copper is not touched: FeatherCopper_C11Move.pas (tools/route/c11move/plan.json) follows. }

Var
    Brd : IPCB_Board;
    Report : String;
    NBad : Integer;

Function PadAt(D, PN : String; Var X, Y : Double; Var OnTop : Boolean) : Boolean;
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
            OnTop := (P.Layer = eTopLayer);
            Result := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Procedure Check(D, PN : String; PX, PY : Double);
Var
    x, y : Double;
    t : Boolean;
Begin
    If Not PadAt(D, PN, x, y, t) Then
    Begin
        NBad := NBad + 1;
        Report := Report + D + '-' + PN + ' missing; ';
        Exit;
    End;
    If (Abs(x - PX) > 0.005) Or (Abs(y - PY) > 0.005) Or (Not t) Then
    Begin
        NBad := NBad + 1;
        Report := Report + D + '-' + PN + ' at ' + FormatFloat('0.000', x) + ',' + FormatFloat('0.000', y);
        If Not t Then Report := Report + ' NOT on top';
        Report := Report + '; ';
    End;
End;

Procedure AsarC11Place;
Var
    C : IPCB_Component;
    x1, y1, x2, y2 : Double;
    t : Boolean;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then
    Begin ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.'); Exit; End;
    C := Brd.GetPcbComponentByRefDes('C11');
    If C = Nil Then Begin ShowMessage('Refusing: C11 is not on the board.'); Exit; End;
    If (Not PadAt('C11', '1', x1, y1, t)) Or (Not PadAt('C11', '2', x2, y2, t)) Then
    Begin ShowMessage('Refusing: C11 pads 1/2 not found.'); Exit; End;
    If (C.Layer <> eBottomLayer) Or (Abs(x1 - 32.93) > 0.005) Or (Abs(y1 - 7.23) > 0.005) Or
       (Abs(x2 - 34.23) > 0.005) Or (Abs(y2 - 7.23) > 0.005) Then
    Begin
        ShowMessage('Refusing: C11 is not where the plan expects it (pad 1 ' + FormatFloat('0.000', x1) + ',' +
            FormatFloat('0.000', y1) + ', pad 2 ' + FormatFloat('0.000', x2) + ',' + FormatFloat('0.000', y2) + '); nothing changed.');
        Exit;
    End;
    Report := ''; NBad := 0;
    PCBServer.PreProcess;
    C.BeginModify;
    C.Layer := eTopLayer;
    C.Rotation := 0;
    C.EndModify;
    PadAt('C11', '1', x1, y1, t);
    PadAt('C11', '2', x2, y2, t);
    If x2 > x1 Then
    Begin
        { pad 2 (VCC3V3) must face U4 pin 8 to the west }
        C.BeginModify;
        C.Rotation := 180;
        C.EndModify;
    End;
    PadAt('C11', '2', x2, y2, t);
    C.BeginModify;
    C.X := C.X + MMsToCoord(48.30 - x2);
    C.Y := C.Y + MMsToCoord(17.505 - y2);
    C.NameOn := False;
    C.CommentOn := False;
    C.EndModify;
    PCBServer.PostProcess;
    Check('C11', '2', 48.30, 17.505);
    Check('C11', '1', 49.60, 17.505);
    Brd.ViewManager_FullUpdate;
    ShowMessage('C11 placed on top beside U4-8. Pads off plan: ' + IntToStr(NBad) + ' ' + Report +
        'Undo if anything is off; else run PlaceC11Move.');
End;
