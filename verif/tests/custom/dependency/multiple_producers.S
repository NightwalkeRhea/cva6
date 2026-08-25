  .option norvc
  .globl main

main:
  # A long divide remains live while a newer load overwrites the same t0.
  la s0, multiple_producer_data
  li s1, 7
  li s2, 1000
  li s3, 1

  # Keep two same-register producers live before reading the newest t0.
  # 64 groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    div  t0, s2, s1     # Keep an older producer alive for several cycles.
    lw   t0, 4(s0)      # Overwrite t0 with a newer load producer.
    add  t1, t0, s3     # The RAW checker must choose the newest producer.
    addi x0, x0, 0      # Keep every group at exactly four instructions.
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  # The consumer must observe the second load, not the older first load.
  li t4, 0x22222223
  bne t1, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit

  .section .data
  .align 2
multiple_producer_data:
  .word 0
  .word 0x22222222
