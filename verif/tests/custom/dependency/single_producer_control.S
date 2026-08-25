  .option norvc
  .globl main

main:
  # Match the treatment's operations but give the divider a different result register.
  la s0, single_producer_data
  li s1, 7
  li s2, 1000
  li s3, 1

  # Only the load writes t0, so the consumer has one matching producer.
  # The treatment changes the divider destination from t2 to t0.
  # 64 groups x 4 instructions = 256 payload instructions.
  .globl dependency_payload_start
dependency_payload_start:
  .rept 64
    div  t2, s2, s1     # Keep the same divider activity without writing t0.
    lw   t0, 4(s0)      # Create the single live producer for t0.
    add  t1, t0, s3     # Consume the load result.
    addi x0, x0, 0      # Keep the instruction budget and ordering identical.
  .endr
  .globl dependency_payload_end
dependency_payload_end:

  # Check the same architectural result as multiple_producers.S.
  li t4, 0x22222223
  bne t1, t4, fail
  li a0, 0
  jal exit

fail:
  li a0, 1
  jal exit

  .section .data
  .align 2
single_producer_data:
  .word 0
  .word 0x22222222
