{ FeatherSilkU1.pas -- 2026-11-07. U1's designator 0.05 mm south (anchor y 5.700 -> 5.650 board-relative) to clear Silk To Solder
  Mask (0.254) at balls A18/A19, which DRC measured at 0.235 mm. FeatherSilkDesig.pas set YLocation directly: X1's change held but
  U1's did not, so this one sets U1's name autoposition to manual, moves the text with MoveByXY between robot modify messages, and
  reads the position back through a fresh board iterator. Refuses unless the U1 text is at (19.292, 5.700), so it runs once.
  Run SilkU1 with asar_feather.PcbDoc focused. }

Function CloseTo(A, B : Integer) : Boolean;
Begin
    Result := Abs(A - B) < MMsToCoord(0.002);
End;

Procedure SilkU1;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    CU1 : IPCB_Component;
    TU1 : IPCB_Text;
    T   : IPCB_Text;
    It  : IPCB_BoardIterator;
    Log : TStringList;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    CU1 := Brd.GetPcbComponentByRefDes('U1');
    If CU1 = Nil Then
    Begin
        ShowMessage('Refusing: U1 not found.');
        Exit;
    End;
    TU1 := CU1.Name;
    If Not (CloseTo(TU1.XLocation - Brd.XOrigin, MMsToCoord(19.2918)) And CloseTo(TU1.YLocation - Brd.YOrigin, MMsToCoord(5.7001))) Then
    Begin
        ShowMessage('Refusing: the U1 designator is not at (19.292, 5.700); nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    CU1.BeginModify;
    CU1.ChangeNameAutoposition := eAutoPos_Manual;
    CU1.EndModify;
    PCBServer.SendMessageToRobots(TU1.I_ObjectAddress, c_Broadcast, PCBM_BeginModify, c_NoEventData);
    TU1.MoveByXY(0, -MMsToCoord(0.05));
    PCBServer.SendMessageToRobots(TU1.I_ObjectAddress, c_Broadcast, PCBM_EndModify, c_NoEventData);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    Log := TStringList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If T.IsDesignator And ((T.Text = 'U1') Or (T.Text = 'X1') Or (T.Text = 'U2')) Then
            Log.Add(T.Text + ' anchor ' + FloatToStr(CoordToMMs(T.XLocation - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(T.YLocation - Brd.YOrigin)) +
                    ' size ' + FloatToStr(CoordToMMs(T.Size)) + ' width ' + FloatToStr(CoordToMMs(T.Width)));
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Log.SaveToFile('C:\Users\tambe\AppData\Local\Temp\claude\74c8e1fc98776908\ac1fa567-8c06-4af0-9b2d-65df9ede410f\scratchpad\u1silk\silku1.log');
    Log.Free;
    ShowMessage('SilkU1 done. Run DRC, then save.');
End;
