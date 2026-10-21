#!/usr/bin/env python3
"""Build equal-SM packed/spread experiment sets from an existing T10 RM CSV.

CPU-only. This does not create CUDA/Green resources or establish NUMA domains.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED = {0: 10, 1: 12, 2: 12, 3: 10, 5: 12}
COLUMNS = (
    'global_logical_sm', 'logical_gpc', 'physical_gpc',
    'logical_local_tpc', 'logical_local_sm', 'global_logical_tpc',
)


def load_topology(path: Path) -> list[dict[str, int]]:
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing RM CSV columns: {sorted(missing)}')
        rows = [{k: int(raw[k]) for k in COLUMNS} for raw in reader]
    validate_topology(rows)
    return rows


def validate_topology(rows: list[dict[str, int]]) -> None:
    if len(rows) != 56 or len({r['global_logical_sm'] for r in rows}) != 56:
        raise ValueError('Expected exactly 56 distinct current SM entries; do not use an old map silently.')
    if any(any(v < 0 for v in r.values()) for r in rows):
        raise ValueError('Negative identifiers are not supported.')
    counts = dict(Counter(r['physical_gpc'] for r in rows))
    if counts != EXPECTED:
        raise ValueError(f'T10 configuration changed: observed {counts}; expected {EXPECTED}.')
    tpcs: dict[int, list[dict[str, int]]] = defaultdict(list)
    for row in rows:
        tpcs[row['global_logical_tpc']].append(row)
    if len(tpcs) != 28:
        raise ValueError('Expected 28 enabled TPC objects.')
    local_ids: set[tuple[int, int]] = set()
    for tpc, rr in tpcs.items():
        if len(rr) != 2 or {r['logical_local_sm'] for r in rr} != {0, 1}:
            raise ValueError(f'TPC {tpc} does not contain one SM0 and one SM1.')
        identity = {(r['physical_gpc'], r['logical_local_tpc'], r['logical_gpc']) for r in rr}
        if len(identity) != 1:
            raise ValueError(f'Conflicting GPC/local-TPC membership for TPC {tpc}.')
        key = (rr[0]['physical_gpc'], rr[0]['logical_local_tpc'])
        if key in local_ids:
            raise ValueError(f'Duplicate GPC/logical-TPC identity {key}.')
        local_ids.add(key)


def build_plan(rows: list[dict[str, int]]) -> dict[str, Any]:
    validate_topology(rows)
    all_sms = set(r['global_logical_sm'] for r in rows)
    tpc_rows: dict[int, list[dict[str, int]]] = defaultdict(list)
    for row in rows:
        tpc_rows[row['global_logical_tpc']].append(row)
    by_gpc: dict[int, list[dict[str, Any]]] = defaultdict(list)
    units = []
    for tpc, rr in sorted(tpc_rows.items()):
        unit = {
            'global_logical_tpc': tpc,
            'physical_gpc': rr[0]['physical_gpc'],
            'logical_local_tpc': rr[0]['logical_local_tpc'],
            'sm_ids': sorted(r['global_logical_sm'] for r in rr),
        }
        units.append(unit)
        by_gpc[unit['physical_gpc']].append(unit)
    for g in by_gpc:
        by_gpc[g].sort(key=lambda x: (x['logical_local_tpc'], x['global_logical_tpc']))
    active = sorted(by_gpc)

    def placement(name: str, family: str, us: list[dict[str, Any]]) -> dict[str, Any]:
        sms = sorted(s for u in us for s in u['sm_ids'])
        if len(sms) != 10 or len(set(sms)) != 10:
            raise ValueError(f'{name} is not a ten-SM placement.')
        return {
            'name': name, 'family': family,
            'global_logical_tpcs': [u['global_logical_tpc'] for u in us],
            'physical_gpcs': sorted({u['physical_gpc'] for u in us}),
            'foreground_sm_ids': sms,
            'background_complement_sm_ids': sorted(all_sms - set(sms)),
            'construction_only_not_verified_cuda_resource': True,
        }

    blocks = []
    for block in range(6):
        chosen: dict[int, list[dict[str, Any]]] = {}
        omitted = []
        for g in active:
            us = by_gpc[g]
            if len(us) == 6:
                omitted.append(us[block % 6])
                chosen[g] = [u for i, u in enumerate(us) if i != block % 6]
            else:
                chosen[g] = us[:]
        packed = [placement(f'PACK_G{g}', 'PACK', chosen[g]) for g in active]
        spread = [placement(f'SPREAD_{j}', 'SPREAD', [chosen[g][j] for g in active]) for j in range(5)]
        pack_count = Counter(s for p in packed for s in p['foreground_sm_ids'])
        spread_count = Counter(s for p in spread for s in p['foreground_sm_ids'])
        if pack_count != spread_count or len(pack_count) != 50 or set(pack_count.values()) != {1}:
            raise ValueError('Packed/spread member exposure is not exactly matched.')
        order = []
        for j in range(5):
            i = (j + block) % 5
            pair = [packed[i]['name'], spread[i]['name']]
            order.extend(pair if block % 2 == 0 else reversed(pair))
        neutral = placement('NEUTRAL10_46', 'NEUTRAL', units[:5])
        aliases = [p['name'] for p in packed + spread if p['foreground_sm_ids'] == neutral['foreground_sm_ids']]
        blocks.append({
            'block': block,
            'omitted_tpcs_in_12SM_GPCs': omitted,
            'pool_50_sms': sorted(pack_count),
            'six_sms_not_in_equal_quota_family': sorted(all_sms-set(pack_count)),
            'placements': packed + spread,
            'interleaved_order': order,
            'neutral': neutral,
            'neutral_same_set_as': aliases,
        })
    return {
        'version': '20261019-gpc-contention',
        'status': 'CPU_CONSTRUCTION_ONLY_NO_GPU_CONTROL_OR_PERFORMANCE_VALIDATION',
        'index_semantics': 'TPC IDs are logical identifiers from RM, not physical mask bit positions.',
        'all_sm_ids': sorted(all_sms),
        'physical_gpc_sm_counts': {str(g): EXPECTED[g] for g in active},
        'active_physical_gpcs': active,
        'blocks': blocks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    rows = load_topology(args.csv)
    plan = build_plan(rows)
    plan['input_csv_sha256'] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    plan['input_csv'] = str(args.csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'Wrote {args.out}: six blocks, 10 equal-quota sets/block, 10+46 complements.')


if __name__ == '__main__':
    main()
