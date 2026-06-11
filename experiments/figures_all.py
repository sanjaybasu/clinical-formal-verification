"""Generate all main-text figures from the three suite summaries.

Reads experiments/results{,_hard,_compute}/summary.json and the suite manifests; writes to
paper/figures/. No number is hand-entered. Run after the three analyses.

    python experiments/figures_all.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "paper" / "figures"
SUITES = {
    "v0": ("results", "suite", "interaction depth", [1, 2, 3, 4, 5, 6, 8, 10, 12]),
    "hard": ("results_hard", "suite_hard", "lock length L", [2, 4, 6, 8, 10, 12]),
    "compute": ("results_compute", "suite_compute", "modulus M", [8, 16, 32, 48, 64]),
}
COLORS = {"verification": "#000000", "unit_test": "#0072B2", "llm_judge": "#D55E00"}
MARKERS = {"verification": "o", "unit_test": "s", "llm_judge": "^"}
LABEL = {"verification": "complete verification", "unit_test": "unit-test suite",
         "llm_judge": "language-model judge"}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
    "figure.dpi": 600, "savefig.dpi": 600, "axes.spines.top": False,
    "axes.spines.right": False, "font.family": "sans-serif",
})


def _save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def _summary(results_dir):
    return json.loads((ROOT / "experiments" / results_dir / "summary.json").read_text())


def detection_panels():
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, (tag, (rdir, _suite, xlabel, xs)) in zip(axes, SUITES.items()):
        s = _summary(rdir)
        depth_keys = [str(d) for d in xs]
        present_x = [d for d in xs if str(d) in next(iter(s["methods"].values())).get("by_depth", {})]
        for m, d in s["methods"].items():
            if d.get("status") == "not_run":
                continue
            ys, lo, hi = [], [], []
            for dep in present_x:
                bd = d["by_depth"].get(str(dep))
                if not bd:
                    continue
                ys.append(100 * bd["rate"]); lo.append(100 * (bd["rate"] - bd["ci"][0]))
                hi.append(100 * (bd["ci"][1] - bd["rate"]))
            ax.errorbar(present_x, ys, yerr=[lo, hi], label=LABEL[m], color=COLORS.get(m, "#555"),
                        marker=MARKERS.get(m, "o"), markersize=4, capsize=2, linewidth=1.3)
        ax.set_title(f"CIV-Bench {tag}")
        ax.set_xlabel(xlabel); ax.set_ylim(-3, 103)
        if tag == "v0":
            ax.set_ylabel("violations detected (%)")
            ax.legend(loc="lower left", frameon=False)
    fig.suptitle("Detection of seeded violations by difficulty, across three regimes", y=1.02)
    fig.tight_layout()
    _save(fig, "detection_by_difficulty")


def soundness_summary():
    # false-safe verdicts (decisive holds on a violated item) and abstentions per method per suite
    methods = ["verification", "unit_test", "llm_judge"]
    suites = list(SUITES)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
    width = 0.25
    for ax, field, title in [(a1, "unsound_errors", "false-'safe' / unsound verdicts"),
                             (a2, "abstentions", "abstentions (unknown)")]:
        for i, m in enumerate(methods):
            vals = []
            for tag in suites:
                s = _summary(SUITES[tag][0])
                d = s["methods"].get(m, {})
                vals.append(d.get(field, 0) if d.get("status") != "not_run" else 0)
            ax.bar([j + (i - 1) * width for j in range(len(suites))], vals, width,
                   label=LABEL[m], color=COLORS[m])
        ax.set_xticks(range(len(suites))); ax.set_xticklabels([f"CIV-Bench {t}" for t in suites], rotation=12)
        ax.set_ylabel("count"); ax.set_title(title)
    a1.legend(loc="upper left", frameon=False)
    fig.suptitle("Soundness: verification never reports false safety; it abstains instead", y=1.02)
    fig.tight_layout()
    _save(fig, "soundness_summary")


def benchmark_characterization():
    rows = []
    for tag, (_r, suite, _x, _xs) in SUITES.items():
        rows += json.loads((ROOT / "benchmark" / suite / "manifest.json").read_text())
    by_dom = Counter(r["domain"] for r in rows)
    gt = Counter(r["ground_truth"] for r in rows)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3.0))
    a1.bar(list(by_dom), list(by_dom.values()), color="#0072B2"); a1.set_title("items by domain")
    a1.set_ylabel("items"); a1.tick_params(axis="x", rotation=12)
    a2.bar(list(gt), list(gt.values()), color="#009E73"); a2.set_title("items by ground truth")
    fig.tight_layout()
    _save(fig, "benchmark_characterization")


def main():
    detection_panels()
    soundness_summary()
    benchmark_characterization()
    print(f"wrote figures to {FIGS}")


if __name__ == "__main__":
    raise SystemExit(main())
