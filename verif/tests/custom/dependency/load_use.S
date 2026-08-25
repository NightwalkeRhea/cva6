  .option norvc
  .globl main

main:
  la s0, dependency_data
  li s1, 1
  li s2, 2

  # Each load is immediately followed by its consumer.
  # 64 groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    lw  t0, 0(s0)
    add t1, t0, s1
    lw  t2, 4(s0)
    add t3, t2, s2
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  li t4, 0x22222224
  bne t3, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit

  .section .data
  .align 2
dependency_data:
  .word 0x11111111
  .word 0x22222222
