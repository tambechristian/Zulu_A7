{ NoPmodX3_3M.pas -- 2026-11-24, no-PMOD Rev 4: draw the 3M 2908-05WB-MG microSD socket footprint into the focused
  Rev_4 zulu_a7.PcbLib as '3M-2908-05WB-MG'.

  Land pattern = 3M TS-2197-02 sheet 3 "RECOMMENDED PCB PATTERN LAYOUT" (+-0.05), read from the PDF's own vector
  geometry (scale 6.4364 pt/mm, checked against every dimension on the sheet). Origin = body centre; the card mouth
  is +Y (the card slides in from +Y); body 14.00 (X) x 14.20 (Y), 1.85 high.
    pads 1-8 : 0.80 x 1.50 at 1.10 pitch, #8 centre 1.24 from the body's +X edge, top edges 1.15 below the G2 pad;
               #2 is 0.40 lower, #4 and #6 0.20 higher (staggered contact tails)
    G1, G2   : 1.40 x 1.90 lock/link pins at the mouth corners (G1 overhangs the mouth by 1.30, G2 by 0.30)
    G3, G4   : 1.80 x 1.40 shell tabs at the rear edge (overhang 0.30)
  The 3M 'pattern prohibition area' (no copper) is X 6.65..7.25, Y -7.40..5.50: 0.35 inside to 0.25 outside the
  body's +X edge, under the shell's 0.60 flat flange (re-derived from the PDF hatch after the 2026-11-24 review; an
  earlier note here put it at X 6.16..6.64). Not drawn as a keepout; tools/route/x3_3m/prep2.py keeps it copper-free.
  Silk: body outline (0.12) broken 0.37 mm around every pad. Mechanical 3: body outline.
  Refuses unless the Rev_4 zulu_a7.PcbLib is focused. Save only the PcbLib. }

Function X3LibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_4\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Zulu_A7_no_pmod Rev_4 zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function X3Find(Lib : IPCB_Library; Name : String) : IPCB_LibComponent;
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

Procedure X3Pad(Fp : IPCB_LibComponent; Name : String; X, Y, DX, DY : Double);
Var
    P : IPCB_Pad;
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
    Fp.AddPCBObject(P);
End;

Procedure X3Line(Fp : IPCB_LibComponent; L : TLayer; W, X1, Y1, X2, Y2 : Double);
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

Procedure DrawX3_3M;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    k : Integer;
    Y : Double;
Begin
    Lib := X3LibOrNil;
    If Lib = Nil Then Exit;
    If X3Find(Lib, '3M-2908-05WB-MG') <> Nil Then
    Begin
        ShowMessage('Refusing: 3M-2908-05WB-MG already exists in this library.');
        Exit;
    End;
    Fp := PCBServer.CreatePCBLibComp;
    Fp.Name := '3M-2908-05WB-MG';
    Fp.Description := '3M 2908-05WB-MG microSD push-push socket, 1.85 mm; land pattern per 3M TS-2197-02 sheet 3';
    Fp.Height := MMsToCoord(1.85);
    Lib.RegisterComponent(Fp);

    For k := 1 To 8 Do
    Begin
        Y := 3.60;
        If k = 2 Then Y := 3.20;
        If (k = 4) Or (k = 6) Then Y := 3.80;
        X3Pad(Fp, IntToStr(k), 5.76 - (8 - k) * 1.10, Y, 0.80, 1.50);
    End;
    X3Pad(Fp, 'G1', -6.60,  7.45, 1.40, 1.90);
    X3Pad(Fp, 'G2',  6.55,  6.45, 1.40, 1.90);
    X3Pad(Fp, 'G3', -0.75, -6.70, 1.80, 1.40);
    X3Pad(Fp, 'G4',  4.95, -6.70, 1.80, 1.40);

    { Mechanical 3: body }
    X3Line(Fp, eMechanical3, 0.10, -7.00, -7.10,  7.00, -7.10);
    X3Line(Fp, eMechanical3, 0.10,  7.00, -7.10,  7.00,  7.10);
    X3Line(Fp, eMechanical3, 0.10,  7.00,  7.10, -7.00,  7.10);
    X3Line(Fp, eMechanical3, 0.10, -7.00,  7.10, -7.00, -7.10);

    { Top Overlay: body outline 0.06 outside the body, broken 0.37 mm around the pads }
    X3Line(Fp, eTopOverlay, 0.12, -7.06, -7.16, -7.06,  6.13);   { -X edge, stops below G1 }
    X3Line(Fp, eTopOverlay, 0.12, -7.06, -7.16, -2.02, -7.16);   { rear edge, west of G3 }
    X3Line(Fp, eTopOverlay, 0.12,  0.52, -7.16,  3.68, -7.16);   { rear edge, between G3 and G4 }
    X3Line(Fp, eTopOverlay, 0.12,  6.22, -7.16,  7.06, -7.16);   { rear edge, east of G4 }
    X3Line(Fp, eTopOverlay, 0.12,  7.06, -7.16,  7.06,  5.13);   { +X edge, stops below G2 }
    X3Line(Fp, eTopOverlay, 0.12, -5.53,  7.16,  5.48,  7.16);   { mouth edge, between G1 and G2 }

    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('3M-2908-05WB-MG drawn: 12 pads, 4 Mechanical 3 lines, 6 overlay lines. Save only the PcbLib.');
End;
