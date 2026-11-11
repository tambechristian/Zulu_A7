{ TpsFootprint.pas -- 2026-11-09. Draws VSON10-DLA0010A (TI TPS63802 buck-boost, VSON-HR 10, 2.0 x 3.0 x 1.0 mm) into the
  focused PcbLib of Asar_feather or Zulu_A7_Fab_B. Land pattern = TI drawing 4223750/D "Example board layout" (datasheet
  SLVSEU9D p.36), top view, origin at the package centre, pin 1 top left, 0.5 mm pitch:
    pads 1-5   0.60 x 0.25 at x -0.90, y +1.0 .. -1.0
    pads 10,9,7,6  0.90 x 0.25 at x +0.75, y +1.0, +0.5, -0.5, -1.0
    pad 8 (GND)    1.30 x 0.25 at x +0.55, y 0          (no exposed pad on this package)
  Silk: only a pin-1 tick left of pad 1 at x -1.60 (body-edge lines dropped 2026-11-09, see TpsFootprintFix.pas). Skips if the footprint already exists.
  Run DrawTpsFootprint with the PcbLib focused, then save the library. }

Function TpsLibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or ((Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbLib', Doc.DM_FullPath) = 0) And
       (Pos('\Zulu_A7_Fab_B\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0)) Then
    Begin
        ShowMessage('Refusing: focus asar_feather.PcbLib or the Fab B zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function TpsFpExists(Lib : IPCB_Library; Name : String) : Boolean;
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

Procedure TpsPad(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
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

Procedure TpsSilk(Fp : IPCB_LibComponent; X1, Y1, X2, Y2 : Double);
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

Procedure DrawTpsFootprint;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
Begin
    Lib := TpsLibOrNil;
    If Lib = Nil Then Exit;
    If TpsFpExists(Lib, 'VSON10-DLA0010A') Then
    Begin
        ShowMessage('VSON10-DLA0010A already exists; nothing drawn.');
        Exit;
    End;
    Fp := PCBServer.CreatePCBLibComp;
    Fp.Name := 'VSON10-DLA0010A';
    Fp.Description := 'TI VSON-HR 10 (DLA0010A) 2.0 x 3.0 mm 0.5 pitch, TPS63802; TI land pattern 4223750/D';
    Fp.Height := MMsToCoord(1.0);
    Lib.RegisterComponent(Fp);
    TpsPad(Fp, '1', -0.90, 1.00, 0.60, 0.25);
    TpsPad(Fp, '2', -0.90, 0.50, 0.60, 0.25);
    TpsPad(Fp, '3', -0.90, 0.00, 0.60, 0.25);
    TpsPad(Fp, '4', -0.90, -0.50, 0.60, 0.25);
    TpsPad(Fp, '5', -0.90, -1.00, 0.60, 0.25);
    TpsPad(Fp, '6', 0.75, -1.00, 0.90, 0.25);
    TpsPad(Fp, '7', 0.75, -0.50, 0.90, 0.25);
    TpsPad(Fp, '8', 0.55, 0.00, 1.30, 0.25);
    TpsPad(Fp, '9', 0.75, 0.50, 0.90, 0.25);
    TpsPad(Fp, '10', 0.75, 1.00, 0.90, 0.25);
    TpsSilk(Fp, -1.60, 0.85, -1.60, 1.15);
    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('VSON10-DLA0010A drawn: 10 pads, 1 silk tick. Save the library.');
End;
