{ Draw the validated JST S2B-PH-SM4-TB footprint into the focused Rev_2 PcbLib.
  Geometry follows KiCad 10 JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal
  and the JST recommended land pattern. KiCad's Y-down coordinates are negated
  for Altium's Y-up frame. The footprint origin is the body centre. }

Function X4SmLibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_3\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function X4SmFind(Lib : IPCB_Library; Name : String) : IPCB_LibComponent;
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

Procedure X4SmCounts(Fp : IPCB_LibComponent; Var Pads, Tracks : Integer);
Var
    It : IPCB_GroupIterator;
    Obj : IPCB_Primitive;
Begin
    Pads := 0;
    Tracks := 0;
    It := Fp.GroupIterator_Create;
    It.SetState_FilterAll;
    Obj := It.FirstPCBObject;
    While Obj <> Nil Do
    Begin
        If Obj.ObjectId = ePadObject Then Pads := Pads + 1;
        If Obj.ObjectId = eTrackObject Then Tracks := Tracks + 1;
        Obj := It.NextPCBObject;
    End;
    Fp.GroupIterator_Destroy(It);
End;

Procedure X4SmPad(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
Var
    It : IPCB_GroupIterator;
    P : IPCB_Pad;
    IsNew : Boolean;
Begin
    P := Nil;
    It := Fp.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While (P <> Nil) And (P.Name <> Name) Do P := It.NextPCBObject;
    Fp.GroupIterator_Destroy(It);
    IsNew := P = Nil;
    If IsNew Then P := PCBServer.PCBObjectFactory(ePadObject, eNoDimension, eCreate_Default);
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
    If IsNew Then
    Begin
        Fp.AddPCBObject(P);
    End;
End;

Procedure X4SmLine(Fp : IPCB_LibComponent; L : TLayer; W, X1, Y1, X2, Y2 : Double);
Var
    T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1);
    T.Y1 := MMsToCoord(Y1);
    T.X2 := MMsToCoord(X2);
    T.Y2 := MMsToCoord(Y2);
    T.Width := MMsToCoord(W);
    T.Layer := L;
    Fp.AddPCBObject(T);
End;

Procedure DrawX4Smd;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    Pads, Tracks : Integer;
Begin
    Lib := X4SmLibOrNil;
    If Lib = Nil Then Exit;
    Fp := X4SmFind(Lib, 'JST-S2B-PH-SM4-TB');
    If Fp <> Nil Then
    Begin
        X4SmCounts(Fp, Pads, Tracks);
        If (Pads = 4) And (Tracks = 10) Then
        Begin
            ShowMessage('JST-S2B-PH-SM4-TB already exists with 4 pads and 10 lines; nothing drawn.');
            Exit;
        End;
        If (Pads < 1) Or (Pads > 4) Or (Tracks <> 0) Then
        Begin
            ShowMessage('Refusing: existing JST-S2B-PH-SM4-TB is incomplete but not empty (' +
                IntToStr(Pads) + ' pads, ' + IntToStr(Tracks) + ' lines).');
            Exit;
        End;
    End
    Else
    Begin
        Fp := PCBServer.CreatePCBLibComp;
        Fp.Name := 'JST-S2B-PH-SM4-TB';
        Fp.Description := 'JST PH 2.0 mm 2-pin side-entry SMT header S2B-PH-SM4-TB; validated stock land pattern';
        Fp.Height := MMsToCoord(4.5);
        Lib.RegisterComponent(Fp);
    End;

    Fp.Name := 'JST-S2B-PH-SM4-TB';
    Fp.Description := 'JST PH 2.0 mm 2-pin side-entry SMT header S2B-PH-SM4-TB; validated stock land pattern';
    Fp.Height := MMsToCoord(4.5);

    X4SmPad(Fp, '1', -1.00,  2.85, 1.00, 3.50);
    X4SmPad(Fp, '2',  1.00,  2.85, 1.00, 3.50);
    X4SmPad(Fp, 'MP1', -3.35, -2.90, 1.50, 3.40);
    X4SmPad(Fp, 'MP2',  3.35, -2.90, 1.50, 3.40);

    X4SmLine(Fp, eMechanical3, 0.10, -3.95, -4.40,  3.95, -4.40);
    X4SmLine(Fp, eMechanical3, 0.10,  3.95, -4.40,  3.95,  3.20);
    X4SmLine(Fp, eMechanical3, 0.10,  3.95,  3.20, -3.95,  3.20);
    X4SmLine(Fp, eMechanical3, 0.10, -3.95,  3.20, -3.95, -4.40);

    X4SmLine(Fp, eTopOverlay, 0.12, -4.06,  3.31, -3.04,  3.31);
    X4SmLine(Fp, eTopOverlay, 0.12, -4.06,  3.31, -4.06, -0.85);
    X4SmLine(Fp, eTopOverlay, 0.12,  4.06,  3.31,  3.04,  3.31);
    X4SmLine(Fp, eTopOverlay, 0.12,  4.06,  3.31,  4.06, -0.85);
    X4SmLine(Fp, eTopOverlay, 0.12, -2.25, -4.51,  2.25, -4.51);
    X4SmLine(Fp, eTopOverlay, 0.15, -1.85,  4.60, -1.85,  3.75);

    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('JST-S2B-PH-SM4-TB drawn with 4 SMT pads and Mechanical 3 body. Save only the PcbLib.');
End;
