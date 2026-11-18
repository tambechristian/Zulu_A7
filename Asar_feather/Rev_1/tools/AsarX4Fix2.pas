{ AsarX4Fix2.pas -- 2026-11-16. AsarX4Fix moved U10's tick and removed the dead tracks, but its direct XLocation write
  on the X1 designator did not hold. This repeats FeatherSilkDesig.pas's working order (2026-11-07): component
  BeginModify, ChangeNameAutoposition := eAutoPos_Manual, EndModify, then the text's own BeginModify / XLocation /
  YLocation / EndModify. Target anchor (2.25, 17.35): clear of U10-1's mask, X1-MP3 and the X2 mounting hole.
  Refuses unless the X1 designator is still at (3.664, 17.118). Run AsarX4Fix2 with asar_feather.PcbDoc focused. }

Procedure AsarX4Fix2;
Var
    Brd : IPCB_Board;
    CX1 : IPCB_Component;
    TX1 : IPCB_Text;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus Rev_1 asar_feather.PcbDoc.'); Exit; End;
    CX1 := Brd.GetPcbComponentByRefDes('X1');
    If CX1 = Nil Then Begin ShowMessage('Refusing: X1 not found.'); Exit; End;
    TX1 := CX1.Name;
    If (Abs(CoordToMMs(TX1.XLocation - Brd.XOrigin) - 3.664) > 0.003) Or (Abs(CoordToMMs(TX1.YLocation - Brd.YOrigin) - 17.118) > 0.003) Then
    Begin ShowMessage('Refusing: the X1 designator is not at (3.664, 17.118); nothing changed.'); Exit; End;
    PCBServer.PreProcess;
    CX1.BeginModify;
    CX1.ChangeNameAutoposition := eAutoPos_Manual;
    CX1.EndModify;
    TX1.BeginModify;
    TX1.XLocation := TX1.XLocation + MMsToCoord(2.25 - 3.664);
    TX1.YLocation := TX1.YLocation + MMsToCoord(17.35 - 17.118);
    TX1.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('X1 designator now at ' + FloatToStr(CoordToMMs(TX1.XLocation - Brd.XOrigin)) + ', ' + FloatToStr(CoordToMMs(TX1.YLocation - Brd.YOrigin)) + ' (target 2.25, 17.35).');
End;
