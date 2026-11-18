{ AsarX4Fix4.pas -- 2026-11-16. Last DRC item of the X4 conversion: the VU through via at (17.25, 16.425) fed the
  Bottom chain to the old top-edge bridge, which AsarX4Fix removed, so it now meets copper on Top only (Net Antennae).
  This deletes the via and shortens the Top VU track (17.25, 14.725)-(17.25, 16.425) to end at (17.25, 15.75), the
  junction with (16.625, 16.375)-(17.25, 15.75) and (17.25, 14.775)-(17.25, 15.75). All-or-nothing; refuses unless
  exactly one of each is found. Run AsarX4Fix4 with asar_feather.PcbDoc focused, then Repour All, DRC, save. }

Procedure AsarX4Fix4;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    O : IPCB_Primitive;
    V : IPCB_Via;
    T : IPCB_Track;
    Vs, Ts : TInterfaceList;
    nm : String;
    x1, y1, x2, y2 : Double;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus Rev_1 asar_feather.PcbDoc.'); Exit; End;
    Vs := TInterfaceList.Create;
    Ts := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        V := O;
        nm := ''; If V.Net <> Nil Then nm := V.Net.Name;
        If (nm = 'VU') And (Abs(CoordToMMs(V.X - Brd.XOrigin) - 17.25) < 0.002) And (Abs(CoordToMMs(V.Y - Brd.YOrigin) - 16.425) < 0.002) Then Vs.Add(V);
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopLayer));
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        T := O;
        nm := ''; If T.Net <> Nil Then nm := T.Net.Name;
        x1 := CoordToMMs(T.X1 - Brd.XOrigin); y1 := CoordToMMs(T.Y1 - Brd.YOrigin);
        x2 := CoordToMMs(T.X2 - Brd.XOrigin); y2 := CoordToMMs(T.Y2 - Brd.YOrigin);
        If (nm = 'VU') And (Abs(x1 - 17.25) < 0.002) And (Abs(x2 - 17.25) < 0.002) And
           (((Abs(y1 - 14.725) < 0.002) And (Abs(y2 - 16.425) < 0.002)) Or ((Abs(y2 - 14.725) < 0.002) And (Abs(y1 - 16.425) < 0.002))) Then Ts.Add(T);
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If (Vs.Count <> 1) Or (Ts.Count <> 1) Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(Vs.Count) + ' via(s) and ' + IntToStr(Ts.Count) + ' track(s), expected 1 and 1; nothing changed.');
        Vs.Free; Ts.Free; Exit;
    End;
    PCBServer.PreProcess;
    Brd.RemovePCBObject(Vs.Items[0]);
    T := Ts.Items[0];
    T.BeginModify;
    If Abs(CoordToMMs(T.Y2 - Brd.YOrigin) - 16.425) < 0.002 Then T.Y2 := Brd.YOrigin + MMsToCoord(15.75)
    Else T.Y1 := Brd.YOrigin + MMsToCoord(15.75);
    T.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed the VU via at (17.25, 16.425); track now ends at y ' + FloatToStr(CoordToMMs(T.Y1 - Brd.YOrigin)) + ' / ' + FloatToStr(CoordToMMs(T.Y2 - Brd.YOrigin)) + '. Repour, DRC, save.');
    Vs.Free; Ts.Free;
End;
