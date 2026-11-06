{ Apply the Stage 13 U1 pad and placed-fanout net permutation atomically. }

Function S13SamePoint(A, B, X, Y : Double) : Boolean;
Begin
    Result := (Abs(A - X) < 0.001) And (Abs(B - Y) < 0.001);
End;

Function S13SameTrack(T : IPCB_Track; X1, Y1, X2, Y2 : Double) : Boolean;
Var
    AX, AY, BX, BY : Double;
Begin
    AX := CoordToMMs(T.X1); AY := CoordToMMs(T.Y1);
    BX := CoordToMMs(T.X2); BY := CoordToMMs(T.Y2);
    Result := (S13SamePoint(AX, AY, X1, Y1) And S13SamePoint(BX, BY, X2, Y2)) Or
              (S13SamePoint(AX, AY, X2, Y2) And S13SamePoint(BX, BY, X1, Y1));
End;

Function S13PadState(PadName, OldNet, NewNet : String) : Integer;
Var
    C : IPCB_Component;
    It : IPCB_GroupIterator;
    P : IPCB_Pad;
    Hits : Integer;
Begin
    Result := 0;
    C := Brd.GetPcbComponentByRefDes('U1');
    If C = Nil Then Exit;
    Hits := 0;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = PadName Then
        Begin
            Hits := Hits + 1;
            If P.Net = Nil Then Result := -1
            Else If P.Net.Name = OldNet Then Result := 1
            Else If P.Net.Name = NewNet Then Result := 2
            Else Result := -1;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Hits <> 1 Then Result := -1;
End;

Function S13TrackState(OldNet, NewNet : String; X1, Y1, X2, Y2 : Double) : Integer;
Var
    It : IPCB_BoardIterator;
    T : IPCB_Track;
    Hits : Integer;
    Nm : String;
Begin
    Result := 0;
    Hits := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopLayer));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If S13SameTrack(T, X1, Y1, X2, Y2) Then
        Begin
            Hits := Hits + 1;
            Nm := ''; If T.Net <> Nil Then Nm := T.Net.Name;
            If Nm = OldNet Then Result := 1
            Else If Nm = NewNet Then Result := 2
            Else Result := -1;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Hits <> 1 Then Result := -1;
End;

Function S13ViaState(OldNet, NewNet : String; X, Y : Double) : Integer;
Var
    It : IPCB_BoardIterator;
    V : IPCB_Via;
    Hits : Integer;
    Nm : String;
Begin
    Result := 0;
    Hits := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        If S13SamePoint(CoordToMMs(V.X), CoordToMMs(V.Y), X, Y) And
           (V.LowLayer = eTopLayer) And (V.HighLayer = eBottomLayer) Then
        Begin
            Hits := Hits + 1;
            Nm := ''; If V.Net <> Nil Then Nm := V.Net.Name;
            If Nm = OldNet Then Result := 1
            Else If Nm = NewNet Then Result := 2
            Else Result := -1;
        End;
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Hits <> 1 Then Result := -1;
End;

Procedure S13Count(State : Integer; Var OldCount, NewCount : Integer; Var Bad : Boolean);
Begin
    If State = 1 Then OldCount := OldCount + 1
    Else If State = 2 Then NewCount := NewCount + 1
    Else Bad := True;
End;

Function S13SetPad(PadName, OldNet, NewNet : String) : Boolean;
Var
    C : IPCB_Component;
    It : IPCB_GroupIterator;
    P, Hit : IPCB_Pad;
    N : IPCB_Net;
Begin
    Result := False;
    C := Brd.GetPcbComponentByRefDes('U1');
    N := NetByName(NewNet);
    If (C = Nil) Or (N = Nil) Then Exit;
    Hit := Nil;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If (P.Name = PadName) And (P.Net <> Nil) And (P.Net.Name = OldNet) Then Hit := P;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Hit = Nil Then Exit;
    Hit.BeginModify;
    Hit.Net := N;
    N.AddPCBObject(Hit);
    Hit.EndModify;
    Result := True;
End;

Function S13SetTrack(OldNet, NewNet : String; X1, Y1, X2, Y2 : Double) : Boolean;
Var
    It : IPCB_BoardIterator;
    T, Hit : IPCB_Track;
    N : IPCB_Net;
Begin
    Result := False;
    N := NetByName(NewNet);
    If N = Nil Then Exit;
    Hit := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(MkSet(eTopLayer));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If S13SameTrack(T, X1, Y1, X2, Y2) And
           (T.Net <> Nil) And (T.Net.Name = OldNet) Then Hit := T;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Hit = Nil Then Exit;
    Hit.BeginModify;
    Hit.Net := N;
    N.AddPCBObject(Hit);
    Hit.EndModify;
    Result := True;
End;

Function S13SetVia(OldNet, NewNet : String; X, Y : Double) : Boolean;
Var
    It : IPCB_BoardIterator;
    V, Hit : IPCB_Via;
    N : IPCB_Net;
Begin
    Result := False;
    N := NetByName(NewNet);
    If N = Nil Then Exit;
    Hit := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eViaObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    V := It.FirstPCBObject;
    While V <> Nil Do
    Begin
        If S13SamePoint(CoordToMMs(V.X), CoordToMMs(V.Y), X, Y) And
           (V.LowLayer = eTopLayer) And (V.HighLayer = eBottomLayer) And
           (V.Net <> Nil) And (V.Net.Name = OldNet) Then Hit := V;
        V := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Hit = Nil Then Exit;
    Hit.BeginModify;
    Hit.Net := N;
    N.AddPCBObject(Hit);
    Hit.EndModify;
    Result := True;
End;

Procedure Stage13Prepare;
Var
    OldCount, NewCount, Applied : Integer;
    Bad, Ok : Boolean;
Begin
    Brd := BoardOrNil;
    If Brd = Nil Then Exit;
    OldCount := 0; NewCount := 0; Bad := False;

    S13Count(S13PadState('E19', 'JA8', 'CHAN12'), OldCount, NewCount, Bad);
    S13Count(S13PadState('G17', 'JA3', 'CHAN7'), OldCount, NewCount, Bad);
    S13Count(S13PadState('H19', 'CHAN7', 'CHAN13'), OldCount, NewCount, Bad);
    S13Count(S13PadState('K17', 'CHAN11', 'UART_FT_TXD'), OldCount, NewCount, Bad);
    S13Count(S13PadState('K18', 'UART_FT_TXD', 'CHAN11'), OldCount, NewCount, Bad);
    S13Count(S13PadState('N17', 'BTN', 'LED0_B'), OldCount, NewCount, Bad);
    S13Count(S13PadState('N19', 'LED0_B', 'BTN'), OldCount, NewCount, Bad);
    S13Count(S13PadState('P17', 'FT-PWREN#', 'LED0_R'), OldCount, NewCount, Bad);
    S13Count(S13PadState('P19', 'LED0_R', 'FT-PWREN#'), OldCount, NewCount, Bad);
    S13Count(S13PadState('R19', 'CHAN28', 'JA7'), OldCount, NewCount, Bad);
    S13Count(S13PadState('T17', 'JA7', 'CHAN28'), OldCount, NewCount, Bad);
    S13Count(S13PadState('W18', 'CHAN13', 'JA3'), OldCount, NewCount, Bad);
    S13Count(S13PadState('W19', 'CHAN12', 'JA8'), OldCount, NewCount, Bad);

    S13Count(S13TrackState('JA3', 'CHAN7', 49.4001, 13.4000, 49.9000, 13.4000), OldCount, NewCount, Bad);
    S13Count(S13ViaState('JA3', 'CHAN7', 49.4001, 13.4000), OldCount, NewCount, Bad);
    S13Count(S13TrackState('CHAN11', 'UART_FT_TXD', 49.4001, 11.8999, 49.9000, 11.8999), OldCount, NewCount, Bad);
    S13Count(S13ViaState('CHAN11', 'UART_FT_TXD', 49.4001, 11.8999), OldCount, NewCount, Bad);
    S13Count(S13TrackState('UART_FT_TXD', 'CHAN11', 50.4001, 11.8999, 50.6502, 12.1500), OldCount, NewCount, Bad);
    S13Count(S13TrackState('UART_FT_TXD', 'CHAN11', 50.6502, 12.1500, 51.1125, 12.1500), OldCount, NewCount, Bad);
    S13Count(S13TrackState('BTN', 'LED0_B', 49.4001, 10.3450, 49.9000, 10.4000), OldCount, NewCount, Bad);
    S13Count(S13ViaState('BTN', 'LED0_B', 49.4001, 10.3450), OldCount, NewCount, Bad);
    S13Count(S13TrackState('FT-PWREN#', 'LED0_R', 49.4001, 9.8999, 49.9000, 9.8999), OldCount, NewCount, Bad);
    S13Count(S13ViaState('FT-PWREN#', 'LED0_R', 49.4001, 9.8999), OldCount, NewCount, Bad);
    S13Count(S13TrackState('JA7', 'CHAN28', 49.4001, 8.8999, 49.9000, 8.8999), OldCount, NewCount, Bad);
    S13Count(S13ViaState('JA7', 'CHAN28', 49.4001, 8.8999), OldCount, NewCount, Bad);

    If Bad Or ((OldCount <> 25) And (NewCount <> 25)) Or
       ((OldCount <> 0) And (NewCount <> 0)) Then
    Begin
        ShowMessage('Stage13Prepare preflight failed or found mixed state. Old=' +
                    IntToStr(OldCount) + ' New=' + IntToStr(NewCount) +
                    '. Nothing changed.');
        Exit;
    End;
    If NewCount = 25 Then
    Begin
        ShowMessage('Stage13Prepare: all 13 pads and 12 fan-out objects are already re-netted.');
        Exit;
    End;

    Applied := 0;
    PCBServer.PreProcess;
    Try
        Ok := S13SetPad('E19', 'JA8', 'CHAN12'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('G17', 'JA3', 'CHAN7'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('H19', 'CHAN7', 'CHAN13'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('K17', 'CHAN11', 'UART_FT_TXD'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('K18', 'UART_FT_TXD', 'CHAN11'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('N17', 'BTN', 'LED0_B'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('N19', 'LED0_B', 'BTN'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('P17', 'FT-PWREN#', 'LED0_R'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('P19', 'LED0_R', 'FT-PWREN#'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('R19', 'CHAN28', 'JA7'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('T17', 'JA7', 'CHAN28'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('W18', 'CHAN13', 'JA3'); If Ok Then Applied := Applied + 1;
        Ok := S13SetPad('W19', 'CHAN12', 'JA8'); If Ok Then Applied := Applied + 1;

        Ok := S13SetTrack('JA3', 'CHAN7', 49.4001, 13.4000, 49.9000, 13.4000); If Ok Then Applied := Applied + 1;
        Ok := S13SetVia('JA3', 'CHAN7', 49.4001, 13.4000); If Ok Then Applied := Applied + 1;
        Ok := S13SetTrack('CHAN11', 'UART_FT_TXD', 49.4001, 11.8999, 49.9000, 11.8999); If Ok Then Applied := Applied + 1;
        Ok := S13SetVia('CHAN11', 'UART_FT_TXD', 49.4001, 11.8999); If Ok Then Applied := Applied + 1;
        Ok := S13SetTrack('UART_FT_TXD', 'CHAN11', 50.4001, 11.8999, 50.6502, 12.1500); If Ok Then Applied := Applied + 1;
        Ok := S13SetTrack('UART_FT_TXD', 'CHAN11', 50.6502, 12.1500, 51.1125, 12.1500); If Ok Then Applied := Applied + 1;
        Ok := S13SetTrack('BTN', 'LED0_B', 49.4001, 10.3450, 49.9000, 10.4000); If Ok Then Applied := Applied + 1;
        Ok := S13SetVia('BTN', 'LED0_B', 49.4001, 10.3450); If Ok Then Applied := Applied + 1;
        Ok := S13SetTrack('FT-PWREN#', 'LED0_R', 49.4001, 9.8999, 49.9000, 9.8999); If Ok Then Applied := Applied + 1;
        Ok := S13SetVia('FT-PWREN#', 'LED0_R', 49.4001, 9.8999); If Ok Then Applied := Applied + 1;
        Ok := S13SetTrack('JA7', 'CHAN28', 49.4001, 8.8999, 49.9000, 8.8999); If Ok Then Applied := Applied + 1;
        Ok := S13SetVia('JA7', 'CHAN28', 49.4001, 8.8999); If Ok Then Applied := Applied + 1;
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;
    If Applied = 25 Then
        ShowMessage('Stage13Prepare complete: 13 U1 pads and 12 fan-out objects re-netted. Press Ctrl+S.')
    Else
        ShowMessage('Stage13Prepare applied only ' + IntToStr(Applied) +
                    ' of 25 objects. Do not save; restore the pre-route backup.');
End;
