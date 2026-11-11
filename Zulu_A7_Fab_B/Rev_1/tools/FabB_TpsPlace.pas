{ FabB_TpsPlace.pas -- 2026-11-09. Places the TPS63802 block on Fab B's Bottom side (plan: scratchpad placement/fab_b/
  proposal3.json, checked independently): U5 rot 90 with pin 10 at (7.488, 16.600); C147 rot 90 with pad 2 at (9.100, 16.900);
  R110 rot 0 with pad 1 at (4.900, 13.500); R109 rot 180 with pad 1 at (6.200, 12.380). Each part is moved so the named pad
  lands on its target (pad-anchored, as in ZuluPlacement.pas), then EVERY listed pad is checked against the plan within
  0.005 mm and the result is shown. Refuses unless U5 and C147 are where the ECO left them. Run TpsPlace, check, save. }

Var
    Brd : IPCB_Board;
    Missing, Report : String;
    NDone, NBad : Integer;

Procedure Place(D : String; Rot : Double; PN : String; PX, PY : Double);
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    FX, FY : TCoord;
    Got : Boolean;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then
    Begin
        Missing := Missing + D + ' ';
        Exit;
    End;
    C.BeginModify;
    If C.Layer <> eBottomLayer Then C.Layer := eBottomLayer;
    C.Rotation := Rot;
    C.EndModify;
    Got := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While (P <> Nil) And (Not Got) Do
    Begin
        If P.Name = PN Then
        Begin
            FX := P.X; FY := P.Y;
            Got := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Not Got Then
    Begin
        Missing := Missing + D + '.' + PN + ' ';
        Exit;
    End;
    C.BeginModify;
    C.X := C.X + (Brd.XOrigin + MMsToCoord(PX) - FX);
    C.Y := C.Y + (Brd.YOrigin + MMsToCoord(PY) - FY);
    C.EndModify;
    NDone := NDone + 1;
End;

Procedure Check(D, PN : String; PX, PY : Double);
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    Got : Boolean;
    x, y : Double;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then Exit;
    Got := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = PN Then
        Begin
            Got := True;
            x := CoordToMMs(P.X - Brd.XOrigin);
            y := CoordToMMs(P.Y - Brd.YOrigin);
            If (Abs(x - PX) > 0.005) Or (Abs(y - PY) > 0.005) Then
            Begin
                NBad := NBad + 1;
                Report := Report + D + '-' + PN + ' at ' + FormatFloat('0.000', x) + ',' + FormatFloat('0.000', y) + '; ';
            End;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Not Got Then Report := Report + D + '-' + PN + ' missing; ';
End;

Function At(D : String; X, Y : Double) : Boolean;
Var
    C : IPCB_Component;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    Result := (C <> Nil) And (Abs(CoordToMMs(C.X - Brd.XOrigin) - X) < 0.005) And (Abs(CoordToMMs(C.Y - Brd.YOrigin) - Y) < 0.005);
End;

Procedure TpsPlace;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_Fab_B\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_Fab_B\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Not (At('U5', 6.408, 15.502) And At('C147', 7.198, 12.651)) Then
    Begin
        ShowMessage('Refusing: U5 or C147 is not where the ECO left it (6.408,15.502 / 7.198,12.651); nothing changed.');
        Exit;
    End;
    Missing := ''; Report := ''; NDone := 0; NBad := 0;
    PCBServer.PreProcess;
    Place('U5', 90, '10', 7.488, 16.600);
    Place('C147', 90, '2', 9.100, 16.900);
    Place('R110', 0, '1', 4.900, 13.500);
    Place('R109', 180, '1', 6.200, 12.380);
    PCBServer.PostProcess;
    Check('U5', '1', 7.488, 14.950); Check('U5', '2', 6.988, 14.950); Check('U5', '3', 6.488, 14.950);
    Check('U5', '4', 5.988, 14.950); Check('U5', '5', 5.488, 14.950); Check('U5', '6', 5.488, 16.600);
    Check('U5', '7', 5.988, 16.600); Check('U5', '8', 6.488, 16.400); Check('U5', '9', 6.988, 16.600);
    Check('U5', '10', 7.488, 16.600);
    Check('C147', '1', 9.100, 15.200); Check('C147', '2', 9.100, 16.900);
    Check('R110', '1', 4.900, 13.500); Check('R110', '2', 6.200, 13.500);
    Check('R109', '1', 6.200, 12.380); Check('R109', '2', 4.900, 12.380);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Placed ' + IntToStr(NDone) + ' of 4. Missing: ' + Missing + ' Pads off plan: ' + IntToStr(NBad) + ' ' + Report +
        'Undo (Ctrl+Z) if anything is off; else run the copper script.');
End;
