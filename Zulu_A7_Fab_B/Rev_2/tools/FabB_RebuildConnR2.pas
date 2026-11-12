{ FabB_RebuildConnR2.pas -- Rev 2 copy (2026-11-11) of FabB_RebuildConn.pas with the guard and the log path pointed at
  Zulu_A7_Fab_B\Rev_2 (it removed 0 objects there; saving dropped 2 stale ratsnest lines). Original header:
  FabB_RebuildConn.pas -- 2026-11-08. The board file carried 143 saved connection objects (Connections6; 124 of them GND)
  that Altium shows as ratsnest lines while its DRC finds 0 un-routed nets: the copper was placed by scripts, so the saved
  ratsnest was never recomputed. Same fix as Asar_feather/tools/FeatherRebuildConn.pas + FeatherRebuildGnd.pas in one pass:
  (1) mark every net connectively invalid and have Altium re-analyse them; (2) remove whatever connection objects remain
  (ratsnest only, no copper -- CleanNet is not used), invalidate every net again and re-analyse, so anything Altium re-creates
  is a real open. Lists the survivors in tools\connections_after.txt. Run RebuildConn with zulu_a7_fab_b.PcbDoc focused, save. }

Procedure InvalidateAll(Brd : IPCB_Board);
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        N.ConnectivelyInValidate;
        N := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Brd.ConnectivelyValidateNets;
End;

Procedure RebuildConnR2;
Var
    Doc   : IDocument;
    Brd   : IPCB_Board;
    It    : IPCB_BoardIterator;
    C     : IPCB_Connection;
    Kill  : TInterfaceList;
    Log   : TStringList;
    i     : Integer;
    S     : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    InvalidateAll(Brd);

    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        Kill.Add(C);
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do Brd.RemovePCBObject(Kill.Items[i]);
    PCBServer.PostProcess;
    InvalidateAll(Brd);
    Brd.ViewManager_FullUpdate;

    Log := TStringList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        If C.Net <> Nil Then S := C.Net.Name Else S := '(no net)';
        Log.Add(S + ' ' + FloatToStr(CoordToMMs(C.X1 - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(C.Y1 - Brd.YOrigin)) + ' ' +
                Layer2String(C.Layer1) + ' -> ' + FloatToStr(CoordToMMs(C.X2 - Brd.XOrigin)) + ' ' +
                FloatToStr(CoordToMMs(C.Y2 - Brd.YOrigin)) + ' ' + Layer2String(C.Layer2));
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Log.Insert(0, 'removed ' + IntToStr(Kill.Count) + ' after first re-analysis; ' + IntToStr(Log.Count) + ' after second');
    Log.SaveToFile('C:\Users\tambe\Documents\Electronics\Zulu_A7\Zulu_A7_Fab_B\Rev_2\tools\connections_after.txt');
    ShowMessage('RebuildConn: removed ' + IntToStr(Kill.Count) + ' connection objects; ' + IntToStr(Log.Count - 1) +
        ' remain after re-analysis.');
    Log.Free;
    Kill.Free;
End;
