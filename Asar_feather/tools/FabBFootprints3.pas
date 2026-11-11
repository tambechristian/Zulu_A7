{ FabBFootprints3.pas -- 2026-11-10: SOT23-5 (U7 SC189A) and C0805 (C149) for zulu_a7.PcbLib, which lacks them
  (asar_feather.PcbLib has both; geometry taken from Asar's placed U7/C78). Each only if missing.
  Run DrawFabBFootprints3 with zulu_a7.PcbLib focused, then File > Save. }

Function LtcLibOrNil3 : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or ((Pos('asar_feather.PcbLib', Doc.DM_FullPath) = 0) And (Pos('zulu_a7.PcbLib', Doc.DM_FullPath) = 0)) Then
    Begin
        ShowMessage('Refusing: focus asar_feather.PcbLib or zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function LtcFpExists3(Lib : IPCB_Library; Name : String) : Boolean;
Var
    It : IPCB_LibraryIterator;
    Fp : IPCB_LibComponent;
Begin
    Result := False;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = Name Then Result := True;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
End;

Procedure LtcPad3(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
Var
    P : IPCB_Pad;
Begin
    P := PCBServer.PCBObjectFactory(ePadObject, eNoDimension, eCreate_Default);
    P.Name := Name;
    P.X := MMsToCoord(X);
    P.Y := MMsToCoord(Y);
    P.TopShape := eRectangular; P.MidShape := eRectangular; P.BotShape := eRectangular;
    P.TopXSize := MMsToCoord(DX); P.TopYSize := MMsToCoord(DY);
    P.MidXSize := MMsToCoord(DX); P.MidYSize := MMsToCoord(DY);
    P.BotXSize := MMsToCoord(DX); P.BotYSize := MMsToCoord(DY);
    P.Layer := eTopLayer;
    P.HoleSize := 0;
    Fp.AddPCBObject(P);
    PCBServer.SendMessageToRobots(Fp.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, P.I_ObjectAddress);
End;

Procedure LtcSilk3(Fp : IPCB_LibComponent; X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1); T.Y1 := MMsToCoord(Y1);
    T.X2 := MMsToCoord(X2); T.Y2 := MMsToCoord(Y2);
    T.Width := MMsToCoord(0.150);
    T.Layer := eTopOverlay;
    Fp.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Fp.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
End;

Function LtcNew3(Lib : IPCB_Library; Name, Descr : String; H : Double) : IPCB_LibComponent;
Begin
    Result := PCBServer.CreatePCBLibComp;
    Result.Name := Name;
    Result.Description := Descr;
    Result.Height := MMsToCoord(H);
    Lib.RegisterComponent(Result);
End;

Procedure LtcTwoPad3(Lib : IPCB_Library; Name, Descr : String; H, Pitch, DX, DY : Double; Var Made : String);
Var
    Fp : IPCB_LibComponent;
Begin
    If LtcFpExists3(Lib, Name) Then Exit;
    Fp := LtcNew3(Lib, Name, Descr, H);
    LtcPad3(Fp, '1', -Pitch / 2, 0, DX, DY);
    LtcPad3(Fp, '2', Pitch / 2, 0, DX, DY);
    Made := Made + Name + ' ';
End;

Procedure DrawFabBFootprints3;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    Made : String;
Begin
    Lib := LtcLibOrNil3;
    If Lib = Nil Then Exit;
    Made := '';
    If Not LtcFpExists3(Lib, 'SOT23-5') Then
    Begin
        Fp := LtcNew3(Lib, 'SOT23-5', 'SOT23-5 (Semtech SC189xSKTRT land, datasheet p.23): 0.95 pitch, pads 0.60 x 1.10, rows 2.50 apart; pins 1-3 one side, 4 opposite 3, 5 opposite 1 (as asar_feather.PcbLib)', 1.45);
        LtcPad3(Fp, '1', -0.95, -1.25, 0.60, 1.10);
        LtcPad3(Fp, '2', 0.00, -1.25, 0.60, 1.10);
        LtcPad3(Fp, '3', 0.95, -1.25, 0.60, 1.10);
        LtcPad3(Fp, '4', 0.95, 1.25, 0.60, 1.10);
        LtcPad3(Fp, '5', -0.95, 1.25, 0.60, 1.10);
        LtcSilk3(Fp, -1.55, -1.95, -1.25, -1.95);
        Made := Made + 'SOT23-5 ';
    End;
    LtcTwoPad3(Lib, 'C0805', '0805 capacitor, 1.30 x 1.50 pads on 1.70 pitch (as asar_feather.PcbLib)', 1.25, 1.70, 1.30, 1.50, Made);
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('Drawn: ' + Made + '(empty = all present). Save the library.');
End;
