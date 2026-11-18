{ AsarX4Place.pas -- 2026-11-16, X4 side-entry conversion (docs/x4_jst_entry.md).
  AsarX4Place: after the ECO has swapped X4 to JST-S2B-PH-SM4-TB, puts X4 at the Adafruit Feather position (housing
  centre 10.8, 19.3, rot 0, mouth +y, face 0.56 mm inside the top edge) and moves U10 (93LC46B TDFN) to the pocket west
  of X4's west tab (centre 5.45, 19.0, rot 0, pins 1-4 facing south). Each part is pad-anchored, then every pad is
  checked within 0.005 mm. Refuses unless X4 already carries the 1.0 x 3.5 mm side-entry contact pads and U10 is still
  at (11.0, 13.75). Then run FeatherCopper_X4Conv, then AsarX4Rebuild (ratsnest), repour, save, mark microvias, DRC. }

Var
    Brd : IPCB_Board;
    Missing, Report : String;
    NDone, NBad : Integer;

Procedure PlaceTop(D : String; Rot : Double; PN : String; PX, PY : Double);
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
    If C.Layer <> eTopLayer Then C.Layer := eTopLayer;
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

Function SideEntryPads : Boolean;
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    a, b : Double;
Begin
    Result := False;
    C := Brd.GetPcbComponentByRefDes('X4');
    If C = Nil Then Exit;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = '1' Then
        Begin
            a := CoordToMMs(P.TopXSize); b := CoordToMMs(P.TopYSize);
            If (Abs(a - 1.0) < 0.01) And (Abs(b - 3.5) < 0.01) Then Result := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Procedure InvalidateAll(Brd : IPCB_Board);
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        N.ConnectivelyInValidate;
        N := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Brd.ConnectivelyValidateNets;
End;

Procedure AsarX4Place;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then
    Begin ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.'); Exit; End;
    If Not SideEntryPads Then
    Begin ShowMessage('Refusing: X4 does not have the 1.0 x 3.5 mm side-entry pads yet (run the ECO first); nothing changed.'); Exit; End;
    If Not At('U10', 11.0, 13.75) Then
    Begin ShowMessage('Refusing: U10 is not at (11.0, 13.75); nothing changed.'); Exit; End;
    Missing := ''; Report := ''; NDone := 0; NBad := 0;
    PCBServer.PreProcess;
    PlaceTop('X4', 0, '1', 11.8000, 15.0500);
    PlaceTop('U10', 0, '1', 4.7000, 17.5500);
    PCBServer.PostProcess;
    Check('X4', '1', 11.8000, 15.0500);
    Check('X4', '2', 9.8000, 15.0500);
    Check('X4', 'MP1', 7.4500, 20.8000);
    Check('X4', 'MP2', 14.1500, 20.8000);
    Check('U10', '1', 4.7000, 17.5500);
    Check('U10', '2', 5.2000, 17.5500);
    Check('U10', '3', 5.7000, 17.5500);
    Check('U10', '4', 6.2000, 17.5500);
    Check('U10', '5', 6.2000, 20.4500);
    Check('U10', '6', 5.7000, 20.4500);
    Check('U10', '7', 5.2000, 20.4500);
    Check('U10', '8', 4.7000, 20.4500);
    Check('U10', 'EP', 5.4500, 19.0000);
    If Not At('X4', 10.8, 19.3) Then Report := Report + 'X4 origin not at 10.8,19.3; ';
    If Not At('U10', 5.45, 19.0) Then Report := Report + 'U10 origin not at 5.45,19.0; ';
    Brd.ViewManager_FullUpdate;
    ShowMessage('Placed ' + IntToStr(NDone) + ' of 2. Missing: ' + Missing + ' Pads off plan: ' + IntToStr(NBad) + ' ' + Report + 'Undo if anything is off; else run FeatherCopper_X4Conv.');
End;

Procedure AsarX4Rebuild;
Var
    It : IPCB_BoardIterator;
    C : IPCB_Connection;
    Kill : TInterfaceList;
    i, n : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    InvalidateAll(Brd);
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do Begin Kill.Add(C); C := It.NextPCBObject; End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do Brd.RemovePCBObject(Kill.Items[i]);
    PCBServer.PostProcess;
    InvalidateAll(Brd);
    n := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do Begin n := n + 1; C := It.NextPCBObject; End;
    Brd.BoardIterator_Destroy(It);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Ratsnest: removed ' + IntToStr(Kill.Count) + ', ' + IntToStr(n) + ' remain after re-analysis.');
    Kill.Free;
End;
