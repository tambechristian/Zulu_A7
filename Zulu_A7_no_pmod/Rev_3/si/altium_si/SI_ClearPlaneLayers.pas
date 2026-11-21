{ SI_ClearPlaneLayers.pas -- 2026-11-12. SI-ONLY COPY of Zulu_a7_no_pmod Rev 2 (si/altium_si/Zulu_a7_no_pmod_SI.PcbDoc).
  Altium's SI engine only uses Plane-type layers as return/supply references; on the real board L2-GND and L5-VCC3V3 are
  signal layers carrying whole-layer pours (no tracks), so SI assumed default planes (5 V, far away: 230 ohm traces).
  This removes the pours on L2 (eMidLayer3) and L5 (eMidLayer4) so the two layers can be switched to Plane type in the
  Layer Stack Manager. Refuses to run on anything but the SI copy. Reports every object it removed. }
Procedure SIClearPlaneLayers;
Var
    Doc : IDocument;
    B   : IPCB_Board;
    It  : IPCB_BoardIterator;
    O   : IPCB_Primitive;
    L   : TInterfaceList;
    i, nPoly, nOther : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\si\altium_si\Zulu_a7_no_pmod_SI.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the SI copy si\altium_si\Zulu_a7_no_pmod_SI.PcbDoc first.');
        Exit;
    End;
    B := PCBServer.GetCurrentPCBBoard;
    L := TInterfaceList.Create;
    nPoly := 0; nOther := 0;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(MkSet(eMidLayer3, eMidLayer4));
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If (O.Layer = eMidLayer3) Or (O.Layer = eMidLayer4) Then L.Add(O);
        O := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    nPoly := L.Count;
    For i := 0 To L.Count - 1 Do B.RemovePCBObject(L.Items[i]);
    L.Clear;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eFillObject, eRegionObject));
    It.AddFilter_LayerSet(MkSet(eMidLayer3, eMidLayer4));
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If ((O.Layer = eMidLayer3) Or (O.Layer = eMidLayer4)) And (Not O.InPolygon) Then L.Add(O);
        O := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
    nOther := L.Count;
    For i := 0 To L.Count - 1 Do B.RemovePCBObject(L.Items[i]);
    B.ViewManager_FullUpdate;
    ShowMessage('SI copy: removed ' + IntToStr(nPoly) + ' polygons and ' + IntToStr(nOther) + ' other primitives on L2/L5.');
End;
