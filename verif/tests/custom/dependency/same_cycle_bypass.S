  .option norvc
  .globl main

main:
  li s0, 0x11111111
  li s1, 0x22222222
  li s2, 1
  li s3, 0x33333333
  li s4, 0x44444444
  li s5, 2

  # Adjacent consumers are candidates for the dual-issue ALU bypass.
  # 64 groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    add t0, s0, s1
    add t1, t0, s2
    add t2, s3, s4
    add t3, t2, s5
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  li t4, 0x77777779
  bne t3, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit
