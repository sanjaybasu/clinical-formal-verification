"""Generate CIV-Bench v0.

Each item embeds a documented rule-interaction fault at a controlled interaction depth, or no
fault. Ground truth is established by the enumeration or breadth-first oracle in
verifier.execute, which uses no SMT solver; every violation witness is then confirmed by
concrete replay. The interaction depth is the number of conditions or events that must combine
to produce the violation, and is the axis along which the compositionality hypothesis is tested:
probabilistic methods are expected to miss violations at greater depth.

Determinism: every item is built from an explicit integer seed; no wall-clock or unseeded
randomness is used, so the suite regenerates identically.

    python benchmark/generate.py            # write suite to benchmark/suite/
    python benchmark/generate.py --check     # regenerate in memory and verify, write nothing
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from jsonschema import Draft202012Validator

from verifier.execute import oracle
from verifier.model import Item
from verifier.replay import confirm_witness
from verifier.smt import verify

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "benchmark" / "suite"
ITEM_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "benchmark.schema.json").read_text())

ACUITY = ["self_care", "routine", "urgent", "emergent"]
DEPTHS = [1, 2, 3, 4]
N_VIOLATED_PER_DEPTH = 10
N_HOLDS = 20

SYMPTOMS = [
    "chest_pain", "dyspnea", "syncope", "focal_weakness", "severe_headache",
    "abdominal_pain", "fever", "vomiting", "rash", "dizziness", "palpitations", "vision_loss",
]
CONDITIONS = [
    "anticoagulated", "renal_impairment", "hepatic_impairment", "pregnancy", "qt_prolongation",
    "peptic_ulcer", "asthma", "heart_failure", "elderly", "polypharmacy", "diabetes", "hypertension",
]


def _and(names):
    if len(names) == 1:
        return {"var": names[0]}
    return {"op": "and", "args": [{"var": n} for n in names]}


# --------------------------------------------------------------------------- triage


def triage_item(depth: int, seed: int, holds: bool) -> dict:
    rng = random.Random(("triage", depth, seed, holds).__hash__() & 0xFFFFFFFF)
    n_extra = rng.randint(1, 3)
    flags = rng.sample(SYMPTOMS, depth + n_extra)
    conj = flags[:depth]
    target = conj[-1]
    raisers = conj[:-1]  # flags that lift the base presentation before the perturbation
    distractors = flags[depth:]

    rules = []
    # monotone base rules: each raiser lifts acuity; priority aligned to level so ties never lower
    for i, f in enumerate(raisers):
        level = 2 + (i % 2)  # urgent or emergent
        rules.append({"id": f"raise_{f}", "priority": level,
                      "when": {"var": f}, "then": [{"var": "acuity", "value": ACUITY[level]}]})
    for f in distractors:
        level = 2 + rng.randint(0, 1)
        rules.append({"id": f"raise_{f}", "priority": level,
                      "when": {"var": f}, "then": [{"var": "acuity", "value": ACUITY[level]}]})
    if not holds:
        # seeded fault: a conjunction of the depth flags drops acuity to the floor
        rules.append({"id": "interaction_drop", "priority": 100,
                      "when": _and(conj), "then": [{"var": "acuity", "value": "self_care"}]})
    rng.shuffle(rules)

    return {
        "id": f"triage-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}",
        "domain": "triage",
        "metadata": {
            "description": "symptom-to-acuity rules; adding a red flag must not lower acuity",
            "source": "synthetic",
            "clinical_intent": "no red-flag symptom, once present, may lower the assigned acuity",
        },
        "ruleset": {
            "id": f"triage-{depth}-{seed}",
            "kind": "decision",
            "inputs": [{"name": f, "type": "bool"} for f in flags],
            "outputs": [{"name": "acuity", "type": "enum", "domain": ACUITY}],
            "rules": rules,
            "default": [{"var": "acuity", "value": "routine"}],
            "conflict_resolution": "priority",
        },
        "property": {
            "id": "redflag-never-lowers-acuity",
            "kind": "monotonicity",
            "monotonicity": {
                "perturbation": {"var": target, "change": "set_true"},
                "monotone_var": "acuity",
                "direction": "nondecreasing",
            },
            "intent": f"setting {target} true never lowers acuity",
        },
    }


# --------------------------------------------------------------------------- medication


def medication_item(depth: int, seed: int, holds: bool) -> dict:
    rng = random.Random(("med", depth, seed, holds).__hash__() & 0xFFFFFFFF)
    n_extra = rng.randint(1, 3)
    conds = rng.sample(CONDITIONS, depth + n_extra)
    conj = conds[:depth]  # rec_a fires on the conjunction of these
    trigger_b = conj[0]   # rec_b fires on the first, so co-occurrence needs the full conjunction

    rules = [
        {"id": "rec_a_from_conjunction", "priority": 50, "when": _and(conj),
         "then": [{"var": "rec_drug_a", "value": True}]},
        {"id": "rec_b_from_trigger", "priority": 50, "when": {"var": trigger_b},
         "then": [{"var": "rec_drug_b", "value": True}]},
    ]
    for c in conds[depth:]:
        rules.append({"id": f"rec_c_from_{c}", "priority": 40, "when": {"var": c},
                      "then": [{"var": "rec_drug_c", "value": True}]})
    if holds:
        # protective guard: whenever rec_a's conjunction holds, suppress rec_b
        rules.append({"id": "guard_suppress_b", "priority": 90, "when": _and(conj),
                      "then": [{"var": "rec_drug_b", "value": False}]})
    rng.shuffle(rules)

    return {
        "id": f"medication-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}",
        "domain": "medication",
        "metadata": {
            "description": "condition-to-recommendation rules; a contraindicated pair must not co-occur",
            "source": "synthetic",
            "clinical_intent": "drugs a and b form a contraindicated pair and must never be jointly recommended",
        },
        "ruleset": {
            "id": f"medication-{depth}-{seed}",
            "kind": "decision",
            "inputs": [{"name": c, "type": "bool"} for c in conds],
            "outputs": [
                {"name": "rec_drug_a", "type": "bool"},
                {"name": "rec_drug_b", "type": "bool"},
                {"name": "rec_drug_c", "type": "bool"},
            ],
            "rules": rules,
            "default": [
                {"var": "rec_drug_a", "value": False},
                {"var": "rec_drug_b", "value": False},
                {"var": "rec_drug_c", "value": False},
            ],
            "conflict_resolution": "priority",
        },
        "property": {
            "id": "no-contraindicated-pair",
            "kind": "mutual_exclusion",
            "mutual_exclusion": {"pairs": [[{"var": "rec_drug_a"}, {"var": "rec_drug_b"}]]},
            "intent": "no input recommends both drug a and drug b",
        },
    }


# --------------------------------------------------------------------------- outreach


def outreach_item(depth: int, seed: int, holds: bool) -> dict:
    # a counter must reach `depth` (via ticks) before a faulty resume path can send after opt-out
    transitions = [
        {"id": "t_optout", "event": "optout",
         "update": [{"var": "opted_out", "expr": {"const": True}}, {"var": "sent", "expr": {"const": False}}]},
        {"id": "t_send_allowed", "event": "send_attempt", "guard": {"op": "not", "args": [{"var": "opted_out"}]},
         "update": [{"var": "sent", "expr": {"const": True}}], "emits": [{"action": "send_message"}]},
        {"id": "t_send_blocked", "event": "send_attempt", "guard": {"var": "opted_out"},
         "update": [{"var": "sent", "expr": {"const": False}}]},
        {"id": "t_tick", "event": "tick",
         "update": [{"var": "ticks", "expr": {"op": "ite", "args": [
             {"op": "lt", "args": [{"var": "ticks"}, {"const": depth}]},
             {"op": "add", "args": [{"var": "ticks"}, {"const": 1}]}, {"var": "ticks"}]}},
            {"var": "sent", "expr": {"const": False}}]},
    ]
    if not holds:
        transitions.append({
            "id": "t_resume_glitch", "event": "send_attempt",
            "guard": {"op": "and", "args": [{"var": "opted_out"},
                                            {"op": "ge", "args": [{"var": "ticks"}, {"const": depth}]}]},
            "update": [{"var": "sent", "expr": {"const": True}}], "emits": [{"action": "send_message"}]})

    return {
        "id": f"outreach-d{depth}-{'hold' if holds else 'viol'}-{seed:02d}",
        "domain": "outreach",
        "metadata": {
            "description": "messaging state machine; no message after opt-out",
            "source": "synthetic",
            "clinical_intent": "once a member opts out, no further message is sent on any event sequence",
        },
        "ruleset": {
            "id": f"outreach-{depth}-{seed}",
            "kind": "transition_system",
            "state_vars": [
                {"name": "opted_out", "type": "bool"},
                {"name": "sent", "type": "bool"},
                {"name": "ticks", "type": "int", "bounds": [0, depth]},
            ],
            "events": [{"name": "optout"}, {"name": "send_attempt"}, {"name": "tick"}],
            "init": [{"var": "opted_out", "value": False}, {"var": "sent", "value": False},
                     {"var": "ticks", "value": 0}],
            "transitions": transitions,
        },
        "property": {
            "id": "no-send-after-optout",
            "kind": "temporal",
            "formula": {"op": "G", "args": [{"op": "implies", "args": [
                {"var": "opted_out"}, {"op": "not", "args": [{"var": "sent"}]}]}]},
            "bound": depth + 4,
            "intent": "in every reachable state with opted_out true, sent is false",
        },
    }


# --------------------------------------------------------------------------- build


def build_all():
    items = []
    for depth in DEPTHS:
        for seed in range(N_VIOLATED_PER_DEPTH):
            items.append(triage_item(depth, seed, holds=False))
            items.append(medication_item(depth, seed, holds=False))
            items.append(outreach_item(depth, seed, holds=False))
    for seed in range(N_HOLDS):
        d = DEPTHS[seed % len(DEPTHS)]
        items.append(triage_item(d, 100 + seed, holds=True))
        items.append(medication_item(d, 100 + seed, holds=True))
        items.append(outreach_item(d, 100 + seed, holds=True))
    return items


def main(check_only: bool) -> int:
    validator = Draft202012Validator(ITEM_SCHEMA)
    raw_items = build_all()
    manifest = []
    problems = 0

    if not check_only:
        (SUITE / "items").mkdir(parents=True, exist_ok=True)
        (SUITE / "answer_key").mkdir(parents=True, exist_ok=True)

    for raw in raw_items:
        errs = list(validator.iter_errors(raw))
        if errs:
            problems += 1
            print(f"SCHEMA FAIL {raw['id']}: {errs[0].message}")
            continue
        item = Item.from_dict(raw)
        truth = oracle(item)
        intended_violation = raw["id"].split("-")[2] == "viol"
        seeded_depth = int(raw["id"].split("-d")[1].split("-")[0])

        if intended_violation and truth["ground_truth"] != "violated":
            problems += 1
            print(f"INTENT FAIL {raw['id']}: expected violated, oracle says holds")
            continue
        if not intended_violation and truth["ground_truth"] != "holds":
            problems += 1
            print(f"INTENT FAIL {raw['id']}: expected holds, oracle says violated")
            continue
        if truth["ground_truth"] == "violated" and not confirm_witness(item, truth["witness"]):
            problems += 1
            print(f"REPLAY FAIL {raw['id']}: oracle witness does not replay to a violation")
            continue

        key = {
            "item": raw["id"],
            "ground_truth": truth["ground_truth"],
            "witness": truth["witness"],
            "seeded": intended_violation,
            "interaction_depth": seeded_depth if intended_violation else 0,
            "basis": "concrete_replay" if intended_violation else "manual_proof",
        }
        if intended_violation:
            key["seeded_bug"] = (
                f"a documented rule interaction at depth {seeded_depth} produces the violation; "
                "see generate.py for the construction"
            )
        else:
            key["notes"] = "no fault seeded; the oracle finds no violation over the finite space"

        manifest.append({
            "id": raw["id"], "domain": raw["domain"],
            "kind": item.ruleset.kind, "ground_truth": truth["ground_truth"],
            "interaction_depth": key["interaction_depth"], "space": truth.get("space"),
        })

        if not check_only:
            (SUITE / "items" / f"{raw['id']}.json").write_text(json.dumps(raw, indent=2) + "\n")
            (SUITE / "answer_key" / f"{raw['id']}.json").write_text(json.dumps(key, indent=2) + "\n")

    if not check_only:
        (SUITE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    n_viol = sum(1 for m in manifest if m["ground_truth"] == "violated")
    print(f"built {len(manifest)} items ({n_viol} violated, {len(manifest) - n_viol} holds); "
          f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify in memory, write nothing")
    args = ap.parse_args()
    raise SystemExit(main(args.check))
