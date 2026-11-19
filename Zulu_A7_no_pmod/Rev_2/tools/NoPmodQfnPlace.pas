{ Place the no-notch FT2232HQ + S2B-PH-SM4-TB pair after their footprint
  ECOs have been applied. This script changes only component placement. }

Function QfnPlaceGuard : IPCB_Board;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or
       (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc',
            Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
End;

Function QfnPlacePadCount(C : IPCB_Component) : Integer;
Var
    It : IPCB_GroupIterator;
    P : IPCB_Pad;
Begin
    Result := 0;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        Result := Result + 1;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Function QfnPlacePad(C : IPCB_Component; Name : String) : IPCB_Pad;
Var
    It : IPCB_GroupIterator;
    P : IPCB_Pad;
Begin
    Result := Nil;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = Name Then Result := P;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Function QfnPlaceAt(Board : IPCB_Board; P : IPCB_Pad; X, Y : Double) : Boolean;
Begin
    Result := (P <> Nil) And
              (Abs(P.X - Board.XOrigin - MMsToCoord(X)) < 300) And
              (Abs(P.Y - Board.YOrigin - MMsToCoord(Y)) < 300);
End;

Function QfnPlaceNormalizeX4(X4 : IPCB_Component) : Boolean;
Var
    P1, MP1 : IPCB_Pad;
    It : IPCB_GroupIterator;
    Obj : IPCB_Primitive;
    P : IPCB_Pad;
    T : IPCB_Track;
    AxisY, SignalLocalY, MountLocalY : TCoord;
    OldRotation : Double;
    Pads, Tracks : Integer;
Begin
    Result := False;
    OldRotation := X4.Rotation;
    X4.BeginModify;
    X4.Rotation := 0.0;
    X4.EndModify;
    P1 := QfnPlacePad(X4, '1');
    MP1 := QfnPlacePad(X4, 'MP1');
    If (P1 = Nil) Or (MP1 = Nil) Then
    Begin
        X4.BeginModify;
        X4.Rotation := OldRotation;
        X4.EndModify;
        Exit;
    End;
    AxisY := (P1.Y + MP1.Y - MMsToCoord(0.05)) Div 2;
    SignalLocalY := P1.Y - AxisY;
    MountLocalY := MP1.Y - AxisY;
    If (Abs(SignalLocalY - MMsToCoord(2.85)) < 300) And
       (Abs(MountLocalY + MMsToCoord(2.90)) < 300) Then
    Begin
        Result := True;
        Exit;
    End;
    If Not ((Abs(SignalLocalY + MMsToCoord(2.85)) < 300) And
            (Abs(MountLocalY - MMsToCoord(2.90)) < 300)) Then
    Begin
        X4.BeginModify;
        X4.Rotation := OldRotation;
        X4.EndModify;
        Exit;
    End;

    Pads := 0;
    Tracks := 0;
    It := X4.GroupIterator_Create;
    It.SetState_FilterAll;
    Obj := It.FirstPCBObject;
    While Obj <> Nil Do
    Begin
        If Obj.ObjectId = ePadObject Then Pads := Pads + 1;
        If Obj.ObjectId = eTrackObject Then Tracks := Tracks + 1;
        Obj := It.NextPCBObject;
    End;
    X4.GroupIterator_Destroy(It);
    If (Pads <> 4) Or (Tracks <> 10) Then
    Begin
        X4.BeginModify;
        X4.Rotation := OldRotation;
        X4.EndModify;
        Exit;
    End;

    It := X4.GroupIterator_Create;
    It.SetState_FilterAll;
    Obj := It.FirstPCBObject;
    While Obj <> Nil Do
    Begin
        If Obj.ObjectId = ePadObject Then
        Begin
            P := Obj;
            P.BeginModify;
            P.Y := 2 * AxisY - P.Y;
            P.EndModify;
        End
        Else If Obj.ObjectId = eTrackObject Then
        Begin
            T := Obj;
            T.BeginModify;
            T.Y1 := 2 * AxisY - T.Y1;
            T.Y2 := 2 * AxisY - T.Y2;
            T.EndModify;
        End;
        Obj := It.NextPCBObject;
    End;
    X4.GroupIterator_Destroy(It);
    Result := True;
End;

Procedure PlaceQfnAndX4;
Var
    Board : IPCB_Board;
    U2, U10, X4 : IPCB_Component;
    Good, MoveU10 : Boolean;
Begin
    Board := QfnPlaceGuard;
    If Board = Nil Then Exit;
    U2 := Board.GetPcbComponentByRefDes('U2');
    U10 := Board.GetPcbComponentByRefDes('U10');
    X4 := Board.GetPcbComponentByRefDes('X4');
    If (U2 = Nil) Or (U2.Layer <> eTopLayer) Or
       (U2.Pattern <> 'FT2232HQ-QFN64') Or (QfnPlacePadCount(U2) <> 65) Then
    Begin
        ShowMessage('Refusing: U2 must already be Top-side FT2232HQ-QFN64 with 65 pads.');
        Exit;
    End;
    If (U10 = Nil) Or (U10.Layer <> eBottomLayer) Or
       (U10.Pattern <> 'MSOP-8_3X3_P0.65') Or (QfnPlacePadCount(U10) <> 8) Then
    Begin
        ShowMessage('Refusing: U10 must be Bottom-side MSOP-8_3X3_P0.65 with 8 pads.');
        Exit;
    End;
    If (X4 = Nil) Or (X4.Layer <> eTopLayer) Or
       (X4.Pattern <> 'JST-S2B-PH-SM4-TB') Or (QfnPlacePadCount(X4) <> 4) Then
    Begin
        ShowMessage('Refusing: X4 must already be Top-side JST-S2B-PH-SM4-TB with 4 pads.');
        Exit;
    End;
    MoveU10 := QfnPlaceAt(Board, QfnPlacePad(U10, '1'), 18.8726, 17.6700);
    If (Not MoveU10) And
       (Not QfnPlaceAt(Board, QfnPlacePad(U10, '1'), 21.3726, 19.2700)) Then
    Begin
        ShowMessage('Refusing: U10 is at neither the recovered nor validated location.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        If Not QfnPlaceNormalizeX4(X4) Then
        Begin
            ShowMessage('Refusing: X4 board geometry is neither the known mirrored nor corrected footprint.');
            Exit;
        End;
        U2.BeginModify;
        U2.X := Board.XOrigin + MMsToCoord(30.50);
        U2.Y := Board.YOrigin + MMsToCoord(14.55);
        U2.Rotation := 0.0;
        U2.EndModify;

        X4.BeginModify;
        X4.X := Board.XOrigin + MMsToCoord(31.39);
        X4.Y := Board.YOrigin + MMsToCoord(4.90);
        X4.Rotation := 0.0;
        X4.EndModify;

        If MoveU10 Then
        Begin
            U10.BeginModify;
            U10.X := U10.X + MMsToCoord(2.50);
            U10.Y := U10.Y + MMsToCoord(1.60);
            U10.EndModify;
        End;
    Finally
        PCBServer.PostProcess;
    End;
    Board.ViewManager_FullUpdate;

    Good :=
        QfnPlaceAt(Board, QfnPlacePad(U2, '1'), 26.075, 18.300) And
        QfnPlaceAt(Board, QfnPlacePad(U2, 'EP'), 30.500, 14.550) And
        QfnPlaceAt(Board, QfnPlacePad(X4, '1'), 30.390, 7.750) And
        QfnPlaceAt(Board, QfnPlacePad(X4, '2'), 32.390, 7.750) And
        QfnPlaceAt(Board, QfnPlacePad(X4, 'MP1'), 28.040, 2.000) And
        QfnPlaceAt(Board, QfnPlacePad(X4, 'MP2'), 34.740, 2.000) And
        QfnPlaceAt(Board, QfnPlacePad(U10, '1'), 21.3726, 19.2700) And
        QfnPlaceAt(Board, QfnPlacePad(U10, '8'), 25.5976, 19.2700);
    If Good Then
        ShowMessage('U2, X4, and U10 placed at the validated no-notch sites. Do not save until copper is applied and checked.')
    Else
        ShowMessage('WARNING: component placement did not produce the validated pad coordinates. Do not save.');
End;
