{ FeatherMaskCache.pas -- 2026-10-23, second step after FeatherMask.pas. ProbeU2Mask (FeatherMaskProbe.pas) showed
  SolderMaskExpansion_U2 is the dominant rule for U2's pads, but each pad's cache still held 0.05 mm marked valid,
  and the DRC uses the cache. RefreshU2Mask marks U2's pad solder-mask caches invalid so they are recomputed from
  the rule, then reports the recomputed value. }

Procedure RefreshU2Mask;
Var
    Brd : IPCB_Board;
    C   : IPCB_Component;
    It  : IPCB_GroupIterator;
    P   : IPCB_Pad;
    Ch  : TPadCache;
    N   : Integer;
    S   : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    C := Brd.GetPcbComponentByRefDes('U2');
    N := 0;
    S := '';
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Cache.SolderMaskExpansionValid <> eCacheManual Then
        Begin
            Ch := P.Cache;
            Ch.SolderMaskExpansionValid := eCacheInvalid;
            P.BeginModify;
            P.Cache := Ch;
            P.EndModify;
            N := N + 1;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = '1') Or (P.Name = '48') Then
            S := S + 'pad ' + P.Name + ': cache valid ' + IntToStr(P.Cache.SolderMaskExpansionValid) + ', value ' +
                 FloatToStr(CoordToMMs(P.Cache.SolderMaskExpansion)) + ' mm' + #13#10;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    Brd.ViewManager_FullUpdate;
    ShowMessage(IntToStr(N) + ' U2 pad caches invalidated.' + #13#10 + S + 'Save, then re-run the DRC.');
End;
