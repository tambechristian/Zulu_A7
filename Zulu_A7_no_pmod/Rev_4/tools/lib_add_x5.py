"""Copy the STEMMA QT footprint JST-SM04B-SRSS-TB (pads, silk, pin-1 dot, 3D body) from Asar's library into the
no-PMOD Rev 3 project library (2026-11-21). Close the library in Altium first.

    python tools/lib_add_x5.py

Altium PcbLib = OLE compound file: one storage per footprint, plus Library/Data whose first record is the library
header and whose tail is the footprint name list (uint32 count, then per name: uint32 length, byte length, name).
The footprint storage is copied with IStorage.MoveElementTo(STGMOVE_COPY), the name appended to the list, the count
raised, and the whole file compacted with CopyTo into a new docfile. Refuses if the footprint is already there.
"""
import os
import shutil
import struct
import sys

import olefile
import pythoncom
from win32com import storagecon as sc

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(os.path.dirname(HERE), 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbLib')
SRC = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/Asar_feather.PrjPcb/asar_feather.PcbLib'
NAME = 'JST-SM04B-SRSS-TB'
MODE_R = sc.STGM_READ | sc.STGM_SHARE_DENY_WRITE
MODE_RW = sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE


def names(data):
    first = struct.unpack('<I', data[:4])[0]
    tail = data[4 + first:]
    n = struct.unpack('<I', tail[:4])[0]
    i, out = 4, []
    for _ in range(n):
        ln = struct.unpack('<I', tail[i:i + 4])[0]
        out.append(tail[i + 5:i + 4 + ln].decode('latin-1'))
        i += 4 + ln
    assert i == len(tail), 'name list does not end the stream'
    return first, out


def main():
    f = olefile.OleFileIO(DST)
    if [NAME] in [e[:1] for e in f.listdir()]:
        sys.exit('REFUSED: %s already in %s' % (NAME, DST))
    data = f.openstream(['Library', 'Data']).read()
    f.close()
    first, lst = names(data)
    bak = DST + '.pre-x5'
    if not os.path.exists(bak):
        shutil.copy2(DST, bak)
    tmp = DST + '.tmp'
    src = pythoncom.StgOpenStorage(SRC, None, MODE_R, None, 0)
    dst = pythoncom.StgOpenStorage(DST, None, MODE_RW, None, 0)
    src.MoveElementTo(NAME, dst, NAME, sc.STGMOVE_COPY)
    lib = dst.OpenStorage('Library', None, MODE_RW, None, 0)
    lst.append(NAME)
    tail = struct.pack('<I', len(lst)) + b''.join(
        struct.pack('<I', len(n) + 1) + bytes([len(n)]) + n.encode('latin-1') for n in lst)
    new = data[:4 + first] + tail
    st = lib.OpenStream('Data', None, MODE_RW, 0)
    st.SetSize(len(new))
    st.Write(new)
    st.Commit(0)
    del st, lib
    dst.Commit(0)
    out = pythoncom.StgCreateDocfile(tmp, sc.STGM_CREATE | sc.STGM_READWRITE | sc.STGM_SHARE_EXCLUSIVE, 0)
    dst.CopyTo(None, None, out)
    out.Commit(0)
    del out, dst, src
    os.replace(tmp, DST)
    f = olefile.OleFileIO(DST)
    _, chk = names(f.openstream(['Library', 'Data']).read())
    ok = f.openstream([NAME, 'Data']).read() == olefile.OleFileIO(SRC).openstream([NAME, 'Data']).read()
    print('%d footprints, %s listed: %s, data identical to Asar: %s' % (len(chk), NAME, NAME in chk, ok))


if __name__ == '__main__':
    main()
