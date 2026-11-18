{ AsarX4Fix.pas -- GENERATED 2026-11-16 by the X4 conversion (tools/route/x4conv/fix_plan.json). DRC after FeatherCopper_X4Conv
  found 4 items: two dead stub chains plan_prune kept (fat overlapping segments anchor each other) and two silk items.
  AsarX4Fix: removes the 14 dead tracks (11 VU Bottom from the old top-edge bridge via, 3 EE-CLK Top from the old U10),
  all-or-nothing; moves the X1 designator from (3.664, 17.118) to (2.25, 17.35) (it hit U10-1's mask); moves U10's lone
  Top Overlay tick from (6.6, 19.15-19.25), 0.025 mm from X4-MP1's mask, to a pin-1 mark at (4.15, 17.35-17.55).
  Run with asar_feather.PcbDoc focused, then Repour All, DRC, save. }

Procedure AsarX4Fix;
Var
    Brd : IPCB_Board;
    It : IPCB_BoardIterator;
    GI : IPCB_GroupIterator;
    K : IPCB_Track;
    O : IPCB_Primitive;
    Kill, Ticks : TInterfaceList;
    CX1, CU10 : IPCB_Component;
    TX1 : IPCB_Text;
    nm : String;
    x, y, x2, y2, tw : Double;
    i : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If Brd = Nil Then Begin ShowMessage('Refusing: no PCB is focused.'); Exit; End;
    If Pos('\Rev_1\Asar_feather.PrjPcb\asar_feather.PcbDoc', Brd.FileName) = 0 Then Begin ShowMessage('Refusing: focus Rev_1 asar_feather.PcbDoc.'); Exit; End;
    CX1 := Brd.GetPcbComponentByRefDes('X1');
    CU10 := Brd.GetPcbComponentByRefDes('U10');
    If (CX1 = Nil) Or (CU10 = Nil) Then Begin ShowMessage('Refusing: X1 or U10 not found.'); Exit; End;
    TX1 := CX1.Name;
    If (Abs(CoordToMMs(TX1.XLocation - Brd.XOrigin) - 3.664) > 0.003) Or (Abs(CoordToMMs(TX1.YLocation - Brd.YOrigin) - 17.118) > 0.003) Then
    Begin ShowMessage('Refusing: the X1 designator is not at (3.664, 17.118); nothing changed.'); Exit; End;
    Ticks := TInterfaceList.Create;
    GI := CU10.GroupIterator_Create;
    GI.AddFilter_ObjectSet(MkSet(eTrackObject));
    O := GI.FirstPCBObject;
    While O <> Nil Do
    Begin
        K := O;
        If K.Layer = eTopOverlay Then Ticks.Add(K);
        O := GI.NextPCBObject;
    End;
    CU10.GroupIterator_Destroy(GI);
    If Ticks.Count <> 1 Then Begin ShowMessage('Refusing: U10 has ' + IntToStr(Ticks.Count) + ' Top Overlay tracks, expected 1.'); Ticks.Free; Exit; End;
    K := Ticks.Items[0];
    If (Abs(CoordToMMs(K.X1 - Brd.XOrigin) - 6.6) > 0.003) Or (Abs(CoordToMMs(K.X2 - Brd.XOrigin) - 6.6) > 0.003) Then
    Begin ShowMessage('Refusing: U10 tick is not at x 6.6; nothing changed.'); Ticks.Free; Exit; End;
    Kill := TInterfaceList.Create;
    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTrackObject));
    It.AddFilter_LayerSet(AllLayers);
    It.AddFilter_Method(eProcessAll);
    O := It.FirstPCBObject;
    While O <> Nil Do
    Begin
        K := O;
        nm := ''; If K.Net <> Nil Then nm := K.Net.Name;
        x := CoordToMMs(K.X1 - Brd.XOrigin); y := CoordToMMs(K.Y1 - Brd.YOrigin);
        x2 := CoordToMMs(K.X2 - Brd.XOrigin); y2 := CoordToMMs(K.Y2 - Brd.YOrigin);
        tw := CoordToMMs(K.Width);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 14.7750) < 0.002) And (Abs(y - 21.6500) < 0.002) And (Abs(x2 - 14.7750) < 0.002) And (Abs(y2 - 21.8250) < 0.002)) Or ((Abs(x - 14.7750) < 0.002) And (Abs(y - 21.8250) < 0.002) And (Abs(x2 - 14.7750) < 0.002) And (Abs(y2 - 21.6500) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 14.7750) < 0.002) And (Abs(y - 21.6500) < 0.002) And (Abs(x2 - 16.3250) < 0.002) And (Abs(y2 - 20.1000) < 0.002)) Or ((Abs(x - 16.3250) < 0.002) And (Abs(y - 20.1000) < 0.002) And (Abs(x2 - 14.7750) < 0.002) And (Abs(y2 - 21.6500) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 16.3250) < 0.002) And (Abs(y - 20.1000) < 0.002) And (Abs(x2 - 17.0000) < 0.002) And (Abs(y2 - 20.1000) < 0.002)) Or ((Abs(x - 17.0000) < 0.002) And (Abs(y - 20.1000) < 0.002) And (Abs(x2 - 16.3250) < 0.002) And (Abs(y2 - 20.1000) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.0000) < 0.002) And (Abs(y - 20.1000) < 0.002) And (Abs(x2 - 17.0500) < 0.002) And (Abs(y2 - 20.0750) < 0.002)) Or ((Abs(x - 17.0500) < 0.002) And (Abs(y - 20.0750) < 0.002) And (Abs(x2 - 17.0000) < 0.002) And (Abs(y2 - 20.1000) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.0500) < 0.002) And (Abs(y - 20.0750) < 0.002) And (Abs(x2 - 17.0750) < 0.002) And (Abs(y2 - 20.0500) < 0.002)) Or ((Abs(x - 17.0750) < 0.002) And (Abs(y - 20.0500) < 0.002) And (Abs(x2 - 17.0500) < 0.002) And (Abs(y2 - 20.0750) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.0750) < 0.002) And (Abs(y - 20.0500) < 0.002) And (Abs(x2 - 17.1000) < 0.002) And (Abs(y2 - 20.0500) < 0.002)) Or ((Abs(x - 17.1000) < 0.002) And (Abs(y - 20.0500) < 0.002) And (Abs(x2 - 17.0750) < 0.002) And (Abs(y2 - 20.0500) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.1000) < 0.002) And (Abs(y - 20.0500) < 0.002) And (Abs(x2 - 17.2000) < 0.002) And (Abs(y2 - 19.9500) < 0.002)) Or ((Abs(x - 17.2000) < 0.002) And (Abs(y - 19.9500) < 0.002) And (Abs(x2 - 17.1000) < 0.002) And (Abs(y2 - 20.0500) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.2000) < 0.002) And (Abs(y - 19.9250) < 0.002) And (Abs(x2 - 17.2000) < 0.002) And (Abs(y2 - 19.9500) < 0.002)) Or ((Abs(x - 17.2000) < 0.002) And (Abs(y - 19.9500) < 0.002) And (Abs(x2 - 17.2000) < 0.002) And (Abs(y2 - 19.9250) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.2000) < 0.002) And (Abs(y - 19.9250) < 0.002) And (Abs(x2 - 17.2250) < 0.002) And (Abs(y2 - 19.9000) < 0.002)) Or ((Abs(x - 17.2250) < 0.002) And (Abs(y - 19.9000) < 0.002) And (Abs(x2 - 17.2000) < 0.002) And (Abs(y2 - 19.9250) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.2250) < 0.002) And (Abs(y - 19.9000) < 0.002) And (Abs(x2 - 17.2500) < 0.002) And (Abs(y2 - 19.8500) < 0.002)) Or ((Abs(x - 17.2500) < 0.002) And (Abs(y - 19.8500) < 0.002) And (Abs(x2 - 17.2250) < 0.002) And (Abs(y2 - 19.9000) < 0.002))) Then Kill.Add(K);
        If (nm = 'VU') And (K.Layer = eBottomLayer) And (Abs(tw - 0.4000) < 0.002) And (((Abs(x - 17.2500) < 0.002) And (Abs(y - 16.4250) < 0.002) And (Abs(x2 - 17.2500) < 0.002) And (Abs(y2 - 19.8500) < 0.002)) Or ((Abs(x - 17.2500) < 0.002) And (Abs(y - 19.8500) < 0.002) And (Abs(x2 - 17.2500) < 0.002) And (Abs(y2 - 16.4250) < 0.002))) Then Kill.Add(K);
        If (nm = 'EE-CLK') And (K.Layer = eTopLayer) And (Abs(tw - 0.0762) < 0.002) And (((Abs(x - 11.0500) < 0.002) And (Abs(y - 12.1000) < 0.002) And (Abs(x2 - 11.1750) < 0.002) And (Abs(y2 - 12.4000) < 0.002)) Or ((Abs(x - 11.1750) < 0.002) And (Abs(y - 12.4000) < 0.002) And (Abs(x2 - 11.0500) < 0.002) And (Abs(y2 - 12.1000) < 0.002))) Then Kill.Add(K);
        If (nm = 'EE-CLK') And (K.Layer = eTopLayer) And (Abs(tw - 0.0762) < 0.002) And (((Abs(x - 11.1750) < 0.002) And (Abs(y - 12.4000) < 0.002) And (Abs(x2 - 11.7750) < 0.002) And (Abs(y2 - 13.0000) < 0.002)) Or ((Abs(x - 11.7750) < 0.002) And (Abs(y - 13.0000) < 0.002) And (Abs(x2 - 11.1750) < 0.002) And (Abs(y2 - 12.4000) < 0.002))) Then Kill.Add(K);
        If (nm = 'EE-CLK') And (K.Layer = eTopLayer) And (Abs(tw - 0.0762) < 0.002) And (((Abs(x - 11.7750) < 0.002) And (Abs(y - 13.0000) < 0.002) And (Abs(x2 - 11.7750) < 0.002) And (Abs(y2 - 13.0500) < 0.002)) Or ((Abs(x - 11.7750) < 0.002) And (Abs(y - 13.0500) < 0.002) And (Abs(x2 - 11.7750) < 0.002) And (Abs(y2 - 13.0000) < 0.002))) Then Kill.Add(K);
        O := It.NextPCBObject;
    End;
    Brd.BoardIterator_Destroy(It);
    If Kill.Count <> 14 Then
    Begin ShowMessage('Refusing: found ' + IntToStr(Kill.Count) + ' of the 14 dead tracks; nothing changed.'); Kill.Free; Ticks.Free; Exit; End;
    PCBServer.PreProcess;
    For i := 0 To Kill.Count - 1 Do Brd.RemovePCBObject(Kill.Items[i]);
    TX1.BeginModify;
    TX1.XLocation := Brd.XOrigin + MMsToCoord(2.25);
    TX1.YLocation := Brd.YOrigin + MMsToCoord(17.35);
    TX1.EndModify;
    K := Ticks.Items[0];
    K.BeginModify;
    K.X1 := Brd.XOrigin + MMsToCoord(4.15); K.Y1 := Brd.YOrigin + MMsToCoord(17.35);
    K.X2 := Brd.XOrigin + MMsToCoord(4.15); K.Y2 := Brd.YOrigin + MMsToCoord(17.55);
    K.EndModify;
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Removed ' + IntToStr(Kill.Count) + ' dead tracks (expect 14); X1 designator now at ' + FloatToStr(CoordToMMs(TX1.XLocation - Brd.XOrigin)) + ', ' + FloatToStr(CoordToMMs(TX1.YLocation - Brd.YOrigin)) + '; U10 tick at x ' + FloatToStr(CoordToMMs(K.X1 - Brd.XOrigin)) + '. Repour, DRC, save.');
    Kill.Free; Ticks.Free;
End;
