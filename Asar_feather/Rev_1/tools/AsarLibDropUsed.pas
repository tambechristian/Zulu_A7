{ AsarLibDropUsed.pas -- 2026-11-19 (docs/body_fixes.md). Library rebuild helper, run on a SCRATCH COPY of the old
  asar_feather.PcbLib (the file name must contain 'asar_old_lib'): removes the 32 footprints the board uses, so the
  21 unused ones left (FT2232HL-LQFP64, USB-C-HRO, TSOPII-54, ...) can be copied into the library that
  Design > Make PCB Library builds from the board (those 32 carry the board's 3D bodies). Never run it on the project
  library itself.
  DropVariants runs on the library Make PCB Library built (file name must contain 'asar_bodies_src'): it removes the
  seven '_2' variants (C0201_2, C0402_2, C0603_2, C0805_2, IND2520_2, PTS810_2, R0201_2) that Make PCB Library writes
  when two board instances differ by a 0.0001 mm origin offset; no schematic part names them. }
Procedure DropVariants;
Var
    Lib  : IPCB_Library;
    It   : IPCB_LibraryIterator;
    Fp   : IPCB_LibComponent;
    Kill : TInterfaceList;
    i    : Integer;
Begin
    Lib := PCBServer.GetCurrentPCBLibrary;
    If (Lib = Nil) Or (Pos('asar_bodies_src', Lib.Board.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus the scratch library asar_bodies_src.PcbLib first.');
        Exit;
    End;
    Kill := TInterfaceList.Create;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If (Fp.Name = 'C0201_2') Or (Fp.Name = 'C0402_2') Or (Fp.Name = 'C0603_2') Or (Fp.Name = 'C0805_2') Or
           (Fp.Name = 'IND2520_2') Or (Fp.Name = 'PTS810_2') Or (Fp.Name = 'R0201_2') Then Kill.Add(Fp);
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Kill.Count <> 7 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(Kill.Count) + ' of the 7 variants; nothing removed.');
        Kill.Free;
        Exit;
    End;
    For i := 0 To Kill.Count - 1 Do Lib.RemoveComponent(Kill.Items[i]);
    Kill.Free;
    Lib.RefreshView;
    ShowMessage('Removed the 7 _2 variants. Save the library.');
End;

Procedure DropUsed;
Var
    Lib  : IPCB_Library;
    It   : IPCB_LibraryIterator;
    Fp   : IPCB_LibComponent;
    Kill : TInterfaceList;
    Used : TStringList;
    i    : Integer;
Begin
    Lib := PCBServer.GetCurrentPCBLibrary;
    If (Lib = Nil) Or (Pos('asar_old_lib', Lib.Board.FileName) = 0) Then
    Begin
        ShowMessage('Refusing: focus the scratch copy asar_old_lib.PcbLib first.');
        Exit;
    End;
    Used := TStringList.Create;
    Used.CommaText := '32X25,742C043,742C083,742C163,AMPHENOL-10118193-0001LF,C0201,C0402,C0603,C0805,CC_BY,CC_CC,' +
        'CC_COPYRIGHT,CC_SA,DM3D-SF,EVERLIGHT-19-337,FBGA-54-8X8-P0.8,FEATHER-28,IND0603,IND2520,JST-S2B-PH-SM4-TB,' +
        'JST-SM04B-SRSS-TB,LED0603,PTS810,QFN-64-9X9-P0.5-EP4.35,QFN28-UFD-4X5,R0201,R0402,SOT23-5,TDFN-8-2X3-P0.5,' +
        'TP-1X03-SMD,WSON-8-6X5-P1.27,XC7A35T-CPG236';
    Kill := TInterfaceList.Create;
    It := Lib.LibraryIterator_Create;
    It.SetState_FilterAll;
    Fp := It.FirstPCBObject;
    While Fp <> Nil Do
    Begin
        If Used.IndexOf(Fp.Name) >= 0 Then Kill.Add(Fp);
        Fp := It.NextPCBObject;
    End;
    Lib.LibraryIterator_Destroy(It);
    If Kill.Count <> 32 Then
    Begin
        ShowMessage('Refusing: found ' + IntToStr(Kill.Count) + ' of the 32 used footprints; nothing removed.');
        Kill.Free;
        Used.Free;
        Exit;
    End;
    For i := 0 To Kill.Count - 1 Do Lib.RemoveComponent(Kill.Items[i]);
    Kill.Free;
    Used.Free;
    Lib.RefreshView;
    ShowMessage('Removed the 32 used footprints from the scratch copy. Select the rest in the PCB Library panel and copy them.');
End;
