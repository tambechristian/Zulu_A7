{ FabB_SyncBodies.pas -- GENERATED 2026-11-20 by tools/emit_bodies.py (predicted: pre-sync board md5 33023787 + sync_data.json md5 0a30a658); do not edit by hand.
  200 extruded 3D bodies (Mechanical 13) on 197 parts of zulu_a7_fab_b.PcbDoc, heights from tools/body_heights.json.
  PROVISIONAL heights: none.
  Run SyncBodies with zulu_a7_fab_b.PcbDoc focused, after FabB_SyncPlace, the copper script and FabB_SyncRules.
  Refuses, changing nothing, unless every bodied part is at its predicted footprint/side/rotation/origin and the
  only bodies already present are the library bodies of U2, X4, U10, R119-R134 (at most one each, outline within 0.02 mm;
  those are kept). Then adds the rest and re-counts every part (X2 4, others 1). }

Var
    Brd   : IPCB_Board;
    Bad   : String;
    NBad  : Integer;
    Skip  : TStringList;
    Kept  : String;
    NAdd  : Integer;

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
        ShowMessage('Refusing (SyncBodies): focus Zulu_A7_Fab_B\Rev_2\Imported zulu_a7.PrjPcb\zulu_a7_fab_b.PcbDoc first; nothing changed.');
        Exit;
    End;
    Result := PCBServer.GetCurrentPCBBoard;
    If Result = Nil Then
    Begin
        ShowMessage('Refusing (SyncBodies): no PCB board is current; nothing changed.');
        Exit;
    End;
    If Pos('zulu_a7_fab_b.PcbDoc', Result.FileName) = 0 Then
    Begin
        ShowMessage('Refusing (SyncBodies): the current board is ' + Result.FileName + ', not zulu_a7_fab_b.PcbDoc; nothing changed.');
        Result := Nil;
        Exit;
    End;
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

{ a bodied part must be where the bodies were computed }
Procedure Chk(Ref, Pat : String; Bot : Boolean; Rot, X, Y : Double);
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
    If C.Pattern <> Pat Then Fail(Ref + ' footprint is ' + C.Pattern + ', the bodies were computed for ' + Pat);
    If Bot Then
    Begin
        If C.Layer <> eBottomLayer Then Fail(Ref + ' is not on the Bottom side');
    End
    Else
    Begin
        If C.Layer <> eTopLayer Then Fail(Ref + ' is not on the Top side');
    End;
    cx := CoordToMMs(C.X - Brd.XOrigin);
    cy := CoordToMMs(C.Y - Brd.YOrigin);
    If (Abs(cx - X) > 0.002) Or (Abs(cy - Y) > 0.002) Then
        Fail(Ref + ' origin is (' + FormatFloat('0.0000', cx) + ', ' + FormatFloat('0.0000', cy) + '), the bodies were computed for (' + FormatFloat('0.0000', X) + ', ' + FormatFloat('0.0000', Y) + ')');
    If RotOff(C.Rotation, Rot) > 0.01 Then
        Fail(Ref + ' rotation is ' + FormatFloat('0.###', C.Rotation) + ', the bodies were computed for ' + FormatFloat('0.###', Rot));
End;

{ bodies owned by Ref, and the outline box of the last one }
Function BodyCount(Ref : String; Var X0, Y0, X1, Y1 : Double) : Integer;
Var
    It : IPCB_BoardIterator;
    B  : IPCB_ComponentBody;
    Rc : TCoordRect;
Begin
    Result := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    B := It.FirstPCBObject;
    While B <> Nil Do
    Begin
        If B.InComponent Then
        Begin
            If B.Component.Name.Text = Ref Then
            Begin
                Result := Result + 1;
                Rc := B.BoundingRectangle;
                X0 := CoordToMMs(Rc.Left - Brd.XOrigin);
                Y0 := CoordToMMs(Rc.Bottom - Brd.YOrigin);
                X1 := CoordToMMs(Rc.Right - Brd.XOrigin);
                Y1 := CoordToMMs(Rc.Top - Brd.YOrigin);
            End;
        End;
        B := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

Function AllBodies : Integer;
Var
    It : IPCB_BoardIterator;
    B  : IPCB_ComponentBody;
Begin
    Result := 0;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    B := It.FirstPCBObject;
    While B <> Nil Do
    Begin
        Result := Result + 1;
        B := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
End;

{ a part the ECO placed from the no-PMOD library: keep its library body when it matches the emitted box }
Function LibBody(Ref : String; X0, Y0, X1, Y1 : Double) : Integer;
Var
    n : Integer;
    a, b, c, d : Double;
Begin
    a := 0; b := 0; c := 0; d := 0;
    n := BodyCount(Ref, a, b, c, d);
    Result := n;
    If n = 1 Then
    Begin
        If (Abs(a - X0) > 0.02) Or (Abs(b - Y0) > 0.02) Or (Abs(c - X1) > 0.02) Or (Abs(d - Y1) > 0.02) Then
            Fail(Ref + ' carries a library body at ' + FormatFloat('0.000', a) + ',' + FormatFloat('0.000', b) + ' - ' + FormatFloat('0.000', c) + ',' + FormatFloat('0.000', d) + ', not the emitted ' + FormatFloat('0.000', X0) + ',' + FormatFloat('0.000', Y0) + ' - ' + FormatFloat('0.000', X1) + ',' + FormatFloat('0.000', Y1))
        Else
        Begin
            Skip.Add(Ref);
            Kept := Kept + Ref + ' ';
        End;
    End;
    If n > 1 Then
        Fail(Ref + ' already carries ' + IntToStr(n) + ' bodies');
End;

Procedure AddBody(Ref : String; X0, Y0, X1, Y1, H : Double; Bot : Boolean);
Var
    Cm : IPCB_Component;
    B  : IPCB_ComponentBody;
    Ct : IPCB_Contour;
    Md : IPCB_Model;
Begin
    If Skip.IndexOf(Ref) >= 0 Then Exit;
    Cm := Brd.GetPcbComponentByRefDes(Ref);
    B := PCBServer.PCBObjectFactory(eComponentBodyObject, eNoDimension, eCreate_Default);
    Ct := PCBServer.PCBContourFactory;
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X0), Brd.YOrigin + MMsToCoord(Y0));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X1), Brd.YOrigin + MMsToCoord(Y0));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X1), Brd.YOrigin + MMsToCoord(Y1));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(X0), Brd.YOrigin + MMsToCoord(Y1));
    B.SetOutlineContour(Ct);
    B.Layer := eMechanical13;
    If Bot Then B.BodyProjection := eBoardSide_Bottom Else B.BodyProjection := eBoardSide_Top;
    Md := B.ModelFactory_CreateExtruded(0, MMsToCoord(H), $808080);
    B.SetModel(Md);
    Cm.AddPCBObject(B);
    Brd.AddPCBObject(B);
    NAdd := NAdd + 1;
End;

Procedure Recount(Ref : String; N : Integer);
Var
    a, b, c, d : Double;
    k : Integer;
Begin
    a := 0; b := 0; c := 0; d := 0;
    k := BodyCount(Ref, a, b, c, d);
    If k <> N Then Fail(Ref + ' has ' + IntToStr(k) + ' bodies after the run, expected ' + IntToStr(N));
End;

Procedure SyncBodies;
Var
    nLib, nAll, n : Integer;
Begin
    Brd := SyncBoard;
    If Brd = Nil Then Exit;
    Bad := '';
    NBad := 0;
    Kept := '';
    NAdd := 0;
    Skip := TStringList.Create;

    { ---- preconditions ---- }
    Chk('BTN', 'PTS810', False, 90.000000, 18.000030, 12.920025);
    Chk('C100', 'C0603', True, 0.000000, 41.199885, 21.100001);
    Chk('C101', 'C0603', True, 0.000000, 44.299784, 21.100001);
    Chk('C102', 'C0603', True, 0.000000, 47.399585, 21.100001);
    Chk('C103', 'C0603', True, 0.000000, 50.499485, 21.100001);
    Chk('C104', 'C0603', True, 0.000000, 53.599283, 21.100001);
    Chk('C105', 'C0603', True, 0.000000, 56.699084, 21.100001);
    Chk('C106', 'C0603', True, 0.000000, 41.199885, 22.200001);
    Chk('C107', 'C0201', True, 0.000000, 46.889975, 7.650000);
    Chk('C108', 'C0201', True, 0.000000, 42.449974, 11.050001);
    Chk('C109', 'C0201', True, 0.000000, 44.669974, 7.650000);
    Chk('C11', 'C0402', True, 0.000000, 5.299885, 21.390000);
    Chk('C110', 'C0201', True, 0.000000, 49.109973, 7.650000);
    Chk('C111', 'C0201', True, 0.000000, 51.329974, 11.050001);
    Chk('C112', 'C0201', True, 0.000000, 42.449974, 14.449999);
    Chk('C113', 'C0201', True, 0.000000, 42.449974, 7.650000);
    Chk('C114', 'C0201', True, 0.000000, 51.329974, 14.449999);
    Chk('C115', 'C0201', True, 0.000000, 51.329974, 7.650000);
    Chk('C116', 'C0201', True, 0.000000, 46.889975, 17.850000);
    Chk('C117', 'C0201', True, 0.000000, 44.669974, 17.850000);
    Chk('C118', 'C0201', True, 0.000000, 49.109973, 17.850000);
    Chk('C119', 'C0201', True, 0.000000, 53.550073, 11.050001);
    Chk('C12', 'C0402', True, 0.000000, 7.599787, 21.390000);
    Chk('C120', 'C0201', True, 0.000000, 42.449974, 17.850000);
    Chk('C121', 'C0201', True, 0.000000, 53.550073, 14.449999);
    Chk('C122', 'C0201', True, 0.000000, 53.550073, 7.650000);
    Chk('C123', 'C0201', True, 180.000000, 47.150025, 14.449999);
    Chk('C124', 'C0402', True, 0.000000, 48.599987, 4.249900);
    Chk('C13', 'C0603', True, 0.000000, 2.599883, 21.440000);
    Chk('C133', 'C0201', True, 0.000000, 22.449973, 3.949901);
    Chk('C134', 'C0201', True, 0.000000, 23.649874, 3.949901);
    Chk('C135', 'C0201', True, 0.000000, 24.849775, 3.949901);
    Chk('C136', 'C0201', True, 0.000000, 26.049674, 3.949901);
    Chk('C137', 'C0201', True, 0.000000, 27.249674, 3.949901);
    Chk('C138', 'C0201', True, 0.000000, 28.449575, 3.949901);
    Chk('C139', 'C0402', True, 0.000000, 24.000285, 3.049999);
    Chk('C140', 'C0805', False, 90.000000, 53.000100, 6.699885);
    Chk('C141', 'C0805', False, 90.000000, 54.800200, 6.699885);
    Chk('C142', 'C0805', False, 90.000000, 56.600301, 6.699885);
    Chk('C143', 'C0805', False, 90.000000, 53.000100, 9.999584);
    Chk('C144', 'C0805', False, 90.000000, 54.800200, 9.999584);
    Chk('C145', 'C0805', False, 90.000000, 56.600301, 9.999584);
    Chk('C146', 'C0805', False, 90.000000, 53.000100, 13.299384);
    Chk('C147', 'C0603', True, 270.000000, 2.600000, 9.699998);
    Chk('C148', 'C0603', True, 0.000000, 11.050001, 12.049999);
    Chk('C149', 'C0805', True, 0.000000, 5.950001, 19.349999);
    Chk('C150', 'C0603', True, 0.000000, 4.699884, 7.474999);
    Chk('C151', 'C0603', True, 0.000000, 4.999883, 6.150000);
    Chk('C152', 'C0201', True, 0.000000, 29.649473, 3.949901);
    Chk('C153', 'C0201', True, 0.000000, 30.849374, 3.949901);
    Chk('C154', 'C0201', True, 0.000000, 32.049375, 3.949901);
    Chk('C155', 'C0201', False, 180.000000, 25.999925, 20.250000);
    Chk('C156', 'C0201', True, 180.000000, 29.549926, 20.000001);
    Chk('C157', 'C0201', False, 180.000000, 39.049927, 18.000000);
    Chk('C158', 'C0201', False, 270.000000, 18.099999, 16.649926);
    Chk('C159', 'C0201', False, 180.000000, 23.299925, 7.500000);
    Chk('C160', 'C0402', True, 0.000000, 8.225000, 5.300000);
    Chk('C161', 'C0402', True, 270.000000, 5.150000, 16.474999);
    Chk('C163', 'C0201', True, 0.000000, 8.299999, 6.450000);
    Chk('C164', 'C0201', True, 0.000000, 10.499999, 12.925001);
    Chk('C165', 'C0201', True, 180.000000, 11.475001, 13.500001);
    Chk('C166', 'C0201', True, 0.000000, 4.199999, 13.249999);
    Chk('C167', 'C0402', True, 0.000000, 8.450001, 12.049999);
    Chk('C168', 'C0603', True, 270.000000, 6.450000, 16.774998);
    Chk('C3', 'C0402', True, 0.000000, 26.300285, 3.049999);
    Chk('C36', 'C0402', True, 0.000000, 40.999987, 3.049999);
    Chk('C37', 'C0402', True, 0.000000, 43.299987, 3.049999);
    Chk('C38', 'C0201', True, 0.000000, 33.249273, 3.949901);
    Chk('C4', 'C0402', True, 0.000000, 28.600187, 3.049999);
    Chk('C40', 'C0201', True, 0.000000, 34.449174, 3.949901);
    Chk('C41', 'C0201', True, 0.000000, 35.649075, 3.949901);
    Chk('C5', 'C0402', True, 0.000000, 30.900187, 3.049999);
    Chk('C6', 'C0402', True, 0.000000, 33.200185, 3.049999);
    Chk('C7', 'C0402', True, 0.000000, 35.500186, 3.049999);
    Chk('C78', 'C0805', True, 90.000000, 1.140000, 7.899885);
    Chk('C8', 'C0402', True, 0.000000, 37.800186, 3.049999);
    Chk('C80', 'C0805', True, 270.000000, 13.410001, 12.050116);
    Chk('C82', 'C0603', True, 90.000000, 13.650001, 4.424883);
    Chk('C84', 'C0603', True, 270.000000, 11.775001, 16.000115);
    Chk('C85', 'C0805', False, 90.000000, 54.800200, 13.299384);
    Chk('C86', 'C0805', False, 90.000000, 56.600301, 13.299384);
    Chk('C87', 'C0603', True, 0.000000, 44.299784, 22.200001);
    Chk('C88', 'C0603', True, 0.000000, 47.399585, 22.200001);
    Chk('C89', 'C0201', True, 0.000000, 46.889975, 11.050001);
    Chk('C9', 'C0402', True, 0.000000, 18.399986, 4.249900);
    Chk('C90', 'C0201', True, 0.000000, 44.669974, 11.050001);
    Chk('C91', 'C0201', True, 0.000000, 49.109973, 11.050001);
    Chk('C92', 'C0201', True, 180.000000, 45.900025, 14.449999);
    Chk('C93', 'C0805', False, 90.000000, 53.000100, 16.599083);
    Chk('C94', 'C0603', True, 0.000000, 50.499485, 22.200001);
    Chk('C95', 'C0201', True, 0.000000, 49.109973, 14.449999);
    Chk('C96', 'C0201', True, 0.000000, 44.669974, 14.449999);
    Chk('C97', 'C0805', False, 90.000000, 54.800200, 16.599083);
    Chk('C98', 'C0805', False, 90.000000, 56.600301, 16.599083);
    Chk('C99', 'C0603', True, 0.000000, 53.599283, 22.200001);
    Chk('J1', '2X06', False, 90.000000, 66.399999, 12.700000);
    Chk('L1', 'IND2520', True, 270.000000, 14.275001, 8.599995);
    Chk('L2', 'IND2520', True, 0.000000, 11.225004, 5.300000);
    Chk('L3', 'IND2520', True, 0.000000, 9.100005, 14.924999);
    Chk('L4', 'IND0603', True, 0.000000, 18.650100, 3.049999);
    Chk('L5', 'IND0603', True, 0.000000, 21.450201, 3.049999);
    Chk('L6', 'IND0603', True, 0.000000, 48.850100, 3.049999);
    Chk('L7', 'IND0603', True, 0.000000, 51.650199, 3.049999);
    Chk('L8', 'IND2520', True, 270.000000, 4.450001, 9.875002);
    Chk('L9', 'IND2520', True, 90.000000, 6.000001, 13.475000);
    Chk('LD0', 'EVERLIGHT-19-337', False, 0.000000, 22.200022, 8.909985);
    Chk('LD1', 'LED0603', False, 0.000000, 22.199999, 10.985000);
    Chk('LD2', 'LED0603', False, 0.000000, 22.199999, 12.584999);
    Chk('LD3', 'LED0603', False, 0.000000, 22.199999, 15.785000);
    Chk('LD4', 'LED0603', False, 0.000000, 22.199999, 17.385000);
    Chk('Q1', '32X25', False, 0.000000, 40.450000, 20.849900);
    Chk('R1', '742C043', True, 0.000000, 58.200051, 4.000015);
    Chk('R10', 'R0201', True, 0.000000, 45.049973, 2.750000);
    Chk('R101', 'R0201', True, 0.000000, 17.849974, 18.750001);
    Chk('R102', 'R0402', True, 180.000000, 5.925015, 4.974999);
    Chk('R103', 'R0402', True, 180.000000, 3.640013, 12.350001);
    Chk('R107', 'R0402', True, 270.000000, 15.375001, 12.325015);
    Chk('R108', 'R0402', True, 0.000000, 2.524986, 13.475000);
    Chk('R11', 'R0201', True, 0.000000, 46.249874, 2.750000);
    Chk('R113', 'R0201', True, 180.000000, 10.500002, 3.800000);
    Chk('R114', 'R0201', True, 180.000000, 7.200001, 6.274999);
    Chk('R115', 'R0201', True, 0.000000, 9.299999, 12.949999);
    Chk('R116', 'R0201', True, 270.000000, 12.400001, 8.925001);
    Chk('R117', 'R0201', True, 0.000000, 11.600000, 12.900000);
    Chk('R118', 'R0201', True, 270.000000, 4.349999, 14.075001);
    Chk('R119', 'R0201', True, 0.000000, 38.249901, 5.170104);
    Chk('R12', 'R0201', True, 0.000000, 40.449975, 3.949901);
    Chk('R120', 'R0201', True, 0.000000, 36.649995, 5.170104);
    Chk('R121', 'R0201', True, 270.000000, 35.550102, 4.910104);
    Chk('R122', 'R0201', True, 0.000000, 34.249896, 5.170104);
    Chk('R123', 'R0201', True, 180.000000, 32.850102, 5.170104);
    Chk('R124', 'R0201', True, 270.000000, 31.550102, 4.910104);
    Chk('R125', 'R0201', True, 270.000000, 30.749997, 4.910104);
    Chk('R126', 'R0201', True, 0.000000, 29.450099, 5.210104);
    Chk('R127', 'R0201', False, 0.000000, 39.199995, 13.600003);
    Chk('R128', 'R0201', True, 0.000000, 42.050000, 12.950005);
    Chk('R129', 'R0201', False, 0.000000, 39.210000, 14.360004);
    Chk('R13', 'R0201', True, 0.000000, 41.649874, 3.949901);
    Chk('R130', 'R0201', False, 0.000000, 39.400000, 14.920003);
    Chk('R131', 'R0201', False, 0.000000, 39.199998, 15.800004);
    Chk('R132', 'R0201', False, 180.000000, 38.750004, 16.303506);
    Chk('R133', 'R0201', True, 0.000000, 45.600000, 17.150004);
    Chk('R134', 'R0201', True, 0.000000, 46.800003, 16.800005);
    Chk('R14', 'R0201', True, 0.000000, 42.849775, 3.949901);
    Chk('R15', 'R0201', True, 0.000000, 44.049775, 3.949901);
    Chk('R16', 'R0201', True, 0.000000, 45.249673, 3.949901);
    Chk('R17', 'R0201', True, 0.000000, 46.449574, 3.949901);
    Chk('R18', 'R0402', True, 0.000000, 20.699987, 4.249900);
    Chk('R19', 'R0201', True, 0.000000, 19.049873, 18.750001);
    Chk('R2', 'R0201', True, 0.000000, 55.749175, 22.049999);
    Chk('R20', 'R0201', True, 0.000000, 52.649973, 3.949901);
    Chk('R21', 'R0402', True, 0.000000, 50.899987, 4.249900);
    Chk('R22', 'R0201', True, 0.000000, 53.849875, 3.949901);
    Chk('R23', 'R0201', True, 0.000000, 55.049773, 3.949901);
    Chk('R24', 'R0201', True, 0.000000, 59.049973, 5.649999);
    Chk('R25', 'R0201', True, 0.000000, 61.099974, 5.649999);
    Chk('R26', 'R0201', True, 0.000000, 63.150074, 5.649999);
    Chk('R27', 'R0201', True, 0.000000, 59.049973, 8.490001);
    Chk('R28', 'R0201', True, 0.000000, 61.099974, 8.490001);
    Chk('R29', 'R0201', True, 0.000000, 63.150074, 8.490001);
    Chk('R30', 'R0201', True, 0.000000, 59.049973, 11.330000);
    Chk('R31', 'R0201', True, 0.000000, 61.099974, 11.330000);
    Chk('R32', 'R0201', True, 0.000000, 63.150074, 11.330000);
    Chk('R33', 'R0201', True, 0.000000, 59.049973, 14.170000);
    Chk('R34', '742C083', True, 0.000000, 11.420048, 19.289979);
    Chk('R35', 'R0402', True, 0.000000, 9.899787, 21.390000);
    Chk('R4', '742C163', False, 90.000000, 59.300016, 18.177995);
    Chk('R5', 'R0201', True, 0.000000, 61.099974, 14.170000);
    Chk('R6', 'R0201', True, 0.000000, 56.949073, 22.049999);
    Chk('R7', 'R0201', True, 0.000000, 58.148974, 22.049999);
    Chk('R80', 'R0402', True, 0.000000, 29.549987, 19.050000);
    Chk('R81', 'R0402', True, 0.000000, 31.849987, 19.050000);
    Chk('R82', 'R0402', True, 0.000000, 34.149985, 19.050000);
    Chk('R83', 'R0402', True, 0.000000, 36.449986, 19.050000);
    Chk('R84', 'R0402', True, 0.000000, 30.849987, 20.849900);
    Chk('R85', 'R0402', True, 0.000000, 37.549986, 20.249901);
    Chk('R86', 'R0402', True, 0.000000, 30.849987, 22.049798);
    Chk('R90', 'R0201', True, 0.000000, 63.150074, 14.170000);
    Chk('R91', 'R0201', True, 0.000000, 59.049973, 17.009999);
    Chk('R92', 'R0201', True, 0.000000, 61.099974, 17.009999);
    Chk('R93', 'R0201', True, 0.000000, 63.150074, 17.009999);
    Chk('R94', 'R0201', True, 0.000000, 59.049973, 19.850001);
    Chk('R96', 'R0201', True, 0.000000, 19.289773, 19.950001);
    Chk('R97', 'R0201', True, 0.000000, 17.849974, 19.349999);
    Chk('R98', 'R0201', True, 0.000000, 19.049873, 19.349999);
    Chk('R99', 'R0201', True, 0.000000, 61.099974, 19.850001);
    Chk('U1', 'XC7A35T-CPG236', False, 0.000000, 41.900000, 16.400000);
    Chk('U10', 'MSOP-8_3X3_P0.65', True, 0.000000, 23.485099, 20.244999);
    Chk('U2', 'FT2232HQ-QFN64', False, 0.000000, 30.500000, 14.549999);
    Chk('U3', 'TSOPII-54', True, 90.000000, 38.750001, 6.170099);
    Chk('U4', 'SOIC-8_208MIL', False, 0.000000, 43.550535, 21.704998);
    Chk('U7', 'SOT23-5', True, 0.000000, 8.900000, 18.125001);
    Chk('U8', 'QFN28-UFD-4X5', True, 270.000000, 9.100000, 9.100002);
    Chk('X1', 'MOLEX-105017-0001', False, 0.000000, 30.480028, 21.258500);
    Chk('X2', 'ZULU-DIP37', False, 0.000000, 0.000000, 0.000000);
    Chk('X3', 'DM3D-SF', False, 90.000000, 8.799998, 12.475007);
    Chk('X4', 'JST-S2B-PH-SM4-TB', False, 0.000000, 31.390001, 4.900000);
    nLib := 0;
    n := LibBody('U2', 26.0000, 10.0500, 35.0000, 19.0500);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('X4', 27.4400, 0.5000, 35.3400, 8.1000);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('U10', 21.9851, 18.7450, 24.9851, 21.7450);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R119', 37.9499, 5.0201, 38.5499, 5.3201);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R120', 36.3500, 5.0201, 36.9500, 5.3201);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R121', 35.4001, 4.6101, 35.7001, 5.2101);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R122', 33.9499, 5.0201, 34.5499, 5.3201);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R123', 32.5501, 5.0201, 33.1501, 5.3201);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R124', 31.4001, 4.6101, 31.7001, 5.2101);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R125', 30.6000, 4.6101, 30.9000, 5.2101);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R126', 29.1501, 5.0601, 29.7501, 5.3601);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R127', 38.9000, 13.4500, 39.5000, 13.7500);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R128', 41.7500, 12.8000, 42.3500, 13.1000);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R129', 38.9100, 14.2100, 39.5100, 14.5100);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R130', 39.1000, 14.7700, 39.7000, 15.0700);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R131', 38.9000, 15.6500, 39.5000, 15.9500);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R132', 38.4500, 16.1535, 39.0500, 16.4535);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R133', 45.3000, 17.0000, 45.9000, 17.3000);
    If n = 1 Then nLib := nLib + 1;
    n := LibBody('R134', 46.5000, 16.6500, 47.1000, 16.9500);
    If n = 1 Then nLib := nLib + 1;
    nAll := AllBodies;
    If nAll <> nLib Then
        Fail(IntToStr(nAll - nLib) + ' bodies on the board belong to no part or to parts other than the library-placed ones (reload the board from disk)');
    If NBad > 0 Then
    Begin
        ShowMessage('Refusing: ' + IntToStr(NBad) + ' precondition(s) failed; NOTHING was changed.' + #13#10 + Bad);
        Skip.Free;
        Exit;
    End;

    { ---- bodies ---- }
    PCBServer.PreProcess;
    Try
        AddBody('BTN', 16.4000, 10.8200, 19.6000, 15.0200, 2.700, False);   { BTN PTS810 }
        AddBody('C140', 52.3751, 5.6999, 53.6251, 7.6999, 1.450, False);   { C140 C0805 }
        AddBody('C141', 54.1752, 5.6999, 55.4252, 7.6999, 1.450, False);   { C141 C0805 }
        AddBody('C142', 55.9753, 5.6999, 57.2253, 7.6999, 1.450, False);   { C142 C0805 }
        AddBody('C143', 52.3751, 8.9996, 53.6251, 10.9996, 1.450, False);   { C143 C0805 }
        AddBody('C144', 54.1752, 8.9996, 55.4252, 10.9996, 1.450, False);   { C144 C0805 }
        AddBody('C145', 55.9753, 8.9996, 57.2253, 10.9996, 1.450, False);   { C145 C0805 }
        AddBody('C146', 52.3751, 12.2994, 53.6251, 14.2994, 1.450, False);   { C146 C0805 }
        AddBody('C155', 25.6999, 20.1000, 26.2999, 20.4000, 0.330, False);   { C155 C0201 }
        AddBody('C157', 38.7499, 17.8500, 39.3499, 18.1500, 0.330, False);   { C157 C0201 }
        AddBody('C158', 17.9500, 16.3499, 18.2500, 16.9499, 0.330, False);   { C158 C0201 }
        AddBody('C159', 22.9999, 7.3500, 23.5999, 7.6500, 0.330, False);   { C159 C0201 }
        AddBody('C85', 54.1752, 12.2994, 55.4252, 14.2994, 1.450, False);   { C85 C0805 }
        AddBody('C86', 55.9753, 12.2994, 57.2253, 14.2994, 1.450, False);   { C86 C0805 }
        AddBody('C93', 52.3751, 15.5991, 53.6251, 17.5991, 1.450, False);   { C93 C0805 }
        AddBody('C97', 54.1752, 15.5991, 55.4252, 17.5991, 1.450, False);   { C97 C0805 }
        AddBody('C98', 55.9753, 15.5991, 57.2253, 17.5991, 1.450, False);   { C98 C0805 }
        AddBody('J1', 63.8600, 5.0800, 68.9400, 20.3200, 8.510, False);   { J1 2X06 }
        AddBody('LD0', 21.4000, 8.1100, 23.0000, 9.7100, 0.450, False);   { LD0 EVERLIGHT-19-337 }
        AddBody('LD1', 21.4000, 10.5850, 23.0000, 11.3850, 0.650, False);   { LD1 LED0603 }
        AddBody('LD2', 21.4000, 12.1850, 23.0000, 12.9850, 0.650, False);   { LD2 LED0603 }
        AddBody('LD3', 21.4000, 15.3850, 23.0000, 16.1850, 0.650, False);   { LD3 LED0603 }
        AddBody('LD4', 21.4000, 16.9850, 23.0000, 17.7850, 0.650, False);   { LD4 LED0603 }
        AddBody('Q1', 40.0500, 18.1500, 42.5500, 21.3500, 1.200, False);   { Q1 32X25 }
        AddBody('R127', 38.9000, 13.4500, 39.5000, 13.7500, 0.260, False);   { R127 R0201 }
        AddBody('R129', 38.9100, 14.2100, 39.5100, 14.5100, 0.260, False);   { R129 R0201 }
        AddBody('R130', 39.1000, 14.7700, 39.7000, 15.0700, 0.260, False);   { R130 R0201 }
        AddBody('R131', 38.9000, 15.6500, 39.5000, 15.9500, 0.260, False);   { R131 R0201 }
        AddBody('R132', 38.4500, 16.1535, 39.0500, 16.4535, 0.260, False);   { R132 R0201 }
        AddBody('R4', 58.5000, 14.9780, 60.1000, 21.3780, 0.700, False);   { R4 742C163 }
        AddBody('U1', 41.4000, 6.9000, 51.4000, 16.9000, 1.380, False);   { U1 XC7A35T-CPG236 }
        AddBody('U2', 26.0000, 10.0500, 35.0000, 19.0500, 0.900, False);   { U2 FT2232HQ-QFN64 }
        AddBody('U4', 44.8600, 17.1600, 50.1400, 22.4400, 2.160, False);   { U4 SOIC-8_208MIL }
        AddBody('X1', 26.7049, 21.0745, 34.2551, 26.1245, 2.850, False);   { X1 MOLEX-105017-0001 }
        AddBody('X3', 3.0116, 6.4364, 14.5884, 18.5136, 1.550, False);   { X3 DM3D-SF }
        AddBody('X4', 27.4400, 0.5000, 35.3400, 8.1000, 5.500, False);   { X4 JST-S2B-PH-SM4-TB }
        AddBody('C100', 40.3999, 20.7000, 41.9999, 21.5000, 1.050, True);   { C100 C0603 }
        AddBody('C101', 43.4998, 20.7000, 45.0998, 21.5000, 1.050, True);   { C101 C0603 }
        AddBody('C102', 46.5996, 20.7000, 48.1996, 21.5000, 1.050, True);   { C102 C0603 }
        AddBody('C103', 49.6995, 20.7000, 51.2995, 21.5000, 1.050, True);   { C103 C0603 }
        AddBody('C104', 52.7993, 20.7000, 54.3993, 21.5000, 1.050, True);   { C104 C0603 }
        AddBody('C105', 55.8991, 20.7000, 57.4991, 21.5000, 1.050, True);   { C105 C0603 }
        AddBody('C106', 40.3999, 21.8000, 41.9999, 22.6000, 1.050, True);   { C106 C0603 }
        AddBody('C107', 46.5900, 7.5000, 47.1900, 7.8000, 0.330, True);   { C107 C0201 }
        AddBody('C108', 42.1500, 10.9000, 42.7500, 11.2000, 0.330, True);   { C108 C0201 }
        AddBody('C109', 44.3700, 7.5000, 44.9700, 7.8000, 0.330, True);   { C109 C0201 }
        AddBody('C11', 4.7999, 21.1400, 5.7999, 21.6400, 0.650, True);   { C11 C0402 }
        AddBody('C110', 48.8100, 7.5000, 49.4100, 7.8000, 0.330, True);   { C110 C0201 }
        AddBody('C111', 51.0300, 10.9000, 51.6300, 11.2000, 0.330, True);   { C111 C0201 }
        AddBody('C112', 42.1500, 14.3000, 42.7500, 14.6000, 0.330, True);   { C112 C0201 }
        AddBody('C113', 42.1500, 7.5000, 42.7500, 7.8000, 0.330, True);   { C113 C0201 }
        AddBody('C114', 51.0300, 14.3000, 51.6300, 14.6000, 0.330, True);   { C114 C0201 }
        AddBody('C115', 51.0300, 7.5000, 51.6300, 7.8000, 0.330, True);   { C115 C0201 }
        AddBody('C116', 46.5900, 17.7000, 47.1900, 18.0000, 0.330, True);   { C116 C0201 }
        AddBody('C117', 44.3700, 17.7000, 44.9700, 18.0000, 0.330, True);   { C117 C0201 }
        AddBody('C118', 48.8100, 17.7000, 49.4100, 18.0000, 0.330, True);   { C118 C0201 }
        AddBody('C119', 53.2501, 10.9000, 53.8501, 11.2000, 0.330, True);   { C119 C0201 }
        AddBody('C12', 7.0998, 21.1400, 8.0998, 21.6400, 0.650, True);   { C12 C0402 }
        AddBody('C120', 42.1500, 17.7000, 42.7500, 18.0000, 0.330, True);   { C120 C0201 }
        AddBody('C121', 53.2501, 14.3000, 53.8501, 14.6000, 0.330, True);   { C121 C0201 }
        AddBody('C122', 53.2501, 7.5000, 53.8501, 7.8000, 0.330, True);   { C122 C0201 }
        AddBody('C123', 46.8500, 14.3000, 47.4500, 14.6000, 0.330, True);   { C123 C0201 }
        AddBody('C124', 48.1000, 3.9999, 49.1000, 4.4999, 0.650, True);   { C124 C0402 }
        AddBody('C13', 1.7999, 21.0400, 3.3999, 21.8400, 1.050, True);   { C13 C0603 }
        AddBody('C133', 22.1500, 3.7999, 22.7500, 4.0999, 0.330, True);   { C133 C0201 }
        AddBody('C134', 23.3499, 3.7999, 23.9499, 4.0999, 0.330, True);   { C134 C0201 }
        AddBody('C135', 24.5498, 3.7999, 25.1498, 4.0999, 0.330, True);   { C135 C0201 }
        AddBody('C136', 25.7497, 3.7999, 26.3497, 4.0999, 0.330, True);   { C136 C0201 }
        AddBody('C137', 26.9497, 3.7999, 27.5497, 4.0999, 0.330, True);   { C137 C0201 }
        AddBody('C138', 28.1496, 3.7999, 28.7496, 4.0999, 0.330, True);   { C138 C0201 }
        AddBody('C139', 23.5003, 2.8000, 24.5003, 3.3000, 0.650, True);   { C139 C0402 }
        AddBody('C147', 2.2000, 8.9000, 3.0000, 10.5000, 1.050, True);   { C147 C0603 }
        AddBody('C148', 10.2500, 11.6500, 11.8500, 12.4500, 1.050, True);   { C148 C0603 }
        AddBody('C149', 4.9500, 18.7250, 6.9500, 19.9750, 1.450, True);   { C149 C0805 }
        AddBody('C150', 3.8999, 7.0750, 5.4999, 7.8750, 1.050, True);   { C150 C0603 }
        AddBody('C151', 4.1999, 5.7500, 5.7999, 6.5500, 1.050, True);   { C151 C0603 }
        AddBody('C152', 29.3495, 3.7999, 29.9495, 4.0999, 0.330, True);   { C152 C0201 }
        AddBody('C153', 30.5494, 3.7999, 31.1494, 4.0999, 0.330, True);   { C153 C0201 }
        AddBody('C154', 31.7494, 3.7999, 32.3494, 4.0999, 0.330, True);   { C154 C0201 }
        AddBody('C156', 29.2499, 19.8500, 29.8499, 20.1500, 0.330, True);   { C156 C0201 }
        AddBody('C160', 7.7250, 5.0500, 8.7250, 5.5500, 0.650, True);   { C160 C0402 }
        AddBody('C161', 4.9000, 15.9750, 5.4000, 16.9750, 0.650, True);   { C161 C0402 }
        AddBody('C163', 8.0000, 6.3000, 8.6000, 6.6000, 0.330, True);   { C163 C0201 }
        AddBody('C164', 10.2000, 12.7750, 10.8000, 13.0750, 0.330, True);   { C164 C0201 }
        AddBody('C165', 11.1750, 13.3500, 11.7750, 13.6500, 0.330, True);   { C165 C0201 }
        AddBody('C166', 3.9000, 13.1000, 4.5000, 13.4000, 0.330, True);   { C166 C0201 }
        AddBody('C167', 7.9500, 11.8000, 8.9500, 12.3000, 0.650, True);   { C167 C0402 }
        AddBody('C168', 6.0500, 15.9750, 6.8500, 17.5750, 1.050, True);   { C168 C0603 }
        AddBody('C3', 25.8003, 2.8000, 26.8003, 3.3000, 0.650, True);   { C3 C0402 }
        AddBody('C36', 40.5000, 2.8000, 41.5000, 3.3000, 0.650, True);   { C36 C0402 }
        AddBody('C37', 42.8000, 2.8000, 43.8000, 3.3000, 0.650, True);   { C37 C0402 }
        AddBody('C38', 32.9493, 3.7999, 33.5493, 4.0999, 0.330, True);   { C38 C0201 }
        AddBody('C4', 28.1002, 2.8000, 29.1002, 3.3000, 0.650, True);   { C4 C0402 }
        AddBody('C40', 34.1492, 3.7999, 34.7492, 4.0999, 0.330, True);   { C40 C0201 }
        AddBody('C41', 35.3491, 3.7999, 35.9491, 4.0999, 0.330, True);   { C41 C0201 }
        AddBody('C5', 30.4002, 2.8000, 31.4002, 3.3000, 0.650, True);   { C5 C0402 }
        AddBody('C6', 32.7002, 2.8000, 33.7002, 3.3000, 0.650, True);   { C6 C0402 }
        AddBody('C7', 35.0002, 2.8000, 36.0002, 3.3000, 0.650, True);   { C7 C0402 }
        AddBody('C78', 0.5150, 6.8999, 1.7650, 8.8999, 1.450, True);   { C78 C0805 }
        AddBody('C8', 37.3002, 2.8000, 38.3002, 3.3000, 0.650, True);   { C8 C0402 }
        AddBody('C80', 12.7850, 11.0501, 14.0350, 13.0501, 1.450, True);   { C80 C0805 }
        AddBody('C82', 13.2500, 3.6249, 14.0500, 5.2249, 1.050, True);   { C82 C0603 }
        AddBody('C84', 11.3750, 15.2001, 12.1750, 16.8001, 1.050, True);   { C84 C0603 }
        AddBody('C87', 43.4998, 21.8000, 45.0998, 22.6000, 1.050, True);   { C87 C0603 }
        AddBody('C88', 46.5996, 21.8000, 48.1996, 22.6000, 1.050, True);   { C88 C0603 }
        AddBody('C89', 46.5900, 10.9000, 47.1900, 11.2000, 0.330, True);   { C89 C0201 }
        AddBody('C9', 17.9000, 3.9999, 18.9000, 4.4999, 0.650, True);   { C9 C0402 }
        AddBody('C90', 44.3700, 10.9000, 44.9700, 11.2000, 0.330, True);   { C90 C0201 }
        AddBody('C91', 48.8100, 10.9000, 49.4100, 11.2000, 0.330, True);   { C91 C0201 }
        AddBody('C92', 45.6000, 14.3000, 46.2000, 14.6000, 0.330, True);   { C92 C0201 }
        AddBody('C94', 49.6995, 21.8000, 51.2995, 22.6000, 1.050, True);   { C94 C0603 }
        AddBody('C95', 48.8100, 14.3000, 49.4100, 14.6000, 0.330, True);   { C95 C0201 }
        AddBody('C96', 44.3700, 14.3000, 44.9700, 14.6000, 0.330, True);   { C96 C0201 }
        AddBody('C99', 52.7993, 21.8000, 54.3993, 22.6000, 1.050, True);   { C99 C0603 }
        AddBody('L1', 13.2750, 7.3500, 15.2750, 9.8500, 1.200, True);   { L1 IND2520 }
        AddBody('L2', 9.9750, 4.3000, 12.4750, 6.3000, 1.200, True);   { L2 IND2520 }
        AddBody('L3', 7.8500, 13.9250, 10.3500, 15.9250, 1.200, True);   { L3 IND2520 }
        AddBody('L4', 17.8501, 2.6500, 19.4501, 3.4500, 0.950, True);   { L4 IND0603 }
        AddBody('L5', 20.6502, 2.6500, 22.2502, 3.4500, 0.950, True);   { L5 IND0603 }
        AddBody('L6', 48.0501, 2.6500, 49.6501, 3.4500, 0.950, True);   { L6 IND0603 }
        AddBody('L7', 50.8502, 2.6500, 52.4502, 3.4500, 0.950, True);   { L7 IND0603 }
        AddBody('L8', 3.4500, 8.6250, 5.4500, 11.1250, 1.200, True);   { L8 IND2520 }
        AddBody('L9', 5.0000, 12.2250, 7.0000, 14.7250, 1.200, True);   { L9 IND2520 }
        AddBody('R1', 57.4001, 3.2000, 59.0001, 4.8000, 0.700, True);   { R1 742C043 }
        AddBody('R10', 44.7500, 2.6000, 45.3500, 2.9000, 0.260, True);   { R10 R0201 }
        AddBody('R101', 17.5500, 18.6000, 18.1500, 18.9000, 0.260, True);   { R101 R0201 }
        AddBody('R102', 5.4250, 4.7250, 6.4250, 5.2250, 0.400, True);   { R102 R0402 }
        AddBody('R103', 3.1400, 12.1000, 4.1400, 12.6000, 0.400, True);   { R103 R0402 }
        AddBody('R107', 15.1250, 11.8250, 15.6250, 12.8250, 0.400, True);   { R107 R0402 }
        AddBody('R108', 2.0250, 13.2250, 3.0250, 13.7250, 0.400, True);   { R108 R0402 }
        AddBody('R11', 45.9499, 2.6000, 46.5499, 2.9000, 0.260, True);   { R11 R0201 }
        AddBody('R113', 10.2000, 3.6500, 10.8000, 3.9500, 0.260, True);   { R113 R0201 }
        AddBody('R114', 6.9000, 6.1250, 7.5000, 6.4250, 0.260, True);   { R114 R0201 }
        AddBody('R115', 9.0000, 12.8000, 9.6000, 13.1000, 0.260, True);   { R115 R0201 }
        AddBody('R116', 12.2500, 8.6250, 12.5500, 9.2250, 0.260, True);   { R116 R0201 }
        AddBody('R117', 11.3000, 12.7500, 11.9000, 13.0500, 0.260, True);   { R117 R0201 }
        AddBody('R118', 4.2000, 13.7750, 4.5000, 14.3750, 0.260, True);   { R118 R0201 }
        AddBody('R119', 37.9499, 5.0201, 38.5499, 5.3201, 0.260, True);   { R119 R0201 }
        AddBody('R12', 40.1500, 3.7999, 40.7500, 4.0999, 0.260, True);   { R12 R0201 }
        AddBody('R120', 36.3500, 5.0201, 36.9500, 5.3201, 0.260, True);   { R120 R0201 }
        AddBody('R121', 35.4001, 4.6101, 35.7001, 5.2101, 0.260, True);   { R121 R0201 }
        AddBody('R122', 33.9499, 5.0201, 34.5499, 5.3201, 0.260, True);   { R122 R0201 }
        AddBody('R123', 32.5501, 5.0201, 33.1501, 5.3201, 0.260, True);   { R123 R0201 }
        AddBody('R124', 31.4001, 4.6101, 31.7001, 5.2101, 0.260, True);   { R124 R0201 }
        AddBody('R125', 30.6000, 4.6101, 30.9000, 5.2101, 0.260, True);   { R125 R0201 }
        AddBody('R126', 29.1501, 5.0601, 29.7501, 5.3601, 0.260, True);   { R126 R0201 }
        AddBody('R128', 41.7500, 12.8000, 42.3500, 13.1000, 0.260, True);   { R128 R0201 }
        AddBody('R13', 41.3499, 3.7999, 41.9499, 4.0999, 0.260, True);   { R13 R0201 }
        AddBody('R133', 45.3000, 17.0000, 45.9000, 17.3000, 0.260, True);   { R133 R0201 }
        AddBody('R134', 46.5000, 16.6500, 47.1000, 16.9500, 0.260, True);   { R134 R0201 }
        AddBody('R14', 42.5498, 3.7999, 43.1498, 4.0999, 0.260, True);   { R14 R0201 }
        AddBody('R15', 43.7498, 3.7999, 44.3498, 4.0999, 0.260, True);   { R15 R0201 }
        AddBody('R16', 44.9497, 3.7999, 45.5497, 4.0999, 0.260, True);   { R16 R0201 }
        AddBody('R17', 46.1496, 3.7999, 46.7496, 4.0999, 0.260, True);   { R17 R0201 }
        AddBody('R18', 20.2000, 3.9999, 21.2000, 4.4999, 0.400, True);   { R18 R0402 }
        AddBody('R19', 18.7499, 18.6000, 19.3499, 18.9000, 0.260, True);   { R19 R0201 }
        AddBody('R2', 55.4492, 21.9000, 56.0492, 22.2000, 0.260, True);   { R2 R0201 }
        AddBody('R20', 52.3500, 3.7999, 52.9500, 4.0999, 0.260, True);   { R20 R0201 }
        AddBody('R21', 50.4000, 3.9999, 51.4000, 4.4999, 0.400, True);   { R21 R0402 }
        AddBody('R22', 53.5499, 3.7999, 54.1499, 4.0999, 0.260, True);   { R22 R0201 }
        AddBody('R23', 54.7498, 3.7999, 55.3498, 4.0999, 0.260, True);   { R23 R0201 }
        AddBody('R24', 58.7500, 5.5000, 59.3500, 5.8000, 0.260, True);   { R24 R0201 }
        AddBody('R25', 60.8000, 5.5000, 61.4000, 5.8000, 0.260, True);   { R25 R0201 }
        AddBody('R26', 62.8501, 5.5000, 63.4501, 5.8000, 0.260, True);   { R26 R0201 }
        AddBody('R27', 58.7500, 8.3400, 59.3500, 8.6400, 0.260, True);   { R27 R0201 }
        AddBody('R28', 60.8000, 8.3400, 61.4000, 8.6400, 0.260, True);   { R28 R0201 }
        AddBody('R29', 62.8501, 8.3400, 63.4501, 8.6400, 0.260, True);   { R29 R0201 }
        AddBody('R30', 58.7500, 11.1800, 59.3500, 11.4800, 0.260, True);   { R30 R0201 }
        AddBody('R31', 60.8000, 11.1800, 61.4000, 11.4800, 0.260, True);   { R31 R0201 }
        AddBody('R32', 62.8501, 11.1800, 63.4501, 11.4800, 0.260, True);   { R32 R0201 }
        AddBody('R33', 58.7500, 14.0200, 59.3500, 14.3200, 0.260, True);   { R33 R0201 }
        AddBody('R34', 10.6200, 18.4900, 13.8200, 20.0900, 0.700, True);   { R34 742C083 }
        AddBody('R35', 9.3998, 21.1400, 10.3998, 21.6400, 0.400, True);   { R35 R0402 }
        AddBody('R5', 60.8000, 14.0200, 61.4000, 14.3200, 0.260, True);   { R5 R0201 }
        AddBody('R6', 56.6491, 21.9000, 57.2491, 22.2000, 0.260, True);   { R6 R0201 }
        AddBody('R7', 57.8490, 21.9000, 58.4490, 22.2000, 0.260, True);   { R7 R0201 }
        AddBody('R80', 29.0500, 18.8000, 30.0500, 19.3000, 0.400, True);   { R80 R0402 }
        AddBody('R81', 31.3500, 18.8000, 32.3500, 19.3000, 0.400, True);   { R81 R0402 }
        AddBody('R82', 33.6500, 18.8000, 34.6500, 19.3000, 0.400, True);   { R82 R0402 }
        AddBody('R83', 35.9500, 18.8000, 36.9500, 19.3000, 0.400, True);   { R83 R0402 }
        AddBody('R84', 30.3500, 20.5999, 31.3500, 21.0999, 0.400, True);   { R84 R0402 }
        AddBody('R85', 37.0500, 19.9999, 38.0500, 20.4999, 0.400, True);   { R85 R0402 }
        AddBody('R86', 30.3500, 21.7998, 31.3500, 22.2998, 0.400, True);   { R86 R0402 }
        AddBody('R90', 62.8501, 14.0200, 63.4501, 14.3200, 0.260, True);   { R90 R0201 }
        AddBody('R91', 58.7500, 16.8600, 59.3500, 17.1600, 0.260, True);   { R91 R0201 }
        AddBody('R92', 60.8000, 16.8600, 61.4000, 17.1600, 0.260, True);   { R92 R0201 }
        AddBody('R93', 62.8501, 16.8600, 63.4501, 17.1600, 0.260, True);   { R93 R0201 }
        AddBody('R94', 58.7500, 19.7000, 59.3500, 20.0000, 0.260, True);   { R94 R0201 }
        AddBody('R96', 18.9898, 19.8000, 19.5898, 20.1000, 0.260, True);   { R96 R0201 }
        AddBody('R97', 17.5500, 19.2000, 18.1500, 19.5000, 0.260, True);   { R97 R0201 }
        AddBody('R98', 18.7499, 19.2000, 19.3499, 19.5000, 0.260, True);   { R98 R0201 }
        AddBody('R99', 60.8000, 19.7000, 61.4000, 20.0000, 0.260, True);   { R99 R0201 }
        AddBody('U10', 21.9851, 18.7450, 24.9851, 21.7450, 1.100, True);   { U10 MSOP-8_3X3_P0.65 }
        AddBody('U3', 17.2400, 6.7700, 39.4600, 16.9300, 1.200, True);   { U3 TSOPII-54 }
        AddBody('U7', 7.4500, 17.3250, 10.3500, 18.9250, 1.450, True);   { U7 SOT23-5 }
        AddBody('U8', 6.6000, 7.1000, 11.6000, 11.1000, 0.800, True);   { U8 QFN28-UFD-4X5 }
        AddBody('X2', 35.5600, 22.8600, 60.9600, 25.4000, 2.700, True);   { X2[1-10] ZULU-DIP37 }
        AddBody('X2', 0.0000, 22.8600, 25.4000, 25.4000, 2.700, True);   { X2[11-20] ZULU-DIP37 }
        AddBody('X2', 35.5600, 0.0000, 60.9600, 2.5400, 2.700, True);   { X2[21-30] ZULU-DIP37 }
        AddBody('X2', 0.0000, 0.0000, 25.4000, 2.5400, 2.700, True);   { X2[31-40] ZULU-DIP37 }
    Finally
        PCBServer.PostProcess;
    End;
    Brd.ViewManager_FullUpdate;

    { ---- re-count ---- }
    Recount('BTN', 1);
    Recount('C100', 1);
    Recount('C101', 1);
    Recount('C102', 1);
    Recount('C103', 1);
    Recount('C104', 1);
    Recount('C105', 1);
    Recount('C106', 1);
    Recount('C107', 1);
    Recount('C108', 1);
    Recount('C109', 1);
    Recount('C11', 1);
    Recount('C110', 1);
    Recount('C111', 1);
    Recount('C112', 1);
    Recount('C113', 1);
    Recount('C114', 1);
    Recount('C115', 1);
    Recount('C116', 1);
    Recount('C117', 1);
    Recount('C118', 1);
    Recount('C119', 1);
    Recount('C12', 1);
    Recount('C120', 1);
    Recount('C121', 1);
    Recount('C122', 1);
    Recount('C123', 1);
    Recount('C124', 1);
    Recount('C13', 1);
    Recount('C133', 1);
    Recount('C134', 1);
    Recount('C135', 1);
    Recount('C136', 1);
    Recount('C137', 1);
    Recount('C138', 1);
    Recount('C139', 1);
    Recount('C140', 1);
    Recount('C141', 1);
    Recount('C142', 1);
    Recount('C143', 1);
    Recount('C144', 1);
    Recount('C145', 1);
    Recount('C146', 1);
    Recount('C147', 1);
    Recount('C148', 1);
    Recount('C149', 1);
    Recount('C150', 1);
    Recount('C151', 1);
    Recount('C152', 1);
    Recount('C153', 1);
    Recount('C154', 1);
    Recount('C155', 1);
    Recount('C156', 1);
    Recount('C157', 1);
    Recount('C158', 1);
    Recount('C159', 1);
    Recount('C160', 1);
    Recount('C161', 1);
    Recount('C163', 1);
    Recount('C164', 1);
    Recount('C165', 1);
    Recount('C166', 1);
    Recount('C167', 1);
    Recount('C168', 1);
    Recount('C3', 1);
    Recount('C36', 1);
    Recount('C37', 1);
    Recount('C38', 1);
    Recount('C4', 1);
    Recount('C40', 1);
    Recount('C41', 1);
    Recount('C5', 1);
    Recount('C6', 1);
    Recount('C7', 1);
    Recount('C78', 1);
    Recount('C8', 1);
    Recount('C80', 1);
    Recount('C82', 1);
    Recount('C84', 1);
    Recount('C85', 1);
    Recount('C86', 1);
    Recount('C87', 1);
    Recount('C88', 1);
    Recount('C89', 1);
    Recount('C9', 1);
    Recount('C90', 1);
    Recount('C91', 1);
    Recount('C92', 1);
    Recount('C93', 1);
    Recount('C94', 1);
    Recount('C95', 1);
    Recount('C96', 1);
    Recount('C97', 1);
    Recount('C98', 1);
    Recount('C99', 1);
    Recount('J1', 1);
    Recount('L1', 1);
    Recount('L2', 1);
    Recount('L3', 1);
    Recount('L4', 1);
    Recount('L5', 1);
    Recount('L6', 1);
    Recount('L7', 1);
    Recount('L8', 1);
    Recount('L9', 1);
    Recount('LD0', 1);
    Recount('LD1', 1);
    Recount('LD2', 1);
    Recount('LD3', 1);
    Recount('LD4', 1);
    Recount('Q1', 1);
    Recount('R1', 1);
    Recount('R10', 1);
    Recount('R101', 1);
    Recount('R102', 1);
    Recount('R103', 1);
    Recount('R107', 1);
    Recount('R108', 1);
    Recount('R11', 1);
    Recount('R113', 1);
    Recount('R114', 1);
    Recount('R115', 1);
    Recount('R116', 1);
    Recount('R117', 1);
    Recount('R118', 1);
    Recount('R119', 1);
    Recount('R12', 1);
    Recount('R120', 1);
    Recount('R121', 1);
    Recount('R122', 1);
    Recount('R123', 1);
    Recount('R124', 1);
    Recount('R125', 1);
    Recount('R126', 1);
    Recount('R127', 1);
    Recount('R128', 1);
    Recount('R129', 1);
    Recount('R13', 1);
    Recount('R130', 1);
    Recount('R131', 1);
    Recount('R132', 1);
    Recount('R133', 1);
    Recount('R134', 1);
    Recount('R14', 1);
    Recount('R15', 1);
    Recount('R16', 1);
    Recount('R17', 1);
    Recount('R18', 1);
    Recount('R19', 1);
    Recount('R2', 1);
    Recount('R20', 1);
    Recount('R21', 1);
    Recount('R22', 1);
    Recount('R23', 1);
    Recount('R24', 1);
    Recount('R25', 1);
    Recount('R26', 1);
    Recount('R27', 1);
    Recount('R28', 1);
    Recount('R29', 1);
    Recount('R30', 1);
    Recount('R31', 1);
    Recount('R32', 1);
    Recount('R33', 1);
    Recount('R34', 1);
    Recount('R35', 1);
    Recount('R4', 1);
    Recount('R5', 1);
    Recount('R6', 1);
    Recount('R7', 1);
    Recount('R80', 1);
    Recount('R81', 1);
    Recount('R82', 1);
    Recount('R83', 1);
    Recount('R84', 1);
    Recount('R85', 1);
    Recount('R86', 1);
    Recount('R90', 1);
    Recount('R91', 1);
    Recount('R92', 1);
    Recount('R93', 1);
    Recount('R94', 1);
    Recount('R96', 1);
    Recount('R97', 1);
    Recount('R98', 1);
    Recount('R99', 1);
    Recount('U1', 1);
    Recount('U10', 1);
    Recount('U2', 1);
    Recount('U3', 1);
    Recount('U4', 1);
    Recount('U7', 1);
    Recount('U8', 1);
    Recount('X1', 1);
    Recount('X2', 4);
    Recount('X3', 1);
    Recount('X4', 1);
    nAll := AllBodies;
    If nAll <> 200 Then Fail(IntToStr(nAll) + ' bodies on the board, expected 200');
    If NBad > 0 Then
        ShowMessage('DO NOT SAVE: ' + IntToStr(NBad) + ' check(s) failed after adding ' + IntToStr(NAdd) + ' bodies. Close the PcbDoc WITHOUT saving and reopen it.' + #13#10 + Bad)
    Else
        ShowMessage('SyncBodies OK: ' + IntToStr(NAdd) + ' bodies added, ' + IntToStr(nLib) + ' library bodies kept (' + Kept + '); 200 bodies on 197 parts (Mechanical 13). Save the board.');
    Skip.Free;
End;

