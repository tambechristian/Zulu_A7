#!/bin/sh
# pipeline.sh <tag> step1.json [step2.json ...]   (run from tools/route/rev2/F)
# flatten the steps onto prep/base_moved.json -> augment (B/augment.py connectors) -> compose_plan -> gates
set -e
TAG=$1; shift
BASE=../prep/base_moved.json
TOOLS=../../..
PCB="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc"
WC=C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/widthcheck.py
python flatten.py $BASE s/${TAG}_rip.json s/${TAG}_route.json "$@"
python ../B/augment.py $BASE s/${TAG}_rip.json s/${TAG}_route.json s/${TAG}_route_aug.json | head -3
python $TOOLS/compose_plan.py $BASE s/${TAG}_rip.json s/${TAG}_route_aug.json s/${TAG}_plan.json
python $TOOLS/route_check.py s/${TAG}_plan.json $BASE | grep -v "^  " | head -5
python $TOOLS/route_check.py s/${TAG}_plan.json $BASE | grep "^  " | head -20
python "$WC" "$PCB" s/${TAG}_plan.json | tail -3
python final_check.py $BASE ../model_base.json s/${TAG}_plan.json
