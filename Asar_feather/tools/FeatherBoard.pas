{ FeatherBoard.pas -- 2026-10-23. Turns the copied production board (asar_feather.PcbDoc) into an empty
  Feather board. Focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc, then run in this order:
    FeatherBoardCount   reads only: counts what StripFeatherBoard would remove (also the API canary)
    StripFeatherBoard   removes every free (non-component) track, arc, via, fill, region, polygon and text
                        on the signal, overlay, keep-out and Mechanical 1 layers. The L2-GND / L5-VCC3V3
                        plane layers, rules, classes, stack and via types are left alone.
    SetFeatherOutline   board shape = 50.80 x 22.86 mm rectangle with its lower-left corner at (0, 0)
    ReportFeatherOutline }

Const
    FW = 50.8;
    FH = 22.86;

Function FeatherBoardOrNil : IPCB_Board;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
End;

Function StripLayers : TLayerSet;
Begin
    Result := MkSet(eTopLayer, eMidLayer1, eMidLayer2, eBottomLayer, eTopOverlay, eBottomOverlay,
                    eKeepOutLayer, eMechanical1);
End;

Procedure Collect(Brd : IPCB_Board; Kind : Integer; Layers : TLayerSet; List : TInterfaceList);
Var
    It  : IPCB_BoardIterator;
    Obj : IPCB_Primitive;
Begin
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(Kind));
    It.AddFilter_LayerSet(Layers);
    Obj := It.FirstPCBObject;
    While Obj <> Nil Do
    Begin
        If Not Obj.InComponent Then List.Add(Obj);
        Obj := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Function Census(Brd : IPCB_Board; Remove : Boolean) : String;
Var
    L : TInterfaceList;
    K, I : Integer;
    Kinds : Array[0..6] Of Integer;
    Names : Array[0..6] Of String;
Begin
    Kinds[0] := ePolyObject;   Names[0] := 'polygons';
    Kinds[1] := eTrackObject;  Names[1] := 'tracks';
    Kinds[2] := eArcObject;    Names[2] := 'arcs';
    Kinds[3] := eViaObject;    Names[3] := 'vias';
    Kinds[4] := eFillObject;   Names[4] := 'fills';
    Kinds[5] := eRegionObject; Names[5] := 'regions';
    Kinds[6] := eTextObject;   Names[6] := 'texts';
    Result := '';
    For K := 0 To 6 Do
    Begin
        L := TInterfaceList.Create;
        If Kinds[K] = eViaObject Then Collect(Brd, Kinds[K], AllLayers, L)
        Else Collect(Brd, Kinds[K], StripLayers, L);
        Result := Result + Names[K] + ' ' + IntToStr(L.Count) + #13#10;
        If Remove Then
            For I := 0 To L.Count - 1 Do
                Brd.RemovePCBObject(L.Items[I]);
        L.Free;
    End;
End;

Procedure FeatherBoardCount;
Var
    Brd : IPCB_Board;
Begin
    Brd := FeatherBoardOrNil;
    If Brd = Nil Then Exit;
    ShowMessage('Would remove:' + #13#10 + Census(Brd, False));
End;

Procedure StripFeatherBoard;
Var
    Brd : IPCB_Board;
    S   : String;
Begin
    Brd := FeatherBoardOrNil;
    If Brd = Nil Then Exit;
    S := Census(Brd, True);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed:' + #13#10 + S + 'Left now:' + #13#10 + Census(Brd, False));
End;

Procedure SetFeatherOutline;
Var
    Brd : IPCB_Board;
    BO  : IPCB_BoardOutline;
Begin
    Brd := FeatherBoardOrNil;
    If Brd = Nil Then Exit;
    BO := Brd.BoardOutline;
    PCBServer.PreProcess;
    Try
        BO.BeginModify;
        BO.PointCount := 4;
        BO.Segments[0].Kind := ePolySegmentLine; BO.Segments[0].vx := MMsToCoord(0);  BO.Segments[0].vy := MMsToCoord(0);
        BO.Segments[1].Kind := ePolySegmentLine; BO.Segments[1].vx := MMsToCoord(FW); BO.Segments[1].vy := MMsToCoord(0);
        BO.Segments[2].Kind := ePolySegmentLine; BO.Segments[2].vx := MMsToCoord(FW); BO.Segments[2].vy := MMsToCoord(FH);
        BO.Segments[3].Kind := ePolySegmentLine; BO.Segments[3].vx := MMsToCoord(0);  BO.Segments[3].vy := MMsToCoord(FH);
        BO.EndModify;
        BO.Invalidate;
        BO.Validate;
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Board outline set to 50.80 x 22.86 mm. Run ReportFeatherOutline.');
End;

Procedure ReportFeatherOutline;
Var
    Brd : IPCB_Board;
    I   : Integer;
    S   : String;
Begin
    Brd := FeatherBoardOrNil;
    If Brd = Nil Then Exit;
    S := 'Board outline vertices (mm), origin ' + FloatToStr(CoordToMMs(Brd.XOrigin)) + ', ' +
         FloatToStr(CoordToMMs(Brd.YOrigin)) + #13#10;
    For I := 0 To Brd.BoardOutline.PointCount - 1 Do
        S := S + FloatToStr(CoordToMMs(Brd.BoardOutline.Segments[I].vx - Brd.XOrigin)) + ', ' +
             FloatToStr(CoordToMMs(Brd.BoardOutline.Segments[I].vy - Brd.YOrigin)) + #13#10;
    ShowMessage(S);
End;
