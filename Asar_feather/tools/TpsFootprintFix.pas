{ TpsFootprintFix.pas -- 2026-11-09. Fix-up of VSON10-DLA0010A after the placement check: the two body-edge silk lines
  (y = +-1.60) break silk-to-mask (0.254) and component clearance against the input/output caps in any compact layout,
  and the pin-1 tick at x -1.55 sat 0.225 from pad 1's mask opening. This deletes the two edge lines and moves the tick to
  x -1.60 (0.275 from pad 1's opening). Run FixTpsFootprint with asar_feather.PcbLib or the Fab B zulu_a7.PcbLib focused,
  then File > Save, then PCB Library panel > right-click VSON10-DLA0010A > Update PCB With VSON10-DLA0010A. }

Procedure FixTpsFootprint;
Var
    Doc : IDocument;
    Lib : IPCB_Library;
    It : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI : IPCB_GroupIterator;
    O : IPCB_Primitive;
    Kill : TInterfaceList;
    T : IPCB_Track;
    i, nTick : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or ((Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbLib', Doc.DM_FullPath) = 0) And
       (Pos('\Zulu_A7_Fab_B\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib', Doc.DM_FullPath) = 0)) Then
    Begin
        ShowMessage('Refusing: focus asar_feather.PcbLib or the Fab B zulu_a7.PcbLib first.');
        Exit;
    End;
    Lib := PCBServer.GetCurrentPCBLibrary;
    Hit := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = 'VSON10-DLA0010A' Then Hit := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Hit = Nil Then
    Begin
        ShowMessage('VSON10-DLA0010A not found; nothing changed.');
        Exit;
    End;
    Kill := TInterfaceList.Create;
    nTick := 0;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        T := O;
        If T.Layer = eTopOverlay Then
        Begin
            If (T.Y1 = T.Y2) And (Abs(Abs(CoordToMMs(T.Y1)) - 1.60) < 0.001) Then
                Kill.Add(T)
            Else If (T.X1 = T.X2) And (Abs(CoordToMMs(T.X1) + 1.55) < 0.001) Then
            Begin
                T.BeginModify;
                T.X1 := MMsToCoord(-1.60);
                T.X2 := MMsToCoord(-1.60);
                T.EndModify;
                nTick := nTick + 1;
            End;
        End;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do Hit.RemovePCBObject(Kill.Items[i]);
    PCBServer.PostProcess;
    Lib.CurrentComponent := Hit;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('VSON10-DLA0010A: removed ' + IntToStr(Kill.Count) + ' edge silk lines (expect 2), moved ' + IntToStr(nTick) +
        ' pin-1 tick (expect 1). Save the library.');
    Kill.Free;
End;
