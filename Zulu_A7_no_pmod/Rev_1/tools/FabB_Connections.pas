{ Read-only probe: list every connection (ratsnest) line on the board with its net, layers and end points, written to
  tools\connections.txt next to this script. Changes nothing. }
Procedure ListConnections;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    C : IPCB_Connection;
    L : TStringList;
    n : Integer;
    s : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then
    Begin
        ShowMessage('Focus the PcbDoc first.');
        Exit;
    End;
    L := TStringList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    n := 0;
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        n := n + 1;
        s := '?';
        If C.Net <> Nil Then s := C.Net.Name;
        L.Add(s + ' ' + FloatToStr(CoordToMMs(C.X1 - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(C.Y1 - Brd.YOrigin)) + ' ' +
            Layer2String(C.Layer1) + ' -> ' + FloatToStr(CoordToMMs(C.X2 - Brd.XOrigin)) + ' ' +
            FloatToStr(CoordToMMs(C.Y2 - Brd.YOrigin)) + ' ' + Layer2String(C.Layer2));
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    L.SaveToFile('C:\Users\tambe\Documents\Electronics\Zulu_A7\Zulu_A7_no_pmod\tools\connections.txt');
    L.Free;
    ShowMessage(IntToStr(n) + ' connection lines written to tools\connections.txt');
End;
