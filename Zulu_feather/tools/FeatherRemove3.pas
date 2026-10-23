{ FeatherRemove3.pas -- 2026-10-23. The ECO cannot swap X1, U3 and X2 onto their new footprints ("Cannot match
  pads with new footprint"). Remove them from zulu_feather.PcbDoc; the next Import Changes adds them back fresh. }

Procedure RemoveX1U3X2;
Var
    Brd : IPCB_Board;
    Doc : IDocument;
    C   : IPCB_Component;
    S   : String;
    I   : Integer;
    Refs : Array[0..2] Of String;
Begin
    Doc := GetWorkspace.DM_FocusedDocument;
    If (Doc = Nil) Or (Pos('\Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc', Doc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Zulu_feather\Zulu_feather.PrjPcb\zulu_feather.PcbDoc first.');
        Exit;
    End;
    Brd := PCBServer.GetCurrentPCBBoard;
    Refs[0] := 'X1'; Refs[1] := 'U3'; Refs[2] := 'X2';
    S := '';
    For I := 0 To 2 Do
    Begin
        C := Brd.GetPcbComponentByRefDes(Refs[I]);
        If C = Nil Then S := S + Refs[I] + ' not found' + #13#10
        Else
        Begin
            Brd.RemovePCBObject(C);
            S := S + Refs[I] + ' removed' + #13#10;
        End;
    End;
    Brd.ViewManager_FullUpdate;
    ShowMessage(S + 'Now Design > Import Changes again.');
End;
