# Altium import checks

Scripts used to convert `zulu_a7.sch` (EAGLE 9.7 XML, written by Fusion 360)
into `Imported zulu_a7.PrjPcb` with Altium Designer's EAGLE Import Wizard,
and to check the result.  They edit the SchDoc files directly (OLE compound
documents, `FileHeader` stream of `|RECORD=n|Key=Value|` records), so close
the project in Altium before running the two fix scripts.

    pip install olefile pywin32

* `verify_import.py zulu_a7.sch "Imported zulu_a7.PrjPcb"` - every EAGLE
  part, gate, supply symbol and named net has its Altium counterpart.
* `fix_text_orientation.py <SchDoc...>` - EAGLE draws R180/R270 text
  readable; Altium draws Orientation 2/3 upside down.  Turns them into
  0/90 with mirrored justification, so anchors and text boxes stay put.
* `fix_labels.py <this folder> "Imported zulu_a7.PrjPcb"` - the label
  placements adjusted after reviewing the Smart PDF export (see docstring).
* `fix_gate_labels.py <this folder> <SchDoc...>` - the one-pin-per-gate
  parts (X2, U3, U4, U1) show their gate names through EAGLE's >GATE text;
  the importer gives every such label OwnerPartId=1, so Altium hides all but
  one per part.  Re-owns each label to its gate.
* `add_noerc.py <this folder> "Imported zulu_a7.PrjPcb"` - No-ERC markers on
  the nine pins that are open on purpose (the eight GTP balls the sheet
  marks "float per UG482", and the USB ID pin X1-4).
* `fix_pin_types.py <this folder> "Imported zulu_a7.PrjPcb"` - the EAGLE
  library types the supply/ground pins of U2, U3, U4, U10 and all of X2's
  pins as "io"; makes them Power and Passive so the ERC pin-type rules mean
  something.
* `erc_summary.py erc.txt` - groups a Messages-panel export (right-click,
  Save...) by message kind.
* `eagle_netlist.py zulu_a7.sch eagle.json` then
  `compare_netlists.py "Imported zulu_a7.PrjPcb/Project Outputs for zulu_a7/zulu_a7.NET" eagle.json`
  - connectivity of the Altium project (Design > Netlist For Project >
  Protel) against the EAGLE schematic, pad by pad.  Last result:
  190 components, 175 nets, 799 pads, identical names, no differences.

Import Wizard settings that matter: untick "Do not translate hidden net
names" (else 16 nets named without a label lose their names).  Pins that
own several pads in EAGLE (BTN 1/2 and 3/4, X1 5+shell, X3 G1/G3 and
G2/G4) become single Altium pins named "1,2" etc.; split them before
matching to the imported board.
