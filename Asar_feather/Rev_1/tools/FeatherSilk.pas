{ FeatherSilk.pas -- 2026-10-23, user request: shrink the RESET designator and add 'ASAR A7' under U3.
  Run with asar_feather.PcbDoc focused:
    SilkReport        reads only: BTN's and RESET's designator size/stroke/position (also the API canary)
    ApplyFeatherSilk  RESET's designator takes BTN's size and stroke and sits just right of the RESET part,
                      vertically centred on it; 'ASAR A7' (stroke font, Top Overlay) is centred in the free band
                      south of U3, between the RESET label + 1 mm and x = 40.6 mm (BTN's pads start at 41.0),
                      centred on y = 4.55 mm (header pads end at 2.12, U3's balls start at 8.03). If 1.5 mm text
                      is too wide for the band it is scaled down. Refuses if 'ASAR A7' already exists. }

Const
    BAND_RIGHT = 40.6;
    BAND_Y     = 4.55;
    TITLE_SIZE = 1.5;
    TITLE_W    = 0.2;
    RESET_PADS_RIGHT = 26.55;

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

Function Describe(T : IPCB_Text) : String;
Var
    R : TCoordRect;
Begin
    R := T.BoundingRectangle;
    Result := '''' + T.Text + ''' size ' + FloatToStr(CoordToMMs(T.Size)) + ' stroke ' + FloatToStr(CoordToMMs(T.Width)) +
              '  box x ' + FloatToStr(CoordToMMs(R.Left)) + '..' + FloatToStr(CoordToMMs(R.Right)) +
              ' y ' + FloatToStr(CoordToMMs(R.Bottom)) + '..' + FloatToStr(CoordToMMs(R.Top));
End;

Procedure SilkReport;
Var
    Brd : IPCB_Board;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    ShowMessage('BTN:   ' + Describe(Brd.GetPcbComponentByRefDes('BTN').Name) + #13#10 +
                'RESET: ' + Describe(Brd.GetPcbComponentByRefDes('RESET').Name));
End;

Procedure ApplyFeatherSilk;
Var
    Brd   : IPCB_Board;
    It    : IPCB_BoardIterator;
    T     : IPCB_Text;
    B, Rs : IPCB_Component;
    N     : IPCB_Text;
    R     : TCoordRect;
    Left, Want, Wid : Double;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If T.Text = 'ASAR A7' Then
        Begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('ASAR A7 already exists on Top Overlay; no change made.');
            Exit;
        End;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);

    B := Brd.GetPcbComponentByRefDes('BTN');
    Rs := Brd.GetPcbComponentByRefDes('RESET');
    { RESET designator: BTN's size and stroke, left edge 0.3 mm right of the part's pads (RESET_PADS_RIGHT, from
      tools/placement.json: PTS810 pads +-2.6 mm about x 23.95), centred on the part (y 4.55) }
    N := Rs.Name;
    N.BeginModify;
    N.Size := B.Name.Size;
    N.Width := B.Name.Width;
    N.EndModify;
    R := N.BoundingRectangle;
    N.BeginModify;
    N.XLocation := N.XLocation + (MMsToCoord(RESET_PADS_RIGHT + 0.3) - R.Left);
    N.YLocation := N.YLocation + (MMsToCoord(BAND_Y) - (R.Top + R.Bottom) Div 2);
    N.EndModify;
    R := N.BoundingRectangle;
    Left := CoordToMMs(R.Right) + 1.0;

    { ASAR A7 }
    T := PCBServer.PCBObjectFactory(eTextObject, eNoDimension, eCreate_Default);
    T.XLocation := MMsToCoord(Left);
    T.YLocation := MMsToCoord(BAND_Y);
    T.Layer := eTopOverlay;
    T.Text := 'ASAR A7';
    T.Size := MMsToCoord(TITLE_SIZE);
    T.Width := MMsToCoord(TITLE_W);
    T.Rotation := 0;
    T.UseTTFonts := False;
    Brd.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Brd.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration, T.I_ObjectAddress);
    R := T.BoundingRectangle;
    Wid := CoordToMMs(R.Right - R.Left);
    If Wid > BAND_RIGHT - Left Then
    Begin
        T.BeginModify;
        T.Size := MMsToCoord(TITLE_SIZE * (BAND_RIGHT - Left) / Wid * 0.98);
        T.EndModify;
        R := T.BoundingRectangle;
    End;
    Want := (Left + BAND_RIGHT) / 2;
    T.BeginModify;
    T.XLocation := T.XLocation + (MMsToCoord(Want) - (R.Left + R.Right) Div 2);
    T.YLocation := T.YLocation + (MMsToCoord(BAND_Y) - (R.Top + R.Bottom) Div 2);
    T.EndModify;
    Brd.ViewManager_FullUpdate;
    ShowMessage('RESET: ' + Describe(N) + #13#10 + 'Title: ' + Describe(T));
End;
