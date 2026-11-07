{ FeatherLibX5Silk3.pas -- 2026-11-06: LibX5Silk2 trimmed the side lines of JST-SM04B-SRSS-TB, but its RemovePCBObject on the two
  rear corner segments did not survive the save: that footprint was not the current one in the editor. This makes it current
  first, removes the two corners and counts the tracks afterwards.
  Run LibX5Silk3 with asar_feather.PcbLib focused, then File > Save. }

Procedure LibX5Silk3;
Var
    Doc  : IDocument;
    Lib  : IPCB_Library;
    It   : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI   : IPCB_GroupIterator;
    T    : IPCB_Track;
    Kill : TInterfaceList;
    N, I : Integer;
    OY, MaxY : Double;
    Log  : String;
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
        ShowMessage('Refusing: footprint not found.');
        Exit;
    End;
    Lib.CurrentComponent := Hit;
    MaxY := -100000;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    T := GI.FirstPCBObject;
    While T <> Nil Do
    Begin
        If CoordToMMs(T.Y1) > MaxY Then MaxY := CoordToMMs(T.Y1);
        If CoordToMMs(T.Y2) > MaxY Then MaxY := CoordToMMs(T.Y2);
        T := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    OY := MaxY - 2.75;
    Kill := TInterfaceList.Create;
    N := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    T := GI.FirstPCBObject;
    While T <> Nil Do
    Begin
        N := N + 1;
        If (Abs(CoordToMMs(T.Y1) - OY - 2.18) < 0.01) And (Abs(CoordToMMs(T.Y2) - OY - 2.18) < 0.01) Then Kill.Add(T);
        T := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    Log := IntToStr(N) + ' tracks, ' + IntToStr(Kill.Count) + ' corners. ';
    If Kill.Count <> 2 Then
    Begin
        ShowMessage('Refusing: ' + Log + 'Expected 2 corners. Nothing changed.');
        Kill.Free;
        Exit;
    End;
    For I := 0 To 1 Do Hit.RemovePCBObject(Kill.Items[I]);
    Kill.Free;
    N := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    T := GI.FirstPCBObject;
    While T <> Nil Do
    Begin
        N := N + 1;
        T := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    Log := Log + 'After the removal ' + IntToStr(N) + ' tracks. ';
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage(Log + 'Save the library.');
End;
