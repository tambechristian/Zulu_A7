#!/bin/sh
# Strategy B, Fab B Rev 2 <- no_pmod Rev 2 (2026-11-20): rebuild plan_B.json and its gates (about 45 minutes; never
# more than one python process at a time here). Inputs: ../prep (base_cur/base_new/delta/models).
#   1. build_b.py --rip nets   transplant with every SOURCE addition that fits once the conflicting JA nets
#                              (JA1-JA4, JA8-JA10; JA7 has no conflict and stays) are ripped; stubs mode
#   2. make_seeds.py           SOURCE zone copper (x >= 49.5) of UART_FT_TXD, FPGA-TMS, FPGA-INIT#, LED0_R,
#                              CLK-12M-FPGA, FLASH-D02, PROG# becomes rippable router seed copper
#   3. exact_router.py         (router_b.py = SOURCE's router.py from TARGET's tools, with an exact free-space field)
#                              JA nets first (corner balls W19/V19/W18 first), then FLASH-D02, PROG#, ripped seeds
#   4. exact_router.py         PROG# again with a larger A* budget (the first pass ran out: 'budget')
#   5. compose_b.py            ONE plan vs TARGET's copper, dead stubs pruned (TARGET prune_stubs)
#   6. gates.sh                every gate -> gates_B/
set -e
B="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/sync/B"
cd "$B"
python scripts/build_b.py --rip nets --mode stubs > log_build_nets_stubs.txt 2>&1
python scripts/make_seeds.py transplant_b_nets_stubs.json after_b_nets_stubs.json \
  UART_FT_TXD,FPGA-TMS,FPGA-INIT#,LED0_R,CLK-12M-FPGA,FLASH-D02,PROG# 49.5 nets_s1
NETS=JA8,JA9,JA3,JA2,JA1,JA10,JA4,FLASH-D02,PROG#,UART_FT_TXD,FPGA-TMS,FPGA-INIT#,LED0_R,CLK-12M-FPGA
python scripts/exact_router.py --model model_nets_s1.json --seed seeds_nets_s1.json --nets $NETS \
  --out xroute_nets_s2.json --checkpoint xroute_nets_s2.partial.json --order given --rip 3 --soft 0.1 > log_xroute_nets_s2.txt 2>&1
python scripts/exact_router.py --model model_nets_s1.json --seed xroute_nets_s2.json --nets PROG# \
  --out xroute_nets_s3.json --checkpoint xroute_nets_s3.partial.json --order given --rip 2 --soft 0.1 --pops 3000000 \
  > log_xroute_nets_s3.txt 2>&1
cp xroute_nets_s3.json route_B.json
python scripts/compose_b.py transplant_nets_s1.json route_B.json plan_B.json
sh scripts/gates.sh "$B/plan_B.json" B "$B/route_B.json"
