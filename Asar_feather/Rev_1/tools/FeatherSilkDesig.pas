{ FeatherSilkDesig.pas -- 2026-11-07. Two designator edits after the user's manual move of U1's designator:
  - U1: 0.05 mm south (anchor y 5.700 -> 5.650 board-relative) to clear Silk To Solder Mask (0.254) at balls A18/A19,
    which DRC measured at 0.235 mm.
  - X1: 1.0 mm -> 0.8 mm high (PCBWay's legend minimum, as the pin labels), stroke stays 0.15 mm, autoposition set to manual and
    the anchor moved (+0.1333, +0.1000) mm so the text keeps its centre ("X1" is 8 grid units wide, unit = height / 6).
  Refuses unless U1's anchor is at (19.292, 5.700) and X1's text is 1.0 mm high at (3.531, 17.018), so it runs once.
  The boxes Altium computes afterwards go to the scratch log named below. Run SilkDesig with asar_feather.PcbDoc focused. }

Function CloseTo(A, B : Integer) : Boolean;
Begin
    Result := Abs(A - B) < MMsToCoord(0.002);
End;

Procedure SilkDesig;
Var
    Doc : IDocument;
    Brd : IPCB_Board;
    CU1 : IPCB_Component;
    CX1 : IPCB_Component;
    TU1 : IPCB_Text;
    TX1 : IPCB_Text;
    B   : TCoordRect;
    Log : TStringList;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Asar_feather\Asar_feather.PrjPcb\asar_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    CU1 := Brd.GetPcbComponentByRefDes('U1');
    CX1 := Brd.GetPcbComponentByRefDes('X1');
    If (CU1 = Nil) Or (CX1 = Nil) Then
    Begin
        ShowMessage('Refusing: U1 or X1 not found.');
        Exit;
    End;
    TU1 := CU1.Name;
    TX1 := CX1.Name;
    If Not (CloseTo(TU1.XLocation - Brd.XOrigin, MMsToCoord(19.2918)) And CloseTo(TU1.YLocation - Brd.YOrigin, MMsToCoord(5.7001))
            And CloseTo(TX1.XLocation - Brd.XOrigin, MMsToCoord(3.531)) And CloseTo(TX1.YLocation - Brd.YOrigin, MMsToCoord(17.018))
            And CloseTo(TX1.Size, MMsToCoord(1.0))) Then
    Begin
        ShowMessage('Refusing: U1 / X1 designators are not where this script expects them; nothing changed.');
        Exit;
    End;
    PCBServer.PreProcess;
    CX1.BeginModify;
    CX1.ChangeNameAutoposition := eAutoPos_Manual;
    CX1.EndModify;
    TX1.BeginModify;
    TX1.Size := MMsToCoord(0.8);
    TX1.Width := MMsToCoord(0.15);
    TX1.XLocation := TX1.XLocation + MMsToCoord(0.1333);
    TX1.YLocation := TX1.YLocation + MMsToCoord(0.1);
    TX1.EndModify;
    TU1.BeginModify;
    TU1.YLocation := TU1.YLocation - MMsToCoord(0.05);
    TU1.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    Log := TStringList.Create;
    B := TU1.BoundingRectangle;
    Log.Add('U1 anchor ' + FloatToStr(CoordToMMs(TU1.XLocation - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(TU1.YLocation - Brd.YOrigin)) +
            ' box ' + FloatToStr(CoordToMMs(B.Left - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(B.Right - Brd.XOrigin)) + ' ' +
            FloatToStr(CoordToMMs(B.Bottom - Brd.YOrigin)) + ' ' + FloatToStr(CoordToMMs(B.Top - Brd.YOrigin)));
    B := TX1.BoundingRectangle;
    Log.Add('X1 anchor ' + FloatToStr(CoordToMMs(TX1.XLocation - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(TX1.YLocation - Brd.YOrigin)) +
            ' size ' + FloatToStr(CoordToMMs(TX1.Size)) + ' box ' + FloatToStr(CoordToMMs(B.Left - Brd.XOrigin)) + ' ' +
            FloatToStr(CoordToMMs(B.Right - Brd.XOrigin)) + ' ' + FloatToStr(CoordToMMs(B.Bottom - Brd.YOrigin)) + ' ' +
            FloatToStr(CoordToMMs(B.Top - Brd.YOrigin)));
    Log.SaveToFile('C:\Users\tambe\AppData\Local\Temp\claude\74c8e1fc98776908\ac1fa567-8c06-4af0-9b2d-65df9ede410f\scratchpad\u1silk\designators.log');
    Log.Free;
    ShowMessage('Designators: U1 moved 0.05 mm south, X1 now 0.8 mm. Run DRC, then save.');
End;
