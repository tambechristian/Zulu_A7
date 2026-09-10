`timescale 1ns/1ps
module zulu_a7_top (
  input  wire BTN,
  input  wire CHAN_CLK,
  input  wire CLK_12M_FPGA,
  input  wire FT_PWREN_N,
  input  wire UART_FT_DTR_N,
  input  wire UART_FT_RTS_N,
  input  wire UART_FT_TXD,
  output wire A0,
  output wire A1,
  output wire A10,
  output wire A11,
  output wire A12,
  output wire A2,
  output wire A3,
  output wire A4,
  output wire A5,
  output wire A6,
  output wire A7,
  output wire A8,
  output wire A9,
  output wire BS0,
  output wire BS1,
  output wire CAS_N,
  output wire CKE,
  output wire FLASH_CS_N,
  output wire LDQM,
  output wire LED0_B,
  output wire LED0_G,
  output wire LED0_R,
  output wire LED1,
  output wire LED2,
  output wire RAS_N,
  output wire SDRAM_CLK,
  output wire SDRAM_CS_N,
  output wire SD_CLK,
  output wire SD_CMD,
  output wire UART_FT_CTS_N,
  output wire UART_FT_RXD,
  output wire UDQM,
  output wire WE_N,
  inout  wire CHAN0,
  inout  wire CHAN1,
  inout  wire CHAN10,
  inout  wire CHAN11,
  inout  wire CHAN12,
  inout  wire CHAN13,
  inout  wire CHAN14,
  inout  wire CHAN15,
  inout  wire CHAN16,
  inout  wire CHAN17,
  inout  wire CHAN18,
  inout  wire CHAN19,
  inout  wire CHAN2,
  inout  wire CHAN20,
  inout  wire CHAN21,
  inout  wire CHAN22,
  inout  wire CHAN23,
  inout  wire CHAN24,
  inout  wire CHAN25,
  inout  wire CHAN26,
  inout  wire CHAN27,
  inout  wire CHAN28,
  inout  wire CHAN3,
  inout  wire CHAN4,
  inout  wire CHAN5,
  inout  wire CHAN6,
  inout  wire CHAN7,
  inout  wire CHAN8,
  inout  wire CHAN9,
  inout  wire D0,
  inout  wire D1,
  inout  wire D10,
  inout  wire D11,
  inout  wire D12,
  inout  wire D13,
  inout  wire D14,
  inout  wire D15,
  inout  wire D2,
  inout  wire D3,
  inout  wire D4,
  inout  wire D5,
  inout  wire D6,
  inout  wire D7,
  inout  wire D8,
  inout  wire D9,
  inout  wire FLASH_D00,
  inout  wire FLASH_D01,
  inout  wire FLASH_D02,
  inout  wire FLASH_D03,
  inout  wire JA1,
  inout  wire JA10,
  inout  wire JA2,
  inout  wire JA3,
  inout  wire JA4,
  inout  wire JA7,
  inout  wire JA8,
  inout  wire JA9,
  inout  wire SD_DAT0,
  inout  wire SD_DAT1,
  inout  wire SD_DAT2,
  inout  wire SD_DAT3
);
  wire sysclk, chanclk;
  BUFG u_bufg0 (.I(CLK_12M_FPGA), .O(sysclk));
  BUFG u_bufg1 (.I(CHAN_CLK),     .O(chanclk));
  reg [45:0] qa = 0;  reg oea = 0;
  reg [47:0] qb = 0;  reg oeb = 0;
  assign CHAN0 = oea ? qa[0] : 1'bz;
  assign CHAN1 = oea ? qa[1] : 1'bz;
  assign CHAN10 = oea ? qa[2] : 1'bz;
  assign CHAN11 = oea ? qa[3] : 1'bz;
  assign CHAN12 = oea ? qa[4] : 1'bz;
  assign CHAN13 = oea ? qa[5] : 1'bz;
  assign CHAN14 = oea ? qa[6] : 1'bz;
  assign CHAN15 = oea ? qa[7] : 1'bz;
  assign CHAN16 = oea ? qa[8] : 1'bz;
  assign CHAN17 = oea ? qa[9] : 1'bz;
  assign CHAN18 = oea ? qa[10] : 1'bz;
  assign CHAN19 = oea ? qa[11] : 1'bz;
  assign CHAN2 = oea ? qa[12] : 1'bz;
  assign CHAN20 = oea ? qa[13] : 1'bz;
  assign CHAN21 = oea ? qa[14] : 1'bz;
  assign CHAN22 = oea ? qa[15] : 1'bz;
  assign CHAN23 = oea ? qa[16] : 1'bz;
  assign CHAN24 = oea ? qa[17] : 1'bz;
  assign CHAN25 = oea ? qa[18] : 1'bz;
  assign CHAN26 = oea ? qa[19] : 1'bz;
  assign CHAN27 = oea ? qa[20] : 1'bz;
  assign CHAN28 = oea ? qa[21] : 1'bz;
  assign CHAN3 = oea ? qa[22] : 1'bz;
  assign CHAN4 = oea ? qa[23] : 1'bz;
  assign CHAN5 = oea ? qa[24] : 1'bz;
  assign CHAN6 = oea ? qa[25] : 1'bz;
  assign CHAN7 = oea ? qa[26] : 1'bz;
  assign CHAN8 = oea ? qa[27] : 1'bz;
  assign CHAN9 = oea ? qa[28] : 1'bz;
  assign D0 = oea ? qa[29] : 1'bz;
  assign A0 = qa[30];
  assign A1 = qa[31];
  assign A10 = qa[32];
  assign A11 = qa[33];
  assign A12 = qa[34];
  assign A2 = qa[35];
  assign A3 = qa[36];
  assign A4 = qa[37];
  assign A5 = qa[38];
  assign A6 = qa[39];
  assign A7 = qa[40];
  assign A8 = qa[41];
  assign A9 = qa[42];
  assign BS0 = qa[43];
  assign BS1 = qa[44];
  assign CAS_N = qa[45];
  assign D1 = oeb ? qb[0] : 1'bz;
  assign D10 = oeb ? qb[1] : 1'bz;
  assign D11 = oeb ? qb[2] : 1'bz;
  assign D12 = oeb ? qb[3] : 1'bz;
  assign D13 = oeb ? qb[4] : 1'bz;
  assign D14 = oeb ? qb[5] : 1'bz;
  assign D15 = oeb ? qb[6] : 1'bz;
  assign D2 = oeb ? qb[7] : 1'bz;
  assign D3 = oeb ? qb[8] : 1'bz;
  assign D4 = oeb ? qb[9] : 1'bz;
  assign D5 = oeb ? qb[10] : 1'bz;
  assign D6 = oeb ? qb[11] : 1'bz;
  assign D7 = oeb ? qb[12] : 1'bz;
  assign D8 = oeb ? qb[13] : 1'bz;
  assign D9 = oeb ? qb[14] : 1'bz;
  assign FLASH_D00 = oeb ? qb[15] : 1'bz;
  assign FLASH_D01 = oeb ? qb[16] : 1'bz;
  assign FLASH_D02 = oeb ? qb[17] : 1'bz;
  assign FLASH_D03 = oeb ? qb[18] : 1'bz;
  assign JA1 = oeb ? qb[19] : 1'bz;
  assign JA10 = oeb ? qb[20] : 1'bz;
  assign JA2 = oeb ? qb[21] : 1'bz;
  assign JA3 = oeb ? qb[22] : 1'bz;
  assign JA4 = oeb ? qb[23] : 1'bz;
  assign JA7 = oeb ? qb[24] : 1'bz;
  assign JA8 = oeb ? qb[25] : 1'bz;
  assign JA9 = oeb ? qb[26] : 1'bz;
  assign SD_DAT0 = oeb ? qb[27] : 1'bz;
  assign SD_DAT1 = oeb ? qb[28] : 1'bz;
  assign SD_DAT2 = oeb ? qb[29] : 1'bz;
  assign SD_DAT3 = oeb ? qb[30] : 1'bz;
  assign CKE = qb[31];
  assign FLASH_CS_N = qb[32];
  assign LDQM = qb[33];
  assign LED0_B = qb[34];
  assign LED0_G = qb[35];
  assign LED0_R = qb[36];
  assign LED1 = qb[37];
  assign LED2 = qb[38];
  assign RAS_N = qb[39];
  assign SDRAM_CLK = qb[40];
  assign SDRAM_CS_N = qb[41];
  assign SD_CLK = qb[42];
  assign SD_CMD = qb[43];
  assign UART_FT_CTS_N = qb[44];
  assign UART_FT_RXD = qb[45];
  assign UDQM = qb[46];
  assign WE_N = qb[47];
  always @(posedge sysclk)  begin oea <= BTN ^ FT_PWREN_N ^ UART_FT_DTR_N ^ UART_FT_RTS_N ^ UART_FT_TXD ^ CHAN0 ^ CHAN1 ^ CHAN10 ^ CHAN11 ^ CHAN12 ^ CHAN13 ^ CHAN14 ^ CHAN15 ^ CHAN16 ^ CHAN17 ^ CHAN18 ^ CHAN19 ^ CHAN2 ^ CHAN20 ^ CHAN21 ^ CHAN22 ^ CHAN23 ^ CHAN24 ^ CHAN25 ^ CHAN26 ^ CHAN27 ^ CHAN28 ^ CHAN3 ^ CHAN4 ^ CHAN5 ^ CHAN6 ^ CHAN7 ^ CHAN8 ^ CHAN9 ^ D0; qa <= {qa[44:0], oea}; end
  always @(posedge chanclk) begin oeb <= D1 ^ D10 ^ D11 ^ D12 ^ D13 ^ D14 ^ D15 ^ D2 ^ D3 ^ D4 ^ D5 ^ D6 ^ D7 ^ D8 ^ D9 ^ FLASH_D00 ^ FLASH_D01 ^ FLASH_D02 ^ FLASH_D03 ^ JA1 ^ JA10 ^ JA2 ^ JA3 ^ JA4 ^ JA7 ^ JA8 ^ JA9 ^ SD_DAT0 ^ SD_DAT1 ^ SD_DAT2 ^ SD_DAT3; qb <= {qb[46:0], oeb}; end
endmodule
