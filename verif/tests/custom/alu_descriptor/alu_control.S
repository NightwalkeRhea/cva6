  .option norvc
  .globl main

  # Eight repetitions give 32 ordinary ALU operations per sweep.
  .macro CONTROL_SWEEP
    .rept 8
      add t3, t0, t1
      and t4, t0, t1
      sll t5, t0, t2
      srl t6, t0, t2
    .endr
  .endm

main:
  li t1, 0x01010101
  li t2, 1

  # Four source patterns x two sweeps x 32 operations = 256 operations.
  li t0, 0x12345678
  CONTROL_SWEEP
  CONTROL_SWEEP
  li t0, 0x0000ffff
  CONTROL_SWEEP
  CONTROL_SWEEP
  li t0, 0x00ff00ff
  CONTROL_SWEEP
  CONTROL_SWEEP
  li t0, 0x7fffffff
  CONTROL_SWEEP
  CONTROL_SWEEP

  # Check a representative result from the final source pattern.
  and t4, t0, t1
  bne t4, t1, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit
