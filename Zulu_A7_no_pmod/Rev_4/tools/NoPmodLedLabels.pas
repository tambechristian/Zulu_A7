{ NoPmodLedLabels.pas -- 2026-11-26, Rev 4: free Top Overlay function labels at the X2 names' size (0.8 mm, 0.15 mm
  stroke): 'LD0' below LD0, 'CHRG' above LD4, 'RXTX' above LD6 (rotation 90). Spots from tools/route/led_labels/find_spots.py
  (0.26 mm from every pad and printing silk, off part bodies). LD1, LD2, LD3 (PWR) and LD5 (DONE) have no legal spot and
  stay unlabelled (user choice). Refuses unless the Rev 4 board is focused and none of the texts exists yet. Save, then DRC. }
Procedure NoPmodLedLabels;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    It  : IPCB_BoardIterator;
    T   : IPCB_Text;
    R   : TCoordRect;
    n   : Integer;
    S   : String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_A7_no_pmod\Rev_4\Imported zulu_a7.PrjPcb\Zulu_a7_no_pmod.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus /Zulu_A7_no_pmod/Rev_4/Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    n := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If (Not T.InComponent) And ((T.Text = 'LD0') Or (T.Text = 'CHRG') Or (T.Text = 'RXTX')) Then n := n + 1;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If n <> 0 Then
    Begin
        ShowMessage('Refusing: a free LD0/CHRG/RXTX text already exists; nothing changed.');
        Exit;
    End;
    S := '';
    PCBServer.PreProcess;
    T := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
    T.XLocation := Brd.XOrigin + MMsToCoord(19.5000);
    T.YLocation := Brd.YOrigin + MMsToCoord(6.8350);
    T.Layer := eTopOverlay;
    T.Text := 'LD0';
    T.Size := MMsToCoord(0.8000);
    T.Width := MMsToCoord(0.1500);
    T.Rotation := 0;
    T.UseTTFonts := False;
    Brd.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    R := T.BoundingRectangle;
    S := S + 'LD0 x ' + FormatFloat('0.000', CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Right - Brd.XOrigin)) +
         ' y ' + FormatFloat('0.000', CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Top - Brd.YOrigin)) + #13#10;
    T := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
    T.XLocation := Brd.XOrigin + MMsToCoord(20.5250);
    T.YLocation := Brd.YOrigin + MMsToCoord(18.3850);
    T.Layer := eTopOverlay;
    T.Text := 'CHRG';
    T.Size := MMsToCoord(0.8000);
    T.Width := MMsToCoord(0.1500);
    T.Rotation := 0;
    T.UseTTFonts := False;
    Brd.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    R := T.BoundingRectangle;
    S := S + 'CHRG x ' + FormatFloat('0.000', CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Right - Brd.XOrigin)) +
         ' y ' + FormatFloat('0.000', CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Top - Brd.YOrigin)) + #13#10;
    T := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
    T.XLocation := Brd.XOrigin + MMsToCoord(35.7250);
    T.YLocation := Brd.YOrigin + MMsToCoord(20.8000);
    T.Layer := eTopOverlay;
    T.Text := 'RXTX';
    T.Size := MMsToCoord(0.8000);
    T.Width := MMsToCoord(0.1500);
    T.Rotation := 90;
    T.UseTTFonts := False;
    Brd.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    R := T.BoundingRectangle;
    S := S + 'RXTX x ' + FormatFloat('0.000', CoordToMMs(R.Left - Brd.XOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Right - Brd.XOrigin)) +
         ' y ' + FormatFloat('0.000', CoordToMMs(R.Bottom - Brd.YOrigin)) + '..' + FormatFloat('0.000', CoordToMMs(R.Top - Brd.YOrigin)) + #13#10;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('NoPmodLedLabels done:' + #13#10 + S + 'Save, then DRC.');
End;
