{ FeatherStemmaParts.pas -- 2026-11-06, the STEMMA QT connector X5 and the parts that make room for it.
  X5 goes on Top at the right end, mouth towards x = 50.8 mm. R80 and R81 move right of BTN, R82 stands at the end of
  them, R84 moves to the free patch left of BTN, LD0 shifts 0.90 mm towards U3, BTN's label goes below the part. Coordinates are board-relative mm and
  equal tools/route/stage7/final/model.stemma.json. Each part gets its rotation, then is shifted so the named pad lands
  on the given point. Refuses unless X5 is present and R80 is still where the routed board had it, so it runs once.
  Run StemmaParts with asar_feather.PcbDoc focused, then the copper script S7Q. }

Var
    Brd : IPCB_Board;
    NDone : Integer;
    Missing : String;

Procedure Place(D : String; Rot : Double; PN : String; PX, PY : Double);
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    FX, FY : TCoord;
    Got : Boolean;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then
    Begin
        Missing := Missing + D + ' ';
        Exit;
    End;
    C.BeginModify;
    If C.Layer <> eTopLayer Then C.Layer := eTopLayer;
    C.Rotation := Rot;
    C.EndModify;
    Got := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While (P <> Nil) And (Not Got) Do
    Begin
        If P.Name = PN Then
        Begin
            FX := P.X;
            FY := P.Y;
            Got := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Not Got Then
    Begin
        Missing := Missing + D + '.' + PN + ' ';
        Exit;
    End;
    C.BeginModify;
    C.X := C.X + (Brd.XOrigin + MMsToCoord(PX) - FX);
    C.Y := C.Y + (Brd.YOrigin + MMsToCoord(PY) - FY);
    C.EndModify;
    NDone := NDone + 1;
End;

Procedure StemmaParts;
Var
    Doc : IDocument;
    C   : IPCB_Component;
    It  : IPCB_GroupIterator;
    P   : IPCB_Pad;
    Old : Boolean;
    B   : TCoordRect;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd.GetPcbComponentByRefDes('X5') = Nil Then
    Begin
        ShowMessage('Refusing: X5 is not on the board; run the ECO first.');
        Exit;
    End;
    Old := False;
    C := Brd.GetPcbComponentByRefDes('R80');
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = '1') And (Abs(CoordToMMs(P.X - Brd.XOrigin) - 46.43) < 0.01) And (Abs(CoordToMMs(P.Y - Brd.YOrigin) - 7.73) < 0.01) Then
            Old := True;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Not Old Then
    Begin
        ShowMessage('Refusing: R80 pad 1 is not at 46.43, 7.73; the parts look moved already.');
        Exit;
    End;
    NDone := 0;
    Missing := '';
    PCBServer.PreProcess;
    Place('X5', 90, '1', 45.725, 8.2);
    Place('R80', 180, '1', 48.05, 4.65);
    Place('R81', 180, '1', 48.05, 5.80);
    Place('R82', 90, '1', 49.55, 4.40);
    Place('R84', 0, '1', 38.55, 5.90);
    Place('LD0', 0, '1', 44.2749, 9.7249);
    PCBServer.PostProcess;
    C := Brd.GetPcbComponentByRefDes('X5');
    C.BeginModify;
    C.NameOn := False;
    C.CommentOn := False;
    C.EndModify;
    C := Brd.GetPcbComponentByRefDes('BTN');
    C.BeginModify;
    C.ChangeNameAutoposition(eAutoPos_BottomCenter);
    C.X := C.X + 1;
    C.EndModify;
    C.BeginModify;
    C.X := C.X - 1;
    C.EndModify;
    B := C.Name.BoundingRectangle;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Placed ' + IntToStr(NDone) + ' of 6 parts. Missing:' + Missing + '. BTN label x ' + FloatToStr(CoordToMMs(B.Left - Brd.XOrigin)) + '..' + FloatToStr(CoordToMMs(B.Right - Brd.XOrigin)) + ' y ' + FloatToStr(CoordToMMs(B.Bottom - Brd.YOrigin)) + '..' + FloatToStr(CoordToMMs(B.Top - Brd.YOrigin)) + '. Now run PlaceS7Q.');
End;
