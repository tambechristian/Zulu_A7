{ Reflect the existing JST-S2B-PH-SM4-TB PcbLib component about its local X axis.
  The first generator copied KiCad Y-down coordinates directly into Altium Y-up.
  This fixes pad numbering, body, and silk without depending on the PcbLib's
  internal coordinate offset. Run exactly once with zulu_a7.PcbLib focused. }

Function X4MirrorLibOrNil : IPCB_Library;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or
       (Pos('\Zulu_A7_no_pmod\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7.PcbLib',
            Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_A7_no_pmod Rev_2 zulu_a7.PcbLib first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBLibrary;
End;

Function X4MirrorFind(Lib : IPCB_Library; Name : String) : IPCB_LibComponent;
Var
    It : IPCB_LibraryIterator;
    Fp : IPCB_LibComponent;
Begin
    Result := Nil;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Fp.Name = Name Then Result := Fp;
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
End;

Function X4MirrorPad(Fp : IPCB_LibComponent; Name : String) : IPCB_Pad;
Var
    It : IPCB_GroupIterator;
    P : IPCB_Pad;
Begin
    Result := Nil;
    It := Fp.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = Name Then Result := P;
        P := It.NextPCBObject;
    End;
    Fp.GroupIterator_Destroy(It);
End;

Procedure FixX4Mirror;
Var
    Lib : IPCB_Library;
    Fp : IPCB_LibComponent;
    P1, MP1 : IPCB_Pad;
    It : IPCB_GroupIterator;
    Obj : IPCB_Primitive;
    P : IPCB_Pad;
    T : IPCB_Track;
    AxisY, SignalLocalY, MountLocalY : TCoord;
    Pads, Tracks : Integer;
Begin
    Lib := X4MirrorLibOrNil;
    If Lib = Nil Then Exit;
    Fp := X4MirrorFind(Lib, 'JST-S2B-PH-SM4-TB');
    If Fp = Nil Then
    Begin
        ShowMessage('Refusing: JST-S2B-PH-SM4-TB is missing.');
        Exit;
    End;
    P1 := X4MirrorPad(Fp, '1');
    MP1 := X4MirrorPad(Fp, 'MP1');
    If (P1 = Nil) Or (MP1 = Nil) Then
    Begin
        ShowMessage('Refusing: X4 pin 1 or MP1 is missing.');
        Exit;
    End;

    AxisY := (P1.Y + MP1.Y - MMsToCoord(0.05)) Div 2;
    SignalLocalY := P1.Y - AxisY;
    MountLocalY := MP1.Y - AxisY;
    If (Abs(SignalLocalY - MMsToCoord(2.85)) < 300) And
       (Abs(MountLocalY + MMsToCoord(2.90)) < 300) Then
    Begin
        ShowMessage('JST-S2B-PH-SM4-TB is already in Altium Y-up orientation; nothing changed.');
        Exit;
    End;
    If Not ((Abs(SignalLocalY + MMsToCoord(2.85)) < 300) And
            (Abs(MountLocalY - MMsToCoord(2.90)) < 300)) Then
    Begin
        ShowMessage('Refusing: existing X4 pad geometry is not the known mirrored footprint.');
        Exit;
    End;

    Pads := 0;
    Tracks := 0;
    PCBServer.PreProcess;
    Try
        It := Fp.GroupIterator_Create;
        It.SetState_FilterAll;
        Obj := It.FirstPCBObject;
        While Obj <> Nil Do
        Begin
            If Obj.ObjectId = ePadObject Then
            Begin
                P := Obj;
                P.BeginModify;
                P.Y := 2 * AxisY - P.Y;
                P.EndModify;
                Pads := Pads + 1;
            End
            Else If Obj.ObjectId = eTrackObject Then
            Begin
                T := Obj;
                T.BeginModify;
                T.Y1 := 2 * AxisY - T.Y1;
                T.Y2 := 2 * AxisY - T.Y2;
                T.EndModify;
                Tracks := Tracks + 1;
            End;
            Obj := It.NextPCBObject;
        End;
        Fp.GroupIterator_Destroy(It);
    Finally
        PCBServer.PostProcess;
    End;

    If (Pads <> 4) Or (Tracks <> 10) Then
        ShowMessage('WARNING: reflected footprint, but counted ' + IntToStr(Pads) +
                    ' pads and ' + IntToStr(Tracks) + ' lines; inspect before saving.')
    Else
        ShowMessage('JST-S2B-PH-SM4-TB reflected into Altium Y-up orientation. Save only the PcbLib.');
    Lib.CurrentComponent := Fp;
    Lib.Board.ViewManager_FullUpdate;
End;
