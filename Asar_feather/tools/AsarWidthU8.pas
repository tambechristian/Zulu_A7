Function FindRuleU8(Brd : IPCB_Board; Name : String) : IPCB_Rule;
Var
    It : IPCB_BoardIterator;
    R  : IPCB_Rule;
Begin
    Result := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eRuleObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    R := It.FirstPCBObject;
    While R <> Nil Do
    Begin
        If R.Name = Name Then
        Begin
            Result := R;
            Break;
        End;
        R := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Procedure RelaxWidthU8Inner;
Var
    Brd : IPCB_Board;
    R : IPCB_Rule;
Begin
    Brd := PCBServer.GetCurrentPCBBoard; If Brd = Nil Then Exit;
    If Pos('asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus asar_feather.PcbDoc'); Exit; End;
    R := FindRuleU8(Brd, 'Width_PWR_U8');
    If R = Nil Then Begin ShowMessage('Width_PWR_U8 not found'); Exit; End;
    R.BeginModify;
    R.MinWidth(eMidLayer1) := MMsToCoord(0.2);
    R.MinWidth(eMidLayer2) := MMsToCoord(0.2);
    R.EndModify;
    R := FindRuleU8(Brd, 'Width_PWR_VCC1V0');
    If R = Nil Then Begin ShowMessage('Width_PWR_VCC1V0 not found'); Exit; End;
    R.BeginModify;
    R.MinWidth(eMidLayer1) := MMsToCoord(0.3);
    R.MinWidth(eMidLayer2) := MMsToCoord(0.3);
    R.EndModify;
    ShowMessage('VCC1V0 inner min L3 ' + FloatToStr(CoordToMMs(R.MinWidth(eMidLayer1))) + ' L4 ' + FloatToStr(CoordToMMs(R.MinWidth(eMidLayer2))));
    R := FindRuleU8(Brd, 'Width_PWR_U8');
    ShowMessage('Width_PWR_U8 inner min now L3 ' + FloatToStr(CoordToMMs(R.MinWidth(eMidLayer1))) + ' mm, L4 ' + FloatToStr(CoordToMMs(R.MinWidth(eMidLayer2))) + ' mm; Top ' + FloatToStr(CoordToMMs(R.MinWidth(eTopLayer))) + ', Bottom ' + FloatToStr(CoordToMMs(R.MinWidth(eBottomLayer))));
End;
