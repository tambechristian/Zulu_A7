{ NoPmodBodyProbe.pas -- 2026-11-19. Probe of the 3D-body API before bodies go on every part: adds one extruded body
  to U4 (Top, SOIC-8 208 mil, 5.28 x 5.28 x 2.16 mm) and one to U10 (Bottom, MSOP-8, 3.0 x 3.0 x 1.1 mm) on
  Mechanical 13. Run ProbeBodies with Zulu_a7_no_pmod.PcbDoc focused, then File > Save Copy As to a scratch file and
  read it back; do NOT save the board itself. }
Procedure AddBody(Brd : IPCB_Board; Ref : String; X0, Y0, X1, Y1, H : Double; Bot : Boolean);
Var
    Cm : IPCB_Component;
    B  : IPCB_ComponentBody;
    Ct : IPCB_Contour;
    Md : IPCB_Model;
Begin
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
End;

Procedure ProbeBodies;
Var
    Brd : IPCB_Board;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('Zulu_a7_no_pmod.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_a7_no_pmod.PcbDoc first.');
        Exit;
    End;
    PCBServer.PreProcess;
    AddBody(Brd, 'U4', 44.86, 16.76, 50.14, 22.04, 2.16, False);
    AddBody(Brd, 'U10', 21.985, 18.745, 24.985, 21.745, 1.10, True);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('Probe: 2 bodies added (U4 top, U10 bottom). Save Copy As to a scratch file; do not save the board.');
End;
