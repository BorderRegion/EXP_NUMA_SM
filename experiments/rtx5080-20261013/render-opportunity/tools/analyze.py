#!/usr/bin/env python3
"""Offline CPU analysis. No third-party modules. Never approves GPU/application gates."""
import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import random
import statistics as st


IDENTITY = ["gpu_uuid", "driver_version", "process_id", "context_id",
            "allocation_generation", "allocation_base", "allocation_range_bytes",
            "cache_regime", "load_kind", "workset_bytes", "epoch_id"]
AFFINITY_FIELDS = IDENTITY + ["run_id", "split", "dispatch_id", "smid_begin", "smid_end",
                             "region_id", "region_offset_bytes", "region_span_bytes",
                             "clock_cycles", "loads", "checksum_verified", "source_kind"]
BASELINES = ["B1", "B2", "B3", "B4", "B5"]


def positive(value, name):
    x = float(value)
    if not math.isfinite(x) or x <= 0:
        raise ValueError(f"{name}: expected finite positive value, got {value}")
    return x


def quantile(values, q):
    values = sorted(values)
    p = (len(values) - 1) * q
    lo, hi = math.floor(p), math.ceil(p)
    return values[lo] + (values[hi] - values[lo]) * (p - lo)


def robust_noise(values):
    median = st.median(values)
    return 1.4826 * st.median(abs(x - median) for x in values) / median


def fit_additive(cells):
    """Equal-cell least squares by coordinate descent, including sparse tables."""
    smids = sorted({s for s, _ in cells})
    regions = sorted({r for _, r in cells})
    mu = st.mean(cells.values())
    alpha = dict.fromkeys(smids, 0.0)
    beta = dict.fromkeys(regions, 0.0)
    by_s = {s: [r for ss, r in cells if ss == s] for s in smids}
    by_r = {r: [s for s, rr in cells if rr == r] for r in regions}
    # Connectivity is required for interpreting the separate row/column effects.
    reachable_s, reachable_r = {smids[0]}, set()
    while True:
        rs = {r for s in reachable_s for r in by_s[s]}
        ss = {s for r in rs for s in by_r[r]}
        if rs == reachable_r and ss == reachable_s:
            break
        reachable_r, reachable_s = rs, ss
    connected = len(reachable_s) == len(smids) and len(reachable_r) == len(regions)
    converged = False
    for _ in range(1000):
        old = [mu, *alpha.values(), *beta.values()]
        for s in smids:
            alpha[s] = st.mean(cells[s, r] - mu - beta[r] for r in by_s[s])
        shift = sum(len(by_s[s]) * alpha[s] for s in smids) / len(cells)
        mu += shift
        alpha = {s: v - shift for s, v in alpha.items()}
        for r in regions:
            beta[r] = st.mean(cells[s, r] - mu - alpha[s] for s in by_r[r])
        shift = sum(len(by_r[r]) * beta[r] for r in regions) / len(cells)
        mu += shift
        beta = {r: v - shift for r, v in beta.items()}
        if max(abs(a - b) for a, b in zip(old, [mu, *alpha.values(), *beta.values()])) < 1e-9:
            converged = True
            break
    return mu, alpha, beta, connected, converged


def analyze_map(identity, rows, permutations=199):
    launches = defaultdict(list)
    run_sets = {"calibration": set(), "validation": set()}
    ranges = {}
    migrated = 0
    observed_s, observed_r = set(), set()
    for row in rows:
        split = row["split"]
        if split not in run_sets:
            raise ValueError("split must be calibration or validation")
        run_sets[split].add(row["run_id"])
        if row["checksum_verified"] != "1":
            raise ValueError("checksum failure: entire input is unqualified")
        size = int(row["allocation_range_bytes"])
        offset, span = int(row["region_offset_bytes"]), int(row["region_span_bytes"])
        if size <= 0 or offset < 0 or span <= 0 or offset + span > size:
            raise ValueError("region outside owned allocation")
        if not 0 < int(row["workset_bytes"]) <= size:
            raise ValueError("invalid workset size")
        region = row["region_id"]
        if region in ranges and ranges[region] != (offset, span):
            raise ValueError("region identity changed within allocation")
        ranges[region] = (offset, span)
        sm, end_sm = int(row["smid_begin"]), int(row["smid_end"])
        if sm < 0 or end_sm < 0:
            raise ValueError("negative observed SM ID")
        observed_s.add(sm)
        observed_r.add(region)
        value = positive(row["clock_cycles"], "clock_cycles") / positive(row["loads"], "loads")
        if sm != end_sm:
            migrated += 1
            continue
        launches[split, sm, region, row["run_id"], row["dispatch_id"]].append(value)
    if run_sets["calibration"] & run_sets["validation"]:
        raise ValueError("calibration and validation runs overlap")
    per_cell = defaultdict(list)
    for (split, sm, region, _, _), samples in launches.items():
        per_cell[split, sm, region].append(st.median(samples))
    medians = {split: {(s, r): st.median(v) for (sp, s, r), v in per_cell.items() if sp == split}
               for split in run_sets}
    train, valid = medians["calibration"], medians["validation"]
    common = set(train) & set(valid)
    result = {"identity": dict(zip(IDENTITY, identity)), "rows": len(rows),
              "migrated_rows": migrated, "calibration_runs": sorted(run_sets["calibration"]),
              "validation_runs": sorted(run_sets["validation"]),
              "observed_sm_ids": sorted(observed_s), "observed_region_ids": sorted(observed_r),
              "train_cells": len(train), "validation_cells": len(valid), "paired_cells": len(common),
              "validation_unseen_cells": len(set(valid) - set(train)),
              "missing_cells": [[s, r] for s in sorted(observed_s) for r in sorted(observed_r)
                                if (s, r) not in common],
              "within_allocation_signal_candidate": False,
              "cross_address_generalization_proven": False, "physical_domains_proven": False}
    if len(common) < 32:
        result["screen_state"] = "INSUFFICIENT_PAIRED_CELLS"
        return result
    mu, alpha, beta, connected, converged = fit_additive(train)
    base = lambda s, r: mu + alpha[s] + beta[r]
    residual = {cell: val - base(*cell) for cell, val in train.items()}
    pairs = sorted(common)
    rmse = lambda prediction: math.sqrt(st.mean((valid[s, r] - prediction(s, r)) ** 2 for s, r in pairs))
    base_error = rmse(base)
    inter_error = rmse(lambda s, r: base(s, r) + residual[s, r])
    gain = base_error - inter_error
    rmse_improvement = gain / base_error if base_error > 1e-12 else 0.0
    region_effects = []
    for r in sorted({r for _, r in common}):
        smids = [s for s, rr in pairs if rr == r]
        if len(smids) < 2:
            continue
        best = min(smids, key=lambda s: residual[s, r])
        worst = max(smids, key=lambda s: residual[s, r])
        difference = (valid[worst, r] - alpha[worst]) - (valid[best, r] - alpha[best])
        region_effects.append(difference / st.mean([valid[worst, r], valid[best, r]]))
    relative_effect = st.median(region_effects) if region_effects else 0.0
    noise = st.median(robust_noise(v) for (sp, _, _), v in per_cell.items() if sp == "validation")
    minimum_repeats = min(len(per_cell[sp, s, r]) for s, r in common for sp in run_sets)
    smids = sorted({s for s, _ in common})
    region_ids = sorted({r for _, r in common})
    rectangle = set((s, r) for s in smids for r in region_ids)
    complete = common == rectangle and not result["missing_cells"]
    pvalue = None
    if complete:
        rng, more_extreme = random.Random(20261016), 0
        for _ in range(permutations):
            order = smids[:]
            rng.shuffle(order)
            mapping = dict(zip(smids, order))
            shuffled_error = rmse(lambda s, r: base(s, r) + residual[mapping[s], r])
            more_extreme += base_error - shuffled_error >= gain - 1e-12
        pvalue = (1 + more_extreme) / (1 + permutations)
    eligible = (connected and converged and complete and minimum_repeats >= 8
                and migrated / len(rows) <= 0.05 and result["validation_unseen_cells"] == 0)
    signal = (eligible and relative_effect >= max(0.10, 2 * noise)
              and rmse_improvement >= 0.10 and pvalue is not None and pvalue <= 0.05)
    result.update({"additive_rmse_cycles_per_load": base_error,
                   "interaction_rmse_cycles_per_load": inter_error,
                   "heldout_rmse_improvement_fraction": rmse_improvement,
                   "heldout_relative_interaction": relative_effect,
                   "validation_dispatch_relative_noise": noise,
                   "minimum_dispatches_per_paired_cell_split": minimum_repeats,
                   "complete_cross_matrix": complete, "connected": connected,
                   "additive_fit_converged": converged,
                   "permutation_count": permutations if complete else 0,
                   "permutation_p": pvalue,
                   "within_allocation_screen_eligible": eligible,
                   "within_allocation_signal_candidate": signal,
                   "screen_state": "WITHIN_ALLOCATION_SCREEN_ONLY" if eligible else "COVERAGE_OR_QUALIFICATION_UNRESOLVED",
                   "matrix": [{"sm_id": s, "region_id": r, "calibration": train[s, r],
                               "validation": valid[s, r], "calibration_residual": residual[s, r]}
                              for s, r in pairs]})
    return result


def analyze_affinity(rows):
    if not rows:
        raise ValueError("no rows")
    if any(set(AFFINITY_FIELDS) - set(row) for row in rows):
        raise ValueError("missing required affinity columns")
    kinds = {row["source_kind"] for row in rows}
    if len(kinds) != 1 or not kinds <= {"SYNTHETIC", "HARDWARE"}:
        raise ValueError("mixed/unknown source_kind")
    groups = defaultdict(list)
    for row in rows:
        if any(not str(row[k]).strip() for k in AFFINITY_FIELDS):
            raise ValueError("blank required affinity field")
        groups[tuple(row[k] for k in IDENTITY)].append(row)
    return {"schema_version": 1, "source_kind": next(iter(kinds)),
            "evidence_role": "CPU_SANITY_ONLY" if kinds == {"SYNTHETIC"} else "DESCRIPTIVE_E1_INPUT",
            "automatic_E2_authorization": False,
            "required_additional_evidence": ["three new processes/allocation epochs", "unseen address validation",
                                              "same-allocation reuse", "legal control audit", "GPU safety/manifest audit"],
            "maps": [analyze_map(key, value) for key, value in sorted(groups.items())]}


def lifecycle(m, baseline):
    saving = st.mean(baseline["frame_e2e_ms"]) - st.mean(m["frame_e2e_ms"])
    extra = float(m["one_time_ms"]) - float(baseline["one_time_ms"])
    return {"net_per_frame_saving_ms": saving, "one_time_extra_ms": extra,
            "break_even_frames": math.ceil(max(0, extra) / saving) if saving > 0 else None,
            "N": {str(n): {"measurable": len(m["frame_e2e_ms"]) >= n and len(baseline["frame_e2e_ms"]) >= n,
                           "M_ms": float(m["one_time_ms"]) + sum(m["frame_e2e_ms"][:n])
                           if len(m["frame_e2e_ms"]) >= n else None,
                           "baseline_ms": float(baseline["one_time_ms"]) + sum(baseline["frame_e2e_ms"][:n])
                           if len(baseline["frame_e2e_ms"]) >= n else None}
                  for n in [1, 100, 1000]}}


def analyze_sessions(document, bootstrap_samples=2000):
    if document.get("source_kind") not in {"HARDWARE", "SYNTHETIC"}:
        raise ValueError("sessions source_kind required")
    data, calibration = {}, []
    for session in document["sessions"]:
        split = session["split"]
        if split not in {"calibration", "test"}:
            raise ValueError("invalid session split")
        times = session["frame_e2e_ms"]
        if not times or any(positive(t, "frame_e2e_ms") != float(t) for t in times):
            raise ValueError("invalid frame data")
        cost = float(session["one_time_ms"])
        if not math.isfinite(cost) or cost < 0:
            raise ValueError("invalid one_time_ms")
        key = (split, str(session["process_block"]), session["scene"], session["trajectory"], session["strategy"])
        if key in data:
            raise ValueError("duplicate session")
        data[key] = session
        if split == "calibration":
            calibration.append(session)
    if not calibration:
        raise ValueError("calibration data missing; cannot choose baseline from test")
    calibration_units = {(str(s["process_block"]), s["scene"], s["trajectory"]) for s in calibration}
    scores = {}
    for baseline in BASELINES:
        values = defaultdict(list)
        for block, scene, trajectory in sorted(calibration_units):
            key = ("calibration", block, scene, trajectory, baseline)
            if key not in data:
                raise ValueError("calibration baseline pairing incomplete")
            values[scene, trajectory].append(math.log(st.mean(data[key]["frame_e2e_ms"])))
        scores[baseline] = st.mean(st.mean(v) for v in values.values())
    primary = min(BASELINES, key=lambda b: scores[b])
    frozen = document.get("frozen_primary_baseline")
    if frozen and frozen != primary:
        raise ValueError("frozen primary baseline disagrees with calibration choice")
    test_keys = [key for key in data if key[0] == "test"]
    blocks = sorted({key[1] for key in test_keys})
    cases = sorted({(key[2], key[3]) for key in test_keys})
    if not blocks or not cases:
        raise ValueError("no test data")
    methods = sorted({key[4] for key in test_keys})
    if "M" not in methods or not set(BASELINES) <= set(methods):
        raise ValueError("test requires M and all B1-B5")
    for block in blocks:
        for scene, trajectory in cases:
            for method in methods:
                if ("test", block, scene, trajectory, method) not in data:
                    raise ValueError("test process-block/case/method pairing incomplete")
    output = {"schema_version": 1, "source_kind": document["source_kind"],
              "primary_baseline_selected_on_calibration": primary,
              "calibration_geomean_ms": {b: math.exp(v) for b, v in scores.items()},
              "process_blocks": blocks, "block_count": len(blocks),
              "five_block_requirement_met": len(blocks) >= 5,
              "bootstrap_unit": "process_block (all cases retained together)",
              "session_statistic": "arithmetic mean of all measured end-to-end frame times",
              "case_weighting": "equal scene/trajectory cells", "comparisons": {},
              "application_qualification_proven": False}
    for method in methods:
        if method == "M":
            continue
        logs_by_block, costs = [], []
        for block in blocks:
            logs = []
            for scene, trajectory in cases:
                m = data["test", block, scene, trajectory, "M"]
                b = data["test", block, scene, trajectory, method]
                logs.append(math.log(st.mean(b["frame_e2e_ms"]) / st.mean(m["frame_e2e_ms"])))
                costs.append({"block": block, "scene": scene, "trajectory": trajectory,
                              **lifecycle(m, b)})
            logs_by_block.append(st.mean(logs))
        rng = random.Random(20261017)
        boot = [st.mean(rng.choices(logs_by_block, k=len(blocks))) for _ in range(bootstrap_samples)]
        center = st.mean(logs_by_block)
        lower, upper = quantile(boot, 0.025), quantile(boot, 0.975)
        output["comparisons"][method] = {
            "M_time_reduction_fraction": 1 - math.exp(-center),
            "bootstrap_95_interval": [1 - math.exp(-lower), 1 - math.exp(-upper)],
            "paired_log_baseline_over_M_by_block": logs_by_block,
            "lifecycle": costs}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["affinity", "sessions"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.kind == "affinity":
            with args.input.open(newline="") as f:
                result = analyze_affinity(list(csv.DictReader(f)))
        else:
            result = analyze_sessions(json.loads(args.input.read_text()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write("\n")
        print(json.dumps({"output": str(args.output), "source_kind": result["source_kind"]}))
    except (ValueError, KeyError, OSError) as e:
        parser.exit(2, f"analysis rejected: {e}\n")


if __name__ == "__main__":
    main()
