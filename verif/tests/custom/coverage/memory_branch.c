#include <stdint.h>

static volatile uint32_t values[64];

int main(void) {
  uint32_t sum = 0;

  for (uint32_t i = 0; i < 64; ++i) {
    values[i] = 3u * i + 1u;
  }

  for (uint32_t i = 0; i < 64; ++i) {
    if ((i & 1u) == 0u) {
      sum += values[i];
    } else {
      sum += values[i] - 1u;
    }
  }

  return sum == 6080u ? 0 : 1;
}
