"""Shade saved five-model verdicts by their original winning probabilities.

No new inference, smoothing, calibration, or probability transformation is
performed. Color mixing alone is linear from white at 25% to the verdict's
base color at 100%. All four original probabilities are exported to CSV.
"""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle
import numpy as np

from plot_verdicts import ROOT, STATES, DISPLAY, MODELS, MODEL_NAMES, CASES, load_vectors

BASE_COLORS = ("#68788e", "#078595", "#ca522d", "#7956b7")
INK = "#17263f"
MUTED = "#536580"
BACKGROUND = "#f6f8fc"
STEM = "five_model_verdict_probabilities"


def shade(state_index, probability):
    """Visualization only; the supplied probability remains unchanged."""
    amount = np.clip((probability - .25) / .75, 0, 1)
    return (1 - amount) * np.ones(3) + amount * np.array(to_rgb(BASE_COLORS[state_index]))


def text_color(rgb):
    linear = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    luminance = linear @ np.array([.2126, .7152, .0722])
    dark = np.array(to_rgb(INK))
    dark_linear = np.where(dark <= .04045, dark / 12.92, ((dark + .055) / 1.055) ** 2.4)
    dark_luminance = dark_linear @ np.array([.2126, .7152, .0722])
    white_contrast = 1.05 / (luminance + .05)
    dark_contrast = (luminance + .05) / (dark_luminance + .05)
    return "white" if white_contrast >= dark_contrast else INK


def main():
    vectors = load_vectors()
    winners = {(case, model): max(STATES, key=v.get)
               for (case, model), v in vectors.items()}
    cases = list(CASES)
    matrix = np.array([[STATES.index(winners[case, model]) for model in MODELS]
                       for case in cases])
    probabilities = np.array([[vectors[case, model][winners[case, model]] for model in MODELS]
                              for case in cases])
    disagreement_rows = [i for i, row in enumerate(matrix) if len(set(row)) > 1]
    assert [cases[i] for i in disagreement_rows] == ["K01", "K04", "U06"]
    assert np.all((probabilities >= .25) & (probabilities <= 1))

    with (ROOT / f"{STEM}.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "description", "model", "selected_state",
                         "winning_probability", "runner_up_state", "runner_up_probability",
                         "winner_margin_pp", *STATES])
        for case in cases:
            for model, label in zip(MODELS, MODEL_NAMES):
                vector = vectors[case, model]
                first, second = sorted(STATES, key=vector.get, reverse=True)[:2]
                writer.writerow([case, CASES[case], label, first, vector[first], second,
                                 vector[second], 100 * (vector[first] - vector[second]),
                                 *(vector[state] for state in STATES)])

    colors = np.array([[shade(state, p) for state, p in zip(row, ps)]
                       for row, ps in zip(matrix, probabilities)])
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "svg.fonttype": "none"})
    fig = plt.figure(figsize=(14, 10), facecolor=BACKGROUND)
    fig.text(.04, .95, "Calm verdicts and their probabilities", fontsize=25,
             weight="bold", color=INK)
    fig.text(.04, .913, "Cell hue = verdict   ·   Darker shade = higher probability for that verdict",
             fontsize=12.5, color=MUTED)
    fig.text(.04, .87, "9 / 12 unanimous", fontsize=14, weight="bold", color=INK)
    fig.text(.225, .87, "Amber outlines mark the three rows with different verdicts.",
             fontsize=11.5, color="#7d581e")

    ax = fig.add_axes([.345, .30, .62, .53])
    ax.imshow(colors, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(len(MODELS)), MODEL_NAMES, fontsize=12, weight="bold", color=INK)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=12)
    ax.set_yticks(range(len(cases)), [f"{c}  {CASES[c]}" for c in cases],
                  fontsize=11.7, color=MUTED)
    ax.tick_params(axis="y", length=0, pad=14)
    ax.set_xticks(np.arange(-.5, len(MODELS), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(cases), 1), minor=True)
    ax.grid(which="minor", color=BACKGROUND, linewidth=4)
    ax.tick_params(which="minor", bottom=False, left=False, top=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i, row in enumerate(matrix):
        for j, state in enumerate(row):
            color = text_color(colors[i, j])
            ax.text(j, i-.18, DISPLAY[state], va="center", ha="center",
                    fontsize=10.3, color=color)
            ax.text(j, i+.18, f"{100 * probabilities[i, j]:.1f}%", va="center", ha="center",
                    fontsize=13, weight="bold", color=color)
    for i in disagreement_rows:
        ax.add_patch(Rectangle((-.49, i-.48), 4.98, .96, fill=False,
                              edgecolor="#d49a35", linewidth=2.2, zorder=5))
        ax.get_yticklabels()[i].set_color(INK)
        ax.get_yticklabels()[i].set_weight("bold")

    fig.text(.04, .25, "Probability of the displayed verdict", fontsize=11.5,
             weight="bold", color=INK)
    legend = fig.add_axes([.105, .143, .39, .087])
    levels = np.linspace(.25, 1, 256)
    ramps = np.array([[shade(state, p) for p in levels] for state in range(4)])
    legend.imshow(ramps, extent=(25, 100, 3.5, -.5), aspect="auto", interpolation="nearest")
    legend.set_yticks(range(4), DISPLAY, color=MUTED, fontsize=10.5)
    legend.set_xticks([25, 50, 75, 100], ["25%", "50%", "75%", "100%"],
                     color=MUTED, fontsize=10)
    legend.tick_params(length=0, pad=6)
    for spine in legend.spines.values():
        spine.set_visible(False)
    fig.text(.56, .225, "Neither = no qualifying calm evidence.", fontsize=10.8, color=MUTED)
    fig.text(.56, .198, "Both = evidence for and against calm.", fontsize=10.8, color=MUTED)
    fig.text(.56, .171, "Four alternatives: the winner can be below 50%.", fontsize=10.8, color=MUTED)
    fig.text(.56, .144, "Percentages are rounded; full vectors are saved in the CSV.", fontsize=10.8, color=MUTED)

    fig.text(.04, .083, "Original wording · arithmetic mean of four aligned variants · Gemma native T=1 · no added softening",
             color=MUTED, fontsize=10.5)
    fig.text(.04, .056, "Model probability scales are uncalibrated across systems; darkness shows model commitment, not verified correctness.",
             color=MUTED, fontsize=10.5)
    fig.text(.04, .029, "Gemma's near-100% values retain its previously observed sharp distributions. The 12 development targets are unchanged.",
             color=MUTED, fontsize=10.5)
    for suffix in ("png", "svg"):
        fig.savefig(ROOT / f"{STEM}.{suffix}", dpi=180, facecolor=BACKGROUND,
                    metadata={"Creator": "Saved-result plotting"})
    plt.close(fig)
    print(json.dumps({"cells": int(probabilities.size), "unanimous_targets": 9,
                      "probability_range": [float(probabilities.min()), float(probabilities.max())],
                      "gemma_temperature": 1, "inference_runs": 0,
                      "selected_state_probability_only": True}, indent=2))


if __name__ == "__main__":
    main()
