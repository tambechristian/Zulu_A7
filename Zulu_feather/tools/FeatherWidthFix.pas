{ FeatherWidthFix.pas -- 2026-10-24, stage 2: widens every power track that is under its net's minimum on its layer
  (the board's Width rules, per layer; Freerouting run 5 left 21 such tracks). Tracks are only widened, never moved;
  re-run the DRC afterwards for clearance. Run WidenPowerTracks with zulu_feather.PcbDoc focused.
    VCC3V3            Top 0.0762, L3/L4 1.05, Bottom 0.2
    VU USB5V0 VBATT   Top/Bottom 0.2, L3/L4 1.1
    VCC1V0            Top/Bottom 0.15, L3/L4 0.5
    NetL1_1..NetL3_1  0.2 (PWR_SWITCH)
    VCC1V8 VCCADC FT-VCORE FT-VPHY FT-VPLL  0.15 (PWR_RAILS) }

Function MinWidth(Net : String; L : TLayer) : Double;
Var
    Inner : Boolean;
Begin
    Result := 0;
    Inner := (L = eMidLayer1) Or (L = eMidLayer2);
    If Net = 'VCC3V3' Then
    Begin
        If Inner Then Result := 1.05 Else If L = eBottomLayer Then Result := 0.2;
    End
    Else If (Net = 'VU') Or (Net = 'USB5V0') Or (Net = 'VBATT') Then
    Begin
        If Inner Then Result := 1.1 Else Result := 0.2;
    End
    Else If Net = 'VCC1V0' Then
    Begin
        If Inner Then Result := 0.5 Else Result := 0.15;
    End
    Else If (Net = 'NetL1_1') Or (Net = 'NetL2_1') Or (Net = 'NetL3_1') Then
        Result := 0.2
    Else If (Net = 'VCC1V8') Or (Net = 'VCCADC') Or (Net = 'FT-VCORE') Or (Net = 'FT-VPHY') Or (Net = 'FT-VPLL') Then
        Result := 0.15;
End;

Procedure WidenPowerTracks;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    T   : IPCB_Track;
    L   : TInterfaceList;
    I, N : Integer;
    W   : Double;
    Log : TStringList;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    Log := TStringList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopLayer, eMidLayer1, eMidLayer2, eBottomLayer));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If T.Net <> Nil Then
        Begin
            W := MinWidth(T.Net.Name, T.Layer);
            If (W > 0) And (T.Width < MMsToCoord(W) - 10) Then L.Add(T);
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    N := 0;
    For I := 0 To L.Count - 1 Do
    Begin
        T := L.Items[I];
        W := MinWidth(T.Net.Name, T.Layer);
        Log.Add('  ' + T.Net.Name + ' ' + FloatToStr(CoordToMMs(T.Width)) + ' -> ' + FloatToStr(W) + ' mm');
        T.BeginModify;
        T.Width := MMsToCoord(W);
        T.EndModify;
        N := N + 1;
    End;
    L.Free;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Widened ' + IntToStr(N) + ' power track(s).' + #13#10 + Log.Text + 'Repour, save, then re-run the DRC.');
    Log.Free;
End;
