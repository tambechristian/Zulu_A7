{ NoPmodX3Body.pas -- 2026-11-24, no-PMOD Rev 4: the ECO footprint swap left X3 with no 3D body (the Hirose body went
  with the old footprint). Add (or replace, if one exists) with the 3M 2908-05WB-MG body: 14.20 x 14.00 x 1.85 mm (TS-2197-02 sheet 2),
  board box x 3.50..17.70, y 5.70..19.70 (= tools/body_check.py with body_mech.json X3), Mechanical 13, Top.
  Refuses unless the Rev_4 board is focused and X3 owns at most one body. Save after. }
Procedure AddX3Body;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    It : IPCB_GroupIterator;
    O, Old : IPCB_Primitive;
    B : IPCB_ComponentBody;
    Ct : IPCB_Contour;
    Md : IPCB_Model;
    n : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_4\', Brd.FileName) = 0) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus the Rev_4 Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    Cm := Brd.GetPcbComponentByRefDes('X3');
    If Cm = Nil Then Begin ShowMessage('Refusing: X3 not found.'); Exit; End;
    n := 0; Old := Nil;
    It := Cm.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
    O := It.FirstPCBObject;
    While O <> Nil Do Begin n := n + 1; Old := O; O := It.NextPCBObject; End;
    Cm.GroupIterator_Destroy(It);
    If n > 1 Then Begin ShowMessage('Refusing: X3 owns ' + IntToStr(n) + ' bodies, expected 0 or 1.'); Exit; End;
    PCBServer.PreProcess;
    If Old <> Nil Then
    Begin
        Cm.RemovePCBObject(Old);
        Brd.RemovePCBObject(Old);
    End;
    B := PCBServer.PCBObjectFactory(eComponentBodyObject, eNoDimension, eCreate_Default);
    Ct := PCBServer.PCBContourFactory;
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(3.50), Brd.YOrigin + MMsToCoord(5.70));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(17.70), Brd.YOrigin + MMsToCoord(5.70));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(17.70), Brd.YOrigin + MMsToCoord(19.70));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(3.50), Brd.YOrigin + MMsToCoord(19.70));
    B.SetOutlineContour(Ct);
    B.Layer := eMechanical13;
    B.BodyProjection := eBoardSide_Top;
    Md := B.ModelFactory_CreateExtruded(0, MMsToCoord(1.85), $808080);
    B.SetModel(Md);
    Cm.AddPCBObject(B);
    Brd.AddPCBObject(B);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('X3 body replaced: 14.20 x 14.00 x 1.85 mm (3M 2908-05WB-MG). Save the board.');
End;
