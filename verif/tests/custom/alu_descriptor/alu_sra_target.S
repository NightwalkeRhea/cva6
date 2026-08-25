  .option norvc
  .globl main

  # Exercise every 32-bit SRA shift amount twice for one source value.
  .macro SRA_SWEEP
    srai t1, t0, 0
    srai t1, t0, 1
    srai t1, t0, 2
    srai t1, t0, 3
    srai t1, t0, 4
    srai t1, t0, 5
    srai t1, t0, 6
    srai t1, t0, 7
    srai t1, t0, 8
    srai t1, t0, 9
    srai t1, t0, 10
    srai t1, t0, 11
    srai t1, t0, 12
    srai t1, t0, 13
    srai t1, t0, 14
    srai t1, t0, 15
    srai t1, t0, 16
    srai t1, t0, 17
    srai t1, t0, 18
    srai t1, t0, 19
    srai t1, t0, 20
    srai t1, t0, 21
    srai t1, t0, 22
    srai t1, t0, 23
    srai t1, t0, 24
    srai t1, t0, 25
    srai t1, t0, 26
    srai t1, t0, 27
    srai t1, t0, 28
    srai t1, t0, 29
    srai t1, t0, 30
    srai t1, t0, 31
  .endm

main:
  # Four negative bit patterns x two sweeps x 32 shifts = 256 SRA operations.
  li t0, 0x80000000
  SRA_SWEEP
  SRA_SWEEP
  li t0, 0x80000001
  SRA_SWEEP
  SRA_SWEEP
  li t0, 0xffffffff
  SRA_SWEEP
  SRA_SWEEP
  li t0, 0xf000000f
  SRA_SWEEP
  SRA_SWEEP

  # The final operation must sign-extend the negative input to all ones.
  li t2, -1
  bne t1, t2, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit
