{ FabB_TpsFinish.pas -- 2026-11-09, after FabB_TpsPlace + FabBCopper_TpsSwap. DRC found 26 silk violations, all from the
  R109/R110 designators that the ECO left visible (137 of 141 Bottom parts on this board hide theirs). This hides both,
  adds the new L1-2 switch node NetL1_2 to the PWR_SWITCH net class (NetL1_1, NetL2_1, NetL3_1 are in it), and rebuilds
  the saved ratsnest as FabB_RebuildConn.pas does. Run TpsFinish with Zulu_a7_no_pmod.PcbDoc focused, then save. }

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

Procedure TpsFinish;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    Cls : IPCB_ObjectClass;
    C : IPCB_Connection;
    Cm : IPCB_Component;
    Kill : TInterfaceList;
    i, nHid, nCls, nLeft : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    PCBServer.PreProcess;
    nHid := 0;
    Cm := Brd.GetPcbComponentByRefDes('R109');
    If Cm <> Nil Then Begin Cm.BeginModify; Cm.NameOn := False; Cm.CommentOn := False; Cm.EndModify; nHid := nHid + 1; End;
    Cm := Brd.GetPcbComponentByRefDes('R110');
    If Cm <> Nil Then Begin Cm.BeginModify; Cm.NameOn := False; Cm.CommentOn := False; Cm.EndModify; nHid := nHid + 1; End;

    nCls := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eClassObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Cls := It.FirstPCBObject;
    While Cls <> Nil Do
    Begin
        If (Cls.MemberKind = eClassMemberKind_Net) And (Cls.Name = 'PWR_SWITCH') Then
        Begin
            If Not Cls.IsMember('NetL1_2') Then Cls.AddMemberByName('NetL1_2');
            nCls := nCls + 1;
        End;
        Cls := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PostProcess;

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
    nLeft := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        nLeft := nLeft + 1;
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Designators hidden: ' + IntToStr(nHid) + ' of 2. PWR_SWITCH classes found: ' + IntToStr(nCls) +
        '. Ratsnest: removed ' + IntToStr(Kill.Count) + ', ' + IntToStr(nLeft) + ' remain after re-analysis. Save, re-run DRC.');
    Kill.Free;
End;
