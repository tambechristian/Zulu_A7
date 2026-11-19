{ Clip four X4 Top Overlay lines to meet the 0.254 mm silk-to-mask rule.
  Run FixX4SilkBoard with the Rev_2 PCB focused and FixX4SilkLib with its PcbLib focused. }

Function X4SilkNear(A, B : Double) : Boolean;
Begin
    Result := Abs(A - B) < 0.02;
End;

Function X4SilkPair(A, B, U, V : Double) : Boolean;
Begin
    Result := (X4SilkNear(A, U) And X4SilkNear(B, V)) Or
              (X4SilkNear(A, V) And X4SilkNear(B, U));
End;

Function X4SilkBoardLine(Board : IPCB_Board; T : IPCB_Track) : Boolean;
Var
    X1, Y1, X2, Y2 : Double;
Begin
    X1 := CoordToMMs(T.X1 - Board.XOrigin);
    Y1 := CoordToMMs(T.Y1 - Board.YOrigin);
    X2 := CoordToMMs(T.X2 - Board.XOrigin);
    Y2 := CoordToMMs(T.Y2 - Board.YOrigin);
    Result :=
        (X4SilkNear(X1, X2) And
         (X4SilkNear(X1, 25.94) Or X4SilkNear(X1, 34.06)) And
         (X4SilkPair(Y1, Y2, 0.26, 4.51) Or X4SilkPair(Y1, Y2, 0.35, 4.51))) Or
        (X4SilkNear(Y1, -3.31) And X4SilkNear(Y2, -3.31) And
         (X4SilkPair(X1, X2, 27.66, 32.34) Or X4SilkPair(X1, X2, 27.75, 32.25))) Or
        ((X4SilkNear(X1, 31.76) Or X4SilkNear(X1, 31.85)) And
         (X4SilkNear(X2, 31.76) Or X4SilkNear(X2, 31.85)) And
         X4SilkPair(Y1, Y2, 4.95, 5.80));
End;

Procedure X4SilkFixBoardLine(Board : IPCB_Board; T : IPCB_Track);
Var
    X1, Y1, X2, Y2 : Double;
Begin
    X1 := CoordToMMs(T.X1 - Board.XOrigin);
    Y1 := CoordToMMs(T.Y1 - Board.YOrigin);
    X2 := CoordToMMs(T.X2 - Board.XOrigin);
    Y2 := CoordToMMs(T.Y2 - Board.YOrigin);
    If X4SilkNear(X1, X2) And
       (X4SilkNear(X1, 25.94) Or X4SilkNear(X1, 34.06)) Then
    Begin
        If Y1 < Y2 Then
        Begin
            T.Y1 := Board.YOrigin + MMsToCoord(0.35);
            T.Y2 := Board.YOrigin + MMsToCoord(4.51);
        End
        Else
        Begin
            T.Y1 := Board.YOrigin + MMsToCoord(4.51);
            T.Y2 := Board.YOrigin + MMsToCoord(0.35);
        End;
    End
    Else If X4SilkNear(Y1, -3.31) And X4SilkNear(Y2, -3.31) Then
    Begin
        If X1 < X2 Then
        Begin
            T.X1 := Board.XOrigin + MMsToCoord(27.75);
            T.X2 := Board.XOrigin + MMsToCoord(32.25);
        End
        Else
        Begin
            T.X1 := Board.XOrigin + MMsToCoord(32.25);
            T.X2 := Board.XOrigin + MMsToCoord(27.75);
        End;
    End
    Else
    Begin
        T.X1 := Board.XOrigin + MMsToCoord(31.85);
        T.X2 := Board.XOrigin + MMsToCoord(31.85);
    End;
End;

Procedure FixX4SilkBoard;
Var
    Doc : IDocument;
    Board : IPCB_Board;
    C : IPCB_Component;
    It : IPCB_GroupIterator;
    T : IPCB_Track;
    Count : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or
       (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_2 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Board := PCBServer.GetCurrentPCBBoard;
    C := Board.GetPcbComponentByRefDes('X4');
    If (C = Nil) Or (C.Pattern <> 'JST-S2B-PH-SM4-TB') Then
    Begin
        ShowMessage('Refusing: X4 does not use JST-S2B-PH-SM4-TB.');
        Exit;
    End;

    Count := 0;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (T.Layer = eTopOverlay) And X4SilkBoardLine(Board, T) Then Count := Count + 1;
        T := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Count <> 4 Then
    Begin
        ShowMessage('Refusing: expected 4 repairable X4 Top Overlay lines, found ' + IntToStr(Count) + '.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        It := C.GroupIterator_Create;
        It.AddFilter_ObjectSet(MkSet(eTrackObject));
        T := It.FirstPCBObject;
        While T <> Nil Do
        Begin
            If (T.Layer = eTopOverlay) And X4SilkBoardLine(Board, T) Then X4SilkFixBoardLine(Board, T);
            T := It.NextPCBObject;
        End;
        C.GroupIterator_Destroy(It);
    Finally
        PCBServer.PostProcess;
    End;
    Board.ViewManager_FullUpdate;
    ShowMessage('X4 PCB silk clipped: 4 lines normalized for 0.254 mm mask clearance.');
End;

Function X4SilkFind(Lib : IPCB_Library; Name : String) : IPCB_LibComponent;
Var
    It : IPCB_LibraryIterator;
    Fp : IPCB_LibComponent;
Begin
    Result := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = Name Then Result := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
End;

Function X4SilkLibLine(T : IPCB_Track) : Boolean;
Var
    DX, DY, W : Double;
Begin
    DX := Abs(CoordToMMs(T.X2 - T.X1));
    DY := Abs(CoordToMMs(T.Y2 - T.Y1));
    W := CoordToMMs(T.Width);
    Result :=
        (X4SilkNear(W, 0.12) And X4SilkNear(DX, 0.0) And
         (X4SilkNear(DY, 4.25) Or X4SilkNear(DY, 4.16))) Or
        (X4SilkNear(W, 0.12) And X4SilkNear(DY, 0.0) And
         (X4SilkNear(DX, 4.68) Or X4SilkNear(DX, 4.50))) Or
        (X4SilkNear(W, 0.15) And X4SilkNear(DX, 0.0) And X4SilkNear(DY, 0.85));
End;

Procedure X4SilkFixLibLine(T : IPCB_Track; Pad1X : Double);
Var
    X1, Y1, X2, Y2, DX, DY, W, Mid : Double;
Begin
    X1 := CoordToMMs(T.X1);
    Y1 := CoordToMMs(T.Y1);
    X2 := CoordToMMs(T.X2);
    Y2 := CoordToMMs(T.Y2);
    DX := Abs(X2 - X1);
    DY := Abs(Y2 - Y1);
    W := CoordToMMs(T.Width);
    If X4SilkNear(W, 0.12) And X4SilkNear(DX, 0.0) And
       (X4SilkNear(DY, 4.25) Or X4SilkNear(DY, 4.16)) Then
    Begin
        If Y1 < Y2 Then
        Begin
            T.Y2 := MMsToCoord(Y1 + 4.16);
        End
        Else
        Begin
            T.Y1 := MMsToCoord(Y2 + 4.16);
        End;
    End
    Else If X4SilkNear(W, 0.12) And X4SilkNear(DY, 0.0) And
            (X4SilkNear(DX, 4.68) Or X4SilkNear(DX, 4.50)) Then
    Begin
        Mid := (X1 + X2) / 2;
        If X1 < X2 Then
        Begin
            T.X1 := MMsToCoord(Mid - 2.25);
            T.X2 := MMsToCoord(Mid + 2.25);
        End
        Else
        Begin
            T.X1 := MMsToCoord(Mid + 2.25);
            T.X2 := MMsToCoord(Mid - 2.25);
        End;
    End
    Else
    Begin
        T.X1 := MMsToCoord(Pad1X - 0.85);
        T.X2 := MMsToCoord(Pad1X - 0.85);
    End;
End;

Procedure FixX4SilkLib;
Var
    Doc : IDocument;
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    It : IPCB_GroupIterator;
    PIt : IPCB_GroupIterator;
    T : IPCB_Track;
    P : IPCB_Pad;
    Count : Integer;
    Pad1X : Double;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or
       (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_2 zulu_a7.PcbLib first.');
        Exit;
    End;
    Lib := PCBServer.GetCurrentPCBLibrary;
    Fp := X4SilkFind(Lib, 'JST-S2B-PH-SM4-TB');
    If Fp = Nil Then
    Begin
        ShowMessage('Refusing: JST-S2B-PH-SM4-TB is missing from the focused PcbLib.');
        Exit;
    End;

    P := Nil;
    PIt := Fp.GroupIterator_Create;
    PIt.AddFilter_ObjectSet(MkSet(ePadObject));
    P := PIt.FirstPCBObject;
    While (P <> Nil) And (P.Name <> '1') Do P := PIt.NextPCBObject;
    Fp.GroupIterator_Destroy(PIt);
    If P = Nil Then
    Begin
        ShowMessage('Refusing: X4 library pad 1 is missing.');
        Exit;
    End;
    Pad1X := CoordToMMs(P.X);

    Count := 0;
    It := Fp.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (T.Layer = eTopOverlay) And X4SilkLibLine(T) Then Count := Count + 1;
        T := It.NextPCBObject;
    End;
    Fp.GroupIterator_Destroy(It);
    If Count <> 4 Then
    Begin
        ShowMessage('Refusing: expected 4 repairable library Top Overlay lines, found ' + IntToStr(Count) + '.');
        Exit;
    End;

    PCBServer.PreProcess;
    Try
        It := Fp.GroupIterator_Create;
        It.AddFilter_ObjectSet(MkSet(eTrackObject));
        T := It.FirstPCBObject;
        While T <> Nil Do
        Begin
            If (T.Layer = eTopOverlay) And X4SilkLibLine(T) Then X4SilkFixLibLine(T, Pad1X);
            T := It.NextPCBObject;
        End;
        Fp.GroupIterator_Destroy(It);
    Finally
        PCBServer.PostProcess;
    End;
    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('X4 PcbLib silk clipped: 4 lines normalized for 0.254 mm mask clearance.');
End;
