"""Generate CIV-Bench v3: the scaled whole-person suite plus a labelled computational stress tier.

v3 scales the eight realistic clinical domains of v2 (more seeds per depth) to reach a size
comparable with agentic clinical benchmarks, and adds a computational stress tier that random unit
testing fails on while a sound verifier does not: buried-override rule sets (one contraindication
override hidden among many distractor rules) and integer-feasibility items (does any in-range
parameter combination reach a contraindicated recommendation?). The stress tier is reported as a
stress test; on the pilots, frontier language-model judges solved it, so no claim is made that it
defeats them. Every item is schema-valid, oracle-grounded, witness-replayed, and cross-checked
against the SMT verifier; duplicates (identical ruleset+property) are dropped so the count reflects
distinct items. Deterministic: seeds derive from a stable sha256.

    python benchmark/generate_v3.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

from generate_v2 import (  # same-directory import (benchmark/ is on sys.path when run as a script)
    DEC_DEPTHS, EP_DEPTHS, DECISION_GENS, TRANSITION_GENS,
)
from verifier.execute import oracle
from verifier.model import Item
from verifier.replay import confirm_witness
from verifier.smt import verify

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "benchmark" / "suite_v3"
ITEM_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "benchmark.schema.json").read_text())

VIOL_SEEDS = list(range(12))      # 12 violated seeds per (gen, depth)
HOLD_SEEDS = list(range(100, 104))  # 4 holds seeds per (gen, depth)
NF = 13                            # distractor flags for the buried-needle tier


def _seed(*p):
    return int(hashlib.sha256("-".join(map(str, p)).encode()).hexdigest(), 16) % (2**32)


# --------------------------------------------------------------------------- computational stress tier

def buried_needle(sd, n_rules, conj, holds):
    """A contraindication override hidden among n_rules distractor rules (lost-in-the-middle)."""
    rng = random.Random(_seed("needle", sd, n_rules, conj, holds))
    flags = [f"f{i}" for i in range(NF)]
    inputs = [{"name": "anticoagulated", "type": "bool"}] + [{"name": f, "type": "bool"} for f in flags]
    outs = [{"name": "rec_drug", "type": "bool"}] + [{"name": f"o{j}", "type": "bool"} for j in range(5)]
    needle = flags[:conj - 1]
    conj_expr = {"op": "and", "args": [{"var": "anticoagulated"}] + [{"var": f} for f in needle]}
    rules = [{"id": "guard", "priority": 90, "when": {"var": "anticoagulated"}, "then": [{"var": "rec_drug", "value": False}]},
             {"id": "needle", "priority": 100 if not holds else 80, "when": conj_expr, "then": [{"var": "rec_drug", "value": True}]}]
    for k in range(n_rules):
        sub = rng.sample(flags, rng.randint(1, 3)); oj = f"o{rng.randint(0, 4)}"
        rules.append({"id": f"d{k}", "priority": rng.randint(10, 60),
                      "when": {"op": "and", "args": [{"var": v} for v in sub]} if len(sub) > 1 else {"var": sub[0]},
                      "then": [{"var": oj, "value": True}]})
    rng.shuffle(rules)
    return {"id": f"needle-r{n_rules}-c{conj}-{'hold' if holds else 'viol'}-{sd:02d}", "domain": "medication",
            "metadata": {"description": f"buried contraindication override among {n_rules} rules", "source": "synthetic",
                         "clinical_intent": "no input recommends a contraindicated drug for an anticoagulated patient"},
            "ruleset": {"id": f"n{n_rules}{conj}{sd}{int(holds)}", "kind": "decision", "inputs": inputs, "outputs": outs,
                        "rules": rules, "default": [{"var": "rec_drug", "value": False}] + [{"var": f"o{j}", "value": False} for j in range(5)],
                        "conflict_resolution": "priority"},
            "property": {"id": "no-contraindicated-drug", "kind": "invariant",
                         "formula": {"op": "not", "args": [{"op": "and", "args": [{"var": "anticoagulated"}, {"var": "rec_drug"}]}]},
                         "intent": "rec_drug is never true when anticoagulated"}}


def _lin(coeffs, vs):
    terms = [{"op": "mul", "args": [{"const": c}, {"var": v}]} for c, v in zip(coeffs, vs) if c != 0]
    return terms[0] if len(terms) == 1 else {"op": "add", "args": terms}


def feasibility(sd, nvars, holds, R=12):
    """Does any in-range integer parameter tuple reach the contraindicated recommendation?

    Violated iff the constraint system is integer-feasible over [0,R]^nvars; holds iff infeasible.
    Classification uses the SMT verifier during search and is confirmed by the independent oracle at
    build time. Holds items are interaction-infeasible (dropping one constraint makes them feasible)."""
    vs = ["wt", "renal", "inr", "plt", "na"][:nvars]
    rng = random.Random(_seed("feas", sd, nvars, holds))

    def raw_of(cons):
        S = {"op": "and", "args": [{"op": op, "args": [_lin(c, vs), {"const": t}]} for (c, op, t) in cons]}
        return {"id": "ph", "domain": "medication",
                "metadata": {"description": f"reachability of a contraindicated recommendation across {nvars} physiologic parameters", "source": "synthetic",
                             "clinical_intent": "no in-range parameter combination triggers the high-intensity recommendation"},
                "ruleset": {"id": f"fz{nvars}{sd}{int(holds)}", "kind": "decision",
                            "inputs": [{"name": v, "type": "int", "bounds": [0, R]} for v in vs],
                            "outputs": [{"name": "rec_high", "type": "bool"}],
                            "rules": [{"id": "enable_high_intensity", "priority": 50, "when": S, "then": [{"var": "rec_high", "value": True}]}],
                            "default": [{"var": "rec_high", "value": False}], "conflict_resolution": "priority"},
                "property": {"id": "unsafe-region-unreachable", "kind": "invariant",
                             "formula": {"op": "not", "args": [{"var": "rec_high"}]},
                             "intent": "rec_high is never true for any input in range"}}

    def cls(cons):
        return verify(Item.from_dict(raw_of(cons))).status

    for _ in range(4000):
        cons = [([rng.randint(-3, 3) for _ in range(nvars)], rng.choice(["ge", "le"]), rng.randint(-22, 60)) for _k in range(min(6, nvars + 1))]
        cons = [((c if any(c) else [2] + [0] * (nvars - 1)), op, t) for (c, op, t) in cons]
        if not all(cls([con]) == "violated" for con in cons):
            continue  # each constraint satisfiable alone (non-trivial)
        st = cls(cons)
        if holds and st == "holds" and any(cls(cons[:i] + cons[i + 1:]) == "violated" for i in range(len(cons))):
            break
        if (not holds) and st == "violated":
            break
    else:
        return None
    raw = raw_of(cons)
    raw["id"] = f"feas{nvars}-{'hold' if holds else 'viol'}-{sd:02d}"
    return raw


# --------------------------------------------------------------------------- build

def build_all():
    out = []
    # realistic domains, scaled
    for gen in DECISION_GENS:
        for d in DEC_DEPTHS:
            out += [gen(d, s, False) for s in VIOL_SEEDS] + [gen(d, s, True) for s in HOLD_SEEDS]
    for gen in TRANSITION_GENS:
        for L in EP_DEPTHS:
            out += [gen(L, s, False) for s in VIOL_SEEDS] + [gen(L, s, True) for s in HOLD_SEEDS]
    # computational stress tier: buried-needle
    for conj in (6, 8, 10, 12):
        n_rules = 80 if conj <= 8 else 120
        out += [buried_needle(s, n_rules, conj, False) for s in range(14)]
        out += [buried_needle(s, n_rules, conj, True) for s in range(100, 106)]
    # computational stress tier: integer feasibility (3 and 5 variables)
    for nv in (3, 5):
        for s in range(14):
            it = feasibility(s, nv, False)
            if it: out.append(it)
        for s in range(100, 110):
            it = feasibility(s, nv, True)
            if it: out.append(it)
    return out


def _dedup_key(raw):
    return hashlib.sha256(json.dumps({"r": raw["ruleset"], "p": raw["property"]}, sort_keys=True).encode()).hexdigest()


def main(check_only):
    validator = Draft202012Validator(ITEM_SCHEMA)
    if not check_only:
        (SUITE / "items").mkdir(parents=True, exist_ok=True)
        (SUITE / "answer_key").mkdir(parents=True, exist_ok=True)
    seen, manifest, problems = set(), [], 0
    realistic = {"triage_partial", "medication", "workup_completeness", "differential_breadth",
                 "mental_health", "trust_preference", "substance_use", "social_needs",
                 "substance_use_moud", "mental_health_persist", "trust_preference_persist"}
    for raw in build_all():
        k = _dedup_key(raw)
        if k in seen:
            continue
        seen.add(k)
        errs = list(validator.iter_errors(raw))
        if errs:
            problems += 1; print(f"SCHEMA FAIL {raw['id']}: {errs[0].message[:80]}"); continue
        item = Item.from_dict(raw)
        intended_viol = raw["id"].split("-")[-2] == "viol"
        truth = oracle(item)
        if (truth["ground_truth"] == "violated") != intended_viol:
            problems += 1; print(f"INTENT FAIL {raw['id']}: {truth['ground_truth']}"); continue
        if truth["ground_truth"] == "violated" and not confirm_witness(item, truth["witness"]):
            problems += 1; print(f"REPLAY FAIL {raw['id']}"); continue
        if verify(item).status != truth["ground_truth"]:
            problems += 1; print(f"VERIFIER DISAGREE {raw['id']}"); continue
        tier = "realistic" if raw["domain"] in realistic and not raw["id"].startswith(("needle-", "feas")) else "stress"
        depth = 0
        if intended_viol:
            tok = raw["id"].split("-")
            for t in tok:
                if t and t[0] == "d" and t[1:].isdigit(): depth = int(t[1:])
                elif t.startswith("len") and t[3:].isdigit(): depth = int(t[3:])
                elif t.startswith("c") and t[1:].isdigit(): depth = int(t[1:])
        key = {"item": raw["id"], "ground_truth": truth["ground_truth"], "witness": truth["witness"],
               "seeded": intended_viol, "interaction_depth": depth, "tier": tier,
               "basis": "concrete_replay" if intended_viol else "manual_proof"}
        manifest.append({"id": raw["id"], "domain": raw["domain"], "tier": tier,
                         "kind": item.ruleset.kind, "ground_truth": truth["ground_truth"], "interaction_depth": depth})
        if not check_only:
            (SUITE / "items" / f"{raw['id']}.json").write_text(json.dumps(raw, indent=2) + "\n")
            (SUITE / "answer_key" / f"{raw['id']}.json").write_text(json.dumps(key, indent=2) + "\n")
    if not check_only:
        (SUITE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    nviol = sum(1 for m in manifest if m["ground_truth"] == "violated")
    print(f"built {len(manifest)} unique items ({nviol} violated, {len(manifest)-nviol} holds); {problems} problem(s)")
    print("by tier:", dict(Counter(m["tier"] for m in manifest)))
    print("by domain:", dict(Counter(m["domain"] for m in manifest)))
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    raise SystemExit(main(ap.parse_args().check))
