{ NoPmodLibFix.pas -- 2026-11-14. Two library edits in the focused Zulu_A7_no_pmod Rev_2 zulu_a7.PcbLib:
  1. JST-B2B-PH-K-S (X4): lands 1.30 -> 1.15 mm on every layer (0.75 mm holes kept, 0.20 mm ring). The 1.30 lands left
     0.05 / 0.079 mm bottom solder-mask slivers to C4-2 / C5-1 (DRC 2026-11-14 17:17); 1.15 gives 0.125 mm.
  2. MSOP-8_3X3_P0.65 (U10 becomes 93LC46BT-I/MS, user decision 2026-11-14): JEDEC MO-187 AA as KiCad's
     MSOP-8_3x3mm_P0.65mm, top view, origin at the package centre, pin 1 top left:
       pads 1-4  1.625 x 0.40 at x -2.1125, y +0.975, +0.325, -0.325, -0.975
       pads 5-8  1.625 x 0.40 at x +2.1125, y -0.975, -0.325, +0.325, +0.975
       body      3.0 x 3.0 on Mechanical 3; height 1.1 mm; silk pin-1 tick at x -1.6, y +1.75 .. +2.05
  Run LibFix with the PcbLib focused, then save the library. }

Function LfLibOrNil : IPCB_Library;
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

Function LfFind(Lib : IPCB_Library; Name : String) : IPCB_LibComponent;
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

Procedure LfPad(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
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

Procedure LfLine(Fp : IPCB_LibComponent; L : TLayer; W, X1, Y1, X2, Y2 : Double);
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

Procedure LibFix;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    GIt : IPCB_GroupIterator;
    P : IPCB_Pad;
    n : Integer;
    Msg : String;
Begin
    Lib := LfLibOrNil;
    If Lib = Nil Then Exit;
    Msg := '';
    // 1. X4 lands
    Fp := LfFind(Lib, 'JST-B2B-PH-K-S');
    If Fp = Nil Then Msg := Msg + 'JST-B2B-PH-K-S not found. ' Else
    Begin
        n := 0;
        GIt := Fp.GroupIterator_Create;
        GIt.AddFilter_ObjectSet(MkSet(ePadObject));
        P := GIt.FirstPCBObject;
        While P <> Nil Do
        Begin
            P.BeginModify;
            P.TopXSize := MMsToCoord(1.15); P.TopYSize := MMsToCoord(1.15);
            P.MidXSize := MMsToCoord(1.15); P.MidYSize := MMsToCoord(1.15);
            P.BotXSize := MMsToCoord(1.15); P.BotYSize := MMsToCoord(1.15);
            P.EndModify;
            n := n + 1;
            P := GIt.NextPCBObject;
        End;
        Fp.GroupIterator_Destroy(GIt);
        Msg := Msg + 'JST-B2B-PH-K-S: ' + IntToStr(n) + ' lands set to 1.15 mm. ';
    End;
    // 2. MSOP-8
    If LfFind(Lib, 'MSOP-8_3X3_P0.65') <> Nil Then Msg := Msg + 'MSOP-8_3X3_P0.65 already exists. ' Else
    Begin
        Fp := PCBServer.CreatePCBLibComp;
        Fp.Name := 'MSOP-8_3X3_P0.65';
        Fp.Description := 'MSOP-8 3 x 3 mm, 0.65 mm pitch (JEDEC MO-187 AA); pads 1.625 x 0.40 at +-2.1125; 93LC46BT-I/MS';
        Fp.Height := MMsToCoord(1.1);
        Lib.RegisterComponent(Fp);
        LfPad(Fp, '1', -2.1125, 0.975, 1.625, 0.40);
        LfPad(Fp, '2', -2.1125, 0.325, 1.625, 0.40);
        LfPad(Fp, '3', -2.1125, -0.325, 1.625, 0.40);
        LfPad(Fp, '4', -2.1125, -0.975, 1.625, 0.40);
        LfPad(Fp, '5', 2.1125, -0.975, 1.625, 0.40);
        LfPad(Fp, '6', 2.1125, -0.325, 1.625, 0.40);
        LfPad(Fp, '7', 2.1125, 0.325, 1.625, 0.40);
        LfPad(Fp, '8', 2.1125, 0.975, 1.625, 0.40);
        LfLine(Fp, eMechanical3, 0.10, -1.5, -1.5, 1.5, -1.5);
        LfLine(Fp, eMechanical3, 0.10, 1.5, -1.5, 1.5, 1.5);
        LfLine(Fp, eMechanical3, 0.10, 1.5, 1.5, -1.5, 1.5);
        LfLine(Fp, eMechanical3, 0.10, -1.5, 1.5, -1.5, -1.5);
        LfLine(Fp, eTopOverlay, 0.15, -1.6, 1.75, -1.6, 2.05);
        Msg := Msg + 'MSOP-8_3X3_P0.65 drawn: 8 pads. ';
        Lib.CurrentComponent := Fp;
    End;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage(Msg + 'Save the library.');
End;
