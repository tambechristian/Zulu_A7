{ AsarX4Fix3.pas -- 2026-11-16. The X1 designator text would not move by script (AsarX4Fix, AsarX4Fix2: the
  XLocation writes read back unchanged), and at (3.664, 17.118) it overlaps U10-1's mask opening. This hides X1's
  designator and places a free Top Overlay text "X1" (0.8 mm, 0.15 mm stroke, as the designator) with its anchor at
  (2.25, 17.35), clear of U10-1, X1-MP3 and the X2 mounting hole. No SendMessageToRobots (it crashes the scripting
  engine on Altium 26.11.1; Brd.AddPCBObject alone persists, as the copper scripts show).
  Refuses if a free "X1" text already exists. Run AsarX4Fix3 with asar_feather.PcbDoc focused. }

Procedure AsarX4Fix3;
Var
    Brd : IPCB_Board;
    CX1 : IPCB_Component;
    It : IPCB_BoardIterator;
    T : IPCB_Text;
    B : TCoordRect;
    Dup : Boolean;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus Rev_1 asar_feather.PcbDoc.'); Exit; End;
    CX1 := Brd.GetPcbComponentByRefDes('X1');
    If CX1 = Nil Then Begin ShowMessage('Refusing: X1 not found.'); Exit; End;
    Dup := False;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (Not T.InComponent) And (T.Text = 'X1') Then Dup := True;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Dup Then Begin ShowMessage('Refusing: a free X1 text already exists; nothing changed.'); Exit; End;
    CX1.BeginModify;
    CX1.NameOn := False;
    CX1.EndModify;
    T := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
    T.XLocation := Brd.XOrigin + MMsToCoord(2.25);
    T.YLocation := Brd.YOrigin + MMsToCoord(17.35);
    T.Layer := eTopOverlay;
    T.Text := 'X1';
    T.Size := MMsToCoord(0.8);
    T.Width := MMsToCoord(0.15);
    T.Rotation := 0;
    T.UseTTFonts := False;
    Brd.AddPCBObject(T);
    Brd.ViewManager_FullUpdate;
    B := T.BoundingRectangle;
    ShowMessage('X1 designator hidden; free text X1 box x ' + FloatToStr(CoordToMMs(B.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(B.Right - Brd.XOrigin)) +
        ', y ' + FloatToStr(CoordToMMs(B.Bottom - Brd.YOrigin)) + '..' + FloatToStr(CoordToMMs(B.Top - Brd.YOrigin)) + '. Repour, DRC, save.');
End;
