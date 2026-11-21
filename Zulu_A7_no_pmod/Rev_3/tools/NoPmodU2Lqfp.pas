{ Restore the Rev_2 schematic U2 design-item ID to the retained FT2232HL LQFP-64.
  The symbol and PCB already use this part; this prevents future ECOs from proposing the rejected QFN swap. }

Function U2LqfpDoc : ISch_Document;
Var
    WDoc : IDocument;
Begin
    Result := Nil;
    WDoc := GetWorkspace.DM_FocusedDocument;
    If (WDoc = Nil) Or
       (Pos('\Zulu_A7_no_pmod\Rev_3\Imported zulu_a7.PrjPcb\zulu_a7_4.SchDoc', WDoc.DM_FullPath) = 0) Then
    Begin
        ShowMessage('Refusing: focus Rev_2 zulu_a7_4.SchDoc first.');
        Exit;
    End;
    Result := SchServer.GetCurrentSchDocument;
End;

Function U2LqfpFind(Doc : ISch_Document) : ISch_Component;
Var
    It : ISch_Iterator;
    C : ISch_Component;
Begin
    Result := Nil;
    It := Doc.SchIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eSchComponent));
    C := It.FirstSchObject;
    While C <> Nil Do
    Begin
        If C.Designator.Text = 'U2' Then Result := C;
        C := It.NextSchObject;
    End;
    Doc.SchIterator_Destroy(It);
End;

Procedure FixU2LqfpModel;
Var
    Doc : ISch_Document;
    C : ISch_Component;
    OldId : String;
Begin
    Doc := U2LqfpDoc;
    If Doc = Nil Then Exit;
    C := U2LqfpFind(Doc);
    If C = Nil Then
    Begin
        ShowMessage('Refusing: U2 is missing from zulu_a7_4.SchDoc.');
        Exit;
    End;
    If C.LibReference <> 'FT2232HL-LQFP64' Then
    Begin
        ShowMessage('Refusing: U2 library reference is "' + C.LibReference + '", not FT2232HL-LQFP64.');
        Exit;
    End;
    OldId := C.DesignItemId;
    If OldId = 'FT2232HL-LQFP64' Then
    Begin
        ShowMessage('U2 already has design-item ID FT2232HL-LQFP64; nothing changed.');
        Exit;
    End;
    If OldId <> 'FT2232HQ-QFN64' Then
    Begin
        ShowMessage('Refusing: unexpected U2 design-item ID "' + OldId + '".');
        Exit;
    End;

    SchServer.ProcessControl.PreProcess(Doc, '');
    C.DesignItemId := 'FT2232HL-LQFP64';
    SchServer.ProcessControl.PostProcess(Doc, '');
    Doc.GraphicallyInvalidate;
    ShowMessage('U2 schematic design-item ID restored: FT2232HQ-QFN64 -> FT2232HL-LQFP64. Save only zulu_a7_4.SchDoc.');
End;
