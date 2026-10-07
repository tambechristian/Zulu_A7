117 signal balls: 13 dedicated, 6 fixed-function, 4 XADC, 94 freely permutable

ring surcharge, identical for every assignment: 330 mm-equivalent (40 balls in ring 1, 35 in ring 2)

rotation   distance (mm)   by group
    0 deg          3007   header 1018  SDRAM 696  other 293  microSD 249  flash 231  XADC 198  config 167  Pmod 154
   90 deg          2944   header 841  SDRAM 806  other 260  flash 248  microSD 246  XADC 207  Pmod 202  config 135
  180 deg          3136   SDRAM 1088  header 772  microSD 245  XADC 238  Pmod 216  flash 206  other 199  config 171
  270 deg          3241   SDRAM 978  header 959  other 291  microSD 237  XADC 229  flash 206  Pmod 181  config 161
-> the package should sit at 90 degrees

the 94 permutable nets cost 2532 as assigned; the best legal permutation costs 2121
-> a full re-pin takes 411 mm out, 16% of what those nets cost

that permutation is 5 INDEPENDENT cycles -- each is a self-contained rotation of nets between balls, adoptable on its own:
   1. 34-cycle  saves  162.7 mm   cumulative  40%
      D14@A14  ->  JA4@C17  ->  CHAN-CLK@P18  ->  BS0@V2  ->  CHAN21@U15  ->  LED0_R@P19  ->  D7@U4  ->  A5@R2  ->  A12@M3  ->  CHAN17@U16  ->  LED0_B@N19  ->  A1@T3  ->  D11@J1  ->  CHAN16@W16  ->  SD-DAT2@L3  ->  CHAN20@V15  ->  LED1@N18  ->  A2@T2  ->  D10@K2  ->  A8@N3  ->  D13@H1  ->  CHAN15@V17  ->  D0@V8  ->  UART_FT_DTR#@M18  ->  BS1@U1  ->  A6@P3  ->  A4@R3  ->  CKE@M2  ->  D12@J3  ->  CHAN14@W17  ->  CHAN13@W18  ->  D4@U5  ->  UART_FT_TXD@K18  ->  A10@U3  ->  back to D14@A14
   2. 39-cycle  saves  155.8 mm   cumulative  78%
      CHAN3@A17  ->  CHAN1@A18  ->  CHAN0@B18  ->  CHAN2@B17  ->  JA10@U17  ->  D3@W6  ->  UART_FT_CTS#@B16  ->  JA2@U19  ->  CHAN11@K17  ->  D5@W5  ->  CHAN28@R19  ->  D6@V5  ->  CHAN27@T18  ->  CHAN6@H17  ->  SD-CLK@U8  ->  FT-PWREN#@P17  ->  A3@T1  ->  UDQM@L2  ->  A7@P1  ->  SDRAM-CLK@M1  ->  A9@N2  ->  D9@K3  ->  CHAN18@V16  ->  LED2@M19  ->  LDQM@W4  ->  CHAN26@V13  ->  LED0_G@R18  ->  WE#@V4  ->  CHAN23@V14  ->  BTN@N17  ->  CHAN4@C16  ->  JA7@T17  ->  CHAN7@H19  ->  SDRAM-CS#@W2  ->  CHAN25@W13  ->  SD-DAT0@C15  ->  JA3@G17  ->  D1@V7  ->  UART_FT_RXD@G19  ->  back to CHAN3@A17
   3. 7-cycle  saves   41.2 mm   cumulative  88%
      SD-DAT1@B15  ->  JA9@V19  ->  D2@W7  ->  SD-CMD@U7  ->  UART_FT_RTS#@L18  ->  A0@U2  ->  CHAN19@W15  ->  back to SD-DAT1@B15
   4. 6-cycle  saves   31.0 mm   cumulative  95%
      SD-DAT3@A16  ->  JA1@U18  ->  CHAN9@J17  ->  CHAN8@J18  ->  CAS#@W3  ->  CHAN22@W14  ->  back to SD-DAT3@A16
   5. 5-cycle  saves   20.0 mm   cumulative 100%
      D15@A15  ->  JA8@E19  ->  CHAN12@W19  ->  CHAN10@J19  ->  RAS#@V3  ->  back to D15@A15

the tail -- the worst nets now, and what the optimum does with them:
  CHAN28       R19  ring 0   52.7 mm  ->  moves to W5   ( 43.7 mm)
  AIN15_P      G3   ring 2   52.5 mm  (fixed, cannot move)
  AIN15_N      G2   ring 1   52.0 mm  (fixed, cannot move)
  AIN16_P      H2   ring 1   51.5 mm  (fixed, cannot move)
  AIN16_N      J2   ring 1   51.0 mm  (fixed, cannot move)
  FLASH-D01    D19  ring 0   50.9 mm  (fixed, cannot move)
  FLASH-D00    D18  ring 1   50.4 mm  (fixed, cannot move)
  FLASH-D03    F18  ring 1   49.4 mm  (fixed, cannot move)
  CHAN27       T18  ring 1   49.1 mm  ->  moves to V5   ( 41.6 mm)
  FLASH-D02    G18  ring 1   48.9 mm  (fixed, cannot move)
  FLASH-CS#    K19  ring 0   47.9 mm  (fixed, cannot move)
  FPGA-CCLK    C11  ring 2   47.4 mm  (fixed, cannot move)
  SD-DAT3      A16  ring 0   44.8 mm  ->  moves to W14  ( 34.8 mm)
  SD-DAT1      B15  ring 1   43.8 mm  ->  moves to W15  ( 35.3 mm)

written: C:\Users\tambe\Documents\Electronics\Zulu_A7\Zulu_Altrium\docs\repin_study.json
