"""Shared helpers for the 2026-11-20 schematic sync: Zulu_A7_no_pmod Rev_2 (SOURCE) -> Zulu_A7_Fab_B Rev_2 (this board).

docs/sync_schematics.md has the what and why.  Every script of the sync imports this module.  Paths are derived from
this file's location (Rev_2/tools), so nothing depends on a scratch folder:

    PRJ      Rev_2/Imported zulu_a7.PrjPcb                        (the sheets written)
    BAK      Rev_2/backups                                        (git-ignored; <sheet>.pre-sync, written before any edit)
    SRC_PRJ  <repo>/Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb (read only)

A SchDoc's FileHeader stream is a list of records: 2-byte little-endian length, 2 more header bytes, then a
|KEY=value|... body ending in NUL.  OwnerIndex=k points at recs[k + 1] (record 0 is the header); owner() returns that
list index.  Header field Weight must equal the record count after the header (Altium silently drops records past it).
The scripts write only the FileHeader stream (the Additional and Storage streams are identical on both boards).
"""
import hashlib
import os
import re
from collections import defaultdict

import olefile
import pythoncom
from win32com import storagecon

HERE = os.path.dirname(os.path.abspath(__file__))
REV2 = os.path.dirname(HERE)
PRJ = os.path.join(REV2, 'Imported zulu_a7.PrjPcb')
BAK = os.path.join(REV2, 'backups')
REPO = os.path.dirname(os.path.dirname(REV2))
SRC_PRJ = os.path.join(REPO, 'Zulu_A7_no_pmod', 'Rev_2', 'Imported zulu_a7.PrjPcb')
NEW_HDR = b'\x00\x00\x00\x00'      # header bytes of a new text record (join() rewrites the length)


def sheet(n, src=False):
    return os.path.join(SRC_PRJ if src else PRJ, 'zulu_a7_%d.SchDoc' % n)


def read_stream(path, name='FileHeader'):
    ole = olefile.OleFileIO(path)
    try:
        return ole.openstream(name).read()
    finally:
        ole.close()


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
    stg = None


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


def load(path):
    return split(read_stream(path))


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


def strip_field(body, key):
    """The body with key's value blanked (to compare two bodies that may differ only in that field)."""
    return re.sub(rb'(\|(?:%UTF8%)?' + re.escape(key.encode()) + rb'=)[^|\x00]*', rb'\1', body, flags=re.I)


def owner(body):
    v = field(body, 'OwnerIndex')
    return int(v) + 1 if v is not None else None


def num(body, key):
    v = field(body, key)
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def designators(recs):
    """{component record index: designator text}."""
    return {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34' and owner(b) is not None}


def component(recs, des, part='1'):
    """Index of the one component record with this designator and CurrentPartId."""
    d = designators(recs)
    hits = [i for i, (h, b) in enumerate(recs)
            if field(b, 'RECORD') == '1' and d.get(i) == des and (field(b, 'CurrentPartId') or '1') == part]
    if len(hits) != 1:
        raise RuntimeError('expected one %s part %s, found %d' % (des, part, len(hits)))
    return hits[0]


def subtree(recs, root):
    """Sorted indices of root and everything that (transitively) belongs to it."""
    kids = defaultdict(list)
    for i, (h, b) in enumerate(recs):
        o = owner(b)
        if o is not None and o > 0:
            kids[o].append(i)
    out, stack = [], [root]
    while stack:
        k = stack.pop()
        out.append(k)
        stack += kids.get(k, [])
    return sorted(out)


def by_uid(recs):
    out = {}
    for i, (h, b) in enumerate(recs):
        u = field(b, 'UniqueID')
        if u:
            out.setdefault(u, []).append(i)
    return out


def insert(recs, inserts):
    """Insert records and renumber every OwnerIndex.

    inserts: [(position, hdr, body, owner)] -- the record goes before the record now at `position` (len(recs) appends);
    owner is None (keep the body's own OwnerIndex, i.e. none for a sheet-level record), ('old', i) for an existing
    record or ('new', k) for the k-th entry of `inserts`.  Entries at the same position keep their order.
    Returns (new record list, {old index: new index}, {insert number: new index})."""
    at = defaultdict(list)
    for k, (pos, hdr, body, own) in enumerate(inserts):
        assert 0 <= pos <= len(recs)
        at[pos].append(k)
    rows, new_old, new_ins = [], {}, {}
    for i in range(len(recs) + 1):
        for k in at.get(i, []):
            new_ins[k] = len(rows)
            rows.append(('ins', k))
        if i < len(recs):
            new_old[i] = len(rows)
            rows.append(('old', i))
    out = []
    for kind, ref in rows:
        if kind == 'old':
            h, b = recs[ref]
            o = owner(b)
            if o is not None and o > 0:
                b = set_field(b, 'OwnerIndex', str(new_old[o] - 1))
        else:
            pos, h, b, own = inserts[ref]
            if own is not None:
                tgt = new_old[own[1]] if own[0] == 'old' else new_ins[own[1]]
                b = set_field(b, 'OwnerIndex', str(tgt - 1))
        out.append([h, b])
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    return out, new_old, new_ins


def duplicate_uids(recs):
    seen, dup = set(), set()
    for h, b in recs:
        u = field(b, 'UniqueID')
        if u:
            (dup if u in seen else seen).add(u)
    return dup


def check_sheet(recs, allow_dup=()):
    """Structural sanity: Weight, NUL terminators, every owner is an earlier record, UniqueIDs unique (except the
    duplicates in allow_dup, which the sheet already had -- sheet 1 has one, BWLGLMAY, on both boards)."""
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'Weight'
    for i, (h, b) in enumerate(recs):
        assert b.endswith(b'\x00'), ('no NUL', i)
        o = owner(b)
        if o is not None and o > 0:
            assert o < i, ('owner after child', i, o)
    extra = duplicate_uids(recs) - set(allow_dup)
    assert not extra, ('new duplicate UniqueIDs', sorted(extra))


def require_backup(path):
    bak = os.path.join(BAK, os.path.basename(path) + '.pre-sync')
    if not os.path.exists(bak):
        raise SystemExit('Refusing: no backup %s (copy the sheet there before the first edit)' % bak)
    return bak


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def save(path, recs):
    """Check (allowing only the pre-sync backup's duplicate UniqueIDs), write the FileHeader stream, read it back;
    returns the file md5 (8 hex)."""
    check_sheet(recs, duplicate_uids(load(require_backup(path))))
    blob = join(recs)
    write_stream(path, blob)
    if read_stream(path) != blob:
        raise RuntimeError('read-back mismatch on %s' % path)
    return md5(path)
