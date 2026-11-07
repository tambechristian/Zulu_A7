{ FeatherLibX5Silk2.pas -- 2026-11-06 (the first version compared raw coordinates; in the library editor they carry an offset, so it refused and changed nothing): footprint JST-SM04B-SRSS-TB in asar_feather.PcbLib, silk as tools/footprints.py now has it.
  The review found the rear of the outline 0.025 mm into BTN's mask clearance and 0.10 mm from U4's silk on the board. The
  two rear corner segments go and the two side lines end at y = 1.25. Pads are untouched. Refuses unless the footprint still
  has the six tracks as first drawn, so it runs once.
  Run LibX5Silk2 with asar_feather.PcbLib focused, then File > Save. }

Procedure LibX5Silk2;
Var
    Doc  : IDocument;
    Lib  : IPCB_Library;
    It   : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI   : IPCB_GroupIterator;
    T    : IPCB_Track;
    Kill, Side : TInterfaceList;
    N, I : Integer;
    OX, OY : Double;
    Cnt, MaxX, MinX, MaxY : Double;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbLib', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbLib first.');
        Exit;
    End;
    Lib := PCBServer.GetCurrentPCBLibrary;
    Hit := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = 'JST-SM04B-SRSS-TB' Then Hit := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Hit = Nil Then
    Begin
        ShowMessage('Refusing: footprint JST-SM04B-SRSS-TB not found.');
        Exit;
    End;
    Kill := TInterfaceList.Create;
    Side := TInterfaceList.Create;
    { the silk spans x -3..3 and tops out at the pin-1 tick, y = 2.75: that gives the editor's offset }
    Cnt := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    T := GI.FirstPCBObject;
    While T <> Nil Do
    Begin
        If Cnt = 0 Then
        Begin
            MinX := CoordToMMs(T.X1);
            MaxX := MinX;
            MaxY := CoordToMMs(T.Y1);
        End;
        Cnt := Cnt + 1;
        If CoordToMMs(T.X1) < MinX Then MinX := CoordToMMs(T.X1);
        If CoordToMMs(T.X2) < MinX Then MinX := CoordToMMs(T.X2);
        If CoordToMMs(T.X1) > MaxX Then MaxX := CoordToMMs(T.X1);
        If CoordToMMs(T.X2) > MaxX Then MaxX := CoordToMMs(T.X2);
        If CoordToMMs(T.Y1) > MaxY Then MaxY := CoordToMMs(T.Y1);
        If CoordToMMs(T.Y2) > MaxY Then MaxY := CoordToMMs(T.Y2);
        T := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    OX := (MinX + MaxX) / 2;
    OY := MaxY - 2.75;
    N := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    T := GI.FirstPCBObject;
    While T <> Nil Do
    Begin
        N := N + 1;
        If (Abs(CoordToMMs(T.Y1) - OY - 2.18) < 0.01) And (Abs(CoordToMMs(T.Y2) - OY - 2.18) < 0.01) Then Kill.Add(T);
        If (Abs(Abs(CoordToMMs(T.X1) - OX) - 3.0) < 0.01) And (Abs(Abs(CoordToMMs(T.X2) - OX) - 3.0) < 0.01) Then Side.Add(T);
        T := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (N <> 6) Or (Kill.Count <> 2) Or (Side.Count <> 2) Then
    Begin
        ShowMessage('Refusing: ' + IntToStr(N) + ' tracks, ' + IntToStr(Kill.Count) + ' corners, ' + IntToStr(Side.Count) +
                    ' side lines; expected 6, 2, 2 (offset ' + FloatToStr(OX) + ', ' + FloatToStr(OY) + '). Nothing changed.');
        Kill.Free;
        Side.Free;
        Exit;
    End;
    PCBServer.PreProcess;
    For I := 0 To 1 Do
    Begin
        T := Side.Items[I];
        T.BeginModify;
        T.Y2 := MMsToCoord(OY + 1.25);
        T.EndModify;
    End;
    For I := 0 To 1 Do Hit.RemovePCBObject(Kill.Items[I]);
    PCBServer.PostProcess;
    Kill.Free;
    Side.Free;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('JST-SM04B-SRSS-TB silk: 2 corners removed, 2 side lines end at y = 1.25. Save the library.');
End;
