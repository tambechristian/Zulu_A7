# Zulu_a7_no_pmod Rev 2: design-specific IBIS for U1 (XC7A35T-2CPG236I) from Vivado write_ibis.
set here [file dirname [file normalize [info script]]]
read_verilog $here/zulu_a7_no_pmod_top.v
read_xdc $here/zulu_a7_no_pmod.xdc
synth_design -top zulu_a7_top -part xc7a35tcpg236-2
opt_design
place_design
report_io -file $here/zulu_a7_no_pmod_io.rpt
write_ibis -force -allmodels $here/zulu_a7_no_pmod_u1.ibs
