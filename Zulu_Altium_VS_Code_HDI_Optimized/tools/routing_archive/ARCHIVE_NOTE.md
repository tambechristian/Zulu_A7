# Routing tools archive

This folder is a reference copy of the scripts that routed the Zulu A7 board. They were written for the production
board in `Zulu_Altium_VS_Code/`, before this HDI_Optimized copy existed. The scripts that made this copy are one folder
up, in `tools/`, and were not changed.

- **Source:** the 295 git-tracked files of `Zulu_Altium_VS_Code/tools/`, last changed in commit 8df3577.
- **Copied:** 2026-11-05, byte for byte, keeping the subfolders. `__pycache__` was left out.
- **Added here:** only this note.

## Do not run these scripts from this folder

They still expect to sit in the production copy's `tools/` folder:

- 35 scripts contain absolute paths, most of them into `Zulu_Altrium/`. Run from here, they would still read or write
  those folders, not this board.
- Many scripts find their inputs and outputs relative to their own folder. Run from here, they would either fail or
  overwrite the files in this archive.

To re-run one, use the original in `Zulu_Altium_VS_Code/tools/`.

## Comparing with the source

This should report only this note, plus any `__pycache__` folder in the source:

    git diff --no-index --stat Zulu_Altium_VS_Code/tools Zulu_Altium_VS_Code_HDI_Optimized/tools/routing_archive
