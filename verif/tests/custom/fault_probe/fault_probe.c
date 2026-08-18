#include <stdint.h>

int main(void) {
  uint32_t result;

  __asm__ volatile(
      "li t0, 2\n\t"
      "li t1, 3\n\t"
      "add %0, t0, t1\n\t"
      : "=r"(result)
      :
      : "t0", "t1");

  return result == 5u ? 0 : 1;
}
