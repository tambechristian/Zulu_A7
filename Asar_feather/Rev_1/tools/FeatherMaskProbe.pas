{ FeatherMaskProbe.pas -- read-only: what mask expansion U2's corner pads actually get, and from where. }

Procedure ProbeU2Mask;
Var
    Brd : IPCB_Board;
    C   : IPCB_Component;
    It  : IPCB_GroupIterator;
    P   : IPCB_Pad;
    R   : IPCB_Rule;
    S   : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    C := Brd.GetPcbComponentByRefDes('U2');
    S := '';
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = '48') Or (P.Name = '49') Or (P.Name = '1') Then
        Begin
            R := Brd.FindDominantRuleForObject(P, eRule_SolderMaskExpansion);
            S := S + 'pad ' + P.Name + ': dominant rule ';
            If R = Nil Then S := S + '(none)' Else S := S + R.Name;
            S := S + ', cache valid ' + IntToStr(P.Cache.SolderMaskExpansionValid) +
                 ', cache value ' + FloatToStr(CoordToMMs(P.Cache.SolderMaskExpansion)) + ' mm' + #13#10;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    ShowMessage(S + '(eCacheInvalid=0, eCacheValid=1, eCacheManual=2)');
End;
