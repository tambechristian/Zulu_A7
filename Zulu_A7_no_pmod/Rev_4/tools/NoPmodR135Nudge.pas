{ NoPmodR135Nudge.pas -- 2026-11-25, no-PMOD Rev 4 DONE LED: DRC Component Clearance (0.254 mm) flagged BTN's 3D
  body against R135's. R135 moves +0.08 mm in x (pad 1 20.450 -> 20.530, 13.885). Its pads then span x 20.38..20.68;
  the DONE and NetLD5_A tracks end at x 20.55 inside them; LD5's anode pad starts at 20.95 (0.27 mm). Refuses unless
  R135 pad 1 is at (20.450, 13.885). Save after. }
Procedure NudgeR135;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    It : IPCB_GroupIterator;
    Pd, P1 : IPCB_Pad;
    S : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_4\', Brd.FileName) = 0) Then Begin ShowMessage('Refusing: focus the Rev_4 board.'); Exit; End;
    Cm := Brd.GetPcbComponentByRefDes('R135');
    If Cm = Nil Then Begin ShowMessage('Refusing: no R135.'); Exit; End;
    P1 := Nil;
    It := Cm.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    Pd := It.FirstPCBObject;
    While Pd <> Nil Do Begin If Pd.Name = '1' Then P1 := Pd; Pd := It.NextPCBObject; End;
    Cm.GroupIterator_Destroy(It);
    If (P1 = Nil) Or (Abs(CoordToMMs(P1.X - Brd.XOrigin) - 20.45) > 0.002) Or (Abs(CoordToMMs(P1.Y - Brd.YOrigin) - 13.885) > 0.002) Then
    Begin
        ShowMessage('Refusing: R135 pad 1 is not at (20.450, 13.885).');
        Exit;
    End;
    PCBServer.PreProcess;
    Cm.BeginModify;
    Cm.MoveByXY(MMsToCoord(0.08), 0);
    Cm.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    S := '';
    It := Cm.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    Pd := It.FirstPCBObject;
    While Pd <> Nil Do
    Begin
        S := S + Pd.Name + ' ' + FormatFloat('0.000', CoordToMMs(Pd.X - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Pd.Y - Brd.YOrigin)) + '; ';
        Pd := It.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(It);
    ShowMessage('R135 pads: ' + S + '(expected 1 20.530,13.885; 2 20.530,14.485). Save the board.');
End;
