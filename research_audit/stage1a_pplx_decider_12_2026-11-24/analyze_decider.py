#!/usr/bin/env python3
"""Analyze saved PPLX-Decider scores; no inherited-reference accuracy claims."""
import csv
import json
from pathlib import Path
import statistics

import numpy as np

ROOT = Path(__file__).resolve().parent
STATES = ("neither", "support_only", "opposition_only", "both")


def write_csv(name, rows):
    with (ROOT / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    rows = [json.loads(line) for line in (ROOT / "readouts.jsonl").read_text().splitlines()]
    main_rows = [r for r in rows if r["phase"] == "main"]
    reloaded = [r for r in rows if r["phase"] == "reloaded"]
    inputs = {r["case_id"]: r for r in map(json.loads, (ROOT / "inputs.jsonl").read_text().splitlines())}
    baseline = json.loads((ROOT / "baseline_vectors.json").read_text())
    groups, group_stats = {}, []
    for case in sorted(inputs):
        for order in range(4):
            key = (case, f"order_{order}")
            found = [r for r in main_rows if (r["case_id"], r["order_id"]) == key]
            if not found:
                continue
            q = np.array([[r["probabilities"][s] for s in STATES] for r in found])
            z = np.array([[r["raw_logits"][s] for s in STATES] for r in found])
            assert np.isfinite(q).all() and np.isfinite(z).all()
            assert np.min(q) >= 0 and np.allclose(q.sum(axis=1), 1, atol=1e-10, rtol=0)
            groups[key] = {"records": found, "probabilities": q, "logits": z, "mean": q.mean(axis=0)}
            group_stats.append({"case_id": case, "order_id": key[1], "repeats": len(found),
                "max_repeat_probability_range_pp": float(100 * np.ptp(q, axis=0).max()),
                "max_raw_logit_repeat_range": float(np.ptp(z, axis=0).max()),
                "distinct_probability_vectors": len({tuple(x) for x in q}),
                "distinct_raw_logit_vectors": len({tuple(x) for x in z}),
                "observed_selected_states": "/".join(sorted({r["selected_state"] for r in found})),
                **{f"mean_{s}": float(q.mean(axis=0)[j]) for j, s in enumerate(STATES)}})
    if not group_stats:
        raise RuntimeError("No main readouts to analyze")

    case_stats, order_rows, comparison = [], [], []
    for case in sorted(inputs):
        keys = [(case, f"order_{i}") for i in range(4)]
        if any(k not in groups for k in keys):
            continue
        q = np.array([groups[k]["mean"] for k in keys])
        mean = q.mean(axis=0)
        winners = [STATES[int(x.argmax())] for x in q]
        avg_winner = STATES[int(mean.argmax())]
        entry = {"case_id": case, "target_segment": inputs[case]["target_segment"],
                 "canonical_selected_state": winners[0], "mapping_mean_selected_state": avg_winner,
                 "winning_probability_of_mapping_mean": float(mean.max()),
                 "max_native_order_range_pp": float(100 * np.ptp(q, axis=0).max()),
                 "canonical_winner_probability_min_across_orders": float(q[:, STATES.index(winners[0])].min()),
                 "canonical_winner_probability_max_across_orders": float(q[:, STATES.index(winners[0])].max()),
                 "order_winners": "/".join(winners), "different_order_winners": len(set(winners)),
                 **{s: float(mean[j]) for j, s in enumerate(STATES)}}
        case_stats.append(entry)
        for i, vector in enumerate(q):
            order_rows.append({"case_id": case, "order_id": f"order_{i}", "selected_state": winners[i],
                               **dict(zip(STATES, map(float, vector)))})
        compare = {"case_id": case, "target_segment": inputs[case]["target_segment"],
                   "decider_canonical": winners[0], "decider_order_mean": avg_winner,
                   "decider_order_mean_winning_probability": float(mean.max())}
        for name, vector in baseline["cases"][case].items():
            winner = max(vector, key=vector.get)
            compare[name + "_state"] = winner
            compare[name + "_winning_probability"] = vector[winner]
        comparison.append(compare)

    align = [r["native_decide_alignment"] for r in rows if "native_decide_alignment" in r]
    reload_details = []
    for r in reloaded:
        original = groups[(r["case_id"], "order_0")]["mean"]
        first = groups[(r["case_id"], "order_0")]["records"][0]
        q = np.array([r["probabilities"][s] for s in STATES])
        reload_details.append({"case_id": r["case_id"],
            "max_probability_shift_from_main_mean_pp": float(100 * np.abs(q - original).max()),
            "max_probability_shift_from_original_readout_pp": max(100 * abs(r["probabilities"][s] - first["probabilities"][s]) for s in STATES),
            "raw_logits_exactly_match_original": r["raw_logits"] == first["raw_logits"],
            "probabilities_exactly_match_original": r["probabilities"] == first["probabilities"],
            "same_selected_state": r["selected_state"] == STATES[int(original.argmax())]})
    all_q = np.array([[r["probabilities"][s] for s in STATES] for r in main_rows])
    t1_q = np.array([[r["probabilities_T1"][s] for s in STATES] for r in main_rows])
    entropy = -np.sum(all_q * np.log2(np.clip(all_q, 1e-300, None)), axis=1)
    gaps = [r["max_native_order_range_pp"] for r in case_stats]
    runtime = json.loads((ROOT / "runtime.json").read_text())
    summary = {
        "model_repo": runtime["model_repo"], "model_revision": runtime["model_revision"],
        "publisher_temperature": runtime["saved_temperature"], "main_readouts": len(main_rows),
        "unique_conditions": len(group_stats), "all_expected_main_readouts_complete": len(main_rows) == 480 and all(r["repeats"] == 10 for r in group_stats) and len(group_stats) == 48,
        "repeatability": {"max_probability_range_pp": max(r["max_repeat_probability_range_pp"] for r in group_stats),
            "max_raw_logit_range": max(r["max_raw_logit_repeat_range"] for r in group_stats),
            "groups_with_identical_probabilities": sum(r["distinct_probability_vectors"] == 1 for r in group_stats),
            "groups_with_identical_raw_logits": sum(r["distinct_raw_logit_vectors"] == 1 for r in group_stats),
            "groups_with_changed_selected_states": sum('/' in r["observed_selected_states"] for r in group_stats)},
        "native_option_order_sensitivity": {"cases": len(case_stats), "maximum_review_gap_pp": max(gaps),
            "mean_review_gap_pp": statistics.mean(gaps), "median_review_gap_pp": statistics.median(gaps),
            "cases_with_changed_selected_state": sum(r["different_order_winners"] > 1 for r in case_stats)},
        "native_decide_alignment": {"checks": len(align),
            "max_probability_difference": max((r["max_probability_difference"] for r in align), default=None),
            "all_choices_agree": all(r["chosen_state_agrees"] for r in align)},
        "native_distribution": {"mean_winning_probability": float(all_q.max(axis=1).mean()),
            "median_winning_probability": float(np.median(all_q.max(axis=1))),
            "minimum_winning_probability": float(all_q.max(axis=1).min()),
            "winning_probability_ge_999_count": int((all_q.max(axis=1) >= .999).sum()),
            "mean_entropy_bits": float(entropy.mean()),
            "T1_mean_winning_probability": float(t1_q.max(axis=1).mean())},
        "reloaded": {"readouts": len(reloaded),
            "max_probability_shift_from_main_mean_pp": max((r["max_probability_shift_from_main_mean_pp"] for r in reload_details), default=None),
            "max_probability_shift_from_original_readout_pp": max((r["max_probability_shift_from_original_readout_pp"] for r in reload_details), default=None),
            "all_raw_logits_exactly_match_original": all(r["raw_logits_exactly_match_original"] for r in reload_details),
            "all_probabilities_exactly_match_original": all(r["probabilities_exactly_match_original"] for r in reload_details),
            "mean_comparison_note": "Any approximately 1e-14 percentage-point difference against the arithmetic mean of ten identical vectors is floating-point averaging roundoff, not observed model variation.",
            "changed_selected_states": sum(not r["same_selected_state"] for r in reload_details), "case_details": reload_details},
        "median_forward_seconds": statistics.median(r["elapsed_seconds"] for r in main_rows),
        "confidence_field_definition": "For four-way choice, the author's formatter computes confidence=(max_probability-0.25)/0.75, clipped to [0,1]. It is a concentration transform, not an additional independent correctness estimate.",
        "qualification": "Native criterion reordering jointly changes option position and internal A-D assignment; not the isolated Gemma letter-only factor. Stored Qwen/Gemma baselines differ in runtime, precision, wrapper and temperature. No inherited-reference accuracy or task-calibration claim is computed.",
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_csv("condition_repeatability.csv", group_stats)
    write_csv("case_probability_summary.csv", case_stats)
    write_csv("order_mean_vectors.csv", order_rows)
    write_csv("comparison_with_saved_baselines.csv", comparison)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
