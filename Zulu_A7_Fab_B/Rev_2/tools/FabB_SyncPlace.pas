{ FabB_SyncPlace.pas -- GENERATED 2026-11-20 by tools/sync_altium_emit.py from tools/route/sync_altium/sync_data.json
  (no-PMOD Zulu_a7_no_pmod.PcbDoc at 427960e, md5 9b0341ba; Fab B zulu_a7_fab_b.PcbDoc before the sync, md5 33023787).
  Do not edit by hand. Run SyncPlace with zulu_a7_fab_b.PcbDoc focused, AFTER the library copy and the ECO
  (U2/X4/U10 footprints swapped in place, R119-R134 added off the board, U3 DQ pads re-netted; saved, closed
  and reopened). Moves U2, X4, U10, R119-R134, U4, R34, C87, C88, C94, C99, C106, R1 and the designators of those parts and U1.
  Preconditions (all checked before anything moves): footprint and pad count per part, every pad net, U3 DQ
  nets, pre-sync Fab B origin/rotation/side of U2 X4 U10 U4 R34 C87 C88 C94 C99 C106 R1, R119-R134 parked off
  the board, U1 designator at its pre-sync place. After the moves all 139 pads are re-measured (0.001 mm) and
  every designator (0.005 mm); a miss is reported as DO NOT SAVE (close without saving and reopen). }

Var
    Brd    : IPCB_Board;
    Bad    : String;
    NBad   : Integer;
    Info   : String;
    Forced : String;
    NPadOk : Integer;

Function SyncBoard : IPCB_Board;
Var
    Doc : IDocument;
    Ok  : Boolean;
Begin
    Result := Nil;
    Ok := False;
    Doc := GetWorkspace.DM_FocusedDocument;
    If Doc <> Nil Then
        If Pos('\Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc', Doc.DM_FullPath) > 0 Then Ok := True;
    If Not Ok Then
    Begin
        ShowMessage('Refusing (SyncPlace): focus Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc first; nothing changed.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
    If Result = Nil Then
    Begin
        ShowMessage('Refusing (SyncPlace): no PCB board is current; nothing changed.');
        Exit;
    End;
    If Pos('zulu_a7_fab_b.PcbDoc', Result.FileName) = 0 Then
    Begin
        ShowMessage('Refusing (SyncPlace): the current board is ' + Result.FileName + ', not zulu_a7_fab_b.PcbDoc; nothing changed.');
        Result := Nil;
        Exit;
    End;
End;

Function FindPad(C : IPCB_Component; PName : String) : IPCB_Pad;
Var
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
Begin
    Result := Nil;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = PName Then Result := P;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Function PadCount(C : IPCB_Component) : Integer;
Var
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
Begin
    Result := 0;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        Result := Result + 1;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;

Function NetOf(P : IPCB_Pad) : String;
Begin
    Result := '';
    If P.Net <> Nil Then Result := P.Net.Name;
End;

Procedure Fail(S : String);
Begin
    NBad := NBad + 1;
    If NBad <= 30 Then Bad := Bad + S + #13#10;
End;

Function RotOff(A, B : Double) : Double;
Var
    d : Double;
Begin
    d := A - B;
    While d < 0 Do d := d + 360;
    While d >= 360 Do d := d - 360;
    If d > 180 Then d := 360 - d;
    Result := d;
End;

Function FmtXY(X, Y : Double) : String;
Begin
    Result := '(' + FormatFloat('0.0000', X) + ', ' + FormatFloat('0.0000', Y) + ')';
End;

{ Mode 0: an existing part, must be at its pre-sync Fab B origin/rotation/side. Mode 1: a part the ECO added,
  must be parked off the board (origin more than 0.5 mm outside the 69.85 x 25.40 mm outline). }
Procedure PreComp(Ref, Pat : String; NP, Mode : Integer; Bot : Boolean; Rot, X, Y : Double);
Var
    C : IPCB_Component;
    cx, cy : Double;
Begin
    C := Brd.GetPcbComponentByRefDes(Ref);
    If C = Nil Then
    Begin
        Fail(Ref + ' is not on the board');
        Exit;
    End;
    If C.Pattern <> Pat Then
    Begin
        Fail(Ref + ' footprint is ' + C.Pattern + ', expected ' + Pat);
        Exit;
    End;
    If PadCount(C) <> NP Then
        Fail(Ref + ' has ' + IntToStr(PadCount(C)) + ' pads, expected ' + IntToStr(NP));
    cx := CoordToMMs(C.X - Brd.XOrigin);
    cy := CoordToMMs(C.Y - Brd.YOrigin);
    If Mode = 1 Then
    Begin
        If (cx > -0.5) And (cx < 70.350000) And (cy > -0.5) And (cy < 25.900000) Then
            Fail(Ref + ' is already on the board at ' + FmtXY(cx, cy) + '; the ECO leaves it parked off the board');
        Exit;
    End;
    If Bot Then
    Begin
        If C.Layer <> eBottomLayer Then Fail(Ref + ' is not on the Bottom side');
    End
    Else
    Begin
        If C.Layer <> eTopLayer Then Fail(Ref + ' is not on the Top side');
    End;
    If (Abs(cx - X) > 0.002) Or (Abs(cy - Y) > 0.002) Then
        Fail(Ref + ' origin is ' + FmtXY(cx, cy) + ', not its pre-sync Fab B ' + FmtXY(X, Y));
    If RotOff(C.Rotation, Rot) > 0.01 Then
        Fail(Ref + ' rotation is ' + FormatFloat('0.###', C.Rotation) + ', not ' + FormatFloat('0.###', Rot));
End;

Procedure PreNet(Ref, PName, Net : String);
Var
    C : IPCB_Component;
    P : IPCB_Pad;
Begin
    C := Brd.GetPcbComponentByRefDes(Ref);
    If C = Nil Then Exit;
    P := FindPad(C, PName);
    If P = Nil Then
    Begin
        Fail(Ref + '-' + PName + ' pad is missing');
        Exit;
    End;
    If NetOf(P) <> Net Then
        Fail(Ref + '-' + PName + ' net is "' + NetOf(P) + '", expected "' + Net + '"');
End;

Procedure PreDesig(Ref : String; X, Y : Double);
Var
    C : IPCB_Component;
    tx, ty : Double;
Begin
    C := Brd.GetPcbComponentByRefDes(Ref);
    If C = Nil Then
    Begin
        Fail(Ref + ' is not on the board');
        Exit;
    End;
    tx := CoordToMMs(C.Name.XLocation - Brd.XOrigin);
    ty := CoordToMMs(C.Name.YLocation - Brd.YOrigin);
    If (Abs(tx - X) > 0.002) Or (Abs(ty - Y) > 0.002) Then
        Fail(Ref + ' designator is at ' + FmtXY(tx, ty) + ', not its pre-sync Fab B place ' + FmtXY(X, Y));
End;

Procedure PlaceAt(Ref : String; Bot : Boolean; Rot, X, Y : Double);
Var
    C : IPCB_Component;
Begin
    C := Brd.GetPcbComponentByRefDes(Ref);
    If Bot Then
    Begin
        If C.Layer <> eBottomLayer Then
        Begin
            C.BeginModify;
            C.Layer := eBottomLayer;
            C.EndModify;
        End;
    End
    Else
    Begin
        If C.Layer <> eTopLayer Then
        Begin
            C.BeginModify;
            C.Layer := eTopLayer;
            C.EndModify;
        End;
    End;
    C.BeginModify;
    C.Rotation := Rot;
    C.EndModify;
    C.BeginModify;
    C.X := Brd.XOrigin + MMsToCoord(X);
    C.Y := Brd.YOrigin + MMsToCoord(Y);
    C.EndModify;
End;

Function PadAt(Ref, PName : String; X, Y : Double) : Boolean;
Var
    C : IPCB_Component;
    P : IPCB_Pad;
Begin
    Result := False;
    C := Brd.GetPcbComponentByRefDes(Ref);
    If C = Nil Then Exit;
    P := FindPad(C, PName);
    If P = Nil Then Exit;
    If (Abs(CoordToMMs(P.X - Brd.XOrigin) - X) <= 0.001) And (Abs(CoordToMMs(P.Y - Brd.YOrigin) - Y) <= 0.001) Then
        Result := True;
End;

{ a two-pad resistor the ECO added: side, then the planned rotation (or +90/+180/+270 if the flip turned it),
  then the origin; accepted only when both pads land within 0.001 mm of the no-PMOD pads }
Procedure PlaceR(Ref : String; Bot : Boolean; Rot, X, Y, X1, Y1, X2, Y2 : Double);
Var
    k : Integer;
    ok, ok1, ok2 : Boolean;
    r : Double;
Begin
    ok := False;
    k := 0;
    While (Not ok) And (k < 4) Do
    Begin
        r := Rot + 90 * k;
        While r >= 360 Do r := r - 360;
        PlaceAt(Ref, Bot, r, X, Y);
        ok1 := PadAt(Ref, '1', X1, Y1);
        ok2 := PadAt(Ref, '2', X2, Y2);
        ok := ok1 And ok2;
        k := k + 1;
    End;
    If Not ok Then
        Fail(Ref + ' pads do not land on the no-PMOD pads at any rotation')
    Else
    Begin
        If k > 1 Then Info := Info + Ref + ' took rotation +' + IntToStr(90 * (k - 1)) + '; ';
    End;
End;

Procedure VPad(Ref, PName : String; X, Y : Double);
Begin
    If PadAt(Ref, PName, X, Y) Then
        NPadOk := NPadOk + 1
    Else
        Fail(Ref + '-' + PName + ' is not at ' + FmtXY(X, Y));
End;

{ designator: visibility as on the no-PMOD board; when the text is not at the no-PMOD place after the moves, set
  manual auto-position and move it (no-PMOD NoPmodU2Label2.pas pattern) }
Procedure Desig(Ref : String; NOn, COn : Boolean; X, Y, Rot : Double);
Var
    C : IPCB_Component;
    T : IPCB_Text;
    tx, ty : Double;
Begin
    C := Brd.GetPcbComponentByRefDes(Ref);
    C.BeginModify;
    C.NameOn := NOn;
    C.CommentOn := COn;
    C.EndModify;
    T := C.Name;
    tx := CoordToMMs(T.XLocation - Brd.XOrigin);
    ty := CoordToMMs(T.YLocation - Brd.YOrigin);
    If (Abs(tx - X) > 0.002) Or (Abs(ty - Y) > 0.002) Or (RotOff(T.Rotation, Rot) > 0.01) Then
    Begin
        C.BeginModify;
        C.ChangeNameAutoposition(eAutoPos_Manual);
        T.BeginModify;
        T.MoveToXY(Brd.XOrigin + MMsToCoord(X), Brd.YOrigin + MMsToCoord(Y));
        T.Rotation := Rot;
        T.EndModify;
        C.EndModify;
        T.GraphicallyInvalidate;
        Forced := Forced + Ref + ' ';
    End;
    T := C.Name;
    tx := CoordToMMs(T.XLocation - Brd.XOrigin);
    ty := CoordToMMs(T.YLocation - Brd.YOrigin);
    If (Abs(tx - X) > 0.005) Or (Abs(ty - Y) > 0.005) Then
        Fail(Ref + ' designator is at ' + FmtXY(tx, ty) + ', not ' + FmtXY(X, Y));
    If C.NameOn <> NOn Then
        Fail(Ref + ' designator visibility did not take');
End;

Procedure SyncPlace;
Begin
    Brd := SyncBoard;
    If Brd = Nil Then Exit;
    Bad := '';
    NBad := 0;
    Info := '';
    Forced := '';
    NPadOk := 0;

    { ---- preconditions: nothing changes unless all of them hold ---- }
    PreComp('U2', 'FT2232HQ-QFN64', 65, 0, False, 0.000000, 31.475012, 13.600044);
    PreComp('X4', 'JST-S2B-PH-SM4-TB', 4, 0, False, 0.000000, 29.859999, 5.300033);
    PreComp('U10', 'MSOP-8_3X3_P0.65', 8, 0, True, 0.000000, 20.985099, 18.645000);
    PreComp('U4', 'SOIC-8_208MIL', 8, 0, False, 0.000000, 43.550535, 21.304999);
    PreComp('R34', '742C083', 8, 0, True, 0.000000, 11.020049, 19.289979);
    PreComp('C87', 'C0603', 2, 0, True, 0.000000, 44.299784, 22.400001);
    PreComp('C88', 'C0603', 2, 0, True, 0.000000, 47.399585, 22.400001);
    PreComp('C94', 'C0603', 2, 0, True, 0.000000, 50.499485, 22.400001);
    PreComp('C99', 'C0603', 2, 0, True, 0.000000, 53.599283, 22.400001);
    PreComp('C106', 'C0603', 2, 0, True, 0.000000, 41.199885, 22.400001);
    PreComp('R1', '742C043', 4, 0, True, 0.000000, 58.200051, 3.700015);
    PreComp('R119', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R120', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R121', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R122', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R123', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R124', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R125', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R126', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R127', 'R0201', 2, 1, False, 0, 0, 0);
    PreComp('R128', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R129', 'R0201', 2, 1, False, 0, 0, 0);
    PreComp('R130', 'R0201', 2, 1, False, 0, 0, 0);
    PreComp('R131', 'R0201', 2, 1, False, 0, 0, 0);
    PreComp('R132', 'R0201', 2, 1, False, 0, 0, 0);
    PreComp('R133', 'R0201', 2, 1, True, 0, 0, 0);
    PreComp('R134', 'R0201', 2, 1, True, 0, 0, 0);
    PreNet('U2', '1', 'GND');
    PreNet('U2', '10', 'GND');
    PreNet('U2', '11', 'GND');
    PreNet('U2', '12', 'FT-VCORE');
    PreNet('U2', '13', 'GND');
    PreNet('U2', '14', 'FT-RESETN');
    PreNet('U2', '15', 'GND');
    PreNet('U2', '16', 'TCK');
    PreNet('U2', '17', 'TDI');
    PreNet('U2', '18', 'TDO');
    PreNet('U2', '19', 'TMS');
    PreNet('U2', '2', 'CLK-12M-FT');
    PreNet('U2', '20', 'VCC3V3');
    PreNet('U2', '21', 'PROG#');
    PreNet('U2', '22', 'DONE');
    PreNet('U2', '23', '');
    PreNet('U2', '24', '');
    PreNet('U2', '25', 'GND');
    PreNet('U2', '26', '');
    PreNet('U2', '27', '');
    PreNet('U2', '28', '');
    PreNet('U2', '29', '');
    PreNet('U2', '3', '');
    PreNet('U2', '30', '');
    PreNet('U2', '31', 'VCC3V3');
    PreNet('U2', '32', '');
    PreNet('U2', '33', '');
    PreNet('U2', '34', '');
    PreNet('U2', '35', 'GND');
    PreNet('U2', '36', '');
    PreNet('U2', '37', 'FT-VCORE');
    PreNet('U2', '38', 'UART_FT_TXD');
    PreNet('U2', '39', 'UART_FT_RXD');
    PreNet('U2', '4', 'FT-VPHY');
    PreNet('U2', '40', 'UART_FT_RTS#');
    PreNet('U2', '41', 'UART_FT_CTS#');
    PreNet('U2', '42', 'VCC3V3');
    PreNet('U2', '43', 'UART_FT_DTR#');
    PreNet('U2', '44', '');
    PreNet('U2', '45', '');
    PreNet('U2', '46', '');
    PreNet('U2', '47', 'GND');
    PreNet('U2', '48', '');
    PreNet('U2', '49', 'FT-VCORE');
    PreNet('U2', '5', 'GND');
    PreNet('U2', '50', 'VCC3V3');
    PreNet('U2', '51', 'GND');
    PreNet('U2', '52', '');
    PreNet('U2', '53', '');
    PreNet('U2', '54', '');
    PreNet('U2', '55', '');
    PreNet('U2', '56', 'VCC3V3');
    PreNet('U2', '57', '');
    PreNet('U2', '58', '');
    PreNet('U2', '59', '');
    PreNet('U2', '6', 'FT-REF');
    PreNet('U2', '60', 'FT-PWREN#');
    PreNet('U2', '61', 'EE-DATA');
    PreNet('U2', '62', 'EE-CLK');
    PreNet('U2', '63', 'EE-CS');
    PreNet('U2', '64', 'FT-VCORE');
    PreNet('U2', '7', 'USB_D_N');
    PreNet('U2', '8', 'USB_D_P');
    PreNet('U2', '9', 'FT-VPLL');
    PreNet('U2', 'EP', 'GND');
    PreNet('X4', '1', 'VBATT');
    PreNet('X4', '2', 'GND');
    PreNet('X4', 'MP1', '');
    PreNet('X4', 'MP2', '');
    PreNet('U10', '1', 'EE-CS');
    PreNet('U10', '2', 'EE-CLK');
    PreNet('U10', '3', 'EE-DATA');
    PreNet('U10', '4', 'EE-DATA-DO');
    PreNet('U10', '5', 'GND');
    PreNet('U10', '6', '');
    PreNet('U10', '7', '');
    PreNet('U10', '8', 'VCC3V3');
    PreNet('R119', '1', 'SDRAM-D0');
    PreNet('R119', '2', 'D0');
    PreNet('R120', '1', 'SDRAM-D1');
    PreNet('R120', '2', 'D1');
    PreNet('R121', '1', 'SDRAM-D2');
    PreNet('R121', '2', 'D2');
    PreNet('R122', '1', 'SDRAM-D3');
    PreNet('R122', '2', 'D3');
    PreNet('R123', '1', 'SDRAM-D4');
    PreNet('R123', '2', 'D4');
    PreNet('R124', '1', 'SDRAM-D5');
    PreNet('R124', '2', 'D5');
    PreNet('R125', '1', 'SDRAM-D6');
    PreNet('R125', '2', 'D6');
    PreNet('R126', '1', 'SDRAM-D7');
    PreNet('R126', '2', 'D7');
    PreNet('R127', '1', 'SDRAM-D8');
    PreNet('R127', '2', 'D8');
    PreNet('R128', '1', 'SDRAM-D9');
    PreNet('R128', '2', 'D9');
    PreNet('R129', '1', 'SDRAM-D10');
    PreNet('R129', '2', 'D10');
    PreNet('R130', '1', 'SDRAM-D11');
    PreNet('R130', '2', 'D11');
    PreNet('R131', '1', 'SDRAM-D12');
    PreNet('R131', '2', 'D12');
    PreNet('R132', '1', 'SDRAM-D13');
    PreNet('R132', '2', 'D13');
    PreNet('R133', '1', 'SDRAM-D14');
    PreNet('R133', '2', 'D14');
    PreNet('R134', '1', 'SDRAM-D15');
    PreNet('R134', '2', 'D15');
    PreNet('U4', '1', 'FLASH-CS#');
    PreNet('U4', '2', 'FLASH-D01');
    PreNet('U4', '3', 'FLASH-D02');
    PreNet('U4', '4', 'GND');
    PreNet('U4', '5', 'FLASH-D00');
    PreNet('U4', '6', 'FPGA-CCLK');
    PreNet('U4', '7', 'FLASH-D03');
    PreNet('U4', '8', 'VCC3V3');
    PreNet('R34', '1', 'SD-DAT0');
    PreNet('R34', '2', 'SD-DAT1');
    PreNet('R34', '3', 'SD-DAT2');
    PreNet('R34', '4', 'SD-DAT3');
    PreNet('R34', '5', 'VCC3V3');
    PreNet('R34', '6', 'VCC3V3');
    PreNet('R34', '7', 'VCC3V3');
    PreNet('R34', '8', 'VCC3V3');
    PreNet('C87', '1', 'VCC1V0');
    PreNet('C87', '2', 'GND');
    PreNet('C88', '1', 'VCC1V0');
    PreNet('C88', '2', 'GND');
    PreNet('C94', '1', 'VCC1V8');
    PreNet('C94', '2', 'GND');
    PreNet('C99', '1', 'VCC3V3');
    PreNet('C99', '2', 'GND');
    PreNet('C106', '1', 'VCC3V3');
    PreNet('C106', '2', 'GND');
    PreNet('R1', '1', 'FPGA-INIT#');
    PreNet('R1', '2', 'RST#');
    PreNet('R1', '3', 'VCC3V3');
    PreNet('R1', '4', 'VCC3V3');
    PreNet('U3', '10', 'SDRAM-D5');
    PreNet('U3', '11', 'SDRAM-D6');
    PreNet('U3', '13', 'SDRAM-D7');
    PreNet('U3', '2', 'SDRAM-D0');
    PreNet('U3', '4', 'SDRAM-D1');
    PreNet('U3', '42', 'SDRAM-D8');
    PreNet('U3', '44', 'SDRAM-D9');
    PreNet('U3', '45', 'SDRAM-D10');
    PreNet('U3', '47', 'SDRAM-D11');
    PreNet('U3', '48', 'SDRAM-D12');
    PreNet('U3', '5', 'SDRAM-D2');
    PreNet('U3', '50', 'SDRAM-D13');
    PreNet('U3', '51', 'SDRAM-D14');
    PreNet('U3', '53', 'SDRAM-D15');
    PreNet('U3', '7', 'SDRAM-D3');
    PreNet('U3', '8', 'SDRAM-D4');
    PreDesig('U1', 39.216772, 16.625080);
    If NBad > 0 Then
    Begin
        ShowMessage('Refusing: ' + IntToStr(NBad) + ' precondition(s) failed; NOTHING was changed.' + #13#10 + Bad);
        Exit;
    End;

    { ---- moves ---- }
    PCBServer.PreProcess;
    Try
        PlaceAt('U2', False, 0.000000, 30.500000, 14.549999);
        PlaceAt('X4', False, 0.000000, 31.390001, 4.900000);
        PlaceAt('U10', True, 0.000000, 23.485099, 20.244999);
        PlaceAt('U4', False, 0.000000, 43.550535, 21.704998);
        PlaceAt('R34', True, 0.000000, 11.420048, 19.289979);
        PlaceAt('C87', True, 0.000000, 44.299784, 22.200001);
        PlaceAt('C88', True, 0.000000, 47.399585, 22.200001);
        PlaceAt('C94', True, 0.000000, 50.499485, 22.200001);
        PlaceAt('C99', True, 0.000000, 53.599283, 22.200001);
        PlaceAt('C106', True, 0.000000, 41.199885, 22.200001);
        PlaceAt('R1', True, 0.000000, 58.200051, 4.000015);
        PlaceR('R119', True, 0.000000, 38.249901, 5.170104, 37.949901, 5.170104, 38.549900, 5.170104);
        PlaceR('R120', True, 0.000000, 36.649995, 5.170104, 36.349996, 5.170104, 36.949995, 5.170104);
        PlaceR('R121', True, 270.000000, 35.550102, 4.910104, 35.550102, 5.210104, 35.550102, 4.610105);
        PlaceR('R122', True, 0.000000, 34.249896, 5.170104, 33.949897, 5.170104, 34.549895, 5.170104);
        PlaceR('R123', True, 180.000000, 32.850102, 5.170104, 33.150101, 5.170104, 32.550103, 5.170104);
        PlaceR('R124', True, 270.000000, 31.550102, 4.910104, 31.550102, 5.210104, 31.550102, 4.610105);
        PlaceR('R125', True, 270.000000, 30.749997, 4.910104, 30.749997, 5.210104, 30.749997, 4.610105);
        PlaceR('R126', True, 0.000000, 29.450099, 5.210104, 29.150099, 5.210104, 29.750098, 5.210104);
        PlaceR('R127', False, 0.000000, 39.199995, 13.600003, 38.899996, 13.600003, 39.499995, 13.600003);
        PlaceR('R128', True, 0.000000, 42.050000, 12.950005, 41.750000, 12.950005, 42.349999, 12.950005);
        PlaceR('R129', False, 0.000000, 39.210000, 14.360004, 38.910001, 14.360004, 39.510000, 14.360004);
        PlaceR('R130', False, 0.000000, 39.400000, 14.920003, 39.100001, 14.920003, 39.699999, 14.920003);
        PlaceR('R131', False, 0.000000, 39.199998, 15.800004, 38.899998, 15.800004, 39.499997, 15.800004);
        PlaceR('R132', False, 180.000000, 38.750004, 16.303506, 39.050003, 16.303506, 38.450004, 16.303506);
        PlaceR('R133', True, 0.000000, 45.600000, 17.150004, 45.300001, 17.150004, 45.900000, 17.150004);
        PlaceR('R134', True, 0.000000, 46.800003, 16.800005, 46.500004, 16.800005, 47.100002, 16.800005);
        { designators after every move: a move re-applies a component's auto-position }
        Desig('U2', True, False, 24.749999, 8.650000, 0.000000);
        Desig('X4', False, False, 30.714602, 8.134368, 0.000000);
        Desig('U10', False, False, 26.955605, 25.451399, 0.000000);
        Desig('R119', False, False, 43.385039, 6.422680, 0.000000);
        Desig('R120', False, False, 42.040429, 6.422680, 0.000000);
        Desig('R121', False, False, 40.416810, 6.162680, 0.000000);
        Desig('R122', False, False, 39.625900, 6.422680, 0.000000);
        Desig('R123', False, False, 38.235771, 6.422680, 0.000000);
        Desig('R124', False, False, 36.937470, 6.162680, 0.000000);
        Desig('R125', False, False, 36.138660, 6.162680, 0.000000);
        Desig('R126', False, False, 34.840451, 6.462679, 0.000000);
        Desig('R127', False, False, 39.263495, 14.857303, 0.000000);
        Desig('R128', False, False, 47.427091, 14.202580, 0.000000);
        Desig('R129', False, False, 39.273500, 15.617304, 0.000000);
        Desig('R130', False, False, 39.463500, 16.177303, 0.000000);
        Desig('R131', False, False, 39.263498, 17.057304, 0.000000);
        Desig('R132', False, False, 38.813504, 17.560806, 0.000000);
        Desig('R133', False, False, 50.975311, 18.402579, 0.000000);
        Desig('R134', False, False, 52.176614, 18.052580, 0.000000);
        Desig('U4', False, False, 46.837600, 23.209199, 0.000000);
        Desig('R34', True, False, 13.909815, 21.988612, 0.000000);
        Desig('C87', False, False, 47.017584, 23.673201, 0.000000);
        Desig('C88', False, False, 50.117385, 23.673201, 0.000000);
        Desig('C94', False, False, 53.217285, 23.673201, 0.000000);
        Desig('C99', False, False, 56.317083, 23.673201, 0.000000);
        Desig('C106', False, False, 45.187685, 23.673201, 0.000000);
        Desig('R1', True, False, 59.140009, 6.978048, 0.000000);
        Desig('U1', True, False, 39.699999, 16.550000, 0.000000);
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    { ---- re-measure every pad of every moved part ---- }
    VPad('U2', '1', 26.075000, 18.299999);
    VPad('U2', '10', 26.075000, 13.799998);
    VPad('U2', '11', 26.075000, 13.299999);
    VPad('U2', '12', 26.075000, 12.800000);
    VPad('U2', '13', 26.075000, 12.299998);
    VPad('U2', '14', 26.075000, 11.799999);
    VPad('U2', '15', 26.075000, 11.299998);
    VPad('U2', '16', 26.075000, 10.799999);
    VPad('U2', '17', 26.750000, 10.124999);
    VPad('U2', '18', 27.249999, 10.124999);
    VPad('U2', '19', 27.750000, 10.124999);
    VPad('U2', '2', 26.075000, 17.800000);
    VPad('U2', '20', 28.249999, 10.124999);
    VPad('U2', '21', 28.750001, 10.124999);
    VPad('U2', '22', 29.250000, 10.124999);
    VPad('U2', '23', 29.749999, 10.124999);
    VPad('U2', '24', 30.250000, 10.124999);
    VPad('U2', '25', 30.749999, 10.124999);
    VPad('U2', '26', 31.250001, 10.124999);
    VPad('U2', '27', 31.750000, 10.124999);
    VPad('U2', '28', 32.249999, 10.124999);
    VPad('U2', '29', 32.750001, 10.124999);
    VPad('U2', '3', 26.075000, 17.299998);
    VPad('U2', '30', 33.250000, 10.124999);
    VPad('U2', '31', 33.750001, 10.124999);
    VPad('U2', '32', 34.250000, 10.124999);
    VPad('U2', '33', 34.925000, 10.799999);
    VPad('U2', '34', 34.925000, 11.299998);
    VPad('U2', '35', 34.925000, 11.799999);
    VPad('U2', '36', 34.925000, 12.299998);
    VPad('U2', '37', 34.925000, 12.800000);
    VPad('U2', '38', 34.925000, 13.299999);
    VPad('U2', '39', 34.925000, 13.799998);
    VPad('U2', '4', 26.075000, 16.799999);
    VPad('U2', '40', 34.925000, 14.299999);
    VPad('U2', '41', 34.925000, 14.799998);
    VPad('U2', '42', 34.925000, 15.300000);
    VPad('U2', '43', 34.925000, 15.799999);
    VPad('U2', '44', 34.925000, 16.299998);
    VPad('U2', '45', 34.925000, 16.799999);
    VPad('U2', '46', 34.925000, 17.299998);
    VPad('U2', '47', 34.925000, 17.800000);
    VPad('U2', '48', 34.925000, 18.299999);
    VPad('U2', '49', 34.250000, 18.974999);
    VPad('U2', '5', 26.075000, 16.299998);
    VPad('U2', '50', 33.750001, 18.974999);
    VPad('U2', '51', 33.250000, 18.974999);
    VPad('U2', '52', 32.750001, 18.974999);
    VPad('U2', '53', 32.249999, 18.974999);
    VPad('U2', '54', 31.750000, 18.974999);
    VPad('U2', '55', 31.250001, 18.974999);
    VPad('U2', '56', 30.749999, 18.974999);
    VPad('U2', '57', 30.250000, 18.974999);
    VPad('U2', '58', 29.749999, 18.974999);
    VPad('U2', '59', 29.250000, 18.974999);
    VPad('U2', '6', 26.075000, 15.799999);
    VPad('U2', '60', 28.750001, 18.974999);
    VPad('U2', '61', 28.249999, 18.974999);
    VPad('U2', '62', 27.750000, 18.974999);
    VPad('U2', '63', 27.249999, 18.974999);
    VPad('U2', '64', 26.750000, 18.974999);
    VPad('U2', '7', 26.075000, 15.300000);
    VPad('U2', '8', 26.075000, 14.799998);
    VPad('U2', '9', 26.075000, 14.299999);
    VPad('U2', 'EP', 30.500000, 14.549999);
    VPad('X4', '1', 30.390000, 7.750000);
    VPad('X4', '2', 32.390001, 7.750000);
    VPad('X4', 'MP1', 28.040000, 2.000001);
    VPad('X4', 'MP2', 34.740002, 2.000001);
    VPad('U10', '1', 21.372599, 19.270000);
    VPad('U10', '2', 21.372599, 19.919998);
    VPad('U10', '3', 21.372599, 20.569999);
    VPad('U10', '4', 21.372599, 21.219998);
    VPad('U10', '5', 25.597599, 21.219998);
    VPad('U10', '6', 25.597599, 20.569999);
    VPad('U10', '7', 25.597599, 19.919998);
    VPad('U10', '8', 25.597599, 19.270000);
    VPad('R119', '1', 37.949901, 5.170104);
    VPad('R119', '2', 38.549900, 5.170104);
    VPad('R120', '1', 36.349996, 5.170104);
    VPad('R120', '2', 36.949995, 5.170104);
    VPad('R121', '1', 35.550102, 5.210104);
    VPad('R121', '2', 35.550102, 4.610105);
    VPad('R122', '1', 33.949897, 5.170104);
    VPad('R122', '2', 34.549895, 5.170104);
    VPad('R123', '1', 33.150101, 5.170104);
    VPad('R123', '2', 32.550103, 5.170104);
    VPad('R124', '1', 31.550102, 5.210104);
    VPad('R124', '2', 31.550102, 4.610105);
    VPad('R125', '1', 30.749997, 5.210104);
    VPad('R125', '2', 30.749997, 4.610105);
    VPad('R126', '1', 29.150099, 5.210104);
    VPad('R126', '2', 29.750098, 5.210104);
    VPad('R127', '1', 38.899996, 13.600003);
    VPad('R127', '2', 39.499995, 13.600003);
    VPad('R128', '1', 41.750000, 12.950005);
    VPad('R128', '2', 42.349999, 12.950005);
    VPad('R129', '1', 38.910001, 14.360004);
    VPad('R129', '2', 39.510000, 14.360004);
    VPad('R130', '1', 39.100001, 14.920003);
    VPad('R130', '2', 39.699999, 14.920003);
    VPad('R131', '1', 38.899998, 15.800004);
    VPad('R131', '2', 39.499997, 15.800004);
    VPad('R132', '1', 39.050003, 16.303506);
    VPad('R132', '2', 38.450004, 16.303506);
    VPad('R133', '1', 45.300001, 17.150004);
    VPad('R133', '2', 45.900000, 17.150004);
    VPad('R134', '1', 46.500004, 16.800005);
    VPad('R134', '2', 47.100002, 16.800005);
    VPad('U4', '1', 43.850001, 21.704998);
    VPad('U4', '2', 43.850001, 20.434998);
    VPad('U4', '3', 43.850001, 19.164998);
    VPad('U4', '4', 43.850001, 17.894998);
    VPad('U4', '5', 51.149961, 17.894998);
    VPad('U4', '6', 51.149961, 19.164998);
    VPad('U4', '7', 51.149961, 20.434998);
    VPad('U4', '8', 51.149961, 21.704998);
    VPad('R34', '1', 11.019998, 20.189901);
    VPad('R34', '2', 11.820098, 20.189901);
    VPad('R34', '3', 12.619944, 20.189901);
    VPad('R34', '4', 13.420044, 20.189901);
    VPad('R34', '5', 13.420044, 18.390057);
    VPad('R34', '6', 12.619944, 18.390057);
    VPad('R34', '7', 11.820098, 18.390057);
    VPad('R34', '8', 11.019998, 18.390057);
    VPad('C87', '1', 43.449900, 22.200001);
    VPad('C87', '2', 45.149668, 22.200001);
    VPad('C88', '1', 46.549701, 22.200001);
    VPad('C88', '2', 48.249469, 22.200001);
    VPad('C94', '1', 49.649601, 22.200001);
    VPad('C94', '2', 51.349369, 22.200001);
    VPad('C99', '1', 52.749399, 22.200001);
    VPad('C99', '2', 54.449167, 22.200001);
    VPad('C106', '1', 40.350001, 22.200001);
    VPad('C106', '2', 42.049769, 22.200001);
    VPad('R1', '1', 57.800001, 4.849899);
    VPad('R1', '2', 58.600101, 4.849899);
    VPad('R1', '3', 58.600101, 3.150131);
    VPad('R1', '4', 57.800001, 3.150131);
    If NBad > 0 Then
        ShowMessage('DO NOT SAVE: ' + IntToStr(NBad) + ' check(s) failed after the moves (' + IntToStr(NPadOk) + ' of 139 pads at the no-PMOD place). Close the PcbDoc WITHOUT saving and reopen it.' + #13#10 + Bad + Info)
    Else
        ShowMessage('SyncPlace OK: 27 parts placed, 139 of 139 pads within 0.001 mm of the no-PMOD board, ' +
            '28 designators set (forced to manual: ' + Forced + '). ' + Info + 'Next: the copper script, then FabB_SyncRules. Save only after the copper script reports success.');
End;

