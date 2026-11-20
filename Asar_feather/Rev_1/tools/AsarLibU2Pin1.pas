{ AsarLibU2Pin1.pas -- 2026-11-20: the pin-1 mark for QFN-64-9X9-P0.5-EP4.35 in asar_feather.PcbLib (U2, FT2232HQ).
  Altium 26.11.1 cannot ADD primitives in a PcbLib script, so the new track is made in the GUI first: select one of the
  footprint's 8 Top Overlay corner ticks and Edit > Duplicate it anywhere. MovePin1Mark then moves the one Top Overlay
  track that is not a corner tick to the mark: (-5.25, +3.25) -> (-5.25, +3.75), 0.15 mm, beside pads 1 and 2 -- the
  same track tools/AsarU2Pin1.pas placed on the board and the old library had before 2026-11-19.
  Coordinates are relative to the footprint origin, measured from pad 1 at (-4.425, +3.75) (checked against pad 2 at
  (-4.425, +3.25)). Refuses unless asar_feather.PcbLib is focused, the footprint has exactly 9 Top Overlay tracks of
  which 8 are the known corner ticks, and no track is at the mark yet. Then File > Save the library. }

Var
    OffX, OffY : TCoord;

Function CloseTo(A : TCoord; V : Double) : Boolean;
Begin
    Result := Abs(CoordToMMs(A) - V) < 0.01;
End;

Function SegIs(T : IPCB_Track; X1, Y1, X2, Y2 : Double) : Boolean;
Begin
    Result := (CloseTo(T.X1 - OffX, X1) And CloseTo(T.Y1 - OffY, Y1) And CloseTo(T.X2 - OffX, X2) And CloseTo(T.Y2 - OffY, Y2)) Or
              (CloseTo(T.X1 - OffX, X2) And CloseTo(T.Y1 - OffY, Y2) And CloseTo(T.X2 - OffX, X1) And CloseTo(T.Y2 - OffY, Y1));
End;

Function IsTick(T : IPCB_Track) : Boolean;
Begin
    Result := SegIs(T, -4.6, 4.34, -4.6, 4.6) Or SegIs(T, -4.6, 4.6, -4.34, 4.6) Or
              SegIs(T, -4.6, -4.6, -4.34, -4.6) Or SegIs(T, -4.6, -4.6, -4.6, -4.34) Or
              SegIs(T, 4.34, 4.6, 4.6, 4.6) Or SegIs(T, 4.6, 4.34, 4.6, 4.6) Or
              SegIs(T, 4.34, -4.6, 4.6, -4.6) Or SegIs(T, 4.6, -4.6, 4.6, -4.34);
End;

Procedure MovePin1Mark;
Var
    Lib : IPCB_Library;
    It : IPCB_LibraryIterator;
    Fp, Hit : IPCB_LibComponent;
    GI : IPCB_GroupIterator;
    O : IPCB_Primitive;
    P, P1, P2 : IPCB_Pad;
    T, NewT : IPCB_Track;
    nAll, nTick, nOther : Integer;
    Fn : String;
Begin
    Lib := PCBServer.GetCurrentPCBLibrary;
    If Lib = Nil Then Begin ShowMessage('Refusing: no PCB library is focused.'); Exit; End;
    Fn := Lib.Board.FileName;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbLib', Fn) = 0 Then
    Begin ShowMessage('Refusing: the focused library is ' + Fn); Exit; End;
    Hit := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = 'QFN-64-9X9-P0.5-EP4.35' Then Hit := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Hit = Nil Then Begin ShowMessage('QFN-64-9X9-P0.5-EP4.35 not found; nothing changed.'); Exit; End;

    P1 := Nil; P2 := Nil;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(ePadObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        P := O;
        If P.Name = '1' Then P1 := P;
        If P.Name = '2' Then P2 := P;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (P1 = Nil) Or (P2 = Nil) Then Begin ShowMessage('Refusing: pads 1 and 2 not found.'); Exit; End;
    OffX := P1.X - MMsToCoord(-4.425);
    OffY := P1.Y - MMsToCoord(3.75);
    If (Not CloseTo(P2.X - OffX, -4.425)) Or (Not CloseTo(P2.Y - OffY, 3.25)) Then
    Begin ShowMessage('Refusing: pad 2 is not 0.5 mm below pad 1; unexpected footprint.'); Exit; End;

    nAll := 0; nTick := 0; nOther := 0; NewT := Nil;
    GI := Hit.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        T := O;
        If T.Layer = eTopOverlay Then
        Begin
            nAll := nAll + 1;
            If SegIs(T, -5.25, 3.25, -5.25, 3.75) Then
            Begin
                Hit.GroupIterator_Destroy(GI);
                ShowMessage('Refusing: the pin-1 mark is already there; nothing changed.');
                Exit;
            End;
            If IsTick(T) Then nTick := nTick + 1
            Else
            Begin
                nOther := nOther + 1;
                NewT := T;
            End;
        End;
        O := GI.NextPCBObject;
    End;
    Hit.GroupIterator_Destroy(GI);
    If (nAll <> 9) Or (nTick <> 8) Or (nOther <> 1) Then
    Begin
        ShowMessage('Refusing: Top Overlay tracks ' + IntToStr(nAll) + ', corner ticks ' + IntToStr(nTick) + ', others ' +
            IntToStr(nOther) + ' (expected 9 / 8 / 1: duplicate one corner tick first); nothing changed.');
        Exit;
    End;

    NewT.BeginModify;
    NewT.X1 := OffX + MMsToCoord(-5.25); NewT.Y1 := OffY + MMsToCoord(3.25);
    NewT.X2 := OffX + MMsToCoord(-5.25); NewT.Y2 := OffY + MMsToCoord(3.75);
    NewT.Width := MMsToCoord(0.15);
    NewT.EndModify;
    Lib.CurrentComponent := Hit;
    Lib.Board.ViewManager_FullUpdate;
    ShowMessage('QFN-64 pin-1 mark set: Top Overlay 0.15 mm (' + FloatToStr(CoordToMMs(NewT.X1 - OffX)) + ', ' +
        FloatToStr(CoordToMMs(NewT.Y1 - OffY)) + ') -> (' + FloatToStr(CoordToMMs(NewT.X2 - OffX)) + ', ' +
        FloatToStr(CoordToMMs(NewT.Y2 - OffY)) + ') from the footprint origin. File > Save the library.');
End;
