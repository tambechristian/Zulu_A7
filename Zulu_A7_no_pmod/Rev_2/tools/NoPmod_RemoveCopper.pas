{ NoPmod_RemoveCopper.pas -- 2026-11-12. Zulu_a7_no_pmod Rev 2: deletes every track, arc and via on the 16 Pmod nets
  (JA1-4, JA7-10, PMOD-1..4, PMOD-7..10). The plan (tools/route/no_pmod/final.json, route_check PASS) expects 128 tracks
  and 73 vias; the script refuses unless it finds exactly those counts. J1, R26-R33 and the nets go with the ECO afterwards. }
Function IsPmod(S : String) : Boolean;
Begin
    Result := (S = 'JA1') Or (S = 'JA2') Or (S = 'JA3') Or (S = 'JA4') Or (S = 'JA7') Or (S = 'JA8') Or (S = 'JA9') Or (S = 'JA10')
           Or (S = 'PMOD-1') Or (S = 'PMOD-2') Or (S = 'PMOD-3') Or (S = 'PMOD-4') Or (S = 'PMOD-7') Or (S = 'PMOD-8')
           Or (S = 'PMOD-9') Or (S = 'PMOD-10');
End;

Procedure NoPmodRemoveCopper;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    It  : IPCB_BoardIterator;
    O   : IPCB_Primitive;
    L   : TInterfaceList;
    i, nt, nv, na : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_2\...\Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    nt := 0; nv := 0; na := 0;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eViaObject, eArcObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If (O.Net <> Nil) And (Not O.InComponent) Then
            If IsPmod(O.Net.Name) Then
            Begin
                L.Add(O);
                If O.ObjectId = eTrackObject Then nt := nt + 1
                Else If O.ObjectId = eViaObject Then nv := nv + 1
                Else na := na + 1;
            End;
        O := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    If (nt <> 128) Or (nv <> 73) Or (na <> 0) Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(nt) + ' tracks, ' + IntToStr(nv) + ' vias, ' + IntToStr(na) + ' arcs; expected 128 / 73 / 0.');
        Exit;
    End;
    PCBServer.PreProcess;
    For i := 0 To L.Count - 1 Do B.RemovePCBObject(L.Items[i]);
    PCBServer.PostProcess;
    B.ViewManager_FullUpdate;
    ShowMessage('Removed ' + IntToStr(nt) + ' tracks and ' + IntToStr(nv) + ' vias on the Pmod nets.');
End;
