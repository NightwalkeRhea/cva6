  .option norvc
  .globl main

main:
  li s0, 0x11111111
  li s1, 0x22222222
  la s2, wrap_target_sink

  # Shift the circular allocation position without changing the payload budget.
  # The measured non-wrapped control starts its producer at scoreboard entry 3.
  # Four extra allocations move that producer to entry 7, just before wraparound.
  .rept 4
    addi x0, x0, 0
  .endr

  # Use the same 256-instruction payload as wrap_pair_early.
  # Only the pre-payload scoreboard alignment is intentionally different.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 32
    add  t0, s0, s1     # Create the producer at the aligned circular position.
    sw   t0, 0(s2)      # Consume it after the issue pointer wraps to entry 0.
    addi x0, x0, 0      # Pad the group without adding another dependency.
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  # Confirm that alignment changes only internal state, not program behavior.
  lw t1, 0(s2)
  li t2, 0x33333333
  bne t1, t2, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit

  .section .data
  .align 2
wrap_target_sink:
  .word 0
