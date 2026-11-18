{ AsarX1Remove.pas -- 2026-11-17, X1 USB-C -> micro-B (docs/x1_microb.md).
  The ECO could not swap X1's footprint USB-C-HRO-TYPE-C-31-M-12 -> AMPHENOL-10118193-0001LF ("Cannot match pads"), so
  this removes the old X1 component from the board; re-running Design > Update PCB Document then adds X1 back with the
  new footprint and its nets, and AsarX1Place puts it on the west edge. Copper is not touched.
  Refuses unless the focused board is Asar Rev_1 and X1 still carries the USB-C footprint. }

Procedure AsarX1Remove;
Var
    Brd : IPCB_Board;
    C : IPCB_Component;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then
    Begin ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.'); Exit; End;
    C := Brd.GetPcbComponentByRefDes('X1');
    If C = Nil Then Begin ShowMessage('X1 is not on the board; nothing changed.'); Exit; End;
    If C.Pattern <> 'USB-C-HRO-TYPE-C-31-M-12' Then
    Begin ShowMessage('Refusing: X1 footprint is ' + C.Pattern + ', not the USB-C one; nothing changed.'); Exit; End;
    PCBServer.PreProcess;
    Brd.RemovePCBObject(C);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    If Brd.GetPcbComponentByRefDes('X1') = Nil Then
        ShowMessage('X1 (USB-C) removed. Now Design > Update PCB Document from sheet 1 to add X1 with AMPHENOL-10118193-0001LF.')
    Else
        ShowMessage('X1 is still on the board -- removal did not take.');
End;
