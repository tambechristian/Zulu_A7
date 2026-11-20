{ AsarU2Pin1.pas -- 2026-11-20: restore U2's pin-1 silk mark.
  tools/FeatherSilkFix4.pas deleted it on 2026-10-23 (logged as "X1 mark at x 8.45: no clean spot within 1 mm").
  The mark is the old library QFN-64-9X9-P0.5-EP4.35 line: Top Overlay, 0.15 mm, footprint-relative
  (-5.25, +3.25) -> (-5.25, +3.75), beside pads 1 and 2; on the board (8.45, 10.65) -> (8.45, 11.15).
  Run RestoreU2Pin1 with asar_feather.PcbDoc focused, then File > Save. Refuses if U2 is not where it was measured
  (13.7, 7.4, rotation 0, Top, QFN-64-9X9-P0.5-EP4.35) or if U2 already owns a Top Overlay track at the mark. }

Procedure RestoreU2Pin1;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    Cm  : IPCB_Component;
    GI  : IPCB_GroupIterator;
    O   : IPCB_Primitive;
    Tr  : IPCB_Track;
    nTicks, nAfter : Integer;
    x1, y1, x2, y2 : Integer;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Cm := Brd.GetPcbComponentByRefDes('U2');
    If Cm = Nil Then
    Begin
        ShowMessage('Refusing: U2 not found; nothing changed.');
        Exit;
    End;
    If (Abs(CoordToMMs(Cm.X - Brd.XOrigin) - 13.7) > 0.002) Or (Abs(CoordToMMs(Cm.Y - Brd.YOrigin) - 7.4) > 0.002) Then
    Begin
        ShowMessage('Refusing: U2 is not at (13.7, 7.4); nothing changed.');
        Exit;
    End;
    If (Abs(Cm.Rotation) > 0.01) Or (Cm.Layer <> eTopLayer) Or (Cm.Pattern <> 'QFN-64-9X9-P0.5-EP4.35') Then
    Begin
        ShowMessage('Refusing: U2 is not QFN-64-9X9-P0.5-EP4.35 on Top at rotation 0; nothing changed.');
        Exit;
    End;
    x1 := Cm.X + MMsToCoord(-5.25); y1 := Cm.Y + MMsToCoord(3.25);
    x2 := Cm.X + MMsToCoord(-5.25); y2 := Cm.Y + MMsToCoord(3.75);
    nTicks := 0;
    GI := Cm.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        If O.Layer = eTopOverlay Then
        Begin
            nTicks := nTicks + 1;
            If (Abs(O.X1 - x1) < 1000) And (Abs(O.X2 - x2) < 1000) Then
            Begin
                Cm.GroupIterator_Destroy(GI);
                ShowMessage('Refusing: U2 already has a Top Overlay track on x = 8.45 mm; nothing changed.');
                Exit;
            End;
        End;
        O := GI.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(GI);
    If nTicks <> 8 Then
    Begin
        ShowMessage('Refusing: U2 has ' + IntToStr(nTicks) + ' Top Overlay tracks, expected the 8 corner ticks; nothing changed.');
        Exit;
    End;

    PCBServer.PreProcess;
    Tr := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Tr.X1 := x1; Tr.Y1 := y1; Tr.X2 := x2; Tr.Y2 := y2;
    Tr.Layer := eTopOverlay;
    Tr.Width := MMsToCoord(0.15);
    Cm.AddPCBObject(Tr);
    Brd.AddPCBObject(Tr);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;

    nAfter := 0;
    GI := Cm.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        If O.Layer = eTopOverlay Then nAfter := nAfter + 1;
        O := GI.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(GI);
    ShowMessage('U2 pin-1 mark placed: Top Overlay 0.15 mm from (' + FloatToStr(CoordToMMs(x1 - Brd.XOrigin)) + ', ' +
        FloatToStr(CoordToMMs(y1 - Brd.YOrigin)) + ') to (' + FloatToStr(CoordToMMs(x2 - Brd.XOrigin)) + ', ' +
        FloatToStr(CoordToMMs(y2 - Brd.YOrigin)) + '). U2 now owns ' + IntToStr(nAfter) +
        ' Top Overlay tracks (expected 9). Run DRC, then File > Save.');
End;
