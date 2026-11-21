{ AsarRebuildConn.pas -- 2026-11-21. Rev_1 copy of FeatherRebuildConn.pas (2026-11-07), whose path guard predates the move
  to Asar_feather\Rev_1. The board saved one stale connection object (ratsnest line) in Connections6, CLK-12M-SHARED
  (15.375, 12.650) -> (16.325, 13.750), although Altium's DRC finds 0 un-routed nets; the project gate is an empty
  Connections6 on a fully routed save (docs/routing.md). This marks every net connectively invalid
  (IPCB_Net.ConnectivelyInValidate) and has Altium re-analyse them all (IPCB_Board.ConnectivelyValidateNets). It touches
  no copper. It then lists the connection objects that remain in "Project Logs for asar_feather\rebuild_conn.log".
  Run RebuildConnections with Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc focused, then save. }

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
    If (Doc = Nil) Or (Pos('\Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
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
    Log.SaveToFile(ExtractFilePath(Doc.DM_FullPath) + 'Project Logs for asar_feather\rebuild_conn.log');
    Log.Free;
    ShowMessage('RebuildConnections: ' + IntToStr(Nets) + ' nets re-analysed, ' + IntToStr(Conns) + ' connection objects remain.');
End;
