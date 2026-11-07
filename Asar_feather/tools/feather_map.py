"""The Feather design decisions as data (2026-10-23). Every edit script and checker reads this file.

Feather pads: 1-16 are the 16-pin strip, 17-28 the 12-pin strip, both in Adafruit's pin-naming order
(learn.adafruit.com/adafruit-feather/feather-specification): the 16-pin strip is centred 1.0 in from the
USB end, the 12-pin strip 1.2 in, strips 0.8 in apart on a 2.0 x 0.9 in board.
"""

# Feather pad -> (Feather name, old X2 pin whose schematic gate becomes this pad, new net label or None to keep)
# Ball comments are the final balls, as in vivado/asar_feather_pins.xdc: the schematic netlist holds them, this
# table does not. The XADC net names AIN15_P/N and AIN16_P/N are inherited and do not match the channel numbers:
# the balls are AD4 and AD12 (Datasheet/xc7a35tcpg236pkg_pinout.txt); AD15 is on SDRAM balls N2/N1, and the
# package has no AD16.
FEATHER = {
    1: ('RST', 23, None),           # RST# = FPGA PROGRAM_B: pressing RST reloads the FPGA
    2: ('3V3', 18, None),           # VCC3V3
    3: ('AREF', 17, 'AREF'),        # no Artix equivalent: a one-pin net, left open
    4: ('GND', 1, None),
    5: ('A0', 39, None),            # ANALOG-IO0 -> R10/R11 divider -> XADC AD4 (U1 G3/G2, nets AIN15_P/N)
    6: ('A1', 40, None),            # ANALOG-IO1 -> R14/R15 divider -> XADC AD12 (U1 H2/J2, nets AIN16_P/N)
    7: ('A2', 3, None),             # CHAN0  U1-A18 (digital only)
    8: ('A3', 4, None),             # CHAN1  U1-B18
    9: ('A4', 5, None),             # CHAN2  U1-C17
    10: ('A5', 6, None),            # CHAN3  U1-B17
    11: ('SCK', 7, None),           # CHAN4  U1-C15
    12: ('MOSI', 8, None),          # CHAN5  U1-C16
    13: ('MISO', 9, None),          # CHAN6  U1-D17
    14: ('RX', 10, None),           # CHAN7  U1-G17
    15: ('TX', 11, None),           # CHAN8  U1-H17
    16: ('D4', 2, None),            # CHAN-CLK U1-P18 (clock-capable)
    17: ('VBAT', 20, 'VBATT'),      # was VCC1V0
    18: ('EN', 22, 'EN'),           # was VU; EN now drives the three SC189 enables
    19: ('VUSB', 19, 'USB5V0'),     # was VCC1V8
    20: ('D13', 24, None),          # CHAN14 U1-J19
    21: ('D12', 25, None),          # CHAN15 U1-R19
    22: ('D11', 26, None),          # CHAN16 U1-W14
    23: ('D10', 27, None),          # CHAN17 U1-U16
    24: ('D9', 28, None),           # CHAN18 U1-W15
    25: ('D6', 29, None),           # CHAN19 U1-V14
    26: ('D5', 30, None),           # CHAN20 U1-V13
    27: ('SCL', 31, None),          # CHAN21 U1-U15
    28: ('SDA', 32, None),          # CHAN22 U1-U14
}
X2_OLD_TO_NEW = {old: pad for pad, (_, old, _) in FEATHER.items()}
X2_DROPPED = sorted(set(range(1, 41)) - set(X2_OLD_TO_NEW))   # 12-16 (CHAN9-13), 21 (GND), 33-38 (CHAN23-28)

# TSOP-II-54 pin -> 54-ball FBGA ball, from the AS4C32M16SB datasheet Rev 1.2 Figures 1 and 1.1
# (JEDEC x16 SDRAM ball-out; columns 4-6 depopulated). Same-name supply pins are interchangeable.
SDRAM_BALL = {
    1: 'A9', 2: 'A8', 3: 'A7', 4: 'B9', 5: 'B8', 6: 'A3', 7: 'C9', 8: 'C8', 9: 'B3', 10: 'D9',
    11: 'D8', 12: 'B7', 13: 'E9', 14: 'E7', 15: 'E8', 16: 'F9', 17: 'F7', 18: 'F8', 19: 'G9', 20: 'G7',
    21: 'G8', 22: 'H9', 23: 'H7', 24: 'H8', 25: 'J8', 26: 'J7', 27: 'J9', 28: 'J1', 29: 'J3', 30: 'J2',
    31: 'H3', 32: 'H2', 33: 'H1', 34: 'G3', 35: 'G2', 36: 'G1', 37: 'F3', 38: 'F2', 39: 'F1', 40: 'E2',
    41: 'E3', 42: 'E1', 43: 'C7', 44: 'D2', 45: 'D1', 46: 'C3', 47: 'C2', 48: 'C1', 49: 'D3', 50: 'B2',
    51: 'B1', 52: 'D7', 53: 'A2', 54: 'A1',
}

# New footprints (to be drawn into asar_feather.PcbLib)
FOOTPRINT = {
    'U3': 'FBGA-54-8X8-P0.8',
    'U2': 'QFN-64-9X9-P0.5-EP4.35',
    'U4': 'WSON-8-6X5-P1.27',
    'U10': 'TDFN-8-2X3-P0.5',
    'X1': 'USB-C-HRO-TYPE-C-31-M-12',
    'X2': 'FEATHER-28',
    'JP3': 'TP-1X03-SMD',
    'JP4': 'TP-1X03-SMD',
}

# U10 (FT2232H config EEPROM) and its pull-ups R96/R98 were removed on 2026-10-23 and RESTORED the same day in the
# 2x3 mm TDFN: without it Vivado cannot use the bridge (program_ftdi needs an EEPROM), there is no USB serial
# number, and the chip declares only the default bus power.
REMOVED = ['J1', 'R29', 'R30', 'R31', 'R32', 'R33']

# Pmod series resistors kept and re-used: ref -> (pin1 net, pin2 net, value, MANF#)
REUSED = {
    'R26': ('VU', 'EN', '100k', 'RC0201FR-07100KL'),         # EN pull-up: board on unless EN is grounded
    'R27': ('GND', 'USB-CC1', '5.1k', 'RC0201FR-075K1L'),     # USB-C sink Rd on CC1
    'R28': ('GND', 'USB-CC2', '5.1k', 'RC0201FR-075K1L'),     # USB-C sink Rd on CC2
}

# X1 symbol pins: micro-B ID pin becomes CC1, shell pin MH1 becomes CC2, MS1/MS2 go (the USB-C part has
# six GND contacts: 4 shell tabs + 2 GND pads)
X1_PINS = {'4': ('CC1', 'USB-CC1'), 'MH1': ('CC2', 'USB-CC2')}
X1_DROPPED_PINS = ['MS1', 'MS2']

# Nets left with a single pin by the removals: their labels and stubs are deleted and the pin gets a no-ERC
# mark (tools/clear_single_pin_nets.py). AREF keeps its label (it names a Feather pin) and only gets the mark.
CLEARED_NETS = ['CHAN9', 'CHAN10', 'CHAN11', 'CHAN12', 'CHAN13', 'CHAN23', 'CHAN24', 'CHAN25', 'CHAN26', 'CHAN27',
                'CHAN28', 'JA1', 'JA2', 'JA3', 'JA4', 'JA7', 'JA8', 'JA9', 'JA10']
NO_ERC_ONLY = ['AREF']

PARAMS = {
    'U3': {'MANF#': 'AS4C32M16SB-7BIN', 'Comment': 'AS4C32M16SB-7BIN',
           'NOTE': '512Mbit (32M x 16) = 64MB, 54-ball FBGA 8 x 8 mm, 0.8 mm pitch, industrial. Same die as the '
                   'TSOP-II AS4C32M16SB-7TCN; ball map from datasheet Rev 1.2 Figure 1.1 (JEDEC x16).'},
    'U2': {'MANF#': 'FT2232HQ-REEL', 'Comment': 'FT2232HQ USB-UART/JTAG Bridge', 'DeviceName': '-QFN64',
           'SPEC': 'USB 2.0 Hi-Speed dual-channel UART/FIFO/MPSSE bridge, QFN-64 9 x 9 mm, 0.5 mm pitch, '
                   '4.35 mm exposed pad (not internally grounded; left without a net). Same pin numbers as FT2232HL.'},
    'U4': {'MANF#': 'W25Q128JVPIQ', 'Comment': 'W25Q128JVPIQ'},
    'U10': {'MANF#': '93LC46BT-I/MNY', 'Comment': '93LC46BT-I/MNY', 'DeviceName': '-I/MNY'},
    'X1': {'MANF': 'HRO (Korean Hroparts)', 'MANF#': 'TYPE-C-31-M-12',
           'Comment': 'USB-C receptacle, USB 2.0 (LCSC C165948)'},
    'X2': {'Comment': 'Feather headers: 1x16 + 1x12, 0.1 in'},
    'JP3': {'Comment': 'JTAG TCK/TMS/GND test pads'},
    'JP4': {'Comment': 'JTAG TDI/TDO/3V3 test pads'},
}

# Parts added on the Feather (not on the production board): (ref, pin) -> net. RESET = hardware reset button,
# a second PTS810 from RST# (FPGA PROGRAM_B) to GND, 2026-10-23 (tools/add_reset_button.py).
# X5 = STEMMA QT connector, JST SH 4-pin, on the Feather I2C pins, 2026-11-06 (tools/add_stemma_qt.py).
ADDED_PINS = {('RESET', '1'): 'RST#', ('RESET', '2'): 'RST#', ('RESET', '3'): 'GND', ('RESET', '4'): 'GND',
              ('X5', '1'): 'GND', ('X5', '2'): 'VCC3V3', ('X5', '3'): 'CHAN22', ('X5', '4'): 'CHAN21',
              ('X5', 'MP1'): 'GND', ('X5', 'MP2'): 'GND'}
