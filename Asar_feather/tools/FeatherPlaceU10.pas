{ FeatherPlaceU10.pas -- 2026-10-23. Places only the restored U10/R96/R98 at their tools/placement.json points
  (PlaceAt copied from the generated FeatherPlace.pas). Each part goes to its side and rotation, then is shifted so the
  centre of its pads' bounding box lands on the planned point (padless parts: the origin does). }

Var
    Brd : IPCB_Board;
    NDone : Integer;
    Missing : String;

Procedure PlaceAt(D : String; Lay : Integer; Rot : Double; PX, PY : Double);
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    X0, Y0, X1, Y1 : TCoord;
    Got : Boolean;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then Begin Missing := Missing + D + ' '; Exit; End;
    C.BeginModify;
    If (Lay = 1) And (C.Layer <> eBottomLayer) Then C.Layer := eBottomLayer;
    If (Lay = 0) And (C.Layer <> eTopLayer) Then C.Layer := eTopLayer;
    C.Rotation := Rot;
    C.EndModify;
    Got := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If Not Got Then Begin X0 := P.X; X1 := P.X; Y0 := P.Y; Y1 := P.Y; Got := True; End;
        If P.X < X0 Then X0 := P.X;
        If P.X > X1 Then X1 := P.X;
        If P.Y < Y0 Then Y0 := P.Y;
        If P.Y > Y1 Then Y1 := P.Y;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    C.BeginModify;
    If Got Then
    Begin
        C.X := C.X + (MMsToCoord(PX) - (X0 + X1) Div 2);
        C.Y := C.Y + (MMsToCoord(PY) - (Y0 + Y1) Div 2);
    End
    Else
    Begin
        C.X := MMsToCoord(PX);
        C.Y := MMsToCoord(PY);
    End;
    C.EndModify;
    NDone := NDone + 1;
End;

Procedure PlaceU10R96R98;
Var
    Doc : IDocument;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    NDone := 0;
    Missing := '';
    PCBServer.PreProcess;
    PlaceAt('U10', 1, 90, 6.420, 17.720);
    PlaceAt('R96', 1, 0, 9.770, 12.570);
    PlaceAt('R98', 1, 0, 12.670, 8.270);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Placed ' + IntToStr(NDone) + ' parts. Missing: ' + Missing);
End;
