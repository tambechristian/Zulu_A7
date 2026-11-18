{ AsarX4Footprint4.pas -- 2026-11-16. Fourth try (no SendMessageToRobots: v1 and v3 both died right after the first pad, in ScriptingSystem.DLL, on Altium 26.11.1): AsarX4Footprint.pas crashed after the first pad (access violation in ScriptingSystem.DLL)
  and left a 1-pad footprint (discarded unsaved). This copy follows Altium's own CreateFootprintInLibrary order:
  register, make it the current component, then add the primitives (no PreProcess: a crash must not strand a transaction).
  Draws JST-S2B-PH-SM4-TB (JST PH 2.0 mm, 2 circuits, SIDE-entry SMT header S2B-PH-SM4-TB(LF)(SN), body
  7.9 x 6.0 x 5.5 mm) into Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbLib.
  Land = JST ePH catalogue p.2, side entry type (minimum land), drawn with the MOUTH toward +y and the origin at the
  housing centre (the mating face is the line y = +3.0):
    pads 1, 2   1.0 x 3.5 at x +1.0 / -1.0, y -4.25 (5.5 .. 9.0 behind the face)
    MP1, MP2    1.5 x 3.4 at x -3.35 / +3.35, y +1.5 (0.2 past the face .. 3.2 behind it)
  Pin 1 (battery +) is the EAST pad: looking into the mouth, JST's No. 1 circuit mark is on the left.
  Pad names match JST-B2B-PH-SM4-TB (1, 2, MP1, MP2), so the ECO can swap the footprint.
  Mechanical 3: housing outline; Mechanical 7: the same outline broken at the pads (as on the B2B footprint).
  Skips if the footprint already exists. Run DrawAsarX4Footprint4 with the PcbLib focused, then File > Save. }

Function X4LibOrNil4 : IPCB_Library;
Var
    Lib : IPCB_Library;
    Fn : String;
Begin
    Result := Nil;
    Lib := PCBServer.GetCurrentPCBLibrary;
    If Lib = Nil Then
    Begin
        ShowMessage('Refusing: no PCB library is focused; focus Asar_feather Rev_1 asar_feather.PcbLib first.');
        Exit;
    End;
    Fn := Lib.Board.FileName;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbLib', Fn) = 0 Then
    Begin
        ShowMessage('Refusing: the focused library is ' + Fn + ', not Rev_1 asar_feather.PcbLib.');
        Exit;
    End;
    Result := Lib;
End;

Function X4FpExists4(Lib : IPCB_Library; Name : String) : Boolean;
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

Procedure X4Pad4(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
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
End;

Procedure X4Line4(Fp : IPCB_LibComponent; L : TLayer; X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1); T.Y1 := MMsToCoord(Y1);
    T.X2 := MMsToCoord(X2); T.Y2 := MMsToCoord(Y2);
    T.Width := MMsToCoord(0.127);
    T.Layer := L;
    Fp.AddPCBObject(T);
End;

Procedure DrawAsarX4Footprint4;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
Begin
    Lib := X4LibOrNil4;
    If Lib = Nil Then Exit;
    If X4FpExists4(Lib, 'JST-S2B-PH-SM4-TB') Then
    Begin
        ShowMessage('JST-S2B-PH-SM4-TB already exists; nothing drawn.');
        Exit;
    End;
    Fp := PCBServer.CreatePCBLibComp;
    Fp.Name := 'JST-S2B-PH-SM4-TB';
    Fp.Description := 'JST PH 2.0 mm 2-pin side-entry SMT header S2B-PH-SM4-TB; JST ePH land; origin at housing centre, mouth +y, pin 1 east';
    Fp.Height := MMsToCoord(5.5);
    Lib.RegisterComponent(Fp);
    Lib.CurrentComponent := Fp;
    X4Pad4(Fp, '1', 1.00, -4.25, 1.00, 3.50);
    X4Pad4(Fp, '2', -1.00, -4.25, 1.00, 3.50);
    X4Pad4(Fp, 'MP1', -3.35, 1.50, 1.50, 3.40);
    X4Pad4(Fp, 'MP2', 3.35, 1.50, 1.50, 3.40);
    X4Line4(Fp, eMechanical3, -3.95, -3.00, 3.95, -3.00);
    X4Line4(Fp, eMechanical3, 3.95, -3.00, 3.95, 3.00);
    X4Line4(Fp, eMechanical3, 3.95, 3.00, -3.95, 3.00);
    X4Line4(Fp, eMechanical3, -3.95, 3.00, -3.95, -3.00);
    X4Line4(Fp, eMechanical7, -3.95, -3.00, -1.75, -3.00);
    X4Line4(Fp, eMechanical7, -0.25, -3.00, 0.25, -3.00);
    X4Line4(Fp, eMechanical7, 1.75, -3.00, 3.95, -3.00);
    X4Line4(Fp, eMechanical7, 3.95, -3.00, 3.95, -0.45);
    X4Line4(Fp, eMechanical7, -3.95, -3.00, -3.95, -0.45);
    X4Line4(Fp, eMechanical7, -2.35, 3.00, 2.35, 3.00);
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('JST-S2B-PH-SM4-TB drawn: 4 pads, 4 + 6 mechanical lines. File > Save the library.');
End;
