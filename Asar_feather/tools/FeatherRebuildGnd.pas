{ FeatherRebuildGnd.pas -- 2026-11-07. After RebuildConnections (FeatherRebuildConn.pas) every net's saved ratsnest was recomputed
  except GND's: its 124 connection objects still end on an old parking grid off the board's east edge (x 53-57 mm), so they were
  never rebuilt, presumably because GND connects through the L2 pour. This removes GND's connection objects (ratsnest only, no
  copper), marks GND connectively invalid and has Altium re-analyse every net, then lists the connection objects that exist
  afterwards, so whatever Altium re-creates is what it really finds open. Run RebuildGnd with asar_feather.PcbDoc focused. }

Procedure RebuildGnd;
Var
    Doc   : IDocument;
    Brd   : IPCB_Board;
    It    : IPCB_BoardIterator;
    C     : IPCB_Connection;
    G     : IPCB_Net;
    Kill  : TInterfaceList;
    Log   : TStringList;
    i     : Integer;
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
    Kill := TInterfaceList.Create;
    G := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        If C.Net <> Nil Then
            If C.Net.Name = 'GND' Then
            Begin
                Kill.Add(C);
                G := C.Net;
            End;
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If G = Nil Then
    Begin
        ShowMessage('No GND connection objects found; nothing changed.');
        Kill.Free;
        Exit;
    End;
    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do Brd.RemovePCBObject(Kill.Items[i]);
    PCBServer.PostProcess;
    G.ConnectivelyInValidate;
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
    Log.Insert(0, 'removed ' + IntToStr(Kill.Count) + ' GND connection objects; connections after re-analysis ' + IntToStr(Conns));
    Log.SaveToFile('C:\Users\tambe\AppData\Local\Temp\claude\74c8e1fc98776908\ac1fa567-8c06-4af0-9b2d-65df9ede410f\scratchpad\u1silk\rebuild_gnd.log');
    Log.Free;
    ShowMessage('RebuildGnd: removed ' + IntToStr(Kill.Count) + ' GND connection objects; ' + IntToStr(Conns) + ' connection objects after re-analysis.');
    Kill.Free;
End;
