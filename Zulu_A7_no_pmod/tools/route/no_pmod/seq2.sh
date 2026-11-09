#!/bin/bash
tag=$1; shift
cd "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/tools"
prev=route/no_pmod/tdi.json
log=route/no_pmod/s2_$tag.log; : > $log
i=0
for n in "$@"; do
  i=$((i+1)); out=route/no_pmod/s2_${tag}_$i.json
  python router.py --model route/no_pmod/model.json --seed $prev --nets "$n" --pops 500000 --rip 0 --out $out 2>&1 | grep -E "routed|FAIL|ripped" | sed "s/^/$n: /" >> $log
  [ -f $out ] && prev=$out
done
cp $prev route/no_pmod/s2_$tag.json
echo DONE $tag >> $log
