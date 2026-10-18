#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
driver_src="$task_root/sources/open-gpu-kernel-modules-580.178.04"
gcc -std=gnu11 -O2 -Wall -Wextra -Werror \
  -I"$driver_src/src/common/sdk/nvidia/inc" \
  -I"$driver_src/src/nvidia/arch/nvalloc/unix/include" \
  "$task_root/src/read_topology.c" -o "$task_root/read_topology"
