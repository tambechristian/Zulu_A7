{ NoPmodX4Footprint.pas -- 2026-11-14. Draws JST-B2B-PH-K-S (JST PH 2.0 mm, 2 circuits, vertical through-hole header
  B2B-PH-K-S(LF)(SN)) into the focused Zulu_A7_no_pmod Rev_2 zulu_a7.PcbLib. Replaces the top-entry SMD
  B2B-PH-SM4-TB on X4, whose housing sat 0.74 mm over U2's south pins (audit 2026-11-14, user decision).
  Geometry = KiCad JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical (JST ePH catalog), top view, origin at pad 1:
    pads 1, 2   round 1.30 mm lands, 0.75 mm plated holes, at (0, 0) and (+2.0, 0)
    body        5.9 x 4.5 mm: x -1.95 .. +3.95, y -2.80 .. +1.70 (the pin row is 1.7 mm from the +y face),
                drawn on Mechanical 3 like X1/X3's bodies; height 6.0 mm
    silk        a pin-1 tick at x -1.20, y +1.10 .. +1.60 only (the -y face sits on the board edge once placed)
  Skips if the footprint already exists. Run DrawX4Footprint with the PcbLib focused, then save the library. }

Function X4LibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_3\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_3 zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function X4FpExists(Lib : IPCB_Library; Name : String) : Boolean;
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

Procedure X4Pad(Fp : IPCB_LibComponent; Name : String; X, Y : Double);
Var
    P : IPCB_Pad;
Begin
    P := PCBServer.PCBObjectFactory(ePadObject, eNoDimension, eCreate_Default);
    P.Name := Name;
    P.X := MMsToCoord(X);
    P.Y := MMsToCoord(Y);
    P.TopShape := eRounded; P.MidShape := eRounded; P.BotShape := eRounded;
    P.TopXSize := MMsToCoord(1.30); P.TopYSize := MMsToCoord(1.30);
    P.MidXSize := MMsToCoord(1.30); P.MidYSize := MMsToCoord(1.30);
    P.BotXSize := MMsToCoord(1.30); P.BotYSize := MMsToCoord(1.30);
    P.Layer := eMultiLayer;
    P.HoleSize := MMsToCoord(0.75);
    P.Plated := True;
    Fp.AddPCBObject(P);
    PCBServer.SendMessageToRobots(Fp.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, P.I_ObjectAddress);
End;

Procedure X4Line(Fp : IPCB_LibComponent; L : TLayer; W, X1, Y1, X2, Y2 : Double);
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

Procedure DrawX4Footprint;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
Begin
    Lib := X4LibOrNil;
    If Lib = Nil Then Exit;
    If X4FpExists(Lib, 'JST-B2B-PH-K-S') Then
    Begin
        ShowMessage('JST-B2B-PH-K-S already exists; nothing drawn.');
        Exit;
    End;
    Fp := PCBServer.CreatePCBLibComp;
    Fp.Name := 'JST-B2B-PH-K-S';
    Fp.Description := 'JST PH 2.0 mm 2-pin vertical through-hole header B2B-PH-K-S; 0.75 mm holes, 1.30 mm lands; body 5.9 x 4.5 x 6.0';
    Fp.Height := MMsToCoord(6.0);
    Lib.RegisterComponent(Fp);
    X4Pad(Fp, '1', 0.0, 0.0);
    X4Pad(Fp, '2', 2.0, 0.0);
    X4Line(Fp, eMechanical3, 0.10, -1.95, -2.80, 3.95, -2.80);
    X4Line(Fp, eMechanical3, 0.10, 3.95, -2.80, 3.95, 1.70);
    X4Line(Fp, eMechanical3, 0.10, 3.95, 1.70, -1.95, 1.70);
    X4Line(Fp, eMechanical3, 0.10, -1.95, 1.70, -1.95, -2.80);
    X4Line(Fp, eTopOverlay, 0.15, -1.20, 1.10, -1.20, 1.60);
    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('JST-B2B-PH-K-S drawn: 2 through-hole pads, Mechanical 3 body, pin-1 tick. Save the library.');
End;
