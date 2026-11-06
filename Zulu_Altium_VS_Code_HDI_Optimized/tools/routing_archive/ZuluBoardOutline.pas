{..............................................................................}
{  ZuluBoardOutline.pas            DelphiScript for Altium Designer            }
{                                                                              }
{  Sets the PCB board shape to an exact rectangle:                             }
{      lower-left  (0.00 mm , 0.00 mm)                                         }
{      upper-right (69.85 mm , 25.40 mm)      = 2.750 x 1.000 inch             }
{                                                                              }
{  Run with  File >> Run Script...  >> Browse to this file >> pick a procedure }
{                                                                              }
{  Parameterless procedures appear in the "Select Item To Run" dialog:         }
{     SetBoardOutlineViaTracks   - primary  (tracks + Define-from-selected)    }
{     SetBoardOutlineDirect      - alternate (writes BoardOutline segments)    }
{     ReportBoardOutline         - verification, prints vertices in mm         }
{..............................................................................}

Const
    BRD_X0 = 0.0;
    BRD_Y0 = 0.0;
    BRD_X1 = 69.85;
    BRD_Y1 = 25.4;

{ helper - has parameters, so it stays hidden from the Run Script list }
Procedure MakeEdge(Board : IPCB_Board; ALayer : TLayer; AWidth : TCoord;
                   ax1, ay1, ax2, ay2 : TCoord);
Var
    Track : IPCB_Track;
Begin
    Track := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    Track.X1    := ax1;
    Track.Y1    := ay1;
    Track.X2    := ax2;
    Track.Y2    := ay2;
    Track.Layer := ALayer;
    Track.Width := AWidth;
    Board.AddPCBObject(Track);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_BroadCast,
                                  PCBM_BoardRegisteration, Track.I_ObjectAddress);
    Track.Selected := True;
End;

{ PRIMARY: place four exactly-coincident tracks on Mechanical 1, then run the
  same command the Design menu runs for "Define Board Shape from Selected Objects" }
Procedure SetBoardOutlineViaTracks;
Var
    Board : IPCB_Board;
    x0, y0, x1, y1, w : TCoord;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    x0 := MMsToCoord(BRD_X0);
    y0 := MMsToCoord(BRD_Y0);
    x1 := MMsToCoord(BRD_X1);
    y1 := MMsToCoord(BRD_Y1);
    w  := MMsToCoord(0.1);

    Board.CurrentLayer := eMechanical1;

    { make sure nothing else is selected }
    ResetParameters;
    AddStringParameter('Scope', 'All');
    RunProcess('PCB:DeSelect');

    PCBServer.PreProcess;
    Try
        MakeEdge(Board, eMechanical1, w, x0, y0, x1, y0);   { bottom }
        MakeEdge(Board, eMechanical1, w, x1, y0, x1, y1);   { right  }
        MakeEdge(Board, eMechanical1, w, x1, y1, x0, y1);   { top    }
        MakeEdge(Board, eMechanical1, w, x0, y1, x0, y0);   { left   }
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;

    { Design >> Board Shape >> Define Board Shape from Selected Objects }
    ResetParameters;
    AddStringParameter('Mode', 'BOARDOUTLINE_FROM_SEL_PRIMS');
    RunProcess('PCB:PlaceBoardOutline');

    ShowMessage('Outline tracks placed on Mechanical 1 and board shape redefined.' + #13#10 +
                'Now run ReportBoardOutline to verify the numbers.');
End;

{ ALTERNATE: write the board outline contour directly }
Procedure SetBoardOutlineDirect;
Var
    Board : IPCB_Board;
    BO    : IPCB_BoardOutline;
    x0, y0, x1, y1 : TCoord;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    x0 := MMsToCoord(BRD_X0);
    y0 := MMsToCoord(BRD_Y0);
    x1 := MMsToCoord(BRD_X1);
    y1 := MMsToCoord(BRD_Y1);

    BO := Board.BoardOutline;

    PCBServer.PreProcess;
    Try
        BO.BeginModify;
        BO.PointCount := 4;

        BO.Segments[0].Kind := ePolySegmentLine;
        BO.Segments[0].vx   := x0;
        BO.Segments[0].vy   := y0;

        BO.Segments[1].Kind := ePolySegmentLine;
        BO.Segments[1].vx   := x1;
        BO.Segments[1].vy   := y0;

        BO.Segments[2].Kind := ePolySegmentLine;
        BO.Segments[2].vx   := x1;
        BO.Segments[2].vy   := y1;

        BO.Segments[3].Kind := ePolySegmentLine;
        BO.Segments[3].vx   := x0;
        BO.Segments[3].vy   := y1;

        BO.EndModify;
        BO.Invalidate;
        BO.Validate;          { Rebuild is called implicitly by Validate }
    Finally
        PCBServer.PostProcess;
    End;

    Board.ViewManager_FullUpdate;
    ShowMessage('Board outline rewritten. Run ReportBoardOutline to verify.');
End;

{ VERIFICATION: print every board-outline vertex in millimetres }
Procedure ReportBoardOutline;
Var
    Board : IPCB_Board;
    i     : Integer;
    s     : String;
Begin
    Board := PCBServer.GetCurrentPCBBoard;
    If Board = Nil Then
    Begin
        ShowMessage('No PCB document is focused.');
        Exit;
    End;

    s := 'PointCount = ' + IntToStr(Board.BoardOutline.PointCount) + #13#10;
    For i := 0 To Board.BoardOutline.PointCount - 1 Do
        s := s + IntToStr(i) +
             ':  X = ' + FloatToStr(CoordToMMs(Board.BoardOutline.Segments[i].vx)) +
             ' mm   Y = ' + FloatToStr(CoordToMMs(Board.BoardOutline.Segments[i].vy)) +
             ' mm' + #13#10;

    s := s + #13#10 +
         'Relative origin: X = ' + FloatToStr(CoordToMMs(Board.XOrigin)) +
         ' mm  Y = ' + FloatToStr(CoordToMMs(Board.YOrigin)) + ' mm';

    ShowMessage(s);
End;

End.
