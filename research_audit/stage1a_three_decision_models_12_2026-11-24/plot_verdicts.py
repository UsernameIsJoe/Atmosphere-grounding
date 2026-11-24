"""Plot saved five-model calm verdicts; performs no model inference.

Verdict = argmax of the original-wording mean of four semantic-aligned
probability vectors. New models / Decider vary criterion order and native
codes together; Gemma varies letter assignment at fixed definition order.
These are practical saved-system comparisons, not a controlled head ablation.
"""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parent
STATES = ("neither", "support_only", "opposition_only", "both")
DISPLAY = ("Neither", "Support", "Opposition", "Both")
COLORS = ("#dce2eb", "#078595", "#ca522d", "#7956b7")
MODELS = ("mammoth", "karpo", "glide", "decider", "gemma")
MODEL_NAMES = ("Mammoth-1", "Karpo 31B", "GLiDE 27B", "Decider v1.2", "Gemma")
CASES = {
    "K01": "Personal wedding stress",
    "K02": "Dark restroom",
    "K03": "Unsuitable for walking",
    "K04": "Surprisingly uncrowded visit",
    "K05": "Owner yelling at visitors",
    "K06": "Watching children near traffic",
    "U01": "Space for a future dance floor",
    "U02": "Underwhelming exhibits",
    "U03": "Intrusive traffic noise",
    "U04": "Fun for all ages",
    "U05": "Fame and cleanliness",
    "U06": "Comfortable seating and music",
}


def load_vectors():
    with (ROOT / "case_probability_comparison.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 36
    vectors = {}
    for row in rows:
        key = (row["case_id"], row["model"])
        assert key not in vectors
        vectors[key] = {s: float(row[s]) for s in STATES}
        assert max(STATES, key=vectors[key].get) == row["selected_state"]
    baseline = json.loads((ROOT / "baseline_vectors.json").read_text())["cases"]
    decider = json.loads((ROOT / "decider_baseline.json").read_text())["cases"]
    for case in CASES:
        vectors[case, "decider"] = decider[case]
        vectors[case, "gemma"] = baseline[case]["gemma_T1_mapping_mean"]
        assert max(STATES, key=vectors[case, "gemma"].get) == max(
            STATES, key=baseline[case]["gemma_T4_mapping_mean"].get)
    assert set(vectors) == {(c, m) for c in CASES for m in MODELS}
    for v in vectors.values():
        assert all(0 <= v[s] <= 1 for s in STATES)
        assert abs(sum(v[s] for s in STATES) - 1) < 1e-6
    return vectors


def main():
    vectors = load_vectors()
    verdicts = {(c, m): max(STATES, key=v.get) for (c, m), v in vectors.items()}
    matrix = np.array([[STATES.index(verdicts[c, m]) for m in MODELS] for c in CASES])
    disagree = [i for i, row in enumerate(matrix) if len(set(row)) > 1]
    assert [list(CASES)[i] for i in disagree] == ["K01", "K04", "U06"]
    assert all(verdicts[c, "gemma"] == verdicts[c, "decider"] for c in CASES)

    with (ROOT / "five_model_verdict_comparison.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "description", "target_segment", *MODEL_NAMES, "unanimous"])
        targets = {d["case_id"]: d["target_segment"] for d in map(json.loads,
                   (ROOT / "inputs.jsonl").read_text().splitlines())}
        for c in CASES:
            values = [verdicts[c, m] for m in MODELS]
            writer.writerow([c, CASES[c], targets[c], *values, len(set(values)) == 1])

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "svg.fonttype": "none"})
    fig = plt.figure(figsize=(14, 9), facecolor="#f6f8fc")
    fig.text(.04, .95, "Calm verdicts across five models", fontsize=25,
             weight="bold", color="#17263f")
    fig.text(.04, .912, "Same 12 target segments · original wording · saved experiment results",
             fontsize=12.5, color="#536580")
    fig.text(.04, .867, "9 / 12 unanimous", fontsize=14, weight="bold", color="#17263f")
    fig.text(.225, .867, "Amber outlines mark the three rows with different verdicts.",
             fontsize=11.5, color="#7d581e")

    ax = fig.add_axes([.345, .205, .62, .61])
    ax.imshow(matrix, cmap=ListedColormap(COLORS), vmin=-.5, vmax=3.5, aspect="auto")
    ax.set_xticks(range(len(MODELS)), MODEL_NAMES, fontsize=12, weight="bold", color="#17263f")
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=13)
    ax.set_yticks(range(len(CASES)), [f"{c}  {label}" for c, label in CASES.items()],
                  fontsize=11.7, color="#536580")
    ax.tick_params(axis="y", length=0, pad=14)
    ax.set_xticks(np.arange(-.5, len(MODELS), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(CASES), 1), minor=True)
    ax.grid(which="minor", color="#f6f8fc", linewidth=4)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i, row in enumerate(matrix):
        for j, state in enumerate(row):
            ax.text(j, i, DISPLAY[state], va="center", ha="center", fontsize=11.5,
                    weight="medium", color="#34435b" if state == 0 else "white")
    for i in disagree:
        ax.add_patch(Rectangle((-.49, i-.48), 4.98, .96, fill=False,
                              edgecolor="#d49a35", linewidth=2.2, zorder=5))
        ax.get_yticklabels()[i].set_color("#17263f")
        ax.get_yticklabels()[i].set_weight("bold")

    fig.text(.04, .145, "Neither", color="#34435b", weight="bold", fontsize=11)
    fig.text(.105, .145, "= no qualifying calm evidence; it does not mean the place is emotionally neutral.",
             color="#536580", fontsize=11)
    fig.text(.04, .112, "Support / Opposition", color="#17263f", weight="bold", fontsize=11)
    fig.text(.185, .112, "= evidence for / against calm.  Both = evidence in both directions.",
             color="#536580", fontsize=11)
    fig.text(.04, .065, "Verdict: highest-probability state after averaging four aligned presentation variants.",
             color="#536580", fontsize=10.5)
    fig.text(.04, .038, "Original wording only. Variant types differ by system; agreement is not an accuracy measure.",
             color="#536580", fontsize=10.5)
    for suffix in ("png", "svg"):
        fig.savefig(ROOT / f"five_model_verdict_comparison.{suffix}", dpi=180,
                    facecolor=fig.get_facecolor(), metadata={"Creator": "Saved-result plotting"})
    plt.close(fig)
    print(json.dumps({"cases": 12, "models": 5, "unanimous": 12-len(disagree),
          "disagreement_cases": [list(CASES)[i] for i in disagree],
          "decider_gemma_agreement": 12,
          "counts": {m: {s: sum(verdicts[c,m] == s for c in CASES) for s in STATES}
                     for m in MODELS}}, indent=2))


if __name__ == "__main__":
    main()
