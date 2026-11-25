{ NoPmodDrc20Silk.pas -- GENERATED 2026-11-19 from tools/route/drc20/silk_plan.json (tools/route/drc20/silk.py).
  Clears the Silk To Solder Mask and Minimum Solder Mask Sliver items of the 2026-11-19 DRC:
    FixSilk     moves the ends of 10 overlay lines (U2 corner marks x8, X4 pin-1 line, U10 bottom pin-1 mark).
                Refuses unless all 10 are found exactly (layer, width, ends either way round within 0.002 mm).
    AddU2Mask   adds SolderMaskExpansion_U2, InComponent(U2), 0.035 mm (as Asars FeatherMask.pas): the QFN
                corner webs go from 0.085 to 0.115 mm. Priority is read-only from scripts: read Rules6 back. }

Function FBrd : IPCB_Board;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If (Result = Nil) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Result.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Result := Nil;
    End;
End;

Function Hit(K : IPCB_Track; Brd : IPCB_Board; L : TLayer; W, X1, Y1, X2, Y2 : Double) : Boolean;
Var
    a, b, c, d : Double;
Begin
    Result := False;
    If K.Layer <> L Then Exit;
    If Abs(CoordToMMs(K.Width) - W) > 0.002 Then Exit;
    a := CoordToMMs(K.X1 - Brd.XOrigin); b := CoordToMMs(K.Y1 - Brd.YOrigin);
    c := CoordToMMs(K.X2 - Brd.XOrigin); d := CoordToMMs(K.Y2 - Brd.YOrigin);
    Result := ((Abs(a - X1) < 0.002) And (Abs(b - Y1) < 0.002) And (Abs(c - X2) < 0.002) And (Abs(d - Y2) < 0.002)) Or
              ((Abs(a - X2) < 0.002) And (Abs(b - Y2) < 0.002) And (Abs(c - X1) < 0.002) And (Abs(d - Y1) < 0.002));
End;

Procedure FixSilk;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    K : IPCB_Track;
    Kill : TInterfaceList;
    c0, c1, c2, c3, c4, c5, c6, c7, c8, c9 : Integer;
    i : Integer;
    Msg : String;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    c0 := 0; c1 := 0; c2 := 0; c3 := 0; c4 := 0; c5 := 0; c6 := 0; c7 := 0; c8 := 0; c9 := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay, eBottomOverlay));
    It.AddFilter_Method(eProcessAll);
    K := It.FirstPCBObject;
    While K <> Nil Do
    Begin
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 9.9500, 26.3500, 9.9500) Then c0 := c0 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 9.9500, 25.9000, 10.4000) Then c1 := c1 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 19.1500, 26.3500, 19.1500) Then c2 := c2 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 18.7000, 25.9000, 19.1500) Then c3 := c3 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 34.6500, 9.9500, 35.1000, 9.9500) Then c4 := c4 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 35.1000, 9.9500, 35.1000, 10.4000) Then c5 := c5 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 34.6500, 19.1500, 35.1000, 19.1500) Then c6 := c6 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 35.1000, 18.7000, 35.1000, 19.1500) Then c7 := c7 + 1;
        If Hit(K, Brd, eTopOverlay, 0.1500, 29.5400, 8.6500, 29.5400, 9.5000) Then c8 := c8 + 1;
        If Hit(K, Brd, eBottomOverlay, 0.1500, 21.8851, 18.1950, 21.8851, 18.4950) Then c9 := c9 + 1;
        K := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (c0 <> 1) Or (c1 <> 1) Or (c2 <> 1) Or (c3 <> 1) Or (c4 <> 1) Or (c5 <> 1) Or (c6 <> 1) Or (c7 <> 1) Or (c8 <> 1) Or (c9 <> 1) Then
    Begin
        ShowMessage('Refusing: each of the 10 overlay lines must be found exactly once (counts ' + IntToStr(c0) + ',' + IntToStr(c1) + ',' + IntToStr(c2) + ',' + IntToStr(c3) + ',' + IntToStr(c4) + ',' + IntToStr(c5) + ',' + IntToStr(c6) + ',' + IntToStr(c7) + ',' + IntToStr(c8) + ',' + IntToStr(c9) + '); nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay, eBottomOverlay));
    It.AddFilter_Method(eProcessAll);
    K := It.FirstPCBObject;
    While K <> Nil Do
    Begin
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 9.9500, 26.3500, 9.9500) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(25.9000); K.Y1 := Brd.YOrigin + MMsToCoord(9.9500);
            K.X2 := Brd.XOrigin + MMsToCoord(26.2500); K.Y2 := Brd.YOrigin + MMsToCoord(9.9500);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 9.9500, 25.9000, 10.4000) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(25.9000); K.Y1 := Brd.YOrigin + MMsToCoord(9.9500);
            K.X2 := Brd.XOrigin + MMsToCoord(25.9000); K.Y2 := Brd.YOrigin + MMsToCoord(10.3000);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 19.1500, 26.3500, 19.1500) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(25.9000); K.Y1 := Brd.YOrigin + MMsToCoord(19.1500);
            K.X2 := Brd.XOrigin + MMsToCoord(26.2500); K.Y2 := Brd.YOrigin + MMsToCoord(19.1500);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 25.9000, 18.7000, 25.9000, 19.1500) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(25.9000); K.Y1 := Brd.YOrigin + MMsToCoord(18.8000);
            K.X2 := Brd.XOrigin + MMsToCoord(25.9000); K.Y2 := Brd.YOrigin + MMsToCoord(19.1500);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 34.6500, 9.9500, 35.1000, 9.9500) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(34.7500); K.Y1 := Brd.YOrigin + MMsToCoord(9.9500);
            K.X2 := Brd.XOrigin + MMsToCoord(35.1000); K.Y2 := Brd.YOrigin + MMsToCoord(9.9500);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 35.1000, 9.9500, 35.1000, 10.4000) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(35.1000); K.Y1 := Brd.YOrigin + MMsToCoord(9.9500);
            K.X2 := Brd.XOrigin + MMsToCoord(35.1000); K.Y2 := Brd.YOrigin + MMsToCoord(10.3000);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 34.6500, 19.1500, 35.1000, 19.1500) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(34.7500); K.Y1 := Brd.YOrigin + MMsToCoord(19.1500);
            K.X2 := Brd.XOrigin + MMsToCoord(35.1000); K.Y2 := Brd.YOrigin + MMsToCoord(19.1500);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 35.1000, 18.7000, 35.1000, 19.1500) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(35.1000); K.Y1 := Brd.YOrigin + MMsToCoord(18.8000);
            K.X2 := Brd.XOrigin + MMsToCoord(35.1000); K.Y2 := Brd.YOrigin + MMsToCoord(19.1500);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eTopOverlay, 0.1500, 29.5400, 8.6500, 29.5400, 9.5000) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(29.5400); K.Y1 := Brd.YOrigin + MMsToCoord(8.6500);
            K.X2 := Brd.XOrigin + MMsToCoord(29.5400); K.Y2 := Brd.YOrigin + MMsToCoord(9.3500);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        If Hit(K, Brd, eBottomOverlay, 0.1500, 21.8851, 18.1950, 21.8851, 18.4950) Then
        Begin
            K.BeginModify;
            K.X1 := Brd.XOrigin + MMsToCoord(21.1500); K.Y1 := Brd.YOrigin + MMsToCoord(18.6000);
            K.X2 := Brd.XOrigin + MMsToCoord(21.6000); K.Y2 := Brd.YOrigin + MMsToCoord(18.6000);
            K.EndModify;
            K.GraphicallyInvalidate;
            Kill.Add(K);
        End;
        K := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    Msg := '';
    For i := 0 To Kill.Count - 1 Do
    Begin
        K := Kill.Items[i];
        Msg := Msg + FormatFloat('0.000', CoordToMMs(K.X1 - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(K.Y1 - Brd.YOrigin)) + ' - ' + FormatFloat('0.000', CoordToMMs(K.X2 - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(K.Y2 - Brd.YOrigin)) + #13#10;
    End;
    ShowMessage(IntToStr(Kill.Count) + ' overlay lines moved (expected 10):' + #13#10 + Msg + 'Run AddU2Mask next, then save.');
    Kill.Free;
End;

Procedure AddU2Mask;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    R : IPCB_Rule;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = 'SolderMaskExpansion_U2' Then
        Begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('SolderMaskExpansion_U2 already exists; no change made.');
            Exit;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    R := PCBServer.PCBRuleFactory(eRule_SolderMaskExpansion);
    R.Name := 'SolderMaskExpansion_U2';
    R.Scope1Expression := 'InComponent(''U2'')';
    R.Scope2Expression := 'All';
    R.Expansion := MMsToCoord(0.035);
    R.NetScope := eNetScope_AnyNet;
    R.LayerKind := eRuleLayerKind_SameLayer;
    Brd.AddPCBObject(R);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Added SolderMaskExpansion_U2 (U2 pads, 0.035 mm). Save, then re-run the DRC.');
End;
