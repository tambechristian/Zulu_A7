{ AsarX1Clean.pas -- 2026-11-17, X1 micro-B conversion clean-up after FeatherCopper_X1MicroB (docs/x1_microb.md).
  The first DRC after the copper plan found what the router model could not see:
  - 26 tracks + 2 vias with NO net in the box x 5..8, y 2.5..13: the old USB-C CC1/CC2 routes (their nets went with
    R27/R28 in the ECO, so the copper became net-less and route_model.py, which skips net-less copper, never saw it);
  - three net antennae left by the old X1 / Q1 positions: GND laser (13.675, 12.65) and the VCC3V3 Top>L5 column at
    (13.675, 14.85) (old Q1-2 / Q1-1 ties), GND laser (7.125, 14.45) (old USB-C shell tie);
  - Silk To Solder Mask: U2's designator now sits on the moved Q1-3.
  This removes the dead copper and the antenna vias (refusing unless every count matches and no L3/L4 track touches the
  VCC3V3 column) and moves U2's designator (manual autoposition) so its box starts at (12.70, 12.60), between X4-1 and
  Q1-2 above U2's north pin row. Then repour, save, DRC. }

Var
    Brd : IPCB_Board;

Function MM(V : TCoord) : Double;
Begin
    Result := V / 10000 * 0.0254;
End;

Function At(O : IPCB_Via; X, Y : Double) : Boolean;
Begin
    Result := (Abs(CoordToMMs(O.X - Brd.XOrigin) - X) < 0.003) And (Abs(CoordToMMs(O.Y - Brd.YOrigin) - Y) < 0.003);
End;

Procedure AsarX1Clean;
Var
    It : IPCB_BoardIterator;
    O : IPCB_Primitive;
    V : IPCB_Via;
    T : IPCB_Track;
    KT, KV, KA : TInterfaceList;
    C : IPCB_Component;
    TX : IPCB_Text;
    B : TCoordRect;
    i, nCol, nTouch : Integer;
    x1, y1, x2, y2, dx, dy : Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then
    Begin ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.'); Exit; End;
    KT := TInterfaceList.Create; KV := TInterfaceList.Create; KA := TInterfaceList.Create;
    nCol := 0; nTouch := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If O.ObjectId = eTrackObject Then
        Begin
            T := O;
            x1 := CoordToMMs(T.X1 - Brd.XOrigin); y1 := CoordToMMs(T.Y1 - Brd.YOrigin);
            x2 := CoordToMMs(T.X2 - Brd.XOrigin); y2 := CoordToMMs(T.Y2 - Brd.YOrigin);
            If (T.Net = Nil) And (Not T.InComponent) And (Not T.InPolygon) And (Not T.IsKeepout) And
               (x1 > 5.0) And (x1 < 8.0) And (x2 > 5.0) And (x2 < 8.0) And (y1 > 2.5) And (y1 < 13.0) And (y2 > 2.5) And (y2 < 13.0) Then
                KT.Add(T);
            If ((T.Layer = eMidLayer1) Or (T.Layer = eMidLayer2)) And (T.Net <> Nil) Then
                If T.Net.Name = 'VCC3V3' Then
                    If ((Abs(x1 - 13.675) < 0.2) And (Abs(y1 - 14.85) < 0.2)) Or ((Abs(x2 - 13.675) < 0.2) And (Abs(y2 - 14.85) < 0.2)) Then
                        nTouch := nTouch + 1;
        End
        Else
        Begin
            V := O;
            If V.Net = Nil Then
            Begin
                If (CoordToMMs(V.X - Brd.XOrigin) > 5.0) And (CoordToMMs(V.X - Brd.XOrigin) < 8.0) And
                   (CoordToMMs(V.Y - Brd.YOrigin) > 2.5) And (CoordToMMs(V.Y - Brd.YOrigin) < 13.0) Then KV.Add(V);
            End
            Else
            Begin
                If (V.Net.Name = 'GND') And (At(V, 13.675, 12.65) Or At(V, 7.125, 14.45)) Then KA.Add(V);
                If (V.Net.Name = 'VCC3V3') And At(V, 13.675, 14.85) Then Begin KA.Add(V); nCol := nCol + 1; End;
            End;
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (KT.Count <> 26) Or (KV.Count <> 2) Or (KA.Count <> 6) Or (nCol <> 4) Or (nTouch <> 0) Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(KT.Count) + ' net-less tracks (26), ' + IntToStr(KV.Count) + ' net-less vias (2), ' +
            IntToStr(KA.Count) + ' antenna vias (6, of them ' + IntToStr(nCol) + ' in the VCC3V3 column, 4), ' + IntToStr(nTouch) +
            ' L3/L4 tracks on the column (0); nothing changed.');
        KT.Free; KV.Free; KA.Free; Exit;
    End;
    C := Brd.GetPcbComponentByRefDes('U2');
    If C = Nil Then Begin ShowMessage('Refusing: U2 not found.'); KT.Free; KV.Free; KA.Free; Exit; End;
    TX := C.Name;
    B := TX.BoundingRectangle;
    If (CoordToMMs(B.Left - Brd.XOrigin) < 16.5) Or (CoordToMMs(B.Left - Brd.XOrigin) > 17.5) Then
    Begin
        ShowMessage('Refusing: U2 designator box starts at x ' + FormatFloat('0.000', CoordToMMs(B.Left - Brd.XOrigin)) + ', not near 17.07; nothing changed.');
        KT.Free; KV.Free; KA.Free; Exit;
    End;
    PCBServer.PreProcess;
    For i := 0 To KT.Count - 1 Do Brd.RemovePCBObject(KT.Items[i]);
    For i := 0 To KV.Count - 1 Do Brd.RemovePCBObject(KV.Items[i]);
    For i := 0 To KA.Count - 1 Do Brd.RemovePCBObject(KA.Items[i]);
    dx := 12.70 - CoordToMMs(B.Left - Brd.XOrigin);
    dy := 12.60 - CoordToMMs(B.Bottom - Brd.YOrigin);
    C.BeginModify;
    C.ChangeNameAutoposition := eAutoPos_Manual;
    C.EndModify;
    TX.BeginModify;
    TX.XLocation := TX.XLocation + MMsToCoord(dx);
    TX.YLocation := TX.YLocation + MMsToCoord(dy);
    TX.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    B := TX.BoundingRectangle;
    ShowMessage('Removed 26 net-less tracks, 2 net-less vias, 6 antenna vias. U2 designator box now ' +
        FormatFloat('0.000', CoordToMMs(B.Left - Brd.XOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(B.Right - Brd.XOrigin)) + ' x ' +
        FormatFloat('0.000', CoordToMMs(B.Bottom - Brd.YOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(B.Top - Brd.YOrigin)) +
        '. Repour, save, DRC.');
    KT.Free; KV.Free; KA.Free;
End;
