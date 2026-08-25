  .option norvc
  .globl main

main:
  # Use the same registers and operations as older_producer.S.
  li s1, 7
  li s2, 1000
  li s3, 0x13579bdf
  li s4, 1

  # Consume the divider result immediately, then run the independent work.
  # Reordering only these instructions is the producer-age intervention.
  # 64 groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    div t0, s2, s1      # Create the same long-latency producer as the treatment.
    add t1, t0, s4      # Consume the producer while it is still the newest entry.
    add t2, s2, s3      # Perform the same independent work after the consumer.
    xor t3, s2, s3
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  # Check the same architectural result as older_producer.S.
  li t4, 143
  bne t1, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit
