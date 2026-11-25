{ NoPmodX3Tab.pas -- 2026-11-24, Rev 4 review fix: add the 3M 2908 lock-pin housing to X3's 3D bodies. The housing
  stands 1.0 mm proud of the 14.20 body edge at the G1 (mouth) corner (TS-2197-02 sheet 2: 15.20 vs 14.20), board
  x 2.50..3.50, y 5.70..10.10, 1.85 mm high, Mechanical 13, Top. Refuses unless X3 owns exactly one body. Save after. }
Procedure AddX3Tab;
Var
    Brd : IPCB_Board;
    Cm : IPCB_Component;
    It : IPCB_GroupIterator;
    O : IPCB_Primitive;
    B : IPCB_ComponentBody;
    Ct : IPCB_Contour;
    Md : IPCB_Model;
    n : Integer;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('\Rev_4\', Brd.FileName) = 0) Then Begin ShowMessage('Refusing: focus the Rev_4 board.'); Exit; End;
    Cm := Brd.GetPcbComponentByRefDes('X3');
    n := 0;
    It := Cm.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
    O := It.FirstPCBObject;
    While O <> Nil Do Begin n := n + 1; O := It.NextPCBObject; End;
    Cm.GroupIterator_Destroy(It);
    If n <> 1 Then Begin ShowMessage('Refusing: X3 owns ' + IntToStr(n) + ' bodies, expected 1.'); Exit; End;
    PCBServer.PreProcess;
    B := PCBServer.PCBObjectFactory(eComponentBodyObject, eNoDimension, eCreate_Default);
    Ct := PCBServer.PCBContourFactory;
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(2.50), Brd.YOrigin + MMsToCoord(5.70));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(3.50), Brd.YOrigin + MMsToCoord(5.70));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(3.50), Brd.YOrigin + MMsToCoord(10.10));
    Ct.AddPoint(Brd.XOrigin + MMsToCoord(2.50), Brd.YOrigin + MMsToCoord(10.10));
    B.SetOutlineContour(Ct);
    B.Layer := eMechanical13;
    B.BodyProjection := eBoardSide_Top;
    Md := B.ModelFactory_CreateExtruded(0, MMsToCoord(1.85), $808080);
    B.SetModel(Md);
    Cm.AddPCBObject(B);
    Brd.AddPCBObject(B);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('X3 lock-pin housing body added (2.50..3.50 x 5.70..10.10, 1.85 mm). Save the board.');
End;
