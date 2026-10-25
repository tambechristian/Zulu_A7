{ FeatherDedupeVias.pas -- 2026-10-24: removes exact duplicate vias (same net, same position, same layer pair).
  Stage 3b placed three (the router committed the same via twice where two routes met); Altium flags each pair as
  a hole-to-hole collision. Run RemoveDuplicateVias with asar_feather.PcbDoc focused, then save. }

Procedure RemoveDuplicateVias;
Var
    Brd  : IPCB_Board;
    It   : IPCB_BoardIterator;
    V    : IPCB_Via;
    L    : TInterfaceList;
    Kill : TInterfaceList;
    Keys : TStringList;
    K    : String;
    I    : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Exit;
    L := TInterfaceList.Create;
    Kill := TInterfaceList.Create;
    Keys := TStringList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        L.Add(V);
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    For I := 0 To L.Count - 1 Do
    Begin
        V := L.Items[I];
        K := IntToStr(V.X) + ',' + IntToStr(V.Y) + ',' + IntToStr(V.LowLayer) + ',' + IntToStr(V.HighLayer);
        If V.Net <> Nil Then K := K + ',' + V.Net.Name;
        If Keys.IndexOf(K) >= 0 Then Kill.Add(V) Else Keys.Add(K);
    End;
    For I := 0 To Kill.Count - 1 Do Brd.RemovePCBObject(Kill.Items[I]);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed ' + IntToStr(Kill.Count) + ' duplicate via(s) of ' + IntToStr(L.Count) + '. Save.');
    L.Free; Kill.Free; Keys.Free;
End;
