{ Draw the FT2232HQ QFN-64 footprint into the focused Rev_2 PcbLib.
  The land pattern matches Asar_feather's validated QFN-64-9X9-P0.5-EP4.35:
  0.75 x 0.28 mm perimeter lands and a 4.20 mm exposed-pad land. }

Function U2QfnLibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or
       (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function U2QfnFind(Lib : IPCB_Library; Name : String) : IPCB_LibComponent;
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

Procedure U2QfnCounts(Fp : IPCB_LibComponent; Var Pads, Tracks, Fills : Integer);
Var
    It : IPCB_GroupIterator;
    Obj : IPCB_Primitive;
Begin
    Pads := 0;
    Tracks := 0;
    Fills := 0;
    It := Fp.GroupIterator_Create;
    It.SetState_FilterAll;
    Obj := It.FirstPCBObject;
    While Obj <> Nil Do
    Begin
        If Obj.ObjectId = ePadObject Then Pads := Pads + 1;
        If Obj.ObjectId = eTrackObject Then Tracks := Tracks + 1;
        If Obj.ObjectId = eFillObject Then Fills := Fills + 1;
        Obj := It.NextPCBObject;
    End;
    Fp.GroupIterator_Destroy(It);
End;

Procedure U2QfnPad(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
Var
    P : IPCB_Pad;
    PadCache : TPadCache;
Begin
    P := PCBServer.PCBObjectFactory(ePadObject, eNoDimension, eCreate_Default);
    P.Name := Name;
    P.X := MMsToCoord(X);
    P.Y := MMsToCoord(Y);
    P.TopShape := eRectangular;
    P.MidShape := eRectangular;
    P.BotShape := eRectangular;
    P.TopXSize := MMsToCoord(DX);
    P.TopYSize := MMsToCoord(DY);
    P.MidXSize := MMsToCoord(DX);
    P.MidYSize := MMsToCoord(DY);
    P.BotXSize := MMsToCoord(DX);
    P.BotYSize := MMsToCoord(DY);
    P.Layer := eTopLayer;
    P.HoleSize := 0;
    If Name = 'EP' Then
    Begin
        PadCache := P.GetState_Cache;
        PadCache.PasteMaskExpansionValid := eCacheManual;
        PadCache.PasteMaskExpansion := -MMsToCoord(4.20);
        P.SetState_Cache := PadCache;
    End;
    Fp.AddPCBObject(P);
End;

Procedure U2QfnPaste(Fp : IPCB_LibComponent; X, Y : Double);
Var
    F : IPCB_Fill;
Begin
    F := PCBServer.PCBObjectFactory(eFillObject, eNoDimension, eCreate_Default);
    F.X1Location := MMsToCoord(X - 0.50);
    F.Y1Location := MMsToCoord(Y - 0.50);
    F.X2Location := MMsToCoord(X + 0.50);
    F.Y2Location := MMsToCoord(Y + 0.50);
    F.Rotation := 0;
    F.Layer := eTopPaste;
    Fp.AddPCBObject(F);
End;

Procedure U2QfnLine(Fp : IPCB_LibComponent; L : TLayer; X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1);
    T.Y1 := MMsToCoord(Y1);
    T.X2 := MMsToCoord(X2);
    T.Y2 := MMsToCoord(Y2);
    T.Width := MMsToCoord(0.15);
    T.Layer := L;
    Fp.AddPCBObject(T);
End;

Procedure DrawU2Qfn;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    Pads, Tracks, Fills, I, J, K : Integer;
    O : Double;
Begin
    Lib := U2QfnLibOrNil;
    If Lib = Nil Then Exit;

    Fp := U2QfnFind(Lib, 'FT2232HQ-QFN64');
    If Fp <> Nil Then
    Begin
        U2QfnCounts(Fp, Pads, Tracks, Fills);
        If (Pads = 65) And (Tracks = 13) And (Fills = 9) Then
        Begin
            ShowMessage('FT2232HQ-QFN64 already exists with 65 pads, 13 lines, and 9 paste windows; nothing drawn.');
            Exit;
        End;
        ShowMessage('Refusing: existing FT2232HQ-QFN64 has unexpected geometry (' +
            IntToStr(Pads) + ' pads, ' + IntToStr(Tracks) + ' lines, ' +
            IntToStr(Fills) + ' fills).');
        Exit;
    End;

    Fp := PCBServer.CreatePCBLibComp;
    Fp.Name := 'FT2232HQ-QFN64';
    Fp.Description := 'FTDI FT2232HQ QFN-64 9x9 mm, 0.5 mm pitch, 4.20 mm exposed-pad land';
    Fp.Height := MMsToCoord(0.90);
    Lib.RegisterComponent(Fp);

    For K := 0 To 15 Do
    Begin
        O := 3.75 - 0.50 * K;
        U2QfnPad(Fp, IntToStr(1 + K),  -4.425,  O,      0.75, 0.28);
        U2QfnPad(Fp, IntToStr(17 + K), -O,     -4.425, 0.28, 0.75);
        U2QfnPad(Fp, IntToStr(33 + K),  4.425, -O,      0.75, 0.28);
        U2QfnPad(Fp, IntToStr(49 + K),  O,      4.425, 0.28, 0.75);
    End;
    U2QfnPad(Fp, 'EP', 0.0, 0.0, 4.20, 4.20);
    For I := -1 To 1 Do
        For J := -1 To 1 Do
            U2QfnPaste(Fp, I * 1.25, J * 1.25);

    U2QfnLine(Fp, eMechanical3, -4.50, -4.50,  4.50, -4.50);
    U2QfnLine(Fp, eMechanical3,  4.50, -4.50,  4.50,  4.50);
    U2QfnLine(Fp, eMechanical3,  4.50,  4.50, -4.50,  4.50);
    U2QfnLine(Fp, eMechanical3, -4.50,  4.50, -4.50, -4.50);

    U2QfnLine(Fp, eTopOverlay, -4.60, -4.60, -4.15, -4.60);
    U2QfnLine(Fp, eTopOverlay, -4.60, -4.60, -4.60, -4.15);
    U2QfnLine(Fp, eTopOverlay, -4.60,  4.60, -4.15,  4.60);
    U2QfnLine(Fp, eTopOverlay, -4.60,  4.60, -4.60,  4.15);
    U2QfnLine(Fp, eTopOverlay,  4.60, -4.60,  4.15, -4.60);
    U2QfnLine(Fp, eTopOverlay,  4.60, -4.60,  4.60, -4.15);
    U2QfnLine(Fp, eTopOverlay,  4.60,  4.60,  4.15,  4.60);
    U2QfnLine(Fp, eTopOverlay,  4.60,  4.60,  4.60,  4.15);
    U2QfnLine(Fp, eTopOverlay, -5.25,  3.75, -5.25,  3.25);

    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('FT2232HQ-QFN64 drawn with 64 perimeter pads, EP, and a 3x3 paste grid (51% coverage).' +
        #13#10 + 'The nine EP microvias must be filled and copper capped. Save only the PcbLib.');
End;
