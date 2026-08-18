#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
out_dir="${1:-$repo_root/fi-results/milestone3-coverage}"
elf_dir="$out_dir/elf"
raw_dir="$out_dir/raw"
report_dir="$out_dir/annotated"

: "${RISCV_CC:?Run 'source ~/.bashrc && cva6-research-env' first}"
: "${SPIKE_INSTALL_DIR:?Run 'source ~/.bashrc && cva6-research-env' first}"
: "${NUM_JOBS:=8}"

mkdir -p "$elf_dir" "$raw_dir" "$report_dir"

common_sources=(
  "$repo_root/verif/tests/custom/common/syscalls.c"
  "$repo_root/verif/tests/custom/common/crt.S"
)
common_flags=(
  -static
  -mcmodel=medany
  -fvisibility=hidden
  -nostdlib
  -nostartfiles
  -g
  -march=rv32imc_zba_zbb_zbs_zbc_zicsr_zifencei
  -mabi=ilp32
  -I"$repo_root/verif/tests/custom/env"
  -I"$repo_root/verif/tests/custom/common"
  -T"$repo_root/config/gen_from_riscv_config/cv32a65x/linker/link.ld"
)

tests=(
  "return0:$repo_root/verif/tests/custom/return0/return0.c"
  "hello_world:$repo_root/verif/tests/custom/hello_world/hello_world.c"
  "memory_branch:$repo_root/verif/tests/custom/coverage/memory_branch.c"
  "pmp_granularity:$repo_root/verif/tests/custom/pmp/granularity_test.S"
)

for entry in "${tests[@]}"; do
  name="${entry%%:*}"
  source_file="${entry#*:}"
  "$RISCV_CC" "$source_file" "${common_sources[@]}" "${common_flags[@]}" \
    -lgcc -o "$elf_dir/$name.elf"
done

if [[ "${CVA6_COVERAGE_SKIP_BUILD:-0}" != 1 ]]; then
  make -C "$repo_root" COVERAGE=1 target=cv32a65x verilate
fi

simulator="$repo_root/work-ver/Variane_testharness"
config_file="$repo_root/config/gen_from_riscv_config/cv32a65x/spike/spike.yaml"
coverage_files=()
for entry in "${tests[@]}"; do
  name="${entry%%:*}"
  elf_file="$elf_dir/$name.elf"
  coverage_file="$raw_dir/$name.dat"
  coverage_files+=("$coverage_file")
  echo "Running $name"
  (
    cd "$out_dir"
    CVA6_COVERAGE_FILE="$coverage_file" \
      "$simulator" "$elf_file" +debug_disable=1 \
      "++$elf_file" \
      +elf_file="$elf_file" \
      +core_name=cv32a65x \
      +config_file="$config_file" \
      +tohost_addr=80001000 \
      +signature="$elf_file.signature_output" \
      >"$name.stdout.log" 2>"$name.stderr.log"
  )
done

coverage_tool="$VERILATOR_INSTALL_DIR/bin/verilator_coverage"
"$coverage_tool" --write "$out_dir/merged.dat" "${coverage_files[@]}"
"$coverage_tool" --write-info "$out_dir/merged.info" "${coverage_files[@]}"
"$coverage_tool" --annotate-all --annotate "$report_dir" "$out_dir/merged.dat"
python3 "$repo_root/verif/coverage/summarize_lcov.py" \
  "$out_dir/merged.info" "$out_dir/module-line-coverage.csv"

printf 'Coverage data: %s\n' "$out_dir/merged.dat"
printf 'LCOV data:     %s\n' "$out_dir/merged.info"
printf 'Annotations:   %s\n' "$report_dir"
printf 'Module table:  %s\n' "$out_dir/module-line-coverage.csv"
