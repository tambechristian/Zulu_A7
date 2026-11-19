#!/bin/bash
tag=$1; shift
cd "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools"
D=route/jtag2; log=$D/$tag.log; : > $log
prev=""; i=0
for n in "$@"; do
  i=$((i+1)); out=$D/${tag}_$i.json
  S=""; [ -n "$prev" ] && S="--seed $prev"
  python router.py --model $D/model.json $S --nets "$n" --widths $D/widths.json --pops 1500000 --rip 0 --margin 4 --out $out 2>&1 | grep -E "routed|FAIL" | sed "s/^/$n: /" >> $log
  [ -f $out ] && prev=$out
done
cp $prev $D/$tag.json; echo DONE $tag >> $log
