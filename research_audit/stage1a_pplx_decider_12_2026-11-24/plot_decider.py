#!/usr/bin/env python3
"""Plot the recorded native decision probabilities and balanced-order sensitivity."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter
import numpy as np

ROOT = Path(__file__).resolve().parent
STATES = ("neither", "support_only", "opposition_only", "both")
COLORS = ("#A5AFBD", "#087F8C", "#C85232", "#7858B8")
LABELS = ("Neither", "Support only", "Opposition only", "Both")
NAMES = {"K01": "Personal wedding-logistics stress", "K02": "Dark restroom",
         "K03": "Walking suitability", "K04": "Uncrowded visit", "K05": "Owner yelling",
         "K06": "Street / watching children", "U01": "Future dance floor", "U02": "Underwhelming exhibits",
         "U03": "Intrusive traffic noise", "U04": "Fun for all ages", "U05": "Fame / cleanliness",
         "U06": "Comfortable seating / music"}


def main():
    summary = json.loads((ROOT / "summary.json").read_text())
    with (ROOT / "case_probability_summary.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "text.color": "#17263D",
        "axes.labelcolor": "#475569", "xtick.color": "#526278", "ytick.color": "#526278",
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False, "axes.spines.bottom": False,
        "figure.facecolor": "#F6F8FB", "axes.facecolor": "#F6F8FB", "savefig.facecolor": "#F6F8FB"})
    q = np.array([[float(row[s]) for s in STATES] for row in rows]) * 100
    assert np.allclose(q.sum(axis=1), 100, rtol=0, atol=1e-8)
    ys = np.arange(len(rows))
    labels = [f"{r['case_id']} · {NAMES[r['case_id']]}" for r in rows]
    fig, ax = plt.subplots(figsize=(12, 8.4))
    fig.subplots_adjust(left=.30, right=.96, top=.80, bottom=.16)
    fig.text(.055, .955, "PPLX-Decider v1.2: native probability profiles", fontsize=19, weight="bold", va="top")
    fig.text(.055, .902, f"Calm only · BF16 reference path · publisher temperature {summary['publisher_temperature']:.3f}", fontsize=11, color="#526278")
    fig.text(.055, .865, "Mean of four balanced native option orders; ten serial repeats per order", fontsize=10.5, color="#526278")
    base = np.zeros(len(rows))
    for j, color in enumerate(COLORS):
        ax.barh(ys, q[:, j], left=base, height=.68, color=color, edgecolor="#F6F8FB", linewidth=.7, zorder=3)
        base += q[:, j]
    for i, v in enumerate(q):
        j = int(v.argmax())
        ax.text(v[:j].sum() + v[j] / 2, i, f"{v[j]:.1f}%", ha="center", va="center", weight="bold",
                color="#17263D" if j == 0 else "white", fontsize=10.5)
    ax.set_xlim(0, 100); ax.set_yticks(ys, labels); ax.invert_yaxis()
    ax.set_xticks([0, 25, 50, 75, 100]); ax.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    ax.tick_params(length=0, pad=8); ax.grid(axis="x", color="#DDE4EC"); ax.set_axisbelow(True)
    fig.legend([Patch(facecolor=c) for c in COLORS], LABELS, loc="lower left", bbox_to_anchor=(.30, .066), ncol=4, frameon=False)
    fig.text(.055, .040, "Each bar totals 100%. The label marks the largest component; neither means no qualifying calm evidence.", fontsize=9.4, color="#526278")
    fig.text(.055, .015, "Publisher calibration is retained; these are not independently calibrated probabilities for this emotion task.", fontsize=9.4, color="#526278")
    fig.savefig(ROOT / "native_probability_profiles.png", dpi=175); plt.close(fig)

    gaps = np.array([float(r["max_native_order_range_pp"]) for r in rows])
    stats = summary["native_option_order_sensitivity"]
    repeat = summary["repeatability"]
    fig, ax = plt.subplots(figsize=(12, 8.4))
    fig.subplots_adjust(left=.30, right=.95, top=.79, bottom=.18)
    fig.text(.055, .955, "PPLX-Decider v1.2: native option-order sensitivity", fontsize=18, weight="bold", va="top")
    fig.text(.055, .903, f"Largest repeated-input gap: {repeat['max_probability_range_pp']:.4f} pp; changed-repeat verdict groups: {repeat['groups_with_changed_selected_states']}/48", fontsize=11, color="#526278")
    fig.text(.055, .858, f"Across reviews: mean {stats['mean_review_gap_pp']:.2f} pp · median {stats['median_review_gap_pp']:.2f} pp · maximum {stats['maximum_review_gap_pp']:.2f} pp", fontsize=11, color="#526278")
    ax.barh(ys, gaps, height=.65, color="#C85232", zorder=3)
    for y, gap in zip(ys, gaps):
        ax.text(gap + max(gaps.max() * .015, .03), y, f"{gap:.2f}", va="center", fontsize=10.5, color="#A64228")
    ax.axvline(stats["mean_review_gap_pp"], color="#2563A8", linestyle="--", linewidth=1.8, label="Mean review-level gap")
    ax.axvline(stats["median_review_gap_pp"], color="#087F8C", linestyle=":", linewidth=2, label="Median review-level gap")
    ax.set_xlim(0, max(float(gaps.max()) * 1.22, 1)); ax.set_yticks(ys, labels); ax.invert_yaxis()
    ax.set_xlabel("Largest state-probability range across four native orders (percentage points)", labelpad=11)
    ax.tick_params(length=0, pad=8); ax.grid(axis="x", color="#DDE4EC"); ax.set_axisbelow(True)
    ax.legend(loc="lower left", bbox_to_anchor=(0, -.19), ncol=2, frameon=False, fontsize=10)
    fig.text(.055, .050, "Native criteria reordering jointly changes position and the internal A–D assignment. Four cyclic orders, not all 24.", fontsize=9.2, color="#526278")
    fig.text(.055, .020, "This is not Gemma's isolated fixed-position letter factor. Identical-request repeatability is a separate measurement.", fontsize=9.2, color="#526278")
    fig.savefig(ROOT / "native_order_sensitivity.png", dpi=175); plt.close(fig)
    print("Generated native probability and order-sensitivity figures from the actual readouts.")


if __name__ == "__main__":
    main()
