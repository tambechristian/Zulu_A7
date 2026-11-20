"""Fab B Rev 2 sync (2026-11-20), sheets 3 and 4: Altium SI models on U3 and U10, copied from Zulu_A7_no_pmod Rev 2.

    python tools/si_models_sch.py            dry run
    python tools/si_models_sch.py apply      writes zulu_a7_3.SchDoc (U3 part 3) and zulu_a7_4.SchDoc (U10)

On the no-PMOD board the models were assigned in Altium's GUI (51ffba0) and saved with the sheets:
- U3 (AS4C32M16SB-7TCN SDRAM), on its part 3: SI model AS4C32M16SB_7TCN ("Alliance Memory IBIS 5.0, DQ full drive"),
  SI_INPUT_MODEL / SI_OUTPUT_MODEL parameters on the 16 DQ pins and SI_INPUT_MODEL on the address / control inputs.
- U10 (93LC46B EEPROM): SI model 93LC46B_I_SN_3V3 ("Microchip IBIS 3.2, 3.3 V"), SI_INPUT_MODEL on pins 1-3,
  SI_INPUT_MODEL + SI_OUTPUT_MODEL on pin 4 (DO).  The model keeps the IBIS file's SOIC name on the MSOP part, as on
  the no-PMOD board.
U1's no-PMOD model (ARTIX7_ZULU_NOPMOD, sheet 5) is deliberately NOT copied: it was built for the no-PMOD pin-out.

What is written, per component (found by designator + CurrentPartId on both sheets):
- every SI_* parameter the no-PMOD sheet has under one of the component's pins is appended after that pin's existing
  children on this sheet (matched by pin Designator + OwnerPartId), with IndexInSheet continuing the pin's own
  child numbering;
- the SI implementation record (RECORD=45 ModelType=SI) with its MapDefinerList (46), ImplParams (48) and the two
  ImplParams parameters TYPE / TECH is appended to the component's ImplList after the footprint implementation.
Bodies are the no-PMOD bytes (UniqueIDs checked free here; the font table entries they use are checked equal); only
OwnerIndex and the pin parameters' IndexInSheet are rewritten.  Afterwards each component's subtree must equal the
no-PMOD one apart from IndexInSheet, OwnerIndex, record order inside a pin, the HiddenNetName / PinUniqueId
UniqueIDs that Altium re-keyed when it saved the no-PMOD sheets, the DatafileCount / ModelDatafileEntity0 /
ModelDatafileKind0 fields that save added to the footprint record, and U10's dated description (checked).  No pin, wire or label changes, so the
netlist is untouched.  Needs backups/zulu_a7_3.SchDoc.pre-sync and backups/zulu_a7_4.SchDoc.pre-sync.
"""
import re
import sys
from collections import Counter

from sync_sch_common import (NEW_HDR, component, field, insert, load, num, owner, require_backup, save, set_field,
                             sheet, strip_field, subtree)

# (sheet, designator, part, SI model, root fields that differ on purpose: U10's description dates its MSOP
# change to this board's 2026-11-20, see u10_msop_sch.py)
TARGETS = [(3, 'U3', '3', 'AS4C32M16SB_7TCN', ()), (4, 'U10', '1', '93LC46B_I_SN_3V3', ('ComponentDescription',))]


def pin_key(b):
    return field(b, 'Designator'), field(b, 'OwnerPartId')


def plan(R, S, des, part, model):
    """Return the insert list for this sheet's records R, copying the SI records of des/part from S."""
    rc, sc = component(R, des, part), component(S, des, part)
    rsub, ssub = subtree(R, rc), subtree(S, sc)
    if any(field(R[i][1], 'RECORD') == '45' and field(R[i][1], 'ModelType') == 'SI' for i in rsub):
        raise SystemExit('Refusing: %s already has an SI model' % des)
    rpins = {pin_key(R[i][1]): i for i in rsub if field(R[i][1], 'RECORD') == '2' and owner(R[i][1]) == rc}
    spins = {pin_key(S[i][1]): i for i in ssub if field(S[i][1], 'RECORD') == '2' and owner(S[i][1]) == sc}
    assert len(rpins) == len([i for i in rsub if field(R[i][1], 'RECORD') == '2']), 'duplicate pin keys'
    assert set(rpins) == set(spins), 'pin sets differ'
    ins = []
    n_pin = 0
    for key, sp in sorted(spins.items(), key=lambda kv: kv[1]):
        si = [i for i in ssub if owner(S[i][1]) == sp and field(S[i][1], 'RECORD') == '41'
              and (field(S[i][1], 'Name') or '').upper().startswith('SI_')]
        if not si:
            continue
        rp = rpins[key]
        kids = [i for i in rsub if owner(R[i][1]) == rp]
        assert all(not (field(R[i][1], 'Name') or '').upper().startswith('SI_') for i in kids)
        assert kids == list(range(rp + 1, rp + 1 + len(kids))), 'pin children not contiguous'
        nxt = max([num(R[i][1], 'IndexInSheet') or 0 for i in kids] + [-1]) + 1
        for i in si:
            b = set_after_owner(S[i][1], 'IndexInSheet', str(nxt))
            nxt += 1
            ins.append((rp + 1 + len(kids), S[i][0], b, ('old', rp)))
            n_pin += 1
    # the SI implementation and its children
    rlist = [i for i in rsub if field(R[i][1], 'RECORD') == '44' and owner(R[i][1]) == rc]
    slist = [i for i in ssub if field(S[i][1], 'RECORD') == '44' and owner(S[i][1]) == sc]
    assert len(rlist) == 1 and len(slist) == 1
    simpl = [i for i in ssub if owner(S[i][1]) == slist[0] and field(S[i][1], 'RECORD') == '45'
             and field(S[i][1], 'ModelType') == 'SI']
    assert len(simpl) == 1 and field(S[simpl[0]][1], 'ModelName') == model, simpl
    impl_tree = subtree(S, simpl[0])
    assert [field(S[i][1], 'RECORD') for i in impl_tree] == ['45', '46', '48', '41', '41'], impl_tree
    at = max(subtree(R, rlist[0])) + 1
    base = len(ins)
    pos_of = {}
    for k, i in enumerate(impl_tree):
        pos_of[i] = base + k
        o = owner(S[i][1])
        own = ('old', rlist[0]) if o == slist[0] else ('new', pos_of[o])
        ins.append((at, S[i][0], S[i][1], own))
    return ins, n_pin, rc


def drop_field(body, key):
    return re.sub(rb'\|' + re.escape(key.encode()) + rb'=[^|\x00]*', b'', body, flags=re.I)


def set_after_owner(body, key, value):
    """set_field, but a new field goes right after OwnerIndex (where Altium writes IndexInSheet)."""
    if field(body, key) is not None:
        return set_field(body, key, value)
    m = re.search(rb'\|OwnerIndex=[^|\x00]*', body)
    return body[:m.end()] + b'|' + key.encode() + b'=' + value.encode() + body[m.end():]


def canon(recs, root, root_ignore=()):
    """Multiset view of a component subtree for the equality check (see the docstring): records without OwnerIndex /
    IndexInSheet (and without the UniqueID of HiddenNetName / PinUniqueId parameters), each tagged with its parent's
    record type and name; the root also without the fields in root_ignore."""
    out = Counter()
    for i in subtree(recs, root):
        b = drop_field(drop_field(recs[i][1], 'OwnerIndex'), 'IndexInSheet')
        if field(b, 'RECORD') == '41' and field(b, 'Name') in ('HiddenNetName', 'PinUniqueId'):
            b = drop_field(b, 'UniqueID')
        if field(b, 'RECORD') == '45' and field(b, 'ModelType') == 'PCBLIB':
            # Altium's re-save of the no-PMOD sheet 3 added these three to every footprint record (84 parts);
            # this sheet was never re-saved that way -- a normalisation, not part of the SI model
            for k in ('DatafileCount', 'ModelDatafileEntity0', 'ModelDatafileKind0'):
                b = drop_field(b, k)
        if i == root:
            for k in root_ignore:
                b = drop_field(b, k)
            parent = ('root',)
        else:
            pb = recs[owner(recs[i][1])][1]
            parent = (field(pb, 'RECORD'), field(pb, 'Designator') or field(pb, 'Name') or field(pb, 'ModelName'),
                      field(pb, 'OwnerPartId'))
        out[(parent, b)] += 1
    return out


def main():
    apply = 'apply' in sys.argv[1:]
    for n, des, part, model, root_ignore in TARGETS:
        path = sheet(n)
        R, S = load(path), load(sheet(n, src=True))
        ins, n_pin, rc = plan(R, S, des, part, model)
        # copied UniqueIDs must be free, fonts must agree
        used = {field(b, 'UniqueID') for h, b in R if field(b, 'UniqueID')}
        assert not [field(b, 'UniqueID') for p, h, b, o in ins if field(b, 'UniqueID') in used]
        hr = [b for h, b in R if field(b, 'RECORD') == '31'][0]
        hs = [b for h, b in S if field(b, 'RECORD') == '31'][0]
        for k in {field(b, 'FontID') for p, h, b, o in ins if field(b, 'FontID')}:
            for f in ('FontName', 'Size', 'Rotation', 'Bold', 'Italic', 'Underline'):
                assert field(hr, f + k) == field(hs, f + k), (n, k, f)
        out, new_old, new_ins = insert(R, ins)
        same = canon(out, new_old[rc], root_ignore) == canon(S, component(S, des, part), root_ignore)
        print('sheet %d %s part %s: %d pin SI parameters + %d implementation records (model %s); records %d -> %d; '
              'subtree == no-PMOD (modulo re-keyed pin-parameter IDs): %s'
              % (n, des, part, n_pin, len(ins) - n_pin, model, len(R), len(out), same))
        assert same
        if apply:
            require_backup(path)
            print('   written zulu_a7_%d.SchDoc md5 %s' % (n, save(path, out)))
    if not apply:
        print('dry run (add "apply" to write)')


if __name__ == '__main__':
    main()
