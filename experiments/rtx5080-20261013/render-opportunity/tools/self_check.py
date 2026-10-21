#!/usr/bin/env python3
"""Scientific analysis checks on explicitly synthetic CPU fixtures, never GPU evidence."""
import argparse
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import time
import unittest

from analyze import AFFINITY_FIELDS, analyze_affinity, analyze_sessions, lifecycle


def affinity_fixture(mode):
    rng = random.Random(20261013)
    rows = []
    smids = [0, 3, 11, 24, 38, 57, 63, 79]
    for split in ["calibration", "validation"]:
        for dispatch in range(8):
            for i, smid in enumerate(smids):
                for r in range(8):
                    row_bias = (i - 3.5) * 2
                    address_bias = -35 if r < 4 else 35
                    interaction = 25 * (1 if i < 4 else -1) * (1 if r < 4 else -1)
                    if mode == "separable":
                        interaction = 0
                    if mode == "reversed" and split == "validation":
                        interaction *= -1
                    value = 120 + row_bias + address_bias + interaction + rng.uniform(-0.4, 0.4)
                    rows.append({"gpu_uuid": "SYNTHETIC_NO_GPU", "driver_version": "NONE",
                                 "process_id": "CPU_FIXTURE", "context_id": "NONE",
                                 "allocation_generation": "SYNTHETIC_0", "allocation_base": "NONE",
                                 "allocation_range_bytes": "32768", "cache_regime": "SYNTHETIC",
                                 "load_kind": "SYNTHETIC", "workset_bytes": "32768", "epoch_id": "CPU_0",
                                 "run_id": "CPU_" + split, "split": split, "dispatch_id": str(dispatch),
                                 "smid_begin": str(smid), "smid_end": str(smid), "region_id": str(r),
                                 "region_offset_bytes": str(r * 4096), "region_span_bytes": "4096",
                                 "clock_cycles": str(value * 16), "loads": "16", "checksum_verified": "1",
                                 "source_kind": "SYNTHETIC"})
    return rows


def session_fixture():
    sessions = []
    calibration = {"B1": 11, "B2": 10, "B3": 9, "B4": 10.5, "B5": 9.5}
    measured = {"B0": 11, "B1": 11, "B2": 8, "B3": 10,
                "B4": 10.5, "B5": 9.5, "M": 9, "C": 10}
    for scene in ["SYNTHETIC_SCENE_1", "SYNTHETIC_SCENE_2"]:
        for method, value in calibration.items():
            sessions.append({"split": "calibration", "process_block": "CPU_CALIBRATION",
                             "scene": scene, "trajectory": "SYNTHETIC_CALIBRATION", "strategy": method,
                             "frame_e2e_ms": [value] * 32, "one_time_ms": 0})
        for trajectory in ["SYNTHETIC_SLOW", "SYNTHETIC_FAST"]:
            for block in range(5):
                for method, value in measured.items():
                    sessions.append({"split": "test", "process_block": f"CPU_BLOCK_{block}",
                                     "scene": scene, "trajectory": trajectory, "strategy": method,
                                     "frame_e2e_ms": [value * (1 + block * 0.01)] * 512,
                                     "one_time_ms": 100 if method == "M" else 0})
    return {"schema_version": 1, "source_kind": "SYNTHETIC",
            "frozen_primary_baseline": "B3", "sessions": sessions}


class ScientificChecks(unittest.TestCase):
    def test_additive_bimodal_addresses_are_not_affinity(self):
        m = analyze_affinity(affinity_fixture("separable"))["maps"][0]
        self.assertFalse(m["within_allocation_signal_candidate"])
        self.assertLess(m["heldout_relative_interaction"], 0.01)

    def test_independent_heldout_interaction_is_detected(self):
        result = analyze_affinity(affinity_fixture("interaction"))
        self.assertTrue(result["maps"][0]["within_allocation_signal_candidate"])
        self.assertFalse(result["automatic_E2_authorization"])
        self.assertEqual(result["evidence_role"], "CPU_SANITY_ONLY")

    def test_reversed_heldout_mapping_fails(self):
        m = analyze_affinity(affinity_fixture("reversed"))["maps"][0]
        self.assertFalse(m["within_allocation_signal_candidate"])
        self.assertLess(m["heldout_rmse_improvement_fraction"], 0)

    def test_sparse_sm_labels_and_missing_cells_not_imputed(self):
        rows = [r for r in affinity_fixture("interaction")
                if not (r["smid_begin"] == "0" and r["region_id"] == "0")]
        m = analyze_affinity(rows)["maps"][0]
        self.assertEqual(m["observed_sm_ids"], [0, 3, 11, 24, 38, 57, 63, 79])
        self.assertEqual(m["paired_cells"], 63)
        self.assertEqual(m["missing_cells"], [[0, "0"]])
        self.assertFalse(m["within_allocation_signal_candidate"])
        self.assertIsNone(m["permutation_p"])

    def test_failed_checksum_rejects_input(self):
        rows = affinity_fixture("interaction")
        rows[0]["checksum_verified"] = "0"
        with self.assertRaisesRegex(ValueError, "checksum"):
            analyze_affinity(rows)

    def test_migrated_sample_separate_from_matrix(self):
        rows = affinity_fixture("interaction")
        extra = copy.deepcopy(rows[0])
        extra["smid_end"] = "99"
        extra["dispatch_id"] = "EXTRA_MIGRATED"
        rows.append(extra)
        m = analyze_affinity(rows)["maps"][0]
        self.assertEqual(m["migrated_rows"], 1)
        self.assertEqual(m["paired_cells"], 64)
        self.assertEqual(m["minimum_dispatches_per_paired_cell_split"], 8)

    def test_overlapping_runs_and_out_of_range_rejected(self):
        rows = affinity_fixture("interaction")
        for row in rows:
            row["run_id"] = "LEAKED_SAME_RUN"
        with self.assertRaisesRegex(ValueError, "overlap"):
            analyze_affinity(rows)
        rows = affinity_fixture("interaction")
        rows[0]["region_offset_bytes"] = "32768"
        with self.assertRaisesRegex(ValueError, "outside"):
            analyze_affinity(rows)

    def test_baseline_is_calibration_choice_not_test_winner(self):
        result = analyze_sessions(session_fixture(), bootstrap_samples=200)
        self.assertEqual(result["primary_baseline_selected_on_calibration"], "B3")
        self.assertAlmostEqual(result["comparisons"]["B3"]["M_time_reduction_fraction"], 0.1)
        self.assertLess(result["comparisons"]["B2"]["M_time_reduction_fraction"], 0)
        self.assertEqual(result["block_count"], 5)
        # Preserve a mean of 9 ms while making the median 1 ms: tail work must count.
        skewed = session_fixture()
        for session in skewed["sessions"]:
            if session["split"] == "test" and session["strategy"] == "M":
                factor = 1 + int(session["process_block"].rsplit("_", 1)[1]) * 0.01
                session["frame_e2e_ms"] = [v * factor for v in [1, 1, 25] * 170 + [9, 9]]
        skewed_result = analyze_sessions(skewed, bootstrap_samples=200)
        self.assertAlmostEqual(skewed_result["comparisons"]["B3"]["M_time_reduction_fraction"], 0.1)

    def test_pairing_missing_block_rejected(self):
        document = session_fixture()
        document["sessions"].pop()
        with self.assertRaisesRegex(ValueError, "pairing incomplete"):
            analyze_sessions(document, bootstrap_samples=20)

    def test_lifecycle_no_saving_and_unmeasured_1000_frames(self):
        m = {"frame_e2e_ms": [10] * 512, "one_time_ms": 100}
        b = {"frame_e2e_ms": [9] * 512, "one_time_ms": 0}
        result = lifecycle(m, b)
        self.assertIsNone(result["break_even_frames"])
        self.assertFalse(result["N"]["1000"]["measurable"])
        self.assertIsNone(result["N"]["1000"]["M_ms"])


def save_json(path, value):
    with path.open("x") as out:
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--derived-dir", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.derived_dir.mkdir(parents=True, exist_ok=True)
    for mode in ["separable", "interaction", "reversed"]:
        rows = affinity_fixture(mode)
        with (args.raw_dir / f"SYNTHETIC_{mode}.csv").open("x", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=AFFINITY_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        save_json(args.derived_dir / f"SYNTHETIC_{mode}_analysis.json", analyze_affinity(rows))
    sessions = session_fixture()
    save_json(args.raw_dir / "SYNTHETIC_sessions.json", sessions)
    save_json(args.derived_dir / "SYNTHETIC_sessions_analysis.json", analyze_sessions(sessions))
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(ScientificChecks))
    summary = {"source_kind": "SYNTHETIC", "evidence_role": "ANALYSIS_SOFTWARE_CHECK_ONLY",
               "checks_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "success": result.wasSuccessful(), "wall_seconds": time.monotonic() - started,
               "test_log": stream.getvalue(), "GPU_kernel_count": 0,
               "fixture_generation_seed": 20261013,
               "source_sha256": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                 for name in ["analyze.py", "self_check.py"]}}
    save_json(args.derived_dir / "CPU_SELF_CHECK.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "test_log"}))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
