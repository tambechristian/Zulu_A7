{ NoPmodPlaceX5.pas -- 2026-11-21, no-PMOD Rev 3 STEMMA QT (tools/route/stemma/prep.py).
  PlaceX5   puts X5 (JST-SM04B-SRSS-TB, placed by the ECO somewhere off the board) on the Top, rotation 90 (mouth
            east), origin (58.28, 8.15), and checks pad 1 lands at (55.885, 6.65). Refuses unless X5 exists.
  PinLabel  shortens the vertical Top-overlay pin label '21 GND' at (60.09, 2.41) to '21': its GND part sat under
            X5's MP1 tab. Refuses unless the text is found once.
  Run with the Rev_3 Zulu_a7_no_pmod.PcbDoc focused, then save. }
Function FBrd : IPCB_Board;
Begin
    Result := PCBServer.GetCurrentPCBBoard;
    If (Result = Nil) Or (Pos('\Rev_3\', Result.FileName) = 0) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Result.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_3 Zulu_a7_no_pmod.PcbDoc first.');
        Result := Nil;
    End;
End;

Procedure PlaceX5;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    It : IPCB_GroupIterator;
    Pd : IPCB_Pad;
    Msg : String;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    Cm := Brd.GetPcbComponentByRefDes('X5');
    If Cm = Nil Then
    Begin
        ShowMessage('Refusing: X5 is not on the board (run Design > Update PCB first).');
        Exit;
    End;
    PCBServer.PreProcess;
    Cm.BeginModify;
    If Cm.Layer <> eTopLayer Then Cm.Layer := eTopLayer;
    Cm.Rotation := 90;
    Cm.MoveToXY(Brd.XOrigin + MMsToCoord(58.28), Brd.YOrigin + MMsToCoord(8.15));
    Cm.EndModify;
    PCBServer.PostProcess;
    Msg := '';
    It := Cm.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    Pd := It.FirstPCBObject;
    While Pd <> Nil Do
    Begin
        Msg := Msg + Pd.Name + ' ' + FormatFloat('0.000', CoordToMMs(Pd.X - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Pd.Y - Brd.YOrigin)) + '; ';
        Pd := It.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(It);
    Brd.ViewManager_FullUpdate;
    ShowMessage('X5 placed: ' + Msg + ' (expected 1 at 55.885,6.650; MP1 59.760,5.350)');
End;

Procedure PinLabel;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    T, Hit : IPCB_Text;
    n : Integer;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    n := 0;
    Hit := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (T.Text = '21 GND') And (Abs(CoordToMMs(T.XLocation - Brd.XOrigin) - 60.09) < 0.01) And (Abs(CoordToMMs(T.YLocation - Brd.YOrigin) - 2.411) < 0.01) Then
        Begin
            Hit := T;
            n := n + 1;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 1 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(n) + ' "21 GND" labels at (60.09, 2.41).');
        Exit;
    End;
    PCBServer.PreProcess;
    Hit.BeginModify;
    Hit.Text := '21';
    Hit.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Pin label "21 GND" shortened to "21".');
End;

{ HideX5Name -- X5's designator (the footprint's 'X5' text) landed on C85/C86's pads (DRC Silk To Solder Mask x4) and
  there is no free 0.8 mm spot beside the connector: hide it, as the chip passives' designators are. }
Procedure HideX5Name;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    Cm := Brd.GetPcbComponentByRefDes('X5');
    If Cm = Nil Then
    Begin
        ShowMessage('Refusing: X5 not found.');
        Exit;
    End;
    PCBServer.PreProcess;
    Cm.BeginModify;
    Cm.NameOn := False;
    Cm.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('X5 designator hidden.');
End;
