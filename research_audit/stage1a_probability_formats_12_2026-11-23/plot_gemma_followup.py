#!/usr/bin/env python3
"""Recreate November 24 Gemma figures from the committed CSV exports.

No model calls. The original inference provenance remains in the November 23
reports and raw archives. Rendering may vary with the Matplotlib version.
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter
import numpy as np

ROOT = Path(__file__).resolve().parent
STATES = ("neither", "support_only", "opposition_only", "both")
TEMPS = (1, 2, 4, 6, 8)
MAPPINGS = ("ABCD", "BCDA", "CDAB", "DABC")
COLORS = ("#A5AFBD", "#087F8C", "#C85232", "#7858B8")
STATE_LABELS = ("Neither: no calm evidence", "Support only", "Opposition only", "Both")
NAMES = {
    "K01": "Personal wedding-logistics stress", "K02": "Dark restroom",
    "K03": "Unsuitable for walking", "K04": "An uncrowded visit",
    "K05": "Owner yelling at visitors", "K06": "Street / watching children",
    "U01": "A future dance floor", "U02": "Underwhelming exhibits",
    "U03": "Intrusive traffic noise", "U04": "Fun for all ages",
    "U05": "Fame / cleanliness", "U06": "Comfortable seating / music",
}


def read_csv(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_and_validate():
    means = {(r["case_id"], int(float(r["scoring_temperature"]))):
             np.array([float(r[s]) for s in STATES])
             for r in read_csv("Gemma_probability_distributions.csv")}
    mapped = {(r["case_id"], int(float(r["scoring_temperature"])), r["letter_assignment"]):
              np.array([float(r[s]) for s in STATES])
              for r in read_csv("Gemma_mapping_probabilities_by_temperature.csv")}
    summary = {int(float(r["scoring_temperature"])): r
               for r in read_csv("Gemma_stability_summary.csv")}
    assert len(means) == 60 and len(mapped) == 240 and len(summary) == 5
    ranges = {}
    for temp in TEMPS:
        case_ranges = []
        for case in sorted(NAMES):
            q = np.array([mapped[case, temp, m] for m in MAPPINGS])
            assert np.isfinite(q).all() and np.min(q) >= 0
            assert np.allclose(q.sum(axis=1), 1, rtol=0, atol=1e-12)
            assert np.allclose(q.mean(axis=0), means[case, temp], rtol=0, atol=1e-12)
            case_ranges.append(float(100 * np.ptp(q, axis=0).max()))
        ranges[temp] = case_ranges
        for key, value in (("direct_max_letter_assignment_spread_pp", max(case_ranges)),
                           ("direct_mean_review_letter_assignment_spread_pp", np.mean(case_ranges)),
                           ("direct_median_review_letter_assignment_spread_pp", np.median(case_ranges))):
            assert abs(float(summary[temp][key]) - value) < 1e-9, (temp, key)
    return means, mapped, summary, ranges


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "text.color": "#17263D", "axes.labelcolor": "#475569",
        "xtick.color": "#526278", "ytick.color": "#526278",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.spines.bottom": False,
        "axes.facecolor": "#F6F8FB", "figure.facecolor": "#F6F8FB",
        "savefig.facecolor": "#F6F8FB",
    })


def save(fig, output, name):
    fig.savefig(output / name, dpi=175)
    plt.close(fig)


def temperature_grid(means, cases, output, name):
    nrows = (len(cases) + 1) // 2
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 4 * nrows + 1.2), squeeze=False)
    short = nrows == 2
    fig.subplots_adjust(left=.075, right=.97, top=.86 if short else .945,
                        bottom=.14 if short else .063, hspace=.49 if short else .56, wspace=.20)
    fig.text(.075, .973 if short else .987,
             "Gemma probability distributions across scoring temperatures", fontsize=18, weight="bold", va="top")
    fig.text(.075, .933 if short else .968,
             "Gemma4 31B IT · calm evidence states · mean of four letter mappings", color="#526278", fontsize=11, va="top")
    for ax, case in zip(axes.flat, cases):
        values = np.array([means[case, t] for t in TEMPS]) * 100
        base = np.zeros(5)
        for j, color in enumerate(COLORS):
            ax.bar(range(5), values[:, j], bottom=base, width=.69,
                   color=color, edgecolor="#F6F8FB", linewidth=.8, zorder=3)
            base += values[:, j]
        for i, v in enumerate(values):
            j = int(v.argmax())
            ax.text(i, v[:j].sum() + v[j] / 2, f"{v[j]:.1f}%", ha="center", va="center",
                    weight="bold", color="#17263D" if j == 0 else "white")
        ax.set(ylim=(0, 100), xlim=(-.6, 4.6), yticks=[0, 25, 50, 75, 100])
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.set_xticks(range(5), [f"T={t}" for t in TEMPS])
        ax.tick_params(length=0, pad=7)
        ax.grid(axis="y", color="#DDE3EB", linewidth=.8)
        ax.set_axisbelow(True)
        ax.set_title(f"{case} · {NAMES[case]}", loc="left", fontsize=12, weight="bold", pad=13)
    fig.legend([Patch(facecolor=c) for c in COLORS], STATE_LABELS, frameon=False, ncol=4,
               loc="lower left", bbox_to_anchor=(.075, .064 if short else .027), fontsize=10)
    fig.text(.075, .034 if short else .018,
             "Each bar totals 100%. Labels show the largest component; all four states are included.", fontsize=9, color="#526278")
    fig.text(.075, .015 if short else .008,
             "T=1 is the original scoring scale. Higher T reweights saved logits; no new model runs.", fontsize=9, color="#526278")
    save(fig, output, name)


def repeat_vs_mapping(summary, output):
    native = [float(summary[t]["native_complete_group_max_repeat_spread_pp"]) for t in TEMPS]
    direct = [float(summary[t]["direct_max_repeat_pair_difference_pp"]) for t in TEMPS]
    letter = [float(summary[t]["direct_max_letter_assignment_spread_pp"]) for t in TEMPS]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.25))
    fig.subplots_adjust(left=.075, right=.97, top=.77, bottom=.24, wspace=.23)
    fig.text(.075, .965, "Gemma stability: repeated inputs vs changed letter assignments", fontsize=17, weight="bold", va="top")
    fig.text(.075, .908, "Same Gemma4 31B BF16 checkpoint · calm only · five scoring temperatures", fontsize=11, color="#526278")
    lines = ((axes[0], native, "#B66B18", "o-", "Native Ollama repeats"),
             (axes[0], direct, "#087F8C", "s--", "Direct-backend repeat pairs"),
             (axes[1], letter, "#7254B4", "o-", "Letter assignments"))
    for ax, values, color, fmt, label in lines:
        ax.plot(TEMPS, values, fmt, color=color, label=label, lw=2.3, ms=6)
        for t, value in zip(TEMPS, values):
            ax.annotate(f"{value:.2f}", (t, value), xytext=(0, -18 if label.startswith("Direct") else 10),
                        textcoords="offset points", ha="center", color=color, weight="bold")
    for ax in axes:
        ax.set_xticks(TEMPS, [f"T={t}" for t in TEMPS])
        ax.set_ylabel("Largest probability spread (percentage points)")
        ax.grid(axis="y", color="#DDE4EC"); ax.set_axisbelow(True); ax.tick_params(length=0, pad=7)
    axes[0].set_ylim(-.6, 5.3); axes[1].set_ylim(-.6, 16.5)
    axes[0].set_title("A. Identical prompt, repeated computation", loc="left", weight="bold", pad=16)
    axes[1].set_title("B. Same text, four letter assignments", loc="left", weight="bold", pad=16)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(.075, .145), ncol=2, frameon=False)
    for y, text in ((.10, "Native: 30 complete-score prompt/phase groups. Direct: 16 pairs, four reviews × four mappings."),
                    (.071, "Different backends/settings and coverage: this is not a Gemma cache-only causal comparison."),
                    (.042, "B is the maximum review-level gap across twelve reviews. The tested Gemma verdicts did not change."),
                    (.014, "Temperatures are offline recalculations from saved outputs; no new model inference.")):
        fig.text(.075, y, text, fontsize=9.2, color="#526278")
    save(fig, output, "Gemma_stability_repeat_vs_mapping.png")


def mapping_ranges(mapped, output):
    fig, axes = plt.subplots(1, 2, figsize=(12, 8.8), sharey=True)
    fig.subplots_adjust(left=.255, right=.965, top=.79, bottom=.20, wspace=.18)
    fig.text(.045, .965, "Gemma letter sensitivity: same verdict, different probabilities", fontsize=17, weight="bold", va="top")
    fig.text(.045, .918, "Each dot is one letter assignment; each row is one review. Probability axes show 60–100%.", color="#526278")
    cases = sorted(NAMES)
    for ax, temp in zip(axes, (1, 4)):
        for y, case in enumerate(cases):
            q = np.array([mapped[case, temp, m] for m in MAPPINGS])
            assert len(set(q.argmax(axis=1))) == 1
            values = q.max(axis=1) * 100
            ax.hlines(y, values.min(), values.max(), color="#8291A5", linewidth=2)
            for j, value in enumerate(values):
                ax.scatter(value, y + (j - 1.5) * .075, color=("#2563A8", "#C85232", "#087F8C", "#7858B8")[j],
                           s=34, label=MAPPINGS[j] if y == 0 else None, zorder=3)
            if temp == 4:
                ax.annotate(f"{values.min():.1f}–{values.max():.1f}%", (values.min(), y), xytext=(-7, 8),
                            textcoords="offset points", ha="right", fontsize=8.5, color="#475569")
        ax.set_xlim(60, 100.4); ax.set_xticks([60, 70, 80, 90, 100])
        ax.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.grid(axis="x", color="#DFE5ED"); ax.set_axisbelow(True); ax.tick_params(length=0, pad=8)
        ax.set_xlabel("Probability of the winning evidence state", labelpad=11)
        ax.set_title(f"T={temp} · " + ("original scale" if temp == 1 else "softened scale"), loc="left", weight="bold", pad=15)
    axes[0].set_yticks(range(12), [f"{c} · {NAMES[c]}" for c in cases], fontsize=9.2)
    axes[0].set_ylim(11.6, -.7)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(.255, .096), ncol=4, frameon=False)
    for y, text in ((.065, "Mapping strings list letters for: neither, support only, opposition only, both."),
                    (.036, "Meanings and their order stay fixed; this measures letter sensitivity, not repeated-run noise."),
                    (.012, "Four cyclic assignments were tested; not every permutation, wording or definition order.")):
        fig.text(.045, y, text, fontsize=9.2, color="#526278")
    save(fig, output, "Gemma_stability_letter_ranges_by_case.png")


def mean_median(summary, output):
    fig = plt.figure(figsize=(11, 7.4)); ax = fig.add_axes([.09, .34, .86, .43])
    fig.text(.09, .955, "Gemma letter sensitivity: worst case, mean and median", fontsize=18, weight="bold", va="top")
    fig.text(.09, .902, "Four assignments per review · twelve reviews · gaps in percentage points", fontsize=11, color="#526278")
    rows = []
    for label, key, color, fmt in (
            ("Maximum", "direct_max_letter_assignment_spread_pp", "#7858B8", "o--"),
            ("Mean", "direct_mean_review_letter_assignment_spread_pp", "#2563A8", "o-"),
            ("Median", "direct_median_review_letter_assignment_spread_pp", "#087F8C", "s-")):
        values = [float(summary[t][key]) for t in TEMPS]
        ax.plot(TEMPS, values, fmt, color=color, label=f"{label} across reviews", lw=2.5, ms=7)
        ax.annotate(f"{values[2]:.2f}", (4, values[2]), xytext=(9, -15 if label == "Median" else 5),
                    textcoords="offset points", fontsize=11, weight="bold", color=color)
        rows.append([label] + [f"{v:.2f}" for v in values])
    ax.set(xlim=(.7, 8.35), ylim=(-.3, 16.5), yticks=[0, 4, 8, 12, 16])
    ax.set_xticks(TEMPS, [f"T={t}" for t in TEMPS]); ax.set_ylabel("Letter-assignment gap (percentage points)")
    ax.grid(axis="y", color="#DDE4EC"); ax.set_axisbelow(True); ax.tick_params(length=0, pad=8)
    ax.axvline(4, color="#CBD5E1", lw=1, zorder=0)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.17), ncol=3, frameon=False, columnspacing=1.3)
    table_ax = fig.add_axes([.09, .125, .86, .15]); table_ax.axis("off")
    tab = table_ax.table(cellText=rows, colLabels=["Across twelve reviews"] + [f"T={t}" for t in TEMPS],
                         cellLoc="center", loc="center", colWidths=[.28] + [.144] * 5)
    tab.auto_set_font_size(False); tab.set_fontsize(10); tab.scale(1, 1.32)
    for (i, _), cell in tab.get_celld().items():
        cell.set_edgecolor("#DDE4EC"); cell.set_linewidth(.6)
        cell.set_facecolor("#E8EEF5" if i == 0 else "#F6F8FB")
    for y, text in ((.069, "Per review: largest state-probability range across four assignments."),
                    (.040, "These lines summarize twelve review-level gaps, not averaged prediction vectors."),
                    (.013, "Saved Gemma4 31B BF16 outputs, rescaled offline. T=4 is highlighted for comparison only.")):
        fig.text(.09, y, text, fontsize=9.6, color="#526278")
    save(fig, output, "Gemma_stability_mean_median_mapping.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "figures")
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    means, mapped, summary, _ = load_and_validate()
    style()
    temperature_grid(means, ("K04", "K05", "K06", "U06"), args.output_dir, "Gemma_temperature_four_cases.png")
    temperature_grid(means, sorted(NAMES), args.output_dir, "Gemma_temperature_all_12_cases.png")
    repeat_vs_mapping(summary, args.output_dir)
    mapping_ranges(mapped, args.output_dir)
    mean_median(summary, args.output_dir)
    print("Validated 60 mean vectors, 240 mapping vectors and all five summary rows; generated five figures.")


if __name__ == "__main__":
    main()
