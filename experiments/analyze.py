"""Compute head-to-head metrics from raw per-item run outputs.

Reads answer keys and experiments/runs/<method>/ and computes, per method: detection rate on
violated items, false-alarm rate on holds items, witness validity, detection by interaction
depth, mean latency, and a logistic regression of detection on depth. Every number is derived
here from the raw outputs; none is hand-entered. Proportions carry 95% Wilson score intervals.

    python experiments/analyze.py            # writes experiments/results/{summary.json,tables.md}
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np

from verifier.model import Item
from verifier.replay import confirm_witness

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / os.environ.get("CIVBENCH_SUITE", "benchmark/suite")
RUNS = ROOT / os.environ.get("CIVBENCH_RUNS", "experiments/runs")
RESULTS = ROOT / os.environ.get("CIVBENCH_RESULTS", "experiments/results")
METHOD_LABEL = {
    "verification": "SMT verification",
    "unit_test": "unit-test suite",
    "llm_judge": "language-model judge",
    "judge_gpt55": "language-model judge (GPT-5.5)",
    "judge_gemini31propreview": "language-model judge (Gemini 3.1 Pro)",
    "judge_fable5": "language-model judge (Fable 5)",
    "judge_qwen3_8b": "language-model judge (Qwen3-8B, open)",
    "nemo_guardrails": "NeMo Guardrails",
    "llama_guard": "Llama Guard",
}
# Method list and order are configurable so the same analyzer serves each suite; default below.
_DEFAULT_METHODS = "verification,unit_test,judge_gpt55,judge_gemini31propreview,judge_fable5,llm_judge,nemo_guardrails,llama_guard"
METHOD_ORDER = [m for m in os.environ.get("CIVBENCH_METHODS", _DEFAULT_METHODS).split(",") if m]
for _m in METHOD_ORDER:
    METHOD_LABEL.setdefault(_m, _m)
Z = 1.959963984540054  # 95%


def wilson(x: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = x / n
    denom = 1 + Z * Z / n
    center = (p + Z * Z / (2 * n)) / denom
    half = (Z / denom) * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return (p, max(0.0, center - half), min(1.0, center + half))


def logistic_slope(depths: list[int], y: list[int]):
    """IRLS logistic fit of detection ~ 1 + depth. Returns (slope, lo, hi) or None if degenerate."""
    if len(set(y)) < 2:
        return None  # all detected or all missed; slope not identified
    X = np.column_stack([np.ones(len(depths)), np.array(depths, float)])
    yv = np.array(y, float)
    beta = np.zeros(2)
    for _ in range(50):
        eta = X @ beta
        mu = 1 / (1 + np.exp(-eta))
        W = np.clip(mu * (1 - mu), 1e-9, None)
        try:
            XtWX = X.T @ (W[:, None] * X)
            grad = X.T @ (yv - mu)
            step = np.linalg.solve(XtWX, grad)
        except np.linalg.LinAlgError:
            return None
        beta = beta + step
        if np.max(np.abs(step)) < 1e-8:
            break
    eta = X @ beta
    mu = 1 / (1 + np.exp(-eta))
    W = np.clip(mu * (1 - mu), 1e-9, None)
    cov = np.linalg.inv(X.T @ (W[:, None] * X))
    se = math.sqrt(cov[1, 1])
    return (beta[1], beta[1] - Z * se, beta[1] + Z * se)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def load_runs(method: str) -> dict:
    d = RUNS / method
    if not d.exists():
        return {}
    return {json.loads(f.read_text())["item_id"]: json.loads(f.read_text()) for f in d.glob("*.json")}


def main() -> int:
    keys = {json.loads(f.read_text())["item"]: json.loads(f.read_text())
            for f in (SUITE / "answer_key").glob("*.json")}
    items = {p.stem: Item.load(p) for p in (SUITE / "items").glob("*.json")}
    violated = [i for i, k in keys.items() if k["ground_truth"] == "violated"]
    holds = [i for i, k in keys.items() if k["ground_truth"] == "holds"]
    depths = sorted({keys[i]["interaction_depth"] for i in violated})

    summary = {"n_items": len(keys), "n_violated": len(violated), "n_holds": len(holds),
               "depths": depths, "methods": {}}

    for method in METHOD_ORDER:
        runs = load_runs(method)
        if not runs:
            continue
        effective = {i for i, r in runs.items() if r["verdict"] != "not_run"}
        if not effective:
            marker = next(iter(runs.values()))
            summary["methods"][method] = {
                "label": METHOD_LABEL[method], "status": "not_run",
                "reason": marker.get("extra", {}).get("reason", ""),
                "command": marker.get("extra", {}).get("command", ""),
            }
            continue
        # covered includes any decisive-or-abstaining output; "unknown" is not-detected, not wrong
        covered = [i for i in violated if i in effective]
        det = sum(runs[i]["verdict"] == "violated" for i in covered)
        p, lo, hi = wilson(det, len(covered))
        fa_cov = [i for i in holds if i in effective]
        fa = sum(runs[i]["verdict"] == "violated" for i in fa_cov)
        fp, flo, fhi = wilson(fa, len(fa_cov))
        # abstentions (unknown) and unsound decisive errors
        abstain = sum(runs[i]["verdict"] == "unknown" for i in covered + fa_cov)
        unsound = (sum(runs[i]["verdict"] == "holds" for i in covered)        # said safe, was violated
                   + sum(runs[i]["verdict"] == "violated" for i in fa_cov))   # said violated, was safe

        # witness validity among violated verdicts
        valid = total_claims = 0
        for i in (set(covered) | set(fa_cov)):
            r = runs[i]
            if r["verdict"] == "violated" and r.get("witness") is not None:
                total_claims += 1
                try:
                    if confirm_witness(items[i], r["witness"]):
                        valid += 1
                except Exception:
                    pass  # malformed or incomplete witness (e.g. a weak model omits a variable) is not valid
        wval = (valid / total_claims) if total_claims else None

        by_depth = {}
        for d in depths:
            cov_d = [i for i in covered if keys[i]["interaction_depth"] == d]
            det_d = sum(runs[i]["verdict"] == "violated" for i in cov_d)
            by_depth[d] = {"detected": det_d, "n": len(cov_d), "wilson": wilson(det_d, len(cov_d))}

        slope = logistic_slope([keys[i]["interaction_depth"] for i in covered],
                               [int(runs[i]["verdict"] == "violated") for i in covered])
        secs = [runs[i]["seconds"] for i in covered if runs[i].get("seconds") is not None]
        mean_sec = float(np.mean(secs)) if secs else float("nan")

        summary["methods"][method] = {
            "label": METHOD_LABEL[method],
            "n_covered_violated": len(covered),
            "detection": {"x": det, "n": len(covered), "rate": p, "ci": [lo, hi]},
            "false_alarm": {"x": fa, "n": len(fa_cov), "rate": fp, "ci": [flo, fhi]},
            "abstentions": abstain,
            "unsound_errors": unsound,
            "witness_validity": {"valid": valid, "claims": total_claims, "rate": wval},
            "by_depth": {str(d): {"detected": v["detected"], "n": v["n"],
                                  "rate": v["wilson"][0], "ci": [v["wilson"][1], v["wilson"][2]]}
                         for d, v in by_depth.items()},
            "depth_logistic_slope": ({"slope": slope[0], "ci": [slope[1], slope[2]]} if slope else None),
            "mean_seconds": mean_sec,
        }

    # pre-specified paired inferential test: SMT verification vs unit-test detection on violated items
    vr, ur = load_runs("verification"), load_runs("unit_test")
    if vr and ur:
        b = c = 0  # b: verifier detects, unit-test misses; c: verifier misses, unit-test detects
        for i in violated:
            if i not in vr or i not in ur:
                continue
            vd, ud = vr[i]["verdict"] == "violated", ur[i]["verdict"] == "violated"
            b += vd and not ud
            c += (not vd) and ud
        summary["mcnemar_verif_vs_unittest"] = {"b": b, "c": c, "p_value": mcnemar_exact(b, c)}

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (RESULTS / "tables.md").write_text(_render_tables(summary))
    print(_render_tables(summary))
    return 0


def _pct(x):
    return "--" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}"


def _render_tables(summary: dict) -> str:
    present = [m for m in METHOD_ORDER if m in summary["methods"]]
    suite_name = SUITE.name.replace("suite_", "CIV-Bench-").replace("suite", "CIV-Bench v0")
    L = [f"# {suite_name} head-to-head results",
         "",
         f"Items: {summary['n_items']} ({summary['n_violated']} violated, {summary['n_holds']} holds). "
         "Proportions carry 95% Wilson score intervals.",
         "",
         "## Detection, false alarm, abstention, and soundness",
         "",
         "Abstentions are unknown verdicts (the verifier declines to answer within its resource "
         "bound). Unsound errors are decisive verdicts that contradict ground truth (a safe verdict "
         "on a violated item, or a violated verdict on a safe item); a sound method has zero.",
         "",
         "| method | detection rate % [95% CI] | false-alarm rate % [95% CI] | witness validity % | abstain | unsound | mean s/item |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for m in present:
        d = summary["methods"][m]
        if d.get("status") == "not_run":
            L.append(f"| {d['label']} | not run in this environment | -- | -- | -- | -- | -- |")
            continue
        det = d["detection"]; fa = d["false_alarm"]; wv = d["witness_validity"]["rate"]
        L.append(
            f"| {d['label']} | {_pct(det['rate'])} [{_pct(det['ci'][0])}, {_pct(det['ci'][1])}] "
            f"(n={det['n']}) | {_pct(fa['rate'])} [{_pct(fa['ci'][0])}, {_pct(fa['ci'][1])}] "
            f"(n={fa['n']}) | {_pct(wv)} | {d.get('abstentions', 0)} | {d.get('unsound_errors', 0)} | "
            f"{d['mean_seconds']:.4f} |")
    L += ["", "## Detection by interaction depth (rate % [95% CI])", "",
          "| method | " + " | ".join(f"depth {d}" for d in summary["depths"]) + " | depth slope (logit) [95% CI] |",
          "| --- | " + " | ".join("---" for _ in summary["depths"]) + " | --- |"]
    for m in present:
        d = summary["methods"][m]
        if d.get("status") == "not_run":
            L.append(f"| {d['label']} | " + " | ".join("--" for _ in summary["depths"]) + " | not run |")
            continue
        cells = []
        for dep in summary["depths"]:
            bd = d["by_depth"].get(str(dep))
            cells.append(f"{_pct(bd['rate'])} [{_pct(bd['ci'][0])},{_pct(bd['ci'][1])}]" if bd else "--")
        sl = d["depth_logistic_slope"]
        slope_cell = f"{sl['slope']:.2f} [{sl['ci'][0]:.2f}, {sl['ci'][1]:.2f}]" if sl else "not identified"
        L.append(f"| {d['label']} | " + " | ".join(cells) + f" | {slope_cell} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
