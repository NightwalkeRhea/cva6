  .option norvc
  .globl main

main:
  li s0, 0x11111111
  li s1, 0x22222222
  li s3, 0x33333333
  li s4, 0x44444444
  la s6, forwarding_sink

  # Each store consumes the immediately preceding ALU result. A store cannot
  # use the ALU-to-ALU bypass, so resolution uses scoreboard/writeback data.
  # 64 groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    add t0, s0, s1
    sw  t0, 0(s6)
    add t2, s3, s4
    sw  t2, 4(s6)
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  lw t3, 4(s6)
  li t4, 0x77777777
  bne t3, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit

  .section .data
  .align 2
forwarding_sink:
  .word 0
  .word 0
