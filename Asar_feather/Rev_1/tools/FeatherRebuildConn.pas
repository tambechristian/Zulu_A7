{ FeatherRebuildConn.pas -- 2026-11-07. The board file carries 278 saved connection objects (Connections6) that Altium shows as
  ratsnest lines although its DRC finds 0 un-routed nets: the copper was placed by scripts, so the saved ratsnest was never
  recomputed, and many lines end where parts sat before they moved. This marks every net connectively invalid
  (IPCB_Net.ConnectivelyInValidate) and has Altium re-analyse them all (IPCB_Board.ConnectivelyValidateNets). It touches no copper
  (CleanNet, which rearranges track topology, is not used). It then lists the connection objects that remain, as ListRatsnest does.
  Run RebuildConnections with asar_feather.PcbDoc focused, then save. }

Procedure RebuildConnections;
Var
    Doc   : IDocument;
    Brd   : IPCB_Board;
    It    : IPCB_BoardIterator;
    N     : IPCB_Net;
    C     : IPCB_Connection;
    Log   : TStringList;
    Nets  : Integer;
    Conns : Integer;
    S     : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Nets := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        N.ConnectivelyInValidate;
        Nets := Nets + 1;
        N := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Brd.ConnectivelyValidateNets;
    Brd.ViewManager_FullUpdate;

    Log := TStringList.Create;
    Conns := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        Conns := Conns + 1;
        If C.Net <> Nil Then S := C.Net.Name Else S := '(no net)';
        Log.Add(S + ' ' + FloatToStr(CoordToMMs(C.X1 - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(C.Y1 - Brd.YOrigin)) + ' | ' +
                Layer2String(C.Layer1) + ' | ' + FloatToStr(CoordToMMs(C.X2 - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(C.Y2 - Brd.YOrigin)) + ' | ' +
                Layer2String(C.Layer2));
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Log.Insert(0, 'nets ' + IntToStr(Nets) + ' connections after rebuild ' + IntToStr(Conns));
    Log.SaveToFile('C:\Users\tambe\AppData\Local\Temp\claude\74c8e1fc98776908\ac1fa567-8c06-4af0-9b2d-65df9ede410f\scratchpad\u1silk\rebuild.log');
    Log.Free;
    ShowMessage('RebuildConnections: ' + IntToStr(Nets) + ' nets re-analysed, ' + IntToStr(Conns) + ' connection objects remain.');
End;
