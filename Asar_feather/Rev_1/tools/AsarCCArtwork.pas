{ AsarCCArtwork.pas -- 2026-11-19 (docs/body_fixes.md). The Creative Commons artwork U$2..U$5 sits off the board, 4.0 mm
  apart, so with Component Clearance ticked its bounding boxes overlap (3 DRC hits). Respaces U$3, U$4, U$5 east to the
  no-PMOD board's spacing (5.836 / 4.556 / 5.837 mm centre to centre, its DRC is clean with the same artwork): U$3 +1.8360,
  U$4 +2.3920, U$5 +4.2290 mm. Nothing on the board moves. Refuses unless each part is at its 2026-11-19 place. }
Procedure MoveArt(Brd : IPCB_Board; Ref : String; X0, DX : Double; Var Bad : String);
Var
    Cm : IPCB_Component;
Begin
    Cm := Brd.GetPcbComponentByRefDes(Ref);
    If (Cm = Nil) Or (Abs(CoordToMils(Cm.X - Brd.XOrigin) - X0) > 0.05) Or (Abs(CoordToMils(Cm.Y - Brd.YOrigin) + 157.4803) > 0.05) Then
    Begin
        Bad := Bad + ' ' + Ref;
        Exit;
    End;
End;

Procedure Shift(Brd : IPCB_Board; Ref : String; DX : Double);
Var
    Cm : IPCB_Component;
Begin
    Cm := Brd.GetPcbComponentByRefDes(Ref);
    Cm.BeginModify;
    Cm.X := Cm.X + MMsToCoord(DX);
    Cm.EndModify;
End;

Procedure SpaceArtwork;
Var
    Brd : IPCB_Board;
    Bad : String;
Begin
    Brd := PCBServer.GetCurrentPCBBoard;
    If (Brd = Nil) Or (Pos('asar_feather.PcbDoc', Brd.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus asar_feather.PcbDoc first.');
        Exit;
    End;
    Bad := '';
    MoveArt(Brd, 'U$3', 2401.5748, 0, Bad);
    MoveArt(Brd, 'U$4', 2559.0551, 0, Bad);
    MoveArt(Brd, 'U$5', 2716.5354, 0, Bad);
    If Bad <> '' Then
    Begin
        ShowMessage('Refusing: not at their 2026-11-19 places:' + Bad);
        Exit;
    End;
    PCBServer.PreProcess;
    Shift(Brd, 'U$3', 1.8360);
    Shift(Brd, 'U$4', 2.3920);
    Shift(Brd, 'U$5', 4.2290);
    PCBServer.PostProcess;
    Brd.ViewManager_FullUpdate;
    ShowMessage('U$3, U$4, U$5 respaced (off the board). Save, then re-run the DRC.');
End;
