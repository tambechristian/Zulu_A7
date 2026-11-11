{ AsarTpsPlace.pas -- GENERATED 2026-11-09 from scratchpad placement/asar/verify/parts.json (verifier-corrected survey).
  AsarTpsPlace: Bottom-side U5 (TPS63802) rot 270, L1 rot 0, C80 rot 90, R110 rot 90, R109 rot 270, each pad-anchored, then
  all 18 pads checked within 0.005 mm; hides the R109/R110 designators (Bottom parts hide theirs on this board) and adds
  NetL1_2 to PWR_SWITCH. Refuses unless U5/L1/C80 are where the ECO left them. Then run FeatherCopper_TpsSwap, then
  AsarTpsRebuild (ratsnest), save, mark microvias, DRC. }

Var
    Brd : IPCB_Board;
    Missing, Report : String;
    NDone, NBad : Integer;

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
    If C.Layer <> eBottomLayer Then C.Layer := eBottomLayer;
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
            FX := P.X; FY := P.Y;
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

Procedure Check(D, PN : String; PX, PY : Double);
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    Got : Boolean;
    x, y : Double;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then Exit;
    Got := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = PN Then
        Begin
            Got := True;
            x := CoordToMMs(P.X - Brd.XOrigin);
            y := CoordToMMs(P.Y - Brd.YOrigin);
            If (Abs(x - PX) > 0.005) Or (Abs(y - PY) > 0.005) Then
            Begin
                NBad := NBad + 1;
                Report := Report + D + '-' + PN + ' at ' + FormatFloat('0.000', x) + ',' + FormatFloat('0.000', y) + '; ';
            End;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Not Got Then Report := Report + D + '-' + PN + ' missing; ';
End;

Function At(D : String; X, Y : Double) : Boolean;
Var
    C : IPCB_Component;
Begin
    C := Brd.GetPcbComponentByRefDes(D);
    Result := (C <> Nil) And (Abs(CoordToMMs(C.X - Brd.XOrigin) - X) < 0.005) And (Abs(CoordToMMs(C.Y - Brd.YOrigin) - Y) < 0.005);
End;


Procedure InvalidateAll(Brd : IPCB_Board);
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        N.ConnectivelyInValidate;
        N := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    Brd.ConnectivelyValidateNets;
End;


Procedure AsarTpsPlace;
Var
    Doc : IDocument;
    It : IPCB_BoardIterator;
    Cls : IPCB_ObjectClass;
    Cm : IPCB_Component;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.'); Exit; End;
    Brd := PCBServer.GetCurrentPCBBoard;
    If Not (At('U5', 11.8, 18.6) And At('L1', 14.6, 18.6) And At('C80', 16.705, 18.6)) Then
    Begin ShowMessage('Refusing: U5, L1 or C80 is not where the ECO left it; nothing changed.'); Exit; End;
    Missing := ''; Report := ''; NDone := 0; NBad := 0;
    PCBServer.PreProcess;
    Place('U5', 270, '10', 11.2500, 19.5500);
    Place('L1', 0, '1', 11.0750, 17.7500);
    Place('C80', 90, '2', 14.9000, 19.5500);
    Place('R110', 90, '1', 14.4000, 20.7500);
    Place('R109', 270, '1', 10.1000, 21.9500);
    Cm := Brd.GetPcbComponentByRefDes('R109'); If Cm <> Nil Then Begin Cm.BeginModify; Cm.NameOn := False; Cm.CommentOn := False; Cm.EndModify; End;
    Cm := Brd.GetPcbComponentByRefDes('R110'); If Cm <> Nil Then Begin Cm.BeginModify; Cm.NameOn := False; Cm.CommentOn := False; Cm.EndModify; End;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eClassObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    Cls := It.FirstPCBObject;
    While Cls <> Nil Do
    Begin
        If (Cls.MemberKind = eClassMemberKind_Net) And (Cls.Name = 'PWR_SWITCH') Then If Not Cls.IsMember('NetL1_2') Then Cls.AddMemberByName('NetL1_2');
        Cls := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PostProcess;
    Check('C80', '1', 14.9000, 17.8500);
    Check('C80', '2', 14.9000, 19.5500);
    Check('L1', '1', 11.0750, 17.7500);
    Check('L1', '2', 13.4250, 17.7500);
    Check('R109', '1', 10.1000, 21.9500);
    Check('R109', '2', 10.1000, 20.6500);
    Check('R110', '1', 14.4000, 20.7500);
    Check('R110', '2', 14.4000, 22.0500);
    Check('U5', '1', 11.2500, 21.2000);
    Check('U5', '10', 11.2500, 19.5500);
    Check('U5', '2', 11.7500, 21.2000);
    Check('U5', '3', 12.2500, 21.2000);
    Check('U5', '4', 12.7500, 21.2000);
    Check('U5', '5', 13.2500, 21.2000);
    Check('U5', '6', 13.2500, 19.5500);
    Check('U5', '7', 12.7500, 19.5500);
    Check('U5', '8', 12.2500, 19.7500);
    Check('U5', '9', 11.7500, 19.5500);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Placed ' + IntToStr(NDone) + ' of 5. Missing: ' + Missing + ' Pads off plan: ' + IntToStr(NBad) + ' ' + Report + 'Undo if anything is off; else run the copper script.');
End;

Procedure AsarTpsRebuild;
Var
    It : IPCB_BoardIterator;
    C : IPCB_Connection;
    Kill : TInterfaceList;
    i, n : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    InvalidateAll(Brd);
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do Begin Kill.Add(C); C := It.NextPCBObject; End;
    Brd.BoardIterator_Destroy(It);
    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do Brd.RemovePCBObject(Kill.Items[i]);
    PCBServer.PostProcess;
    InvalidateAll(Brd);
    n := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eConnectionObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    C := It.FirstPCBObject;
    While C <> Nil Do Begin n := n + 1; C := It.NextPCBObject; End;
    Brd.BoardIterator_Destroy(It);
    Brd.ViewManager_FullUpdate;
    ShowMessage('Ratsnest: removed ' + IntToStr(Kill.Count) + ', ' + IntToStr(n) + ' remain after re-analysis.');
    Kill.Free;
End;
