#!/bin/bash
# seq.sh tag net1 net2 ... : route nets one at a time, hardest first, each seeded with the previous plan
tag=$1; shift
cd "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_1/tools"
prev=route/no_pmod/tdi.json
log=route/no_pmod/seq_$tag.log; : > $log
i=0
for n in "$@"; do
  i=$((i+1)); out=route/no_pmod/seq_${tag}_$i.json
  python router.py --model route/no_pmod/model.json --seed $prev --nets "$n" --pops 500000 --rip 1 --out $out >> $log 2>&1
  [ -f $out ] && prev=$out
  grep -c . $log >/dev/null
done
cp $prev route/no_pmod/seq_$tag.json
echo DONE $tag >> $log
