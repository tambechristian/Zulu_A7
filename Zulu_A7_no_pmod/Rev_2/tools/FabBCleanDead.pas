Procedure CleanDeadCopperFB;
Var
    Brd : IPCB_Board; It : IPCB_BoardIterator; O : IPCB_Primitive; KT, KV, KF : TInterfaceList; i : Integer; L : TLayer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit;
    If Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc'); Exit; End;
    KT := TInterfaceList.Create; KV := TInterfaceList.Create; KF := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eViaObject, eFillObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If O.ObjectId = eTrackObject Then
        Begin
            L := O.Layer;
            If (O.Net = Nil) And (Not O.InComponent) And (Not O.InPolygon) And (Not O.IsKeepout) And
               ((L = eTopLayer) Or (L = eBottomLayer) Or (L = eMidLayer1) Or (L = eMidLayer2)) Then KT.Add(O);
        End
        Else If O.ObjectId = eViaObject Then
        Begin
            If (O.Net = Nil) And (Not O.InComponent) Then KV.Add(O);
        End
        Else If O.ObjectId = eFillObject Then
        Begin
            If O.IsKeepout And (O.Layer = eTopLayer) And (Not O.InComponent) Then KF.Add(O);
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (KT.Count <> 87) Or (KV.Count <> 9) Or (KF.Count <> 2) Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(KT.Count) + ' dead tracks (87), ' + IntToStr(KV.Count) + ' no-net vias (9), ' + IntToStr(KF.Count) + ' Top keepout fills (2); nothing changed.');
        KT.Free; KV.Free; KF.Free; Exit;
    End;
    PCBServer.PreProcess;
    For i := 0 To KT.Count - 1 Do Brd.RemovePCBObject(KT.Items[i]);
    For i := 0 To KV.Count - 1 Do Brd.RemovePCBObject(KV.Items[i]);
    For i := 0 To KF.Count - 1 Do Brd.RemovePCBObject(KF.Items[i]);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed 87 dead tracks, 9 no-net vias, 2 Top keepout fills. Save, then DRC.');
    KT.Free; KV.Free; KF.Free;
End;
