Procedure DiagVias;
Var
    Brd : IPCB_Board; It : IPCB_BoardIterator; KV : IPCB_Via; nm, S : String; x, y, tw : Double; n : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit; S := '';
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 4.9000) < 0.01) And (Abs(y - 11.7500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '0:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '0: NONE at 4.9000,11.7500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 13.0000) < 0.01) And (Abs(y - 12.3750) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '1:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '1: NONE at 13.0000,12.3750' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.3000) < 0.01) And (Abs(y - 12.2750) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '2:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '2: NONE at 12.3000,12.2750' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.2200) < 0.01) And (Abs(y - 17.6600) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '3:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '3: NONE at 12.2200,17.6600' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 10.1000) < 0.01) And (Abs(y - 18.3800) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '4:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '4: NONE at 10.1000,18.3800' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 2.6250) < 0.01) And (Abs(y - 17.1500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '5:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '5: NONE at 2.6250,17.1500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 2.6250) < 0.01) And (Abs(y - 16.1250) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '6:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '6: NONE at 2.6250,16.1250' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 2.8750) < 0.01) And (Abs(y - 16.6500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '7:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '7: NONE at 2.8750,16.6500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 15.3250) < 0.01) And (Abs(y - 10.1750) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '8:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '8: NONE at 15.3250,10.1750' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.9750) < 0.01) And (Abs(y - 7.1000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '9:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '9: NONE at 12.9750,7.1000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 6.4251) < 0.01) And (Abs(y - 7.2250) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '10:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '10: NONE at 6.4251,7.2250' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 6.1500) < 0.01) And (Abs(y - 17.7500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '11:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '11: NONE at 6.1500,17.7500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 14.0250) < 0.01) And (Abs(y - 17.0600) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '12:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '12: NONE at 14.0250,17.0600' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 5.2330) < 0.01) And (Abs(y - 20.4000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '13:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '13: NONE at 5.2330,20.4000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 3.4330) < 0.01) And (Abs(y - 20.4000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '14:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '14: NONE at 3.4330,20.4000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 1.1000) < 0.01) And (Abs(y - 9.3000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '15:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '15: NONE at 1.1000,9.3000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.4400) < 0.01) And (Abs(y - 11.0000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '16:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '16: NONE at 12.4400,11.0000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.0000) < 0.01) And (Abs(y - 11.0000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '17:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '17: NONE at 12.0000,11.0000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 7.2000) < 0.01) And (Abs(y - 5.8000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '18:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '18: NONE at 7.2000,5.8000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 8.3000) < 0.01) And (Abs(y - 4.4000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '19:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '19: NONE at 8.3000,4.4000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 8.3000) < 0.01) And (Abs(y - 3.6000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '20:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '20: NONE at 8.3000,3.6000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 10.2500) < 0.01) And (Abs(y - 7.3500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '21:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '21: NONE at 10.2500,7.3500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 9.1000) < 0.01) And (Abs(y - 6.1000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '22:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '22: NONE at 9.1000,6.1000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 5.5350) < 0.01) And (Abs(y - 3.9000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '23:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '23: NONE at 5.5350,3.9000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 14.6665) < 0.01) And (Abs(y - 3.1470) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '24:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '24: NONE at 14.6665,3.1470' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 15.8165) < 0.01) And (Abs(y - 4.3485) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '25:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '25: NONE at 15.8165,4.3485' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 15.8165) < 0.01) And (Abs(y - 5.5500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '26:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '26: NONE at 15.8165,5.5500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 15.3000) < 0.01) And (Abs(y - 8.6000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '27:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '27: NONE at 15.3000,8.6000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.9800) < 0.01) And (Abs(y - 8.6000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '28:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '28: NONE at 12.9800,8.6000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 8.9200) < 0.01) And (Abs(y - 3.7500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '29:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '29: NONE at 8.9200,3.7500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 8.9200) < 0.01) And (Abs(y - 3.1000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '30:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '30: NONE at 8.9200,3.1000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 10.1500) < 0.01) And (Abs(y - 4.5500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '31:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '31: NONE at 10.1500,4.5500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 9.8000) < 0.01) And (Abs(y - 9.7000) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '32:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '32: NONE at 9.8000,9.7000' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 9.5000) < 0.01) And (Abs(y - 7.3500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '33:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '33: NONE at 9.5000,7.3500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 11.0500) < 0.01) And (Abs(y - 15.5415) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '34:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '34: NONE at 11.0500,15.5415' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.6000) < 0.01) And (Abs(y - 12.8500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '35:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '35: NONE at 12.6000,12.8500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.6000) < 0.01) And (Abs(y - 13.7300) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '36:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '36: NONE at 12.6000,13.7300' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 12.6000) < 0.01) And (Abs(y - 13.2900) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '37:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '37: NONE at 12.6000,13.2900' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 3.9065) < 0.01) And (Abs(y - 13.9520) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '38:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '38: NONE at 3.9065,13.9520' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 6.8480) < 0.01) And (Abs(y - 15.5020) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '39:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '39: NONE at 6.8480,15.5020' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 6.4080) < 0.01) And (Abs(y - 15.5020) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '40:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '40: NONE at 6.4080,15.5020' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 5.4540) < 0.01) And (Abs(y - 5.7785) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '41:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '41: NONE at 5.4540,5.7785' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 4.7040) < 0.01) And (Abs(y - 9.7500) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '42:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '42: NONE at 4.7040,9.7500' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 4.7040) < 0.01) And (Abs(y - 8.8700) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '43:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '43: NONE at 4.7040,8.8700' + #13;
    n := 0; It := Brd.BoardIterator_Create; It.AddFilter_ObjectSet(MkSet(eViaObject)); It.AddFilter_LayerSet(AllLayers); It.AddFilter_Method(eProcessAll);
    KV := It.FirstPCBObject;
    While KV <> Nil Do
    Begin
        x := CoordToMMs(KV.X - Brd.XOrigin); y := CoordToMMs(KV.Y - Brd.YOrigin);
        If (Abs(x - 4.7040) < 0.01) And (Abs(y - 9.3100) < 0.01) Then Begin n := n + 1; nm := '-'; If KV.Net <> Nil Then nm := KV.Net.Name; S := S + '44:' + nm + ' h' + FloatToStr(CoordToMMs(KV.HoleSize)) + ' L' + IntToStr(KV.LowLayer) + '-' + IntToStr(KV.HighLayer) + ' x' + FloatToStr(x) + ' y' + FloatToStr(y) + #13; End;
        KV := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n = 0 Then S := S + '44: NONE at 4.7040,9.3100' + #13;
    ShowMessage(S);
End;
