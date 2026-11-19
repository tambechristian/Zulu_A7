#!/bin/bash
# seq.sh tag net1 net2 ... : one net at a time, each seeded with the previous plan, no rip-up
tag=$1; shift
cd "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools"
D=route/jtag; log=$D/$tag.log; : > $log
prev=""; i=0
for n in "$@"; do
  i=$((i+1)); out=$D/${tag}_$i.json
  S=""; [ -n "$prev" ] && S="--seed $prev"
  python router.py --model $D/model.json $S --nets "$n" --pops 500000 --rip 0 --out $out 2>&1 | grep -E "routed|FAIL" | sed "s/^/$n: /" >> $log
  [ -f $out ] && prev=$out
done
cp $prev $D/$tag.json; echo DONE $tag >> $log
