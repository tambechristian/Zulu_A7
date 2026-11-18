{ AsarU2Label.pas -- 2026-11-17, X1 micro-B conversion (docs/x1_microb.md). Q1 moved 1.46 mm east onto U2's designator
  (Silk To Solder Mask on Q1-3). Writing a designator's location does not hold on this board (AsarX1Clean tried it: the
  box stayed at 16.92..18.55 x 12.75..13.86), so, as for X1 on 2026-11-16, U2's designator is hidden and a free Top
  Overlay text "U2" with the designator's size and stroke goes where its box starts at (12.70, 12.60): between X4-1 and
  Q1-2, above U2's north pin row. Refuses unless U2's designator is visible with its box starting near x 16.92. }

Procedure AsarU2Label;
Var
    Brd : IPCB_Board;
    C : IPCB_Component;
    TX, T : IPCB_Text;
    B : TCoordRect;
    offX, offY : TCoord;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then
    Begin ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.'); Exit; End;
    C := Brd.GetPcbComponentByRefDes('U2');
    If C = Nil Then Begin ShowMessage('Refusing: U2 not found.'); Exit; End;
    TX := C.Name;
    B := TX.BoundingRectangle;
    If (Not C.NameOn) Or (Abs(CoordToMMs(B.Left - Brd.XOrigin) - 16.916) > 0.05) Then
    Begin
        ShowMessage('Refusing: U2 designator hidden or not at x 16.92 (box left ' + FormatFloat('0.000', CoordToMMs(B.Left - Brd.XOrigin)) + '); nothing changed.');
        Exit;
    End;
    offX := TX.XLocation - B.Left;
    offY := TX.YLocation - B.Bottom;
    PCBServer.PreProcess;
    C.BeginModify;
    C.NameOn := False;
    C.EndModify;
    T := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
    T.Layer := eTopOverlay;
    T.Text := 'U2';
    T.Size := TX.Size;
    T.Width := TX.Width;
    T.Rotation := 0;
    T.UseTTFonts := False;
    T.XLocation := Brd.XOrigin + MMsToCoord(12.70) + offX;
    T.YLocation := Brd.YOrigin + MMsToCoord(12.60) + offY;
    Brd.AddPCBObject(T);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    B := T.BoundingRectangle;
    ShowMessage('U2 designator hidden; free text U2 (size ' + FormatFloat('0.000', CoordToMMs(T.Size)) + ') box x ' +
        FormatFloat('0.000', CoordToMMs(B.Left - Brd.XOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(B.Right - Brd.XOrigin)) +
        ', y ' + FormatFloat('0.000', CoordToMMs(B.Bottom - Brd.YOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(B.Top - Brd.YOrigin)) + '. Repour, save, DRC.');
End;
