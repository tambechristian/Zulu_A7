# -*- coding: utf-8 -*-
"""Point sheet 4's U2 footprint record at the FT2232HQ-QFN64 library entity (2026-11-19).

    python tools/u2_model_entity.py "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"

tools/u2_ft2232hq.py changed U2's footprint record ModelName to FT2232HQ-QFN64 but left
ModelDatafileEntity0 on FT2232HL-LQFP64, so every other part had ModelName == ModelDatafileEntity0 except U2.
u2_ft2232hq.py now sets both; this script repairs a sheet that was converted before that change.  It rewrites one
field of one record, refuses anything unexpected, and does nothing if the sheet is already correct.
Close sheet 4 in Altium first (or make sure it is unmodified there): the file is opened for exclusive write.
"""
import sys

from fix_text_orientation import field, join, read_stream, set_field, split, write_stream

MODEL = 'FT2232HQ-QFN64'
OLD_ENTITY = 'FT2232HL-LQFP64'


def fix(path):
    data = read_stream(path, 'FileHeader')
    records = split(data)
    hits = [i for i, (_, body) in enumerate(records)
            if field(body, 'RECORD') == '45' and field(body, 'ModelName') == MODEL]
    if len(hits) != 1:
        raise RuntimeError('Refusing: expected one footprint record named %s, found %d' % (MODEL, len(hits)))
    i = hits[0]
    entity = field(records[i][1], 'ModelDatafileEntity0')
    if entity == MODEL:
        print('already correct: ModelDatafileEntity0 = %s' % MODEL)
        return
    if entity != OLD_ENTITY:
        raise RuntimeError('Refusing: unexpected ModelDatafileEntity0 %r' % entity)

    records[i][1] = set_field(records[i][1], 'ModelDatafileEntity0', MODEL)
    output = join(records)
    write_stream(path, 'FileHeader', output)

    check = read_stream(path, 'FileHeader')
    if check != output:
        raise RuntimeError('SchDoc write verification failed')
    after = split(check)
    old = split(data)
    diff = [j for j, (a, b) in enumerate(zip(old, after)) if a[1] != b[1]]
    if len(after) != len(old) or diff != [i]:
        raise RuntimeError('Verification failed: records changed %s of %d' % (diff, len(old)))
    print('U2 footprint record %d: ModelDatafileEntity0 %s -> %s; %d records, only that one changed'
          % (i, OLD_ENTITY, MODEL, len(after)))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: python tools/u2_model_entity.py <zulu_a7_4.SchDoc>')
    fix(sys.argv[1])
