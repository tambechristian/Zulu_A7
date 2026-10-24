{ FeatherSilk4.pas -- 2026-10-23. Fourth step: Name.XLocation and the NameAutoPosition property did not move the label in
  this build; this uses ChangeNameAutoposition(eAutoPos_CenterRight) and nudges the part 1 unit and back so the
  auto-position is re-applied. Third step (FeatherSilk2's centre-right auto-position did not move the label,
  which only re-positions on a part move): label set to MANUAL and placed 0.3 mm right of the RESET pads,
  centred on y 4.55; title re-centred after it. Second step after FeatherSilk.pas: setting XLocation on RESET's designator did not
  stick (Altium re-applied its auto-position and left it over U1's bottom ball lands). FixResetLabel sets the
  designator's auto-position to centre-right of the part, then re-centres 'ZULU A7' between that label + 1 mm and
  x = 40.6 mm (scaling it down if needed), and reports both boxes.
  (Original header follows.)
  FeatherSilk.pas -- shrink the RESET designator and add 'ZULU A7' under U3.
  Run with zulu_feather.PcbDoc focused:
    SilkReport        reads only: BTN's and RESET's designator size/stroke/position (also the API canary)
    ApplyFeatherSilk  RESET's designator takes BTN's size and stroke and sits just right of the RESET part,
                      vertically centred on it; 'ZULU A7' (stroke font, Top Overlay) is centred in the free band
                      south of U3, between the RESET label + 1 mm and x = 40.6 mm (BTN's pads start at 41.0),
                      centred on y = 4.55 mm (header pads end at 2.12, U3's balls start at 8.03). If 1.5 mm text
                      is too wide for the band it is scaled down. Refuses if 'ZULU A7' already exists. }

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
    If (Doc = Nil) Or (Pos('\Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc first.');
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

Procedure AutoPlaceResetLabel;
Var
    Brd  : IPCB_Board;
    It   : IPCB_BoardIterator;
    T, Ti: IPCB_Text;
    Rs   : IPCB_Component;
    R    : TCoordRect;
    Left, Wid : Double;
Begin
    Brd := FBrd;
    If Brd = Nil Then Exit;
    Rs := Brd.GetPcbComponentByRefDes('RESET');
    Rs.BeginModify;
    Rs.ChangeNameAutoposition(eAutoPos_CenterRight);
    Rs.X := Rs.X + 1;
    Rs.EndModify;
    Rs.BeginModify;
    Rs.X := Rs.X - 1;
    Rs.EndModify;
    R := Rs.Name.BoundingRectangle;
    Left := CoordToMMs(R.Right) + 1.0;

    Ti := Nil;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    T := It.FirstPCBObject;
    While T <> Nil Do
    Begin
        If T.Text = 'ZULU A7' Then Ti := T;
        T := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Ti = Nil Then Begin ShowMessage('ZULU A7 not found.'); Exit; End;

    Ti.BeginModify;
    Ti.Size := MMsToCoord(TITLE_SIZE);
    Ti.EndModify;
    R := Ti.BoundingRectangle;
    Wid := CoordToMMs(R.Right - R.Left);
    If Wid > BAND_RIGHT - Left Then
    Begin
        Ti.BeginModify;
        Ti.Size := MMsToCoord(TITLE_SIZE * (BAND_RIGHT - Left) / Wid * 0.98);
        Ti.EndModify;
        R := Ti.BoundingRectangle;
    End;
    Ti.BeginModify;
    Ti.XLocation := Ti.XLocation + (MMsToCoord((Left + BAND_RIGHT) / 2) - (R.Left + R.Right) Div 2);
    Ti.YLocation := Ti.YLocation + (MMsToCoord(BAND_Y) - (R.Top + R.Bottom) Div 2);
    Ti.EndModify;
    Brd.ViewManager_FullUpdate;
    ShowMessage('RESET: ' + Describe(Rs.Name) + #13#10 + 'Title: ' + Describe(Ti));
End;
