Function NN(O : IPCB_Primitive) : String;
Begin
    Result := '';
    If O.Net <> Nil Then Result := O.Net.Name;
End;

Procedure DumpCopperFB;
Var
    Brd : IPCB_Board; It : IPCB_BoardIterator; O : IPCB_Primitive; SL : TStringList; ox, oy : Integer; c : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit;
    ox := Brd.XOrigin; oy := Brd.YOrigin;
    SL := TStringList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eViaObject, eFillObject, eArcObject, eRegionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        c := '';
        If O.InComponent Then c := 'C:' + O.Component.Name.Text;
        If O.ObjectId = eTrackObject Then
            SL.Add('T|' + NN(O) + '|' + Layer2String(O.Layer) + '|' + FloatToStr(CoordToMMs(O.Width)) + '|' + FloatToStr(CoordToMMs(O.X1 - ox)) + '|' + FloatToStr(CoordToMMs(O.Y1 - oy)) + '|' + FloatToStr(CoordToMMs(O.X2 - ox)) + '|' + FloatToStr(CoordToMMs(O.Y2 - oy)) + '|' + c + '|' + BoolToStr(O.InPolygon, True))
        Else If O.ObjectId = eViaObject Then
            SL.Add('V|' + NN(O) + '|' + IntToStr(O.LowLayer) + '-' + IntToStr(O.HighLayer) + '|' + FloatToStr(CoordToMMs(O.Size)) + '|' + FloatToStr(CoordToMMs(O.X - ox)) + '|' + FloatToStr(CoordToMMs(O.Y - oy)) + '|' + c)
        Else If O.ObjectId = eFillObject Then
            SL.Add('F|' + NN(O) + '|' + Layer2String(O.Layer) + '|' + FloatToStr(CoordToMMs(O.X1Location - ox)) + '|' + FloatToStr(CoordToMMs(O.Y1Location - oy)) + '|' + FloatToStr(CoordToMMs(O.X2Location - ox)) + '|' + FloatToStr(CoordToMMs(O.Y2Location - oy)) + '|' + c + '|' + BoolToStr(O.IsKeepout, True))
        Else If O.ObjectId = eArcObject Then
            SL.Add('A|' + NN(O) + '|' + Layer2String(O.Layer) + '|' + FloatToStr(CoordToMMs(O.XCenter - ox)) + '|' + FloatToStr(CoordToMMs(O.YCenter - oy)) + '|' + c + '|' + BoolToStr(O.InPolygon, True))
        Else If O.ObjectId = eRegionObject Then
            SL.Add('R|' + NN(O) + '|' + Layer2String(O.Layer) + '|' + FloatToStr(CoordToMMs(O.BoundingRectangle.Left - ox)) + '|' + FloatToStr(CoordToMMs(O.BoundingRectangle.Bottom - oy)) + '|' + FloatToStr(CoordToMMs(O.BoundingRectangle.Right - ox)) + '|' + FloatToStr(CoordToMMs(O.BoundingRectangle.Top - oy)) + '|' + c + '|' + BoolToStr(O.InPolygon, True) + '|' + BoolToStr(O.IsKeepout, True));
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    SL.SaveToFile('C:/Users/tambe/AppData/Local/Temp/claude/4f46ee6af972add9/cb02897e-21a5-48d4-9f87-57145adc4da2/scratchpad/fb_dump.txt');
    ShowMessage('dumped ' + IntToStr(SL.Count));
    SL.Free;
End;
