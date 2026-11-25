{ NoPmodX4Side.pas -- 2026-11-15. Draws JST-S2B-PH-K-S (JST PH 2.0 mm, 2 circuits, SIDE-ENTRY through-hole header
  S2B-PH-K-S(LF)(SN)) into the focused Zulu_A7_no_pmod Rev_2 zulu_a7.PcbLib (user decision 2026-11-15: a laid-down
  battery plug between X2 pins 30 and 31, housing 1.55 mm past the bottom edge).
  Geometry = KiCad JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal (JST ePH catalog), top view, origin at pad 1:
    pads 1, 2   round 1.20 mm lands, 0.75 mm plated holes, at (0, 0) and (+2.0, 0)
    body        5.9 x 7.6 mm: x -1.95 .. +3.95, y -1.35 .. +6.25; the opening (mating face) is the +y face;
                drawn on Mechanical 3; height 4.8 mm
    silk        a pin-1 tick at x -1.25, y -0.30 .. +0.30
  Skips if the footprint already exists. Run DrawX4Side with the PcbLib focused, then save the library. }

Function X4sLibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_4\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_4 zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function X4sFpExists(Lib : IPCB_Library; Name : String) : Boolean;
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

Procedure X4sPad(Fp : IPCB_LibComponent; Name : String; X, Y : Double);
Var
    P : IPCB_Pad;
Begin
    P := PCBServer.PCBObjectFactory(ePadObject, eNoDimension, eCreate_Default);
    P.Name := Name;
    P.X := MMsToCoord(X);
    P.Y := MMsToCoord(Y);
    P.TopShape := eRounded; P.MidShape := eRounded; P.BotShape := eRounded;
    P.TopXSize := MMsToCoord(1.20); P.TopYSize := MMsToCoord(1.20);
    P.MidXSize := MMsToCoord(1.20); P.MidYSize := MMsToCoord(1.20);
    P.BotXSize := MMsToCoord(1.20); P.BotYSize := MMsToCoord(1.20);
    P.Layer := eMultiLayer;
    P.HoleSize := MMsToCoord(0.75);
    P.Plated := True;
    Fp.AddPCBObject(P);
    PCBServer.SendMessageToRobots(Fp.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, P.I_ObjectAddress);
End;

Procedure X4sLine(Fp : IPCB_LibComponent; L : TLayer; W, X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1); T.Y1 := MMsToCoord(Y1);
    T.X2 := MMsToCoord(X2); T.Y2 := MMsToCoord(Y2);
    T.Width := MMsToCoord(W);
    T.Layer := L;
    Fp.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Fp.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
End;

Procedure DrawX4Side;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
Begin
    Lib := X4sLibOrNil;
    If Lib = Nil Then Exit;
    If X4sFpExists(Lib, 'JST-S2B-PH-K-S') Then
    Begin
        ShowMessage('JST-S2B-PH-K-S already exists; nothing drawn.');
        Exit;
    End;
    Fp := PCBServer.CreatePCBLibComp;
    Fp.Name := 'JST-S2B-PH-K-S';
    Fp.Description := 'JST PH 2.0 mm 2-pin side-entry through-hole header S2B-PH-K-S; 0.75 mm holes, 1.20 mm lands; body 5.9 x 7.6 x 4.8, opening +y';
    Fp.Height := MMsToCoord(4.8);
    Lib.RegisterComponent(Fp);
    X4sPad(Fp, '1', 0.0, 0.0);
    X4sPad(Fp, '2', 2.0, 0.0);
    X4sLine(Fp, eMechanical3, 0.10, -1.95, -1.35, 3.95, -1.35);
    X4sLine(Fp, eMechanical3, 0.10, 3.95, -1.35, 3.95, 6.25);
    X4sLine(Fp, eMechanical3, 0.10, 3.95, 6.25, -1.95, 6.25);
    X4sLine(Fp, eMechanical3, 0.10, -1.95, 6.25, -1.95, -1.35);
    X4sLine(Fp, eTopOverlay, 0.15, -1.25, -0.30, -1.25, 0.30);
    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('JST-S2B-PH-K-S drawn: 2 through-hole pads, Mechanical 3 body, pin-1 tick. Save the library.');
End;
