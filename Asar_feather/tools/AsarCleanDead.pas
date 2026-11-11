Procedure CleanDeadCopperAsar;
Var
    Brd : IPCB_Board; It : IPCB_BoardIterator; O : IPCB_Primitive; KT, KV : TInterfaceList; PadNets : TStringList; i : Integer; L : TLayer; dead : Boolean;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit;
    If Pos('asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus asar_feather.PcbDoc'); Exit; End;
    PadNets := TStringList.Create; PadNets.Sorted := True; PadNets.Duplicates := dupIgnore;
    It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(ePadObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do Begin If O.Net <> Nil Then PadNets.Add(O.Net.Name); O := It.NextPCBObject; End;
    Brd.BoardIterator_Destroy(It);
    KT := TInterfaceList.Create; KV := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        dead := (O.Net = Nil);
        If Not dead Then dead := (PadNets.IndexOf(O.Net.Name) < 0);
        If O.ObjectId = eTrackObject Then
        Begin
            L := O.Layer;
            If dead And (Not O.InComponent) And (Not O.InPolygon) And (Not O.IsKeepout) And
               ((L = eTopLayer) Or (L = eBottomLayer) Or (L = eMidLayer1) Or (L = eMidLayer2)) Then KT.Add(O);
        End
        Else If O.ObjectId = eViaObject Then
        Begin
            If dead And (Not O.InComponent) Then KV.Add(O);
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (KT.Count <> 75) Or (KV.Count <> 34) Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(KT.Count) + ' dead tracks (75), ' + IntToStr(KV.Count) + ' dead vias (34); nothing changed.');
        KT.Free; KV.Free; PadNets.Free; Exit;
    End;
    PCBServer.PreProcess;
    For i := 0 To KT.Count - 1 Do Brd.RemovePCBObject(KT.Items[i]);
    For i := 0 To KV.Count - 1 Do Brd.RemovePCBObject(KV.Items[i]);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed 75 dead tracks and 34 dead vias (no net or a net with no pads).');
    KT.Free; KV.Free; PadNets.Free;
End;
