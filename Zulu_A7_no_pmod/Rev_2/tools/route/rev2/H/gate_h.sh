#!/bin/sh
# gate_h.sh <tag>: every gate on final_<tag>.json (route_check, widthcheck, via_pad, usb_metrics, prune on board)
T=/c/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools
H=$T/route/rev2/H
TAG=$1
cd $T
python route_check.py route/rev2/H/final_$TAG.json route/rev2/prep/base_moved.json | tail -12
python C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/widthcheck.py "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc" route/rev2/H/final_$TAG.json | tail -3
python $H/via_pad.py route/rev2/prep/base_moved.json route/rev2/H/final_$TAG.json
python $H/usb_metrics.py route/rev2/H/board_$TAG.json
python prune_stubs.py route/rev2/H/board_$TAG.json | tail -3
