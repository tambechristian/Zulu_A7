{ SI_PlaneNets.pas -- 2026-11-12. SI-ONLY COPY: after L2-GND / L5-VCC3V3 became Plane layers, give each plane its net.
  SIReportPlanes lists every split-plane object (layer id, layer name, net). SISetPlaneNets sets the plane on the layer
  whose name contains 'L2-GND' to GND and the one whose name contains 'L5-VCC3V3' to VCC3V3, and reports.
  Refuses to run on anything but the SI copy. }
Function NetNamed(B : IPCB_Board; AName : String) : IPCB_Net;
Var
    It : IPCB_BoardIterator;
    N  : IPCB_Net;
Begin
    Result := Nil;
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eNetObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    N := It.FirstPCBObject;
    While N <> Nil Do
    Begin
        If N.Name = AName Then Result := N;
        N := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
End;

Function Guard : IPCB_Board;
Var
    Doc : IDocument;
Begin
    Result := Nil;
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\si\altium_si\Zulu_a7_no_pmod_SI.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus the SI copy si\altium_si\Zulu_a7_no_pmod_SI.PcbDoc first.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
End;

Function Walk(B : IPCB_Board; DoSet : Boolean) : String;
Var
    It : IPCB_BoardIterator;
    O  : IPCB_SplitPlane;
    LName, NName : String;
    N  : IPCB_Net;
Begin
    Result := '';
    It := B.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eSplitPlaneObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        LName := B.LayerStack.LayerObject(O.Layer).Name;
        If O.Net = Nil Then NName := '(no net)' Else NName := O.Net.Name;
        If DoSet Then
        Begin
            N := Nil;
            If Pos('L2-GND', LName) > 0 Then N := NetNamed(B, 'GND');
            If Pos('L5-VCC3V3', LName) > 0 Then N := NetNamed(B, 'VCC3V3');
            If N <> Nil Then
            Begin
                O.BeginModify;
                O.Net := N;
                O.EndModify;
                O.Rebuild;
                NName := NName + ' -> ' + O.Net.Name;
            End;
        End;
        Result := Result + 'layer ' + IntToStr(O.Layer) + ' "' + LName + '": ' + NName + #13#10;
        O := It.NextPCBObject;
    End;
    B.BoardIterator_Destroy(It);
End;

Procedure SIReportPlanes;
Var
    B : IPCB_Board;
Begin
    B := Guard;
    If B = Nil Then Exit;
    ShowMessage('Split planes:' + #13#10 + Walk(B, False));
End;

Procedure SISetPlaneNets;
Var
    B : IPCB_Board;
Begin
    B := Guard;
    If B = Nil Then Exit;
    ShowMessage('Split planes:' + #13#10 + Walk(B, True));
    B.ViewManager_FullUpdate;
End;
