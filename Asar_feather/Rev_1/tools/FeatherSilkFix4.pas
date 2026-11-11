{ FeatherSilkFix4.pas -- third step: the five overlay marks FeatherSilkFix2 could not trim clean (no piece >= 0.1 mm
  clear of the pads) and that the DRC still flags. NudgeMarks moves each, as a whole, to the nearest clean spot
  (0.025 mm steps, up to 1 mm, eight directions; clean = 0.254 mm from every mask opening and every other silk
  object on its side). A mark with no clean spot within 1 mm is deleted.
  (Original header follows.)
  FeatherSilkFix3.pas -- second designator step after FeatherSilkFix2.pas (whose helpers are copied here):
  FixFeatherSilk2 hid 11 designators at their footprint text size. ShowSmaller re-shows each of them except X2
  (off the board, hidden on production too) by trying the eight auto-positions at the current size, then at
  1.0 mm and 0.8 mm text height (PCBWay's minimum, stroke 0.15 mm); the first clean spot is kept, else it stays
  hidden. (Original header follows.)
  FeatherSilkFix.pas -- 2026-10-23, clears the 65 Silk To Solder Mask violations of docs/drc_prerouting.drc.
  Run with asar_feather.PcbDoc focused, after FeatherPlace4 (U10 0.5 -> 0.25 mm north, off U2's top pad row):
    FixFeatherSilk2  (FeatherSilkFix.pas failed to compile: Near is a reserved word)
      1. Overlay tracks: every straight (horizontal or vertical) Top/Bottom Overlay track is cut back so no part of
         it comes within 0.254 mm (SilkToSolderMaskClearance) of a pad's mask opening (copper + 0.05 mm expansion,
         rule SolderMaskExpansion) on its side; through-hole pads count on both. The track is sampled every 0.01 mm
         along its length; the first clean run >= 0.1 mm replaces it, further runs become new free tracks. A track
         with no clean run is left and reported. This is the footprint outline marks of U2, U4, U10, X1 and L5.
      2. Designators: a shown designator whose box hits a pad's mask opening + 0.254 mm, another silkscreen object
         + 0.254 mm (SilkToSilkClearance) or the board edge - 0.25 mm is tried at the eight auto-positions around its
         part (top-centre first); the first clean one is kept. If none is clean the designator is hidden (NameOn
         False), as production did on 2026-09-11 (HideCrowdedDesignators): the part keeps its name in the netlist,
         BOM and pick-and-place; only the silkscreen text goes.
    Boxes are BoundingRectangle, so the test is stricter than the DRC's stroke geometry. }

Const
    MASK_EXP   = 0.05;
    SILK_MASK  = 0.254;
    SILK_SILK  = 0.254;
    MARGIN     = 0.02;
    EDGE_GAP   = 0.25;
    BOARD_W    = 50.8;
    BOARD_H    = 22.86;
    STEP       = 0.01;
    MIN_PIECE  = 0.1;

Var
    Brd : IPCB_Board;

Function FBrd : IPCB_Board;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
End;

Function IMin(A, B : Integer) : Integer;
Begin
    If A < B Then Result := A Else Result := B;
End;

Function IMax(A, B : Integer) : Integer;
Begin
    If A > B Then Result := A Else Result := B;
End;

Function Overlap(AL, AB, AR, AT, BL, BB, BR, BT : Integer) : Boolean;
Begin
    Result := (AL < BR) And (BL < AR) And (AB < BT) And (BB < AT);
End;

Function PadOnSide(P : IPCB_Pad; Lay : Integer) : Boolean;
Begin
    If P.Layer = eMultiLayer Then
        Result := True
    Else If Lay = eTopOverlay Then
        Result := P.Layer = eTopLayer
    Else
        Result := P.Layer = eBottomLayer;
End;

{ True if the box comes within mask expansion + 0.254 mm of a pad on the overlay's side }
Function HitsPad(L, B, R, T, Lay : Integer) : Boolean;
Var
    It : IPCB_BoardIterator;
    P  : IPCB_Pad;
    PR : TCoordRect;
    G  : Integer;
Begin
    Result := False;
    G := MMsToCoord(MASK_EXP + SILK_MASK + MARGIN);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If PadOnSide(P, Lay) Then
        Begin
            PR := P.BoundingRectangle;
            If Overlap(L, B, R, T, PR.Left - G, PR.Bottom - G, PR.Right + G, PR.Top + G) Then
            Begin
                Result := True;
                Break;
            End;
        End;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

{ True if the box comes within 0.254 mm of another shown silkscreen object on the same overlay }
Function HitsSilk(L, B, R, T, Lay : Integer; Me : IPCB_Text) : Boolean;
Var
    It : IPCB_BoardIterator;
    O  : IPCB_Primitive;
    C  : IPCB_Component;
    OBox : TCoordRect;
    G  : Integer;
Begin
    Result := False;
    G := MMsToCoord(SILK_SILK + MARGIN);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eTextObject));
    It.AddFilter_LayerSet(MkSet(Lay));
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        { component texts are checked below, through NameOn; here only tracks, arcs and free texts }
        If (O.ObjectId <> eTextObject) Or (Not O.InComponent) Then
        Begin
            OBox := O.BoundingRectangle;
            If Overlap(L, B, R, T, OBox.Left - G, OBox.Bottom - G, OBox.Right + G, OBox.Top + G) Then
            Begin
                Result := True;
                Break;
            End;
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Result Then Exit;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        If C.NameOn And (C.Name.Layer = Lay) And (C.Name.I_ObjectAddress <> Me.I_ObjectAddress) Then
        Begin
            OBox := C.Name.BoundingRectangle;
            If Overlap(L, B, R, T, OBox.Left - G, OBox.Bottom - G, OBox.Right + G, OBox.Top + G) Then
            Begin
                Result := True;
                Break;
            End;
        End;
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Function NameBad(C : IPCB_Component) : Boolean;
Var
    R : TCoordRect;
    E : Integer;
Begin
    R := C.Name.BoundingRectangle;
    E := MMsToCoord(EDGE_GAP);
    Result := (R.Left < Brd.XOrigin + E) Or (R.Bottom < Brd.YOrigin + E) Or
              (R.Right > Brd.XOrigin + MMsToCoord(BOARD_W) - E) Or (R.Top > Brd.YOrigin + MMsToCoord(BOARD_H) - E);
    If Not Result Then Result := HitsPad(R.Left, R.Bottom, R.Right, R.Top, C.Name.Layer);
    If Not Result Then Result := HitsSilk(R.Left, R.Bottom, R.Right, R.Top, C.Name.Layer, C.Name);
End;

Procedure SetAuto(C : IPCB_Component; P : Integer);
Begin
    { the auto-position is only re-applied when the part moves (FeatherSilk4.pas): nudge 1 unit and back }
    C.BeginModify;
    C.ChangeNameAutoposition(P);
    C.X := C.X + 1;
    C.EndModify;
    C.BeginModify;
    C.X := C.X - 1;
    C.EndModify;
End;

Function AutoPos(K : Integer) : Integer;
Begin
    Case K Of
        1 : Result := eAutoPos_TopCenter;
        2 : Result := eAutoPos_BottomCenter;
        3 : Result := eAutoPos_CenterLeft;
        4 : Result := eAutoPos_CenterRight;
        5 : Result := eAutoPos_TopLeft;
        6 : Result := eAutoPos_TopRight;
        7 : Result := eAutoPos_BottomLeft;
    Else
        Result := eAutoPos_BottomRight;
    End;
End;

Function AutoName(K : Integer) : String;
Begin
    Case K Of
        1 : Result := 'top-centre';
        2 : Result := 'bottom-centre';
        3 : Result := 'centre-left';
        4 : Result := 'centre-right';
        5 : Result := 'top-left';
        6 : Result := 'top-right';
        7 : Result := 'bottom-left';
    Else
        Result := 'bottom-right';
    End;
End;

{ cut one straight overlay track back from the pads; returns a log line, '' if it was already clean }
Function ClipTrack(Tr : IPCB_Track) : String;
Var
    It      : IPCB_BoardIterator;
    P       : IPCB_Pad;
    NearPads    : TInterfaceList;
    PR      : TCoordRect;
    Vert    : Boolean;
    G, A, Z, Fix, Pos0, S, N, I, J, RunStart, Len : Integer;
    Ok, Was : Boolean;
    Starts, Ends : TStringList;
    T2      : IPCB_Track;
    Lay     : Integer;
Begin
    Result := '';
    Lay := Tr.Layer;
    If Tr.X1 = Tr.X2 Then Vert := True
    Else If Tr.Y1 = Tr.Y2 Then Vert := False
    Else Exit;
    G := MMsToCoord(MASK_EXP + SILK_MASK + MARGIN) + Tr.Width Div 2;
    NearPads := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If PadOnSide(P, Lay) Then
        Begin
            PR := P.BoundingRectangle;
            If Overlap(IMin(Tr.X1, Tr.X2), IMin(Tr.Y1, Tr.Y2), IMax(Tr.X1, Tr.X2) + 1, IMax(Tr.Y1, Tr.Y2) + 1,
                       PR.Left - G, PR.Bottom - G, PR.Right + G, PR.Top + G) Then
                NearPads.Add(P);
        End;
        P := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If NearPads.Count = 0 Then
    Begin
        NearPads.Free;
        Exit;
    End;
    If Vert Then
    Begin
        A := IMin(Tr.Y1, Tr.Y2); Z := IMax(Tr.Y1, Tr.Y2); Fix := Tr.X1;
    End
    Else
    Begin
        A := IMin(Tr.X1, Tr.X2); Z := IMax(Tr.X1, Tr.X2); Fix := Tr.Y1;
    End;
    S := MMsToCoord(STEP);
    N := (Z - A) Div S;
    Starts := TStringList.Create;
    Ends := TStringList.Create;
    Was := False;
    RunStart := 0;
    For I := 0 To N + 1 Do
    Begin
        If I > N Then Pos0 := Z Else Pos0 := A + I * S;
        Ok := True;
        For J := 0 To NearPads.Count - 1 Do
        Begin
            P := NearPads.Items[J];
            PR := P.BoundingRectangle;
            If Vert Then
            Begin
                If (Fix > PR.Left - G) And (Fix < PR.Right + G) And (Pos0 > PR.Bottom - G) And (Pos0 < PR.Top + G) Then
                    Ok := False;
            End
            Else
            Begin
                If (Fix > PR.Bottom - G) And (Fix < PR.Top + G) And (Pos0 > PR.Left - G) And (Pos0 < PR.Right + G) Then
                    Ok := False;
            End;
        End;
        If Ok And (Not Was) Then RunStart := Pos0;
        If Was And ((Not Ok) Or (I > N)) Then
        Begin
            If Ok Then Len := Pos0 - RunStart Else Len := Pos0 - S - RunStart;
            If Len >= MMsToCoord(MIN_PIECE) Then
            Begin
                Starts.Add(IntToStr(RunStart));
                Ends.Add(IntToStr(RunStart + Len));
            End;
        End;
        If I > N Then Was := False Else Was := Ok;
    End;
    NearPads.Free;
    If (Starts.Count = 1) And (StrToInt(Starts[0]) = A) And (StrToInt(Ends[0]) = Z) Then
    Begin
        Starts.Free; Ends.Free;
        Exit;                                      { already clean }
    End;
    If Starts.Count = 0 Then
        Result := 'LEFT (no clean piece) '
    Else
    Begin
        Tr.BeginModify;
        If Vert Then
        Begin
            Tr.Y1 := StrToInt(Starts[0]); Tr.Y2 := StrToInt(Ends[0]);
        End
        Else
        Begin
            Tr.X1 := StrToInt(Starts[0]); Tr.X2 := StrToInt(Ends[0]);
        End;
        Tr.EndModify;
        For I := 1 To Starts.Count - 1 Do
        Begin
            T2 := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
            T2.Layer := Lay;
            T2.Width := Tr.Width;
            If Vert Then
            Begin
                T2.X1 := Fix; T2.X2 := Fix; T2.Y1 := StrToInt(Starts[I]); T2.Y2 := StrToInt(Ends[I]);
            End
            Else
            Begin
                T2.Y1 := Fix; T2.Y2 := Fix; T2.X1 := StrToInt(Starts[I]); T2.X2 := StrToInt(Ends[I]);
            End;
            Brd.AddPCBObject(T2);
            PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T2.I_ObjectAddress);
        End;
        Result := 'clipped to ' + IntToStr(Starts.Count) + ' piece(s) ';
    End;
    If Vert Then
        Result := Result + 'x ' + FloatToStr(CoordToMMs(Fix - Brd.XOrigin)) + ' y ' + FloatToStr(CoordToMMs(A - Brd.YOrigin)) +
                  '..' + FloatToStr(CoordToMMs(Z - Brd.YOrigin))
    Else
        Result := Result + 'y ' + FloatToStr(CoordToMMs(Fix - Brd.YOrigin)) + ' x ' + FloatToStr(CoordToMMs(A - Brd.XOrigin)) +
                  '..' + FloatToStr(CoordToMMs(Z - Brd.XOrigin));
    If Lay = eTopOverlay Then Result := 'Top    ' + Result Else Result := 'Bottom ' + Result;
    Starts.Free; Ends.Free;
End;

{ True if the box comes within 0.254 mm of any silkscreen object on the overlay other than the one at SkipAddr }
Function HitsSilkBut(L, B, R, T, Lay, SkipAddr : Integer) : Boolean;
Var
    It   : IPCB_BoardIterator;
    O    : IPCB_Primitive;
    C    : IPCB_Component;
    OBox : TCoordRect;
    G    : Integer;
Begin
    Result := False;
    G := MMsToCoord(SILK_SILK + MARGIN);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject, eArcObject, eTextObject));
    It.AddFilter_LayerSet(MkSet(Lay));
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        If (O.I_ObjectAddress <> SkipAddr) And ((O.ObjectId <> eTextObject) Or (Not O.InComponent)) Then
        Begin
            OBox := O.BoundingRectangle;
            If Overlap(L, B, R, T, OBox.Left - G, OBox.Bottom - G, OBox.Right + G, OBox.Top + G) Then
            Begin
                Result := True;
                Break;
            End;
        End;
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Result Then Exit;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do
    Begin
        If C.NameOn And (C.Name.Layer = Lay) Then
        Begin
            OBox := C.Name.BoundingRectangle;
            If Overlap(L, B, R, T, OBox.Left - G, OBox.Bottom - G, OBox.Right + G, OBox.Top + G) Then
            Begin
                Result := True;
                Break;
            End;
        End;
        C := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

{ the track on Lay whose end points are (X1,Y1)-(X2,Y2) mm from the board origin, either way round }
Function FindMark(Lay : Integer; X1, Y1, X2, Y2 : Double) : IPCB_Track;
Var
    It  : IPCB_BoardIterator;
    T   : IPCB_Track;
    Tol : Integer;
Begin
    Result := Nil;
    Tol := MMsToCoord(0.003);
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(Lay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If ((Abs(T.X1 - Brd.XOrigin - MMsToCoord(X1)) <= Tol) And (Abs(T.Y1 - Brd.YOrigin - MMsToCoord(Y1)) <= Tol) And
            (Abs(T.X2 - Brd.XOrigin - MMsToCoord(X2)) <= Tol) And (Abs(T.Y2 - Brd.YOrigin - MMsToCoord(Y2)) <= Tol)) Or
           ((Abs(T.X1 - Brd.XOrigin - MMsToCoord(X2)) <= Tol) And (Abs(T.Y1 - Brd.YOrigin - MMsToCoord(Y2)) <= Tol) And
            (Abs(T.X2 - Brd.XOrigin - MMsToCoord(X1)) <= Tol) And (Abs(T.Y2 - Brd.YOrigin - MMsToCoord(Y1)) <= Tol)) Then
        Begin
            Result := T;
            Break;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Function NudgeOne(Lay : Integer; X1, Y1, X2, Y2 : Double; What : String) : String;
Var
    T : IPCB_Track;
    D, K, DX, DY, Hw, S : Integer;
    L, B, R, Tp : Integer;
    Done : Boolean;
Begin
    T := FindMark(Lay, X1, Y1, X2, Y2);
    If T = Nil Then
    Begin
        Result := '  ' + What + ': not found';
        Exit;
    End;
    Hw := T.Width Div 2;
    S := MMsToCoord(0.025);
    Done := False;
    For D := 1 To 40 Do
        If Not Done Then
            For K := 1 To 8 Do
                If Not Done Then
                Begin
                    Case K Of
                        1 : Begin DX := 0;  DY := 1;  End;
                        2 : Begin DX := 0;  DY := -1; End;
                        3 : Begin DX := 1;  DY := 0;  End;
                        4 : Begin DX := -1; DY := 0;  End;
                        5 : Begin DX := 1;  DY := 1;  End;
                        6 : Begin DX := -1; DY := 1;  End;
                        7 : Begin DX := 1;  DY := -1; End;
                    Else
                        Begin DX := -1; DY := -1; End;
                    End;
                    DX := DX * D * S;
                    DY := DY * D * S;
                    L := IMin(T.X1, T.X2) - Hw + DX;
                    R := IMax(T.X1, T.X2) + Hw + DX;
                    B := IMin(T.Y1, T.Y2) - Hw + DY;
                    Tp := IMax(T.Y1, T.Y2) + Hw + DY;
                    If (Not HitsPad(L, B, R, Tp, Lay)) And (Not HitsSilkBut(L, B, R, Tp, Lay, T.I_ObjectAddress)) Then
                    Begin
                        T.BeginModify;
                        T.X1 := T.X1 + DX; T.X2 := T.X2 + DX;
                        T.Y1 := T.Y1 + DY; T.Y2 := T.Y2 + DY;
                        T.EndModify;
                        Done := True;
                        Result := '  ' + What + ': moved ' + FloatToStr(CoordToMMs(DX)) + ', ' + FloatToStr(CoordToMMs(DY)) + ' mm';
                    End;
                End;
    If Not Done Then
    Begin
        Brd.RemovePCBObject(T);
        Result := '  ' + What + ': no clean spot within 1 mm, deleted';
    End;
End;

Procedure NudgeMarks;
Var
    Log : TStringList;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    Log := TStringList.Create;
    Log.Add(NudgeOne(eTopOverlay, 12.05, 12.3, 12.45, 12.3, 'U10 pin-1 tick'));
    Log.Add(NudgeOne(eTopOverlay, 10, 12.6, 12, 12.6, 'U10 south outline'));
    Log.Add(NudgeOne(eTopOverlay, 40.7, 17.55, 40.7, 18.05, 'U4 pin-1 tick'));
    Log.Add(NudgeOne(eTopOverlay, 8.45, 10.65, 8.45, 11.15, 'X1 mark at x 8.45'));
    Log.Add(NudgeOne(eBottomOverlay, 17.35, 4.12, 18.15, 4.12, 'L5 centre line'));
    Brd.ViewManager_FullUpdate;
    Log.SaveToFile('C:\Users\tambe\Documents\Electronics\Zulu_A7\Asar_feather\docs\silk_fix4.log');
    ShowMessage(Log.Text + 'Save, then re-run the DRC.');
    Log.Free;
End;
