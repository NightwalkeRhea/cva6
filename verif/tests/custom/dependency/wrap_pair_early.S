  .option norvc
  .globl main

main:
  li s0, 0x11111111
  li s1, 0x22222222
  la s2, wrap_early_sink

  # Use the same instruction mix as wrap_pair_late, but move the pair first.
  # Repeating eight instructions preserves this different circular position.
  # 32 groups x 8 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 32
    add  t0, s0, s1     # Create the producer near the start of the group.
    sw   t0, 0(s2)      # Consume it through scoreboard/writeback forwarding.
    addi x0, x0, 0      # Pad the group without adding another dependency.
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  # Confirm that reordering the group did not change its architectural result.
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
wrap_early_sink:
  .word 0
