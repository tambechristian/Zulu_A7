{ FeatherPour.pas -- 2026-10-23. Removes the production board's two rectangular plane pours (L2_GND_PLANE,
  L5_VCC3V3_PLANE, 0.25..69.6 x 0.25..25.15 mm) from asar_feather.PcbDoc, once the rounded Feather pours
  (L2_GND_FEATHER, L5_VCC3V3_FEATHER, made in the Polygon Manager from the board outline, inset 0.25 mm) exist.
  A pour is "old" when its bounding box reaches past x = 51 mm. Refuses unless exactly two old pours and two
  new ones are found. }

Procedure RemoveOldPours;
Var
    Brd : IPCB_Board;
    Doc : IDocument;
    It  : IPCB_BoardIterator;
    P   : IPCB_Polygon;
    R   : TCoordRect;
    Old : TInterfaceList;
    NNew, I : Integer;
    S   : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Old := TInterfaceList.Create;
    NNew := 0;
    S := '';
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePolyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        R := P.BoundingRectangle;
        S := S + Layer2String(P.Layer) + '  x ' + FloatToStr(CoordToMMs(R.Left)) + '..' + FloatToStr(CoordToMMs(R.Right)) +
             '  y ' + FloatToStr(CoordToMMs(R.Bottom)) + '..' + FloatToStr(CoordToMMs(R.Top)) + #13#10;
        If CoordToMMs(R.Right) > 51 Then Old.Add(P) Else NNew := NNew + 1;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (Old.Count <> 2) Or (NNew <> 2) Then
    Begin
        ShowMessage('Refusing: expected 2 old and 2 new pours, found ' + IntToStr(Old.Count) + ' old, ' +
                    IntToStr(NNew) + ' new.' + #13#10 + S);
        Old.Free;
        Exit;
    End;
    For I := 0 To Old.Count - 1 Do Brd.RemovePCBObject(Old.Items[I]);
    Old.Free;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed the 2 old pours. Before:' + #13#10 + S);
End;
