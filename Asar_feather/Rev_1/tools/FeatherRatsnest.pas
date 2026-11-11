{ FeatherRatsnest.pas -- 2026-11-07, read-only diagnostic. Lists every connection object (ratsnest line) Altium holds for the
  focused board: net, both ends in board-relative mm and both layers, plus a count per net. Changes nothing.
  Run ListRatsnest with asar_feather.PcbDoc focused; the log goes to the scratch path below. }

Procedure ListRatsnest;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    C   : IPCB_Connection;
    Log : TStringList;
    N   : Integer;
    S   : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Log := TStringList.Create;
    N := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        N := N + 1;
        If C.Net <> Nil Then S := C.Net.Name Else S := '(no net)';
        Log.Add(S + ' ' + FloatToStr(CoordToMMs(C.X1 - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(C.Y1 - Brd.YOrigin)) + ' ' +
                Layer2String(C.Layer1) + ' ' + FloatToStr(CoordToMMs(C.X2 - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(C.Y2 - Brd.YOrigin)) + ' ' +
                Layer2String(C.Layer2));
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Log.Insert(0, 'connections ' + IntToStr(N));
    Log.SaveToFile('C:\Users\tambe\AppData\Local\Temp\claude\74c8e1fc98776908\ac1fa567-8c06-4af0-9b2d-65df9ede410f\scratchpad\u1silk\ratsnest.log');
    Log.Free;
    ShowMessage('ListRatsnest: ' + IntToStr(N) + ' connection objects listed.');
End;
