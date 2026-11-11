{ FeatherFixC3Mask.pas -- 2026-10-25, after FeatherFixStage4.pas: SolderMaskExpansion_C3 at 0.035 mm left a web of
  exactly 0.100 mm to X3 (X3 keeps the board-wide 0.05 mm), which the DRC still flags. 0.02 mm leaves 0.115 mm.
  Run SetC3Mask with asar_feather.PcbDoc focused. }

Procedure SetC3Mask;
Var
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    R   : IPCB_Rule;
    C   : IPCB_Component;
    GI  : IPCB_GroupIterator;
    P   : IPCB_Pad;
    Ch  : TPadCache;
    N   : Integer;
    Found : Boolean;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    Found := False;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = 'SolderMaskExpansion_C3' Then
        Begin
            R.BeginModify;
            R.Expansion := MMsToCoord(0.02);
            R.EndModify;
            Found := True;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Not Found Then
    Begin
        ShowMessage('SolderMaskExpansion_C3 not found; nothing changed.');
        Exit;
    End;
    C := Brd.GetPcbComponentByRefDes('C3');
    N := 0;
    GI := C.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    P := GI.FirstPCBObject;
    While P <> Nil Do
    Begin
        Ch := P.Cache;
        Ch.SolderMaskExpansionValid := eCacheInvalid;
        P.BeginModify;
        P.Cache := Ch;
        P.EndModify;
        N := N + 1;
        P := GI.NextPCBObject;
    End;
    C.GroupIterator_Destroy(GI);
    Brd.ViewManager_FullUpdate;
    ShowMessage('SolderMaskExpansion_C3 set to 0.02 mm, ' + IntToStr(N) + ' C3 pad caches invalidated. Save, then re-run the DRC.');
End;
