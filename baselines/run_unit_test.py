"""Unit-test suite baseline: random testing, the current quality-assurance practice.

Draws N uniform random inputs (decision rule sets) or random event sequences (transition
systems) per item with a fixed seed, executes the rule set, and returns violated if any sampled
point violates the property, else holds. Testing raises no false alarm by construction: it only
reports a violation when it has executed a concrete failing case. It misses violations whose
witnesses are rare, which is expected to worsen with interaction depth.

    python baselines/run_unit_test.py
"""

from __future__ import annotations

import hashlib
import random

from baselines.common import run_method
from verifier.execute import (
    _apply_update,
    _global_body,
    _init_state,
    _property_holds_at_decision,
    eval_bool,
    run_decision,
)
from verifier.model import DecisionRuleset, Item, TransitionSystem, typing_of

N_SAMPLES = 1000
SEED = 20260610


def _sample_value(rng, var):
    if var.type == "bool":
        return rng.choice([False, True])
    if var.type == "enum":
        return rng.choice(var.domain)
    lo, hi = var.bounds
    return rng.randint(lo, hi)


def _test_decision(item: Item, rng) -> tuple:
    rs: DecisionRuleset = item.ruleset
    for _ in range(N_SAMPLES):
        inputs = {v.name: _sample_value(rng, v) for v in rs.inputs}
        if not _property_holds_at_decision(item, inputs):
            return "violated", [{"var": k, "value": v} for k, v in inputs.items()]
    return "holds", None


def _test_monotonicity(item: Item, rng) -> tuple:
    rs: DecisionRuleset = item.ruleset
    mono = item.property.monotonicity
    pvar, change = mono["perturbation"]["var"], mono["perturbation"]["change"]
    mname, direction = mono["monotone_var"], mono["direction"]
    in_typing = typing_of(rs.inputs)
    mvar = typing_of(rs.outputs)[mname]

    def mv(out):
        val = out[mname]
        return mvar.domain.index(val) if mvar.type == "enum" else val

    for _ in range(N_SAMPLES):
        base = {v.name: _sample_value(rng, v) for v in rs.inputs}
        pert = dict(base)
        if change == "set_true":
            base[pvar] = False
            pert[pvar] = True
        else:
            lo, hi = in_typing[pvar].bounds
            base[pvar] = rng.randint(lo, hi - 1) if hi > lo else lo
            pert[pvar] = min(base[pvar] + 1, hi)
        m0, m1 = mv(run_decision(rs, base)), mv(run_decision(rs, pert))
        bad = m1 < m0 if direction == "nondecreasing" else m1 > m0
        if bad:
            return "violated", [{"var": k, "value": v} for k, v in pert.items()] + \
                [{"var": f"{k}__base", "value": v} for k, v in base.items()]
    return "holds", None


def _test_transition(item: Item, rng) -> tuple:
    ts: TransitionSystem = item.ruleset
    phi = _global_body(item.property.formula)
    typing = typing_of(ts.state_vars)
    bound = item.property.bound or 8
    event_names = [e.name for e in ts.events]

    for _ in range(N_SAMPLES):
        state = _init_state(ts)
        trace = []
        for _ in range(bound):
            ev = rng.choice(event_names)
            fireable = [t for t in ts.transitions
                        if t.event == ev and (t.guard is None or eval_bool(t.guard, state, typing))]
            if fireable:
                tr = rng.choice(fireable)
                state = _apply_update(ts, state, tr.update, {})
                trace.append({"event": ev, "transition": tr.id})
            else:
                trace.append({"event": ev})  # stutter
            if not eval_bool(phi, state, typing):
                return "violated", trace
    return "holds", None


def verdict_for(item: Item):
    # stable, process-independent seed (Python's tuple hash is salted per process)
    rng = random.Random(int(hashlib.sha256(f"{SEED}:{item.id}".encode()).hexdigest(), 16) % (2**32))
    if item.is_decision:
        if item.property.kind == "monotonicity":
            verdict, witness = _test_monotonicity(item, rng)
        else:
            verdict, witness = _test_decision(item, rng)
    else:
        verdict, witness = _test_transition(item, rng)
    return verdict, witness, {"n_samples": N_SAMPLES, "seed": SEED}


if __name__ == "__main__":
    print(run_method("unit_test", verdict_for))
