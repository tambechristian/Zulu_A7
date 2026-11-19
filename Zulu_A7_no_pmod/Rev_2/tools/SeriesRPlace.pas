{ SeriesRPlace.pas -- GENERATED 2026-11-13 from si/series_r/dq_series_r_plan.json (md5 7c2b8ae6); do not edit by hand.
  Places R119-R134 pad-anchored: side set, rotation tried as planned then +90/+180/+270 until pad 2 also lands within
  0.005 mm of the plan (pad 1 = SDRAM-Dn); designator hidden. Moves U1s designator to (39.7000, 16.5500) rot 0.
  Refuses unless every R is still parked off-board (x > 100 mm). Every pad is re-checked and reported. Run SeriesRPlace, check, save. }

Var
    Brd : IPCB_Board;
    Report : String;
    NDone, NBad : Integer;

Function PadXY(C : IPCB_Component; PN : String; Var X, Y : Double) : Boolean;
Var
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
Begin
    Result := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = PN Then
        Begin
            X := CoordToMMs(P.X - Brd.XOrigin); Y := CoordToMMs(P.Y - Brd.YOrigin); Result := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Procedure Place(D : String; Bottom : Boolean; Rot, X1, Y1, X2, Y2 : Double);
Var
    C : IPCB_Component;
    k : Integer;
    px, py, qx, qy : Double;
    ok : Boolean;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then Begin Report := Report + D + ' missing; '; NBad := NBad + 1; Exit; End;
    C.BeginModify;
    If Bottom Then C.Layer := eBottomLayer Else C.Layer := eTopLayer;
    C.NameOn := False;
    C.EndModify;
    ok := False; k := 0;
    While (Not ok) And (k < 4) Do
    Begin
        C.BeginModify; C.Rotation := Rot + 90 * k; C.EndModify;
        PadXY(C, '1', px, py);
        C.BeginModify; C.X := C.X + MMsToCoord(X1 - px); C.Y := C.Y + MMsToCoord(Y1 - py); C.EndModify;
        PadXY(C, '1', px, py); PadXY(C, '2', qx, qy);
        ok := (Abs(px - X1) < 0.005) And (Abs(py - Y1) < 0.005) And (Abs(qx - X2) < 0.005) And (Abs(qy - Y2) < 0.005);
        k := k + 1;
    End;
    If ok Then NDone := NDone + 1 Else Begin NBad := NBad + 1; Report := Report + D + ' pad1 ' + FormatFloat('0.0000', px) + ',' + FormatFloat('0.0000', py) + ' pad2 ' + FormatFloat('0.0000', qx) + ',' + FormatFloat('0.0000', qy) + '; '; End;
    If ok And (k > 1) Then Report := Report + D + ' needed rot+' + IntToStr(90 * (k - 1)) + '; ';
End;

Function Parked(D : String) : Boolean;
Var
    C : IPCB_Component;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    Result := (C <> Nil) And (CoordToMMs(C.X - Brd.XOrigin) > 100);
End;

Procedure SeriesRPlace;
Var
    Doc : IDocument;
    U : IPCB_Component;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin ShowMessage('Refusing: focus Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc first.'); Exit; End;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Not (Parked('R119') And Parked('R120') And Parked('R121') And Parked('R122') And Parked('R123') And Parked('R124') And Parked('R125') And Parked('R126') And Parked('R127') And Parked('R128') And Parked('R129') And Parked('R130') And Parked('R131') And Parked('R132') And Parked('R133') And Parked('R134')) Then
    Begin ShowMessage('Refusing: R119-R134 are not all parked off-board (x > 100 mm); nothing changed.'); Exit; End;
    Report := ''; NDone := 0; NBad := 0;
    PCBServer.PreProcess;
    Place('R119', True, 0, 37.9499, 5.1701, 38.5499, 5.1701);
    Place('R120', True, 0, 36.3500, 5.1701, 36.9500, 5.1701);
    Place('R121', True, 270, 35.5501, 5.2101, 35.5501, 4.6101);
    Place('R122', True, 0, 33.9499, 5.1701, 34.5499, 5.1701);
    Place('R123', True, 180, 33.1501, 5.1701, 32.5501, 5.1701);
    Place('R124', True, 270, 31.5501, 5.2101, 31.5501, 4.6101);
    Place('R125', True, 270, 30.7500, 5.2101, 30.7500, 4.6101);
    Place('R126', True, 0, 29.1501, 5.2101, 29.7501, 5.2101);
    Place('R127', False, 0, 38.9000, 13.6000, 39.5000, 13.6000);
    Place('R128', True, 0, 41.7500, 12.9500, 42.3500, 12.9500);
    Place('R129', False, 0, 38.9100, 14.3600, 39.5100, 14.3600);
    Place('R130', False, 0, 39.1000, 14.9200, 39.7000, 14.9200);
    Place('R131', False, 0, 38.9000, 15.8000, 39.5000, 15.8000);
    Place('R132', False, 180, 39.0500, 16.3035, 38.4500, 16.3035);
    Place('R133', True, 0, 45.3000, 17.1500, 45.9000, 17.1500);
    Place('R134', True, 0, 46.5000, 16.8000, 47.1000, 16.8000);
    U := Brd.GetPcbComponentByRefDes('U1');
    If U = Nil Then Report := Report + 'U1 missing; ' Else
    Begin
        U.BeginModify;
        U.NameAutoPosition := eAutoPos_Manual;
        U.Name.BeginModify;
        U.Name.XLocation := Brd.XOrigin + MMsToCoord(39.7000);
        U.Name.YLocation := Brd.YOrigin + MMsToCoord(16.5500);
        U.Name.Rotation := 0;
        U.Name.EndModify;
        U.EndModify;
        Report := Report + 'U1 designator at ' + FormatFloat('0.0000', CoordToMMs(U.Name.XLocation - Brd.XOrigin)) + ',' + FormatFloat('0.0000', CoordToMMs(U.Name.YLocation - Brd.YOrigin)) + '; ';
    End;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Placed ' + IntToStr(NDone) + ' of 16; off plan ' + IntToStr(NBad) + '. ' + Report + ' Undo (Ctrl+Z) if anything is off; else save.');
End;
