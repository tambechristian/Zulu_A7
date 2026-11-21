{ NoPmodU2MaskCache.pas -- 2026-11-19, after NoPmodDrc20Silk.pas AddU2Mask: the new SolderMaskExpansion_U2 rule
  (0.035 mm, priority 1) did not reach U2's pads -- the DRC still measured the 0.05 mm opening (0.085 mm corner webs),
  because each pad caches its mask expansion. Invalidates that cache on U2's pads (as Asar's FeatherFixC3Mask.pas).
  Run InvalidateU2Mask with Zulu_a7_no_pmod.PcbDoc focused, then save and re-run the DRC. }
Procedure InvalidateU2Mask;
Var
    Brd : IPCB_Board;
    C   : IPCB_Component;
    GI  : IPCB_GroupIterator;
    P   : IPCB_Pad;
    Ch  : TPadCache;
    N   : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    C := Brd.GetPcbComponentByRefDes('U2');
    If C = Nil Then
    Begin
        ShowMessage('Refusing: U2 not found.');
        Exit;
    End;
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
    ShowMessage(IntToStr(N) + ' U2 pad mask caches invalidated (65 expected). Save, then re-run the DRC.');
End;
