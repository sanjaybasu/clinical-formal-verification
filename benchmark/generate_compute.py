"""Generate CIV-Bench-Compute: violations that require computation, not reading.

Each item is a messaging state machine whose opted-out send is gated by an accumulator that
follows an order-dependent linear-congruential recurrence: each step event maps acc to
(mult * acc + add_j) mod M. The faulty resume path fires only when acc reaches a hidden target.
Unlike the explicit faults in CIV-Bench and the readable secret in CIV-Bench-Hard, the arming
sequence is not present anywhere in the specification: an auditor must simulate the recurrence and
search the state graph to find a sequence of steps that drives acc from 0 to the target. This is
the multi-step-computation regime in which the compositionality literature predicts language
models degrade. Complete verification solves it by bounded model checking; random testing must
stumble onto a reaching sequence; ground truth is set by the breadth-first oracle over the finite
accumulator and confirmed by concrete replay.

Difficulty is the modulus M (the size of the state graph). Items are not pre-labelled: parameters
are sampled and the oracle classifies each as violated (target reachable within the bound) or
holds (unreachable), keeping the labels honest.

    python benchmark/generate_compute.py [--check]
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from jsonschema import Draft202012Validator

import hashlib


def _seed(*parts):
    """Deterministic 32-bit seed; Python's tuple hash is salted per process."""
    return int(hashlib.sha256("-".join(map(str, parts)).encode()).hexdigest(), 16) % (2**32)

from verifier.execute import oracle_transition
from verifier.model import Item
from verifier.replay import confirm_witness

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "benchmark" / "suite_compute"
ITEM_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "benchmark.schema.json").read_text())

MODULI = [8, 16, 32, 48, 64]
MULT = 3
N_STEPS = 3            # number of distinct step events (graph out-degree)
PER_MODULUS = 14       # candidates sampled per modulus; the oracle splits violated vs holds
TARGET_VIOL = 8        # cap on violated kept per modulus
TARGET_HOLD = 4        # cap on holds kept per modulus


def _mod_reduce(expr_unreduced, M):
    """Reduce x mod M with conditional subtractions; mult=3 so x < 4M needs up to 3 subtractions."""
    x = expr_unreduced
    for _ in range(MULT):
        x = {"op": "ite", "args": [{"op": "ge", "args": [x, {"const": M}]},
                                   {"op": "sub", "args": [x, {"const": M}]}, x]}
    return x


def compute_item(M: int, seed: int) -> dict:
    rng = random.Random(_seed("compute", M, seed))
    adds = [rng.randrange(1, M) for _ in range(N_STEPS)]
    target = rng.randrange(1, M)
    steps = [f"step_{j}" for j in range(N_STEPS)]

    transitions = [
        {"id": "t_optout", "event": "optout",
         "update": [{"var": "opted_out", "expr": {"const": True}}, {"var": "sent", "expr": {"const": False}}]},
        {"id": "t_send_allowed", "event": "send_attempt", "guard": {"op": "not", "args": [{"var": "opted_out"}]},
         "update": [{"var": "sent", "expr": {"const": True}}], "emits": [{"action": "send_message"}]},
        {"id": "t_send_blocked", "event": "send_attempt",
         "guard": {"op": "and", "args": [{"var": "opted_out"}, {"op": "neq", "args": [{"var": "acc"}, {"const": target}]}]},
         "update": [{"var": "sent", "expr": {"const": False}}]},
        {"id": "t_resume_glitch", "event": "send_attempt",
         "guard": {"op": "and", "args": [{"var": "opted_out"}, {"op": "eq", "args": [{"var": "acc"}, {"const": target}]}]},
         "update": [{"var": "sent", "expr": {"const": True}}], "emits": [{"action": "send_message"}]},
    ]
    for j, add in enumerate(adds):
        unreduced = {"op": "add", "args": [{"op": "mul", "args": [{"const": MULT}, {"var": "acc"}]}, {"const": add}]}
        transitions.append({
            "id": f"step_{j}", "event": f"step_{j}",
            "update": [{"var": "acc", "expr": _mod_reduce(unreduced, M)}, {"var": "sent", "expr": {"const": False}}]})

    return {
        "id": f"compute-m{M:03d}-{seed:03d}",
        "domain": "outreach",
        "metadata": {
            "description": "messaging state machine gated by a computed accumulator; no message after opt-out",
            "source": "synthetic",
            "clinical_intent": "once a member opts out, no event sequence may cause a message to be sent",
        },
        "ruleset": {
            "id": f"compute-{M}-{seed}",
            "kind": "transition_system",
            "state_vars": [
                {"name": "opted_out", "type": "bool"},
                {"name": "sent", "type": "bool"},
                {"name": "acc", "type": "int", "bounds": [0, M - 1]},
            ],
            "events": [{"name": "optout"}, {"name": "send_attempt"}] + [{"name": s} for s in steps],
            "init": [{"var": "opted_out", "value": False}, {"var": "sent", "value": False},
                     {"var": "acc", "value": 0}],
            "transitions": transitions,
        },
        "property": {
            "id": "no-send-after-optout",
            "kind": "temporal",
            "formula": {"op": "G", "args": [{"op": "implies", "args": [
                {"var": "opted_out"}, {"op": "not", "args": [{"var": "sent"}]}]}]},
            "bound": M + 2,
            "intent": "in every reachable state with opted_out true, sent is false",
        },
        "_meta_target": target, "_meta_adds": adds, "_meta_M": M,
    }


def build_all():
    items = []
    for M in MODULI:
        viol = hold = 0
        for seed in range(PER_MODULUS * 4):
            if viol >= TARGET_VIOL and hold >= TARGET_HOLD:
                break
            raw = compute_item(M, seed)
            truth = oracle_transition(Item.from_dict({k: v for k, v in raw.items() if not k.startswith("_meta")}),
                                      bound=M + 2)
            if truth["ground_truth"] == "violated" and viol < TARGET_VIOL:
                viol += 1; items.append((raw, truth))
            elif truth["ground_truth"] == "holds" and hold < TARGET_HOLD:
                hold += 1; items.append((raw, truth))
    return items


def main(check_only: bool) -> int:
    validator = Draft202012Validator(ITEM_SCHEMA)
    manifest, problems = [], 0
    if not check_only:
        (SUITE / "items").mkdir(parents=True, exist_ok=True)
        (SUITE / "answer_key").mkdir(parents=True, exist_ok=True)
    for raw, truth in build_all():
        M = raw["_meta_M"]
        public = {k: v for k, v in raw.items() if not k.startswith("_meta")}
        errs = list(validator.iter_errors(public))
        if errs:
            problems += 1; print(f"SCHEMA FAIL {raw['id']}: {errs[0].message}"); continue
        item = Item.from_dict(public)
        if truth["ground_truth"] == "violated" and not confirm_witness(item, truth["witness"]):
            problems += 1; print(f"REPLAY FAIL {raw['id']}"); continue
        violated = truth["ground_truth"] == "violated"
        key = {"item": raw["id"], "ground_truth": truth["ground_truth"], "witness": truth["witness"],
               "seeded": violated, "interaction_depth": M if violated else 0,
               "basis": "concrete_replay" if violated else "manual_proof"}
        if violated:
            wlen = len([s for s in truth["witness"] if s.get("event", "").startswith("step")])
            key["seeded_bug"] = (f"accumulator modulus {M}; target reachable by a computed step sequence "
                                 f"of length {wlen}; the arming sequence is not stated in the specification")
        manifest.append({"id": raw["id"], "domain": "outreach", "kind": "transition_system",
                         "ground_truth": truth["ground_truth"], "interaction_depth": key["interaction_depth"],
                         "modulus": M, "space": truth.get("space")})
        if not check_only:
            (SUITE / "items" / f"{raw['id']}.json").write_text(json.dumps(public, indent=2) + "\n")
            (SUITE / "answer_key" / f"{raw['id']}.json").write_text(json.dumps(key, indent=2) + "\n")
    if not check_only:
        (SUITE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    n_viol = sum(1 for m in manifest if m["ground_truth"] == "violated")
    print(f"built {len(manifest)} compute items ({n_viol} violated, {len(manifest)-n_viol} holds); {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    raise SystemExit(main(ap.parse_args().check))
