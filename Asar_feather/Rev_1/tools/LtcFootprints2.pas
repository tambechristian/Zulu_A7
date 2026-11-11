{ LtcFootprints2.pas -- 2026-11-10 (adds C0603 to Fab B; same helpers as LtcFootprints.pas). Footprints for the LTC3556 power section, drawn into the focused PcbLib of Asar_feather
  or Zulu_A7_Fab_B (each only if missing):
    QFN28-UFD-4X5  Analog Devices/Linear UFD 28-lead QFN 4 x 5 mm (LTC DWG 05-08-1712 Rev B, datasheet p.36 "recommended
                   solder pad pitch and dimensions"), top view, pin 1 top left, counter-clockwise:
                   pins 1-8 x -1.90, y +1.75 .. -1.75 (0.70 x 0.25); 9-14 y -2.40, x -1.25 .. +1.25 (0.25 x 0.70);
                   15-22 x +1.90, y -1.75 .. +1.75; 23-28 y +2.40, x +1.25 .. -1.25; exposed pad 29 2.65 x 3.65 (GND).
                   Silk: pin-1 tick only.
    C0201, R0201   0.30 x 0.30 pads at x -/+0.30   (as asar_feather.PcbLib)
    C0402          0.70 x 0.90 pads at x -/+0.65   (as asar_feather.PcbLib)
    IND2520        1.05 x 2.30 pads at x -/+1.175  (as asar_feather.PcbLib)
  Run DrawLtcFootprints with the PcbLib focused, then File > Save. }

Function LtcLibOrNil2 : IPCB_Library;
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

Function LtcFpExists2(Lib : IPCB_Library; Name : String) : Boolean;
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

Procedure LtcPad2(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
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

Procedure LtcSilk2(Fp : IPCB_LibComponent; X1, Y1, X2, Y2 : Double);
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

Function LtcNew2(Lib : IPCB_Library; Name, Descr : String; H : Double) : IPCB_LibComponent;
Begin
    Result := PCBServer.CreatePCBLibComp;
    Result.Name := Name;
    Result.Description := Descr;
    Result.Height := MMsToCoord(H);
    Lib.RegisterComponent(Result);
End;

Procedure LtcTwoPad2(Lib : IPCB_Library; Name, Descr : String; H, Pitch, DX, DY : Double; Var Made : String);
Var
    Fp : IPCB_LibComponent;
Begin
    If LtcFpExists2(Lib, Name) Then Exit;
    Fp := LtcNew2(Lib, Name, Descr, H);
    LtcPad2(Fp, '1', -Pitch / 2, 0, DX, DY);
    LtcPad2(Fp, '2', Pitch / 2, 0, DX, DY);
    Made := Made + Name + ' ';
End;

Procedure DrawLtcFootprints2;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    Made : String;
    i : Integer;
Begin
    Lib := LtcLibOrNil2;
    If Lib = Nil Then Exit;
    Made := '';
    If Not LtcFpExists2(Lib, 'QFN28-UFD-4X5') Then
    Begin
        Fp := LtcNew2(Lib, 'QFN28-UFD-4X5', 'UFD 28-lead QFN 4 x 5 mm, 0.5 pitch, exposed pad 2.65 x 3.65 (pad 29 = GND); LTC DWG 05-08-1712 Rev B recommended pads', 0.75);
        For i := 1 To 8 Do LtcPad2(Fp, IntToStr(i), -1.90, 1.75 - 0.5 * (i - 1), 0.70, 0.25);
        For i := 9 To 14 Do LtcPad2(Fp, IntToStr(i), -1.25 + 0.5 * (i - 9), -2.40, 0.25, 0.70);
        For i := 15 To 22 Do LtcPad2(Fp, IntToStr(i), 1.90, -1.75 + 0.5 * (i - 15), 0.70, 0.25);
        For i := 23 To 28 Do LtcPad2(Fp, IntToStr(i), 1.25 - 0.5 * (i - 23), 2.40, 0.25, 0.70);
        LtcPad2(Fp, '29', 0, 0, 2.65, 3.65);
        LtcSilk2(Fp, -2.65, 1.60, -2.65, 1.90);
        Made := Made + 'QFN28-UFD-4X5 ';
    End;
    LtcTwoPad2(Lib, 'C0603', '0603 capacitor, 1.10 x 1.00 pads on 1.70 pitch (as asar_feather.PcbLib)', 0.9, 1.70, 1.10, 1.00, Made);
    LtcTwoPad2(Lib, 'C0201', '0201 capacitor, 0.30 x 0.30 pads on 0.60 pitch', 0.33, 0.60, 0.30, 0.30, Made);
    LtcTwoPad2(Lib, 'R0201', '0201 resistor, 0.30 x 0.30 pads on 0.60 pitch', 0.26, 0.60, 0.30, 0.30, Made);
    LtcTwoPad2(Lib, 'C0402', '0402 capacitor, 0.70 x 0.90 pads on 1.30 pitch', 0.55, 1.30, 0.70, 0.90, Made);
    LtcTwoPad2(Lib, 'IND2520', '2520 inductor (Murata DFE2520), 1.05 x 2.30 pads on 2.35 pitch', 1.2, 2.35, 1.05, 2.30, Made);
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('Drawn: ' + Made + '(empty = all present). Save the library.');
End;
