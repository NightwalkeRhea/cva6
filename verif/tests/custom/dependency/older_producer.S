  .option norvc
  .globl main

main:
  # Give the divider stable operands and keep one register for the final add.
  li s1, 7
  li s2, 1000
  li s3, 0x13579bdf
  li s4, 1

  # Keep a divider producer live while two younger ALU instructions issue.
  # 64 groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    div t0, s2, s1      # Create a long-latency producer for t0.
    add t2, s2, s3      # Advance the scoreboard without reading t0.
    xor t3, s2, s3      # Advance it once more before the consumer.
    add t1, t0, s4      # Consume t0 after the independent instructions.
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  # Check the final consumer result so the program remains self-testing.
  li t4, 143
  bne t1, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit
