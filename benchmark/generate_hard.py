"""Generate CIV-Bench-Hard: emergent reachability that requires multi-step planning.

Each item is a messaging state machine guarded by a combination lock. After opt-out, a faulty
resume path can send a message, but only once a stage counter has been advanced from 0 to L by
pressing a secret sequence of L keys in order; a wrong key resets the counter to 0. The safety
property is the same as the outreach domain: no message after opt-out.

Reaching the violation therefore requires discovering and executing an exact length-L sequence.
This is a planning and state-tracking task whose difficulty grows with L. The compositionality
literature predicts that a language model's ability to assemble a correct multi-step witness
decays as L grows, even when it can state that a violation exists; random testing must hit the
exact combination (probability about m^-L); complete verification finds it by bounded model
checking. Ground truth and the witness are established by the breadth-first oracle and confirmed
by concrete replay, with no solver.

    python benchmark/generate_hard.py [--check]
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
from verifier.smt import verify

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "benchmark" / "suite_hard"
ITEM_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "benchmark.schema.json").read_text())

LOCK_LENGTHS = [2, 4, 6, 8, 10, 12]
N_VIOLATED_PER_LEN = 8
N_HOLDS = 12
N_KEYS = 3


def _stage_eq(i):
    return {"op": "eq", "args": [{"var": "stage"}, {"const": i}]}


def lock_item(length: int, seed: int, holds: bool) -> dict:
    rng = random.Random(_seed("lock", length, seed, holds))
    secret = [rng.randrange(N_KEYS) for _ in range(length)]
    keys = [f"key_{j}" for j in range(N_KEYS)]

    transitions = [
        {"id": "t_optout", "event": "optout",
         "update": [{"var": "opted_out", "expr": {"const": True}}, {"var": "sent", "expr": {"const": False}}]},
        {"id": "t_send_allowed", "event": "send_attempt",
         "guard": {"op": "not", "args": [{"var": "opted_out"}]},
         "update": [{"var": "sent", "expr": {"const": True}}], "emits": [{"action": "send_message"}]},
    ]
    # combination lock: correct key advances the stage; any wrong key resets it to zero
    for i in range(length):
        transitions.append({
            "id": f"adv_{i}", "event": f"key_{secret[i]}", "guard": _stage_eq(i),
            "update": [{"var": "stage", "expr": {"const": i + 1}}, {"var": "sent", "expr": {"const": False}}]})
        for j in range(N_KEYS):
            if j == secret[i]:
                continue
            transitions.append({
                "id": f"rst_{i}_{j}", "event": f"key_{j}", "guard": _stage_eq(i),
                "update": [{"var": "stage", "expr": {"const": 0}}, {"var": "sent", "expr": {"const": False}}]})

    if holds:
        # opted-out send is always blocked, regardless of the lock
        transitions.append({
            "id": "t_send_blocked", "event": "send_attempt", "guard": {"var": "opted_out"},
            "update": [{"var": "sent", "expr": {"const": False}}]})
    else:
        transitions.append({
            "id": "t_send_blocked", "event": "send_attempt",
            "guard": {"op": "and", "args": [{"var": "opted_out"}, {"op": "lt", "args": [{"var": "stage"}, {"const": length}]}]},
            "update": [{"var": "sent", "expr": {"const": False}}]})
        transitions.append({  # seeded fault: once the lock is open, opted-out send goes through
            "id": "t_resume_glitch", "event": "send_attempt",
            "guard": {"op": "and", "args": [{"var": "opted_out"}, {"op": "ge", "args": [{"var": "stage"}, {"const": length}]}]},
            "update": [{"var": "sent", "expr": {"const": True}}], "emits": [{"action": "send_message"}]})

    return {
        "id": f"lock-len{length:02d}-{'hold' if holds else 'viol'}-{seed:02d}",
        "domain": "outreach",
        "metadata": {
            "description": "messaging state machine behind a combination lock; no message after opt-out",
            "source": "synthetic",
            "clinical_intent": "once a member opts out, no event sequence may cause a message to be sent",
        },
        "ruleset": {
            "id": f"lock-{length}-{seed}",
            "kind": "transition_system",
            "state_vars": [
                {"name": "opted_out", "type": "bool"},
                {"name": "sent", "type": "bool"},
                {"name": "stage", "type": "int", "bounds": [0, length]},
            ],
            "events": [{"name": "optout"}, {"name": "send_attempt"}] + [{"name": k} for k in keys],
            "init": [{"var": "opted_out", "value": False}, {"var": "sent", "value": False},
                     {"var": "stage", "value": 0}],
            "transitions": transitions,
        },
        "property": {
            "id": "no-send-after-optout",
            "kind": "temporal",
            "formula": {"op": "G", "args": [{"op": "implies", "args": [
                {"var": "opted_out"}, {"op": "not", "args": [{"var": "sent"}]}]}]},
            "bound": length + 3,
            "intent": "in every reachable state with opted_out true, sent is false",
        },
    }


def build_all():
    items = []
    for L in LOCK_LENGTHS:
        for seed in range(N_VIOLATED_PER_LEN):
            items.append(lock_item(L, seed, holds=False))
    for seed in range(N_HOLDS):
        L = LOCK_LENGTHS[seed % len(LOCK_LENGTHS)]
        items.append(lock_item(L, 100 + seed, holds=True))
    return items


def main(check_only: bool) -> int:
    validator = Draft202012Validator(ITEM_SCHEMA)
    manifest, problems = [], 0
    if not check_only:
        (SUITE / "items").mkdir(parents=True, exist_ok=True)
        (SUITE / "answer_key").mkdir(parents=True, exist_ok=True)
    for raw in build_all():
        errs = list(validator.iter_errors(raw))
        if errs:
            problems += 1; print(f"SCHEMA FAIL {raw['id']}: {errs[0].message}"); continue
        item = Item.from_dict(raw)
        L = int(raw["id"].split("-len")[1].split("-")[0])
        truth = oracle_transition(item, bound=L + 3)
        intended_violation = raw["id"].split("-")[2] == "viol"
        if intended_violation and truth["ground_truth"] != "violated":
            problems += 1; print(f"INTENT FAIL {raw['id']}: oracle says holds"); continue
        if not intended_violation and truth["ground_truth"] != "holds":
            problems += 1; print(f"INTENT FAIL {raw['id']}: oracle says violated"); continue
        if truth["ground_truth"] == "violated" and not confirm_witness(item, truth["witness"]):
            problems += 1; print(f"REPLAY FAIL {raw['id']}"); continue
        key = {"item": raw["id"], "ground_truth": truth["ground_truth"], "witness": truth["witness"],
               "seeded": intended_violation, "interaction_depth": L if intended_violation else 0,
               "basis": "concrete_replay" if intended_violation else "manual_proof"}
        if intended_violation:
            key["seeded_bug"] = (f"a combination lock of length {L} gates a faulty opted-out send; "
                                 "the violation requires entering the exact secret key sequence")
        manifest.append({"id": raw["id"], "domain": "outreach", "kind": "transition_system",
                         "ground_truth": truth["ground_truth"],
                         "interaction_depth": key["interaction_depth"], "space": truth.get("space")})
        if not check_only:
            (SUITE / "items" / f"{raw['id']}.json").write_text(json.dumps(raw, indent=2) + "\n")
            (SUITE / "answer_key" / f"{raw['id']}.json").write_text(json.dumps(key, indent=2) + "\n")
    if not check_only:
        (SUITE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    n_viol = sum(1 for m in manifest if m["ground_truth"] == "violated")
    print(f"built {len(manifest)} hard items ({n_viol} violated, {len(manifest)-n_viol} holds); {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    raise SystemExit(main(ap.parse_args().check))
