#!/usr/bin/env python3
"""CPU-only resource plan generator. Does NOT bind SMs or call CUDA.

Input: current RM-derived SM_TO_GPC_TPC.csv. IDs are runtime identities,
not physical distances. All generated sets require GPU-side qualification.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

QUOTAS = (10, 20, 28, 36, 46)
EXPECTED_COUNTS = {0: 10, 1: 12, 2: 12, 3: 10, 5: 12}
FAMILIES = ("NEUTRAL", "PACK", "SPREAD")


def rotate(values: list, offset: int) -> list:
    if not values:
        return []
    offset %= len(values)
    return values[offset:] + values[:offset]


def read_topology(path: Path) -> list[dict[str, int]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"global_logical_sm", "physical_gpc", "logical_local_tpc"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing CSV columns: {sorted(required-set(reader.fieldnames or []))}")
        rows = [{name: int(row[name]) for name in required} for row in reader]
    if len(rows) != 56 or len({r['global_logical_sm'] for r in rows}) != 56:
        raise ValueError("Expected 56 unique SMs; do not silently adapt a changed device.")
    counts: dict[int, int] = defaultdict(int)
    tpcs: dict[tuple[int, int], list[int]] = defaultdict(list)
    for row in rows:
        counts[row["physical_gpc"]] += 1
        tpcs[(row["physical_gpc"], row["logical_local_tpc"])].append(row["global_logical_sm"])
    if dict(counts) != EXPECTED_COUNTS:
        raise ValueError(f"Topology changed: {dict(counts)}; expected {EXPECTED_COUNTS}.")
    if len(tpcs) != 28 or any(len(v) != 2 for v in tpcs.values()):
        raise ValueError("Expected 28 TPCs with exactly two exposed SMs each.")
    return rows


def make_plans(rows: list[dict[str, int]], blocks: int = 8) -> list[dict]:
    if blocks < 1:
        raise ValueError("blocks must be positive")
    tpcs: dict[tuple[int, int], list[int]] = defaultdict(list)
    for row in rows:
        tpcs[(row["physical_gpc"], row["logical_local_tpc"])].append(row["global_logical_sm"])
    all_sms = {r["global_logical_sm"] for r in rows}
    if len(all_sms) != 56 or len(tpcs) != 28 or any(len(v) != 2 for v in tpcs.values()):
        raise ValueError("Invalid topology; use read_topology() to validate input.")
    gids = sorted({g for g, _ in tpcs})
    by_gpc = {g: sorted([key for key in tpcs if key[0] == g], key=lambda k: k[1]) for g in gids}
    neutral = sorted(tpcs, key=lambda key: min(tpcs[key]))
    output = []
    for block in range(blocks):
        order_g = rotate(gids, block)
        lists = {g: rotate(by_gpc[g], block) for g in gids}
        orders = {
            "NEUTRAL": rotate(neutral, block),
            "PACK": [key for g in order_g for key in lists[g]],
            "SPREAD": [lists[g][j] for j in range(max(map(len, lists.values())))
                       for g in order_g if j < len(lists[g])],
        }
        for quota in QUOTAS:
            seen = {}
            for family in FAMILIES:
                fg_keys = orders[family][:quota // 2]
                fg = sorted(sm for key in fg_keys for sm in tpcs[key])
                bg = sorted(all_sms - set(fg))
                if len(fg) != quota or len(bg) != 56-quota or set(fg) & set(bg):
                    raise AssertionError("Partition failed exact cover")
                marker = tuple(fg)
                alias = seen.get(marker)
                seen.setdefault(marker, family)
                counts = {str(g): sum(len(tpcs[k]) for k in fg_keys if k[0] == g) for g in gids}
                output.append({
                    "block": block,
                    "cohort": "development" if block < 2 else "confirmation",
                    "family": family,
                    "foreground_sms": quota,
                    "background_sms": 56-quota,
                    "foreground_tpcs": [[g, t] for g, t in fg_keys],
                    "foreground_sm_ids": fg,
                    "background_sm_ids": bg,
                    "foreground_gpc_counts": counts,
                    "same_set_as_family": alias,
                    "qualification": "UNVERIFIED_REQUIRES_ACTUAL_RESOURCE_ROSTER",
                })
    return output


def choose_prefix(fg32_us: float, bg_total_us: float) -> int:
    """One frozen prefix rule; isolated times are proxies, NOT a concurrency model."""
    if not all(math.isfinite(x) and x > 0 for x in (fg32_us, bg_total_us)):
        raise ValueError("Both isolated times must be finite and positive")
    return max(1, min(31, math.floor(32.0 * bg_total_us / fg32_us + 0.5)))


def graph_schedule(prefix: int, background_calls: int) -> dict:
    if not 1 <= prefix <= 31 or background_calls < 1:
        raise ValueError("Invalid prefix/background call count")
    nodes = {
        "FG_PREFIX": {"requests": list(range(prefix)), "resource": "FOREGROUND_PARTITION"},
        "BG_ALL": {"requests": list(range(background_calls)), "resource": "BACKGROUND_PARTITION"},
        "FG_REMAINDER": {"requests": list(range(prefix, 32)), "resource": "PRIMARY56"},
    }
    return {"nodes": nodes,
            "edges": [["FG_PREFIX", "FG_REMAINDER"], ["BG_ALL", "FG_REMAINDER"]],
            "runtime_cpu_waits_before_final_join": 0,
            "new_gpu_scheduler_kernels": 0,
            "status": "CPU_DAG_SPEC_NOT_A_CUDA_IMPLEMENTATION"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=8)
    args = parser.parse_args()
    rows = read_topology(args.csv)
    plans = make_plans(rows, args.blocks)
    result = {"status": "CPU_DESIGN_ONLY", "input_sha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
              "total_sms": 56, "quotas": QUOTAS, "plans": plans,
              "limitation": "Rotations do not guarantee equal per-family member exposure at every quota. Report actual identities; do not claim pure topology causality."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(plans)} CPU plans; CUDA placement not performed.")

if __name__ == "__main__":
    main()
