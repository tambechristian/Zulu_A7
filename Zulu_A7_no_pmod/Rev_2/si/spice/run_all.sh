#!/bin/sh
# Run every SDRAM net, both corners, in 10 parallel workers; merge into results_typ.json / results_max.json.
cd "$(dirname "$0")"
NETS="A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 BS0 BS1 D0 D1 D2 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D13 D14 D15 CAS# RAS# WE# CKE SDRAM-CS# LDQM UDQM SDRAM-CLK"
for corner in typ max; do
  i=0; grp=""; k=0
  for n in $NETS; do
    grp="$grp,$n"; i=$((i+1))
    if [ $i -eq 8 ]; then python bus_sim.py --corner $corner --nets "${grp#,}" --tag _p$k > log_${corner}_$k.txt 2>&1 & k=$((k+1)); i=0; grp=""; fi
  done
  [ -n "$grp" ] && python bus_sim.py --corner $corner --nets "${grp#,}" --tag _p$k > log_${corner}_$k.txt 2>&1 &
done
wait
python - <<'PY'
import json,glob
for c in ('typ','max'):
    out=[]
    for f in sorted(glob.glob('results_%s_p*.json'%c)): out+=json.load(open(f))
    json.dump(out,open('results_%s.json'%c,'w'),indent=1); print(c,len(out))
PY
