  .option norvc
  .globl main

main:
  li s0, 0x11111111
  li s1, 0x22222222
  li s2, 0x33333333
  li s3, 0x44444444

  # 64 independent groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    add t0, s0, s1
    add t1, s2, s3
    xor t2, s0, s2
    or  t3, s1, s3
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  li t4, 0x33333333
  bne t0, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit
