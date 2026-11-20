#!/bin/sh
# Strategy A (keep TARGET's Pmod-zone copper): rebuild plan_A.json from the prep (about 25 minutes; at most 2 python
# processes at once). Inputs: ../prep/after_transplant_stubs.json, ../prep/transplant_stubs.json, ../prep/base_new.json.
#   1. router_a.py (TARGET's router.py + SOURCE's SDRAM-Dn set, through-via-in-SMD-pad mask, via hole-to-hole blocker)
#      on the stubs transplant: 7 of the 10 opens close (r2_stubs.json)
#   2. manual1.py: GND U1-L19 laser + CHAN5 stack, exact geometry (manual1.json, m3.json)
#   3. router_a.py --slack 0 for UART_FT_TXD alone (r3_uart_s0.json)
#   4. compose_a.py (prune_stubs SOURCE version + crumbs + dead branches) -> smooth.py (exact string pulling of the
#      routing tracks) -> compose_a.py again -> plan_A.json; check_a.py -> check_A.json; judge.py -> judge_A/
set -e
A="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/sync/A"
T="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools"
cd "$A"
NETS="CHAN2,CHAN5,CHAN9,CLK-12M-FPGA,FLASH-D02,FPGA-INIT#,FPGA-TMS,GND,PROG#,UART_FT_TXD"
timeout 5400 python router_a.py --model ../prep/after_transplant_stubs.json --nets "$NETS" --out r2_stubs.json \
  --checkpoint r2_stubs.partial.json --order short > r2_stubs.log 2>&1
python - <<'PY'
import json
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
P = json.load(open('r2_stubs.json'))
M = json.load(open('../prep/after_transplant_stubs.json'))
M['tracks'] += P['tracks']
M['vias'] += [dict(v, span=STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]) for v in P['vias']]
json.dump(M, open('m_r2_stubs.json', 'w'))
PY
python manual1.py
timeout 3600 python router_a.py --model m3.json --nets UART_FT_TXD --slack 0 --rip 0 --pops 2000000 \
  --out r3_uart_s0.json > r3_uart_s0.log 2>&1
python compose_a.py ../prep/transplant_stubs.json plan_v4.json r2_stubs.json manual1.json r3_uart_s0.json
python - <<'PY'
import json, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import compose_plan as CP
P = json.load(open('plan_v4.json')); TS = json.load(open('../prep/transplant_stubs.json'))
tk = {CP.tkey(t) for t in TS['tracks']}; vk = {CP.vkey(v) for v in TS['vias']}
json.dump({'tracks': [t for t in P['tracks'] if CP.tkey(t) not in tk],
           'vias': [v for v in P['vias'] if CP.vkey(v) not in vk]}, open('v4_routing_only.json', 'w'), indent=1)
PY
python smooth.py plan_v4.json v4_routing_only.json plan_v5s.json
python compose_a.py plan_v5s.json plan_A.json
python check_a.py plan_A.json A --planeweb > check_A.log 2>&1
python ../prep/scripts/native_keys.py plan_A.json > native_keys_A.txt 2>&1
mkdir -p judge_A
(cd "$T" && python route/rev2/judge/judge.py route/sync/prep/base_new.json route/sync/prep/base_cur.json \
   route/sync/A/plan_A.json route/sync/A/judge_A > route/sync/A/judge_A/judge.txt 2>&1)
