{ X2PowerPins.pas -- 2026-10-07, both Altium copies (Zulu_Altium_VS_Code and Zulu_Altium_VS_Code_HDI_Optimized).
  The X2 prototyping header's power pins at the end of the top row are re-ordered (schematic: tools/x2_power_pins.py):
      before  17 VCC3V3, 18 VCC1V8, 19 VCC1V0, 20 GND
      after   17 GND,    18 VCC3V3, 19 VCC1V8, 20 VCC1V0      (pin 16 CHAN13 unchanged)
  This script:
    1. re-nets the four pads (P.Net plus Net.AddPCBObject, or the net does not save);
    2. moves the VCC1V8 L3 stub from pin 18 (x 6.35) to pin 19 (x 3.81); the L3 trunk at y 23.05 already passes there;
    3. extends the VCC1V0 Bottom run at y 23.05 west from x 3.81 to 1.27 and moves its stub from pin 19 to pin 20.
  GND (pin 17) and VCC3V3 (pin 18) reach their pads through the L2 and L5 planes, so re-pour all polygons afterwards,
  then run DRC and save.
  Run X2PinsCanary first (reads only), then FixX2PowerPins. }

Const
    Y_ROW  = 24.13;
    Y_RUN  = 23.05;

Var
    GV18Stub : IPCB_Track;
    GV10Stub : IPCB_Track;
    GV10Run  : IPCB_Track;

Function PNear(A, B : Double) : Boolean;
Begin
    Result := Abs(A - B) < 0.001;
End;

Function DocOk : Boolean;
Var
    WS  : IWorkspace;
    Doc : IDocument;
    P   : String;
Begin
    Result := False;
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    Doc := WS.DM_FocusedDocument;
    If Doc = Nil Then Exit;
    P := Doc.DM_FullPath;
    If (Pos('\Zulu_Altium_VS_Code\Imported zulu_a7.PrjPcb\zulu_a7.PcbDoc', P) = 0) And
       (Pos('\Zulu_Altium_VS_Code_HDI_Optimized\Imported zulu_a7.PrjPcb\zulu_a7_hdi_optimized.PcbDoc', P) = 0) Then
    Begin
        ShowMessage('Refusing to modify the focused document:' + #13#10 + P);
        Exit;
    End;
    Result := True;
End;

Function FindPin(Brd : IPCB_Board; AName : String) : IPCB_Pad;
Var
    Comp : IPCB_Component;
    It   : IPCB_GroupIterator;
    P    : IPCB_Pad;
Begin
    Result := Nil;
    Comp := Brd.GetPcbComponentByRefDes('X2');
    If Comp = Nil Then Exit;
    It := Comp.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = AName Then Result := P;
        P := It.NextPCBObject;
    End;
    Comp.GroupIterator_Destroy(It);
End;

Function NetName(P : IPCB_Pad) : String;
Begin
    If P.Net = Nil Then Result := '(none)' Else Result := P.Net.Name;
End;

Function PinOk(P : IPCB_Pad; AX : Double; ANet : String) : Boolean;
Begin
    Result := (P <> Nil) And PNear(CoordToMMs(P.X), AX) And PNear(CoordToMMs(P.Y), Y_ROW) And (NetName(P) = ANet);
End;

Function SameTrk(T : IPCB_Track; L : TLayer; AX, AY, BX, BY : Double) : Boolean;
Var
    X1, Y1, X2, Y2 : Double;
Begin
    Result := False;
    If T.Layer <> L Then Exit;
    X1 := CoordToMMs(T.X1); Y1 := CoordToMMs(T.Y1); X2 := CoordToMMs(T.X2); Y2 := CoordToMMs(T.Y2);
    Result := (PNear(X1, AX) And PNear(Y1, AY) And PNear(X2, BX) And PNear(Y2, BY)) Or
              (PNear(X1, BX) And PNear(Y1, BY) And PNear(X2, AX) And PNear(Y2, AY));
End;

Procedure SetTrk(T : IPCB_Track; AX, AY, BX, BY : Double);
Begin
    T.BeginModify;
    T.X1 := MMsToCoord(AX); T.Y1 := MMsToCoord(AY);
    T.X2 := MMsToCoord(BX); T.Y2 := MMsToCoord(BY);
    T.EndModify;
End;

Procedure SetPadNet(P : IPCB_Pad; N : IPCB_Net);
Begin
    P.BeginModify;
    P.Net := N;
    N.AddPCBObject(P);
    P.EndModify;
End;

Procedure FindTracks(Brd : IPCB_Board);
Var
    It : IPCB_BoardIterator;
    T  : IPCB_Track;
Begin
    GV18Stub := Nil; GV10Stub := Nil; GV10Run := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If T.Net <> Nil Then
        Begin
            If (T.Net.Name = 'VCC1V8') And SameTrk(T, eMidLayer1, 6.35, Y_RUN, 6.35, Y_ROW) Then GV18Stub := T;
            If (T.Net.Name = 'VCC1V0') And SameTrk(T, eBottomLayer, 3.81, Y_RUN, 3.81, Y_ROW) Then GV10Stub := T;
            If (T.Net.Name = 'VCC1V0') And SameTrk(T, eBottomLayer, 3.81, Y_RUN, 15.30, Y_RUN) Then GV10Run := T;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure X2PinsCanary;
Var
    Brd : IPCB_Board;
    P   : IPCB_Pad;
    S   : String;
    I   : Integer;
Begin
    If Not DocOk Then Exit;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    S := 'X2 pins:';
    For I := 16 To 20 Do
    Begin
        P := FindPin(Brd, IntToStr(I));
        If P = Nil Then S := S + #13#10 + IntToStr(I) + ' not found'
        Else S := S + #13#10 + IntToStr(I) + ' ' + NetName(P) + ' at ' + FloatToStr(CoordToMMs(P.X)) + ', ' + FloatToStr(CoordToMMs(P.Y));
    End;
    FindTracks(Brd);
    S := S + #13#10 + 'VCC1V8 L3 stub found: ' + BoolToStr(GV18Stub <> Nil, True) +
         #13#10 + 'VCC1V0 Bottom stub found: ' + BoolToStr(GV10Stub <> Nil, True) +
         #13#10 + 'VCC1V0 Bottom run found: ' + BoolToStr(GV10Run <> Nil, True);
    ShowMessage(S);
End;

Procedure FixX2PowerPins;
Var
    Brd : IPCB_Board;
    P17, P18, P19, P20 : IPCB_Pad;
    NGnd, N33, N18, N10 : IPCB_Net;
Begin
    If Not DocOk Then Exit;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    P17 := FindPin(Brd, '17'); P18 := FindPin(Brd, '18'); P19 := FindPin(Brd, '19'); P20 := FindPin(Brd, '20');
    If Not (PinOk(P17, 8.89, 'VCC3V3') And PinOk(P18, 6.35, 'VCC1V8') And PinOk(P19, 3.81, 'VCC1V0') And PinOk(P20, 1.27, 'GND')) Then
    Begin
        ShowMessage('X2-17..20 are not in the guarded state (17 VCC3V3, 18 VCC1V8, 19 VCC1V0, 20 GND at y 24.13); already changed?');
        Exit;
    End;
    FindTracks(Brd);
    If (GV18Stub = Nil) Or (GV10Stub = Nil) Or (GV10Run = Nil) Then
    Begin
        ShowMessage('The guarded VCC1V8 / VCC1V0 tracks at X2-18/19 were not found; nothing changed.');
        Exit;
    End;
    N33 := P17.Net; N18 := P18.Net; N10 := P19.Net; NGnd := P20.Net;

    PCBServer.PreProcess;
    SetPadNet(P17, NGnd);
    SetPadNet(P18, N33);
    SetPadNet(P19, N18);
    SetPadNet(P20, N10);
    SetTrk(GV18Stub, 3.81, Y_RUN, 3.81, Y_ROW);
    SetTrk(GV10Run, 1.27, Y_RUN, 15.30, Y_RUN);
    SetTrk(GV10Stub, 1.27, Y_RUN, 1.27, Y_ROW);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('X2: 17 ' + NetName(P17) + ', 18 ' + NetName(P18) + ', 19 ' + NetName(P19) + ', 20 ' + NetName(P20) + #13#10 +
        'VCC1V8 stub moved to pin 19 (L3); VCC1V0 run extended to pin 20 (Bottom).' + #13#10 +
        'Re-pour all polygons, run DRC, then save.');
End;
