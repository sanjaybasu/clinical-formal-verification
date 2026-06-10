"""Generate the main-text figures from the analysis summary.

Reads experiments/results/summary.json and benchmark/suite/manifest.json and writes figures to
paper/figures/. No number is hand-entered; every value comes from the analysis outputs. Runs
after experiments/analyze.py.

    python experiments/figures.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "experiments" / "results"
FIGS = ROOT / "paper" / "figures"
MANIFEST = ROOT / "benchmark" / "suite" / "manifest.json"

# Okabe-Ito colorblind-safe palette
COLORS = {
    "verification": "#000000",
    "unit_test": "#0072B2",
    "llm_judge": "#D55E00",
    "nemo_guardrails": "#009E73",
    "llama_guard": "#CC79A7",
}
MARKERS = {"verification": "o", "unit_test": "s", "llm_judge": "^",
           "nemo_guardrails": "D", "llama_guard": "v"}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "legend.fontsize": 8, "figure.dpi": 600, "savefig.dpi": 600,
    "axes.spines.top": False, "axes.spines.right": False, "font.family": "sans-serif",
})


def _save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_detection_by_depth(summary):
    depths = summary["depths"]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for method, d in summary["methods"].items():
        if d.get("status") == "not_run":
            continue
        ys, los, his = [], [], []
        for dep in depths:
            bd = d["by_depth"].get(str(dep))
            ys.append(100 * bd["rate"])
            los.append(100 * (bd["rate"] - bd["ci"][0]))
            his.append(100 * (bd["ci"][1] - bd["rate"]))
        ax.errorbar(depths, ys, yerr=[los, his], label=d["label"], color=COLORS.get(method, "#555"),
                    marker=MARKERS.get(method, "o"), markersize=4, capsize=2, linewidth=1.4)
    ax.set_xlabel("interaction depth (conditions or events that must coincide)")
    ax.set_ylabel("violations detected (%)")
    ax.set_ylim(-3, 103)
    ax.set_xticks(depths)
    ax.legend(loc="lower left", frameon=False)
    ax.set_title("Detection of seeded violations by interaction depth")
    _save(fig, "detection_by_depth")


def fig_detection_falsealarm(summary):
    methods = [(m, d) for m, d in summary["methods"].items() if d.get("status") != "not_run"]
    labels = [d["label"] for _, d in methods]
    det = [100 * d["detection"]["rate"] for _, d in methods]
    det_err = [[100 * (d["detection"]["rate"] - d["detection"]["ci"][0]) for _, d in methods],
               [100 * (d["detection"]["ci"][1] - d["detection"]["rate"]) for _, d in methods]]
    fa = [100 * d["false_alarm"]["rate"] for _, d in methods]
    fa_err = [[100 * (d["false_alarm"]["rate"] - d["false_alarm"]["ci"][0]) for _, d in methods],
              [100 * (d["false_alarm"]["ci"][1] - d["false_alarm"]["rate"]) for _, d in methods]]
    x = range(len(methods))
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    w = 0.38
    ax.bar([i - w / 2 for i in x], det, w, yerr=det_err, capsize=3, label="detection (violated items)",
           color="#0072B2")
    ax.bar([i + w / 2 for i in x], fa, w, yerr=fa_err, capsize=3, label="false alarm (holds items)",
           color="#D55E00")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("rate (%)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right", frameon=False)
    ax.set_title("Detection and false-alarm rates with 95% Wilson intervals")
    _save(fig, "detection_falsealarm")


def fig_benchmark_characterization():
    manifest = json.loads(MANIFEST.read_text())
    by_dom = Counter(m["domain"] for m in manifest)
    by_depth = Counter(m["interaction_depth"] for m in manifest if m["ground_truth"] == "violated")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 3.0))
    a1.bar(list(by_dom.keys()), list(by_dom.values()), color="#0072B2")
    a1.set_title("items by domain")
    a1.set_ylabel("items")
    a1.tick_params(axis="x", rotation=15)
    depths = sorted(by_depth)
    a2.bar([str(d) for d in depths], [by_depth[d] for d in depths], color="#009E73")
    a2.set_title("violated items by interaction depth")
    a2.set_xlabel("interaction depth")
    fig.tight_layout()
    _save(fig, "benchmark_characterization")


def main() -> int:
    summary = json.loads((RESULTS / "summary.json").read_text())
    fig_detection_by_depth(summary)
    fig_detection_falsealarm(summary)
    fig_benchmark_characterization()
    print(f"wrote figures to {FIGS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
