{ ProdX1Lib2.pas -- second load of ProdX1Lib.pas: library pad coordinates are footprint-relative (P.X/P.Y),
  not offset by Lib.Board.XOrigin (1270 mm), so the position guard uses P.X/P.Y directly.
  ProdX1Lib.pas -- production copy (Zulu_Altium_VS_Code), 2026-10-07.
  Brings the library footprint MOLEX-105017-0001 in zulu_a7.PcbLib in line with X1 on the board
  (ProdX1Slots*.pas + ProdX1Pads3.pas): MS1/MS2 become plated 0.60 x 1.30 mm slots (rotation 90) with
  top/middle/bottom lands 1.11 x 1.81 / 0.90 x 1.60 / 1.11 x 1.81 mm oblong. X1 is placed at rotation 0, so the
  library values equal the board values.
  Run with zulu_a7.PcbLib FOCUSED: X1LibCanary (reads only), then FixX1LibFootprint, then save the library. }

Const
    FP_NAME = 'MOLEX-105017-0001';
    OUT_W = 1.11;
    OUT_H = 1.81;
    IN_W  = 0.90;
    IN_H  = 1.60;

Function LNear(A, B : Double) : Boolean;
Begin
    Result := Abs(A - B) < 0.01;
End;

Function ProdLibOrNil : IPCB_Library;
Var
    WS  : IWorkspace;
    Doc : IDocument;
Begin
    Result := Nil;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Doc := WS.DM_FocusedDocument;
    If Doc = Nil Then Exit;
    If (Pos('\Zulu_Altium_VS_Code\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0) Or
       (Pos('HDI_Optimized', Doc.DM_FullPath) > 0) Then
    Begin
        ShowMessage('Refusing: focus the production zulu_a7.PcbLib first.' + #13#10 + Doc.DM_FullPath);
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
    If Result = Nil Then ShowMessage('No PCB library is focused.');
End;

Function FindFp(Lib : IPCB_Library) : IPCB_LibComponent;
Var
    FIt : IPCB_LibraryIterator;
    Fp  : IPCB_LibComponent;
Begin
    Result := Nil;
    FIt := Lib.LibraryIterator_Create;
    FIt.SetState_FilterAll;
    Fp := FIt.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = FP_NAME Then Result := Fp;
        Fp := FIt.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(FIt);
End;

Procedure X1LibCanary;
Var
    Lib : IPCB_Library;
    Fp  : IPCB_LibComponent;
    GIt : IPCB_GroupIterator;
    P   : IPCB_Pad;
    S   : String;
Begin
    Lib := ProdLibOrNil;
    If Lib = Nil Then Exit;
    Fp := FindFp(Lib);
    If Fp = Nil Then Begin ShowMessage(FP_NAME + ' not found in the library.'); Exit; End;
    S := FP_NAME + '  origin ' + FloatToStr(CoordToMMs(Lib.Board.XOrigin)) + ', ' + FloatToStr(CoordToMMs(Lib.Board.YOrigin)) +
         '  eRoundHole=' + IntToStr(eRoundHole) + ' eSlotHole=' + IntToStr(eSlotHole) + ' ePadMode_LocalStack=' + IntToStr(ePadMode_LocalStack);
    GIt := Fp.GroupIterator_Create;
    GIt.AddFilter_ObjectSet(MkSet(ePadObject));
    P := GIt.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = 'MS1') Or (P.Name = 'MS2') Then
            S := S + #13#10 + P.Name + ' at ' + FloatToStr(CoordToMMs(P.X - Lib.Board.XOrigin)) + ', ' +
                 FloatToStr(CoordToMMs(P.Y - Lib.Board.YOrigin)) + '  mode ' + IntToStr(P.Mode) +
                 '  top ' + FloatToStr(CoordToMMs(P.TopXSize)) + 'x' + FloatToStr(CoordToMMs(P.TopYSize)) +
                 '  mid ' + FloatToStr(CoordToMMs(P.MidXSize)) + 'x' + FloatToStr(CoordToMMs(P.MidYSize)) +
                 '  bot ' + FloatToStr(CoordToMMs(P.BotXSize)) + 'x' + FloatToStr(CoordToMMs(P.BotYSize)) +
                 '  hole ' + FloatToStr(CoordToMMs(P.HoleSize)) + ' type ' + IntToStr(P.HoleType) +
                 '  plated ' + BoolToStr(P.Plated, True);
        P := GIt.NextPCBObject;
    End;
    Fp.GroupIterator_Destroy(GIt);
    ShowMessage(S);
End;

Procedure FixX1LibFootprint;
Var
    Lib  : IPCB_Library;
    Fp   : IPCB_LibComponent;
    GIt  : IPCB_GroupIterator;
    P    : IPCB_Pad;
    Pads : TInterfaceList;
    I    : Integer;
    X, Y : Double;
Begin
    Lib := ProdLibOrNil;
    If Lib = Nil Then Exit;
    Fp := FindFp(Lib);
    If Fp = Nil Then Begin ShowMessage(FP_NAME + ' not found in the library.'); Exit; End;

    Pads := TInterfaceList.Create;
    GIt := Fp.GroupIterator_Create;
    GIt.AddFilter_ObjectSet(MkSet(ePadObject));
    P := GIt.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = 'MS1') Or (P.Name = 'MS2') Then Pads.Add(P);
        P := GIt.NextPCBObject;
    End;
    Fp.GroupIterator_Destroy(GIt);

    If Pads.Count <> 2 Then
    Begin
        ShowMessage('Expected exactly MS1 and MS2, found ' + IntToStr(Pads.Count));
        Pads.Free;
        Exit;
    End;
    For I := 0 To 1 Do
    Begin
        P := Pads.Items[I];
        X := CoordToMMs(P.X);
        Y := CoordToMMs(P.Y);
        If Not LNear(Abs(X), 3.5001) Or Not LNear(Y, 2.70) Or (P.HoleType <> eRoundHole) Or
           Not LNear(CoordToMMs(P.HoleSize), 0.5999) Or Not LNear(CoordToMMs(P.BotYSize), 0.8999) Or Not P.Plated Then
        Begin
            ShowMessage(P.Name + ' is not in the guarded pre-fix state (round 0.60 hole, 0.90 land at +/-3.50, 2.70).' +
                #13#10 + 'at ' + FloatToStr(X) + ', ' + FloatToStr(Y) + ' hole type ' + IntToStr(P.HoleType));
            Pads.Free;
            Exit;
        End;
    End;

    PCBServer.PreProcess;
    For I := 0 To 1 Do
    Begin
        P := Pads.Items[I];
        P.BeginModify;
        P.Mode := ePadMode_LocalStack;
        P.TopShape := eRounded; P.MidShape := eRounded; P.BotShape := eRounded;
        P.TopXSize := MMsToCoord(OUT_W); P.TopYSize := MMsToCoord(OUT_H);
        P.MidXSize := MMsToCoord(IN_W);  P.MidYSize := MMsToCoord(IN_H);
        P.BotXSize := MMsToCoord(OUT_W); P.BotYSize := MMsToCoord(OUT_H);
        P.HoleType := eSlotHole;
        P.HoleSize := MMsToCoord(0.60);
        P.HoleWidth := MMsToCoord(1.30);
        P.HoleRotation := 90;
        P.EndModify;
    End;
    PCBServer.PostProcess;
    Pads.Free;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage(FP_NAME + ': MS1/MS2 are now plated 0.60 x 1.30 slots (rotation 90),' + #13#10 +
        'lands ' + FloatToStr(OUT_W) + ' x ' + FloatToStr(OUT_H) + ' (top/bottom) and ' + FloatToStr(IN_W) + ' x ' +
        FloatToStr(IN_H) + ' (inner).' + #13#10 + 'Save zulu_a7.PcbLib.');
End;
