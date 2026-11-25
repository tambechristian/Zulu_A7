{ NoPmodX3Probe.pas -- read-only: list X3's primitives (object id, layer, coordinates) and Top Overlay tracks near BTN. }
Procedure ProbeX3;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    GI : IPCB_GroupIterator;
    It : IPCB_BoardIterator;
    O : IPCB_Primitive;
    Tk : IPCB_Track;
    S : String;
    n : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    Cm := Brd.GetPcbComponentByRefDes('X3');
    S := ''; n := 0;
    GI := Cm.GroupIterator_Create;
    GI.SetState_FilterAll;
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        n := n + 1;
        If O.ObjectId = eTrackObject Then
        Begin
            Tk := O;
            S := S + 'T L' + IntToStr(Tk.Layer) + ' ' + FormatFloat('0.00', CoordToMMs(Tk.X1 - Brd.XOrigin)) + ',' + FormatFloat('0.00', CoordToMMs(Tk.Y1 - Brd.YOrigin)) + '-' + FormatFloat('0.00', CoordToMMs(Tk.X2 - Brd.XOrigin)) + ',' + FormatFloat('0.00', CoordToMMs(Tk.Y2 - Brd.YOrigin)) + '; ';
        End
        Else S := S + 'id' + IntToStr(O.ObjectId) + ' ';
        O := GI.NextPCBObject;
    End;
    Cm.GroupIterator_Destroy(GI);
    S := S + ' || board overlay near (17.76,5.64): ';
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    Tk := It.FirstPCBObject;
    While Tk <> Nil Do
    Begin
        If (Abs(CoordToMMs(Tk.X2 - Brd.XOrigin) - 17.76) < 0.05) Or (Abs(CoordToMMs(Tk.X1 - Brd.XOrigin) - 17.76) < 0.05) Then
            S := S + FormatFloat('0.000', CoordToMMs(Tk.X1 - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Tk.Y1 - Brd.YOrigin)) + '-' + FormatFloat('0.000', CoordToMMs(Tk.X2 - Brd.XOrigin)) + ',' + FormatFloat('0.000', CoordToMMs(Tk.Y2 - Brd.YOrigin)) + ' comp=' + BoolToStr(Tk.InComponent, True) + '; ';
        Tk := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    ShowMessage(IntToStr(n) + ' prims: ' + S);
End;
