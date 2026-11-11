"""SchDoc record access (same helpers as Zulu_Altium_VS_Code/tools/fix_text_orientation.py).

A SchDoc's FileHeader stream is a list of records: 2-byte little-endian length, 2 more header bytes,
then a |KEY=value|... body ending in NUL. Children point at their owner with OwnerIndex, which counts
records from 0 after the header record (record 0) -- so OwnerIndex=k means recs[k + 1]. owner() returns
that list index.
"""
import re

import olefile
import pythoncom
from win32com import storagecon


def read_stream(path, name='FileHeader'):
    return olefile.OleFileIO(path).openstream(name).read()


def write_stream(path, data, name='FileHeader'):
    mode = storagecon.STGM_READWRITE | storagecon.STGM_SHARE_EXCLUSIVE
    stg = pythoncom.StgOpenStorage(path, None, mode, None, 0)
    stm = stg.OpenStream(name, None, mode, 0)
    stm.SetSize(0)
    stm.Seek(0, 0)
    stm.Write(data)
    stm.Commit(0)
    stm = None
    stg.Commit(0)


def split(data):
    recs, i = [], 0
    while i + 4 <= len(data):
        n = int.from_bytes(data[i:i + 2], 'little')
        hdr = data[i:i + 4]
        i += 4
        recs.append([hdr, data[i:i + n]])
        i += n
    assert i == len(data)
    return recs


def join(recs):
    return b''.join(len(body).to_bytes(2, 'little') + hdr[2:] + body for hdr, body in recs)


def field(body, key):
    m = re.search(rb'\|(?:%UTF8%)?' + re.escape(key.encode()) + rb'=([^|\x00]*)', body, re.I)
    return m.group(1).decode('latin-1') if m else None


def set_field(body, key, value):
    """Replace key's value, or insert |key=value| right after |RECORD=n|."""
    pat = re.compile(rb'(\|(?:%UTF8%)?' + re.escape(key.encode()) + rb'=)[^|\x00]*', re.I)
    if pat.search(body):
        return pat.sub(lambda m: m.group(1) + value.encode('latin-1'), body, count=1)
    m = re.match(rb'\|RECORD=\d+', body)
    return body[:m.end()] + b'|' + key.encode() + b'=' + value.encode('latin-1') + body[m.end():]


def del_field(body, key):
    return re.sub(rb'\|(?:%UTF8%)?' + re.escape(key.encode()) + rb'=[^|\x00]*', b'', body, count=1, flags=re.I)


def owner(body):
    v = field(body, 'OwnerIndex')
    return int(v) + 1 if v is not None else None


def subtree(recs, roots):
    """Indices of the records in roots plus everything that (transitively) belongs to them."""
    out = set(roots)
    grew = True
    while grew:
        grew = False
        for i, (h, b) in enumerate(recs):
            if i not in out and owner(b) in out:
                out.add(i)
                grew = True
    return out


def delete(recs, drop):
    """Remove records and renumber every OwnerIndex; refuses if a survivor points at a dropped record."""
    drop = set(drop)
    new_index, k = {}, 0
    for i in range(len(recs)):
        if i not in drop:
            new_index[i] = k
            k += 1
    out = []
    for i, (h, b) in enumerate(recs):
        if i in drop:
            continue
        o = owner(b)
        if o is not None and o > 0:
            if o in drop:
                raise ValueError('record %d survives but its owner %d is deleted' % (i, o))
            b = set_field(b, 'OwnerIndex', str(new_index[o] - 1))
        out.append([h, b])
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    return out
