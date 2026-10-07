procedure AddZuluTitle;
var
    WS      : IWorkspace;
    Doc     : IDocument;
    Brd     : IPCB_Board;
    It      : IPCB_BoardIterator;
    Existing: IPCB_Text;
    Title   : IPCB_Text;
begin
    WS := GetWorkspace;
    if WS = nil then
    begin
        ShowMessage('No active Altium workspace.');
        Exit;
    end;
    Doc := WS.DM_FocusedDocument;
    if Doc = nil then
    begin
        ShowMessage('No focused document.');
        Exit;
    end;
    if Pos('zulu_a7_hdi_optimized.PcbDoc', Doc.DM_FullPath) = 0 then
    begin
        ShowMessage(
            'Refusing to modify the focused document:' + #13#10 +
            Doc.DM_FullPath);
        Exit;
    end;

    Brd := PCBServer.GetCurrentPCBBoard;
    if Brd = nil then
    begin
        ShowMessage('No active PCB document.');
        Exit;
    end;

    It := Brd.BoardIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eTextObject));
    It.AddFilter_LayerSet(MkSet(eTopOverlay));
    It.AddFilter_Method(eProcessAll);
    Existing := It.FirstPCBObject;
    while Existing <> nil do
    begin
        if Existing.Text = 'ZULU A7' then
        begin
            Brd.BoardIterator_Destroy(It);
            ShowMessage('ZULU A7 already exists on Top Overlay; no change made.');
            Exit;
        end;
        Existing := It.NextPCBObject;
    end;
    Brd.BoardIterator_Destroy(It);

    PCBServer.PreProcess;
    Title := PCBServer.PCBObjectFactory(
        eTextObject, eNoDimension, eCreate_Default);
    PCBServer.SendMessageToRobots(
        Title.I_ObjectAddress, c_Broadcast, PCBM_BeginModify, c_NoEventData);

    Title.XLocation := MMsToCoord(6.0);
    Title.YLocation := MMsToCoord(20.0);
    Title.Layer := eTopOverlay;
    Title.Text := 'ZULU A7';
    Title.Size := MMsToCoord(2.0);
    Title.Width := MMsToCoord(0.25);
    Title.Rotation := 0;
    Title.UseTTFonts := False;
    Brd.AddPCBObject(Title);

    PCBServer.SendMessageToRobots(
        Title.I_ObjectAddress, c_Broadcast, PCBM_EndModify, c_NoEventData);
    PCBServer.SendMessageToRobots(
        Brd.I_ObjectAddress, c_Broadcast, PCBM_BoardRegisteration,
        Title.I_ObjectAddress);
    PCBServer.PostProcess;

    Brd.ViewManager_FullUpdate;
    ShowMessage(
        'Added ZULU A7 to Top Overlay at X=6.0 mm, Y=20.0 mm.');
end;
