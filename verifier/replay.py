"""Replay a counterexample by concrete execution.

A counterexample from the solver is only trustworthy if it can be replayed: run the rule set on
the witness and observe the violated property, without the solver. This module closes that loop
and renders a counterexample as a short scenario for a case study.
"""

from __future__ import annotations

from .execute import (
    _global_body,
    _init_state,
    _apply_update,
    eval_bool,
    run_decision,
)
from .model import DecisionRuleset, Item, TransitionSystem, typing_of


def confirm_witness(item: Item, witness: list[dict]) -> bool:
    """True if executing the rule set on the witness exhibits the property violation."""
    if item.is_decision:
        return _confirm_decision(item, witness)
    return _confirm_transition(item, witness)


def _confirm_decision(item: Item, witness: list[dict]) -> bool:
    rs: DecisionRuleset = item.ruleset
    prop = item.property
    wmap = {w["var"]: w["value"] for w in witness}

    if prop.kind == "monotonicity":
        mono = prop.monotonicity
        mname = mono["monotone_var"]
        out_typing = typing_of(rs.outputs)
        mvar = out_typing[mname]
        base = {k[: -len("__base")]: v for k, v in wmap.items() if k.endswith("__base")}
        pert = {k: v for k, v in wmap.items() if not k.endswith("__base")}

        def mv(out):
            val = out[mname]
            return mvar.domain.index(val) if mvar.type == "enum" else val

        m_b, m_p = mv(run_decision(rs, base)), mv(run_decision(rs, pert))
        return m_p < m_b if mono["direction"] == "nondecreasing" else m_p > m_b

    inputs = {v.name: wmap[v.name] for v in rs.inputs}
    out = run_decision(rs, inputs)
    env = {**inputs, **out}
    typing = typing_of(rs.inputs + rs.outputs)
    if prop.kind == "invariant":
        return not eval_bool(prop.formula, env, typing)
    if prop.kind == "reachability":
        return eval_bool(prop.formula, env, typing)
    if prop.kind == "mutual_exclusion":
        return any(
            eval_bool(a, env, typing) and eval_bool(b, env, typing)
            for a, b in prop.mutual_exclusion["pairs"]
        )
    raise ValueError(prop.kind)


def _confirm_transition(item: Item, witness: list[dict]) -> bool:
    """A transition witness is confirmed if some execution consistent with the event sequence
    reaches a state violating the invariant. When a step names a transition that branch is taken;
    otherwise every enabled transition for the event is explored, since an event-only witness
    leaves the transition choice nondeterministic.
    """
    ts: TransitionSystem = item.ruleset
    phi = _global_body(item.property.formula)
    typing = typing_of(ts.state_vars)
    start = _init_state(ts)
    if not eval_bool(phi, start, typing):
        return True

    frontier = [start]
    for step in witness:
        if step.get("event") == "stutter":
            continue
        named = step.get("transition")
        event = step["event"]
        event_exists = any(t.event == event for t in ts.transitions)
        nxt_frontier = []
        for state in frontier:
            matched = False
            for tr in ts.transitions:
                if tr.event != event or (named is not None and tr.id != named):
                    continue
                if tr.guard is not None and not eval_bool(tr.guard, state, typing):
                    continue
                matched = True
                nxt = _apply_update(ts, state, tr.update, {})
                if not eval_bool(phi, nxt, typing):
                    return True
                nxt_frontier.append(nxt)
            if not matched and not event_exists:
                nxt_frontier.append(state)  # event the system ignores: stutter
        if nxt_frontier:
            frontier = nxt_frontier
    return False


def _pick_transition(ts: TransitionSystem, state: dict, typing: dict, step: dict):
    """Choose the transition named in the trace step, else the first enabled match for the event."""
    candidates = [t for t in ts.transitions if t.event == step["event"]]
    named = step.get("transition")
    if named is not None:
        for t in candidates:
            if t.id == named:
                return t
    for t in candidates:
        if t.guard is None or eval_bool(t.guard, state, typing):
            return t
    return None


def render_decision_scenario(item: Item, witness: list[dict]) -> str:
    """Render a decision counterexample as input, output, and the violated property."""
    rs: DecisionRuleset = item.ruleset
    wmap = {w["var"]: w["value"] for w in witness if not w["var"].endswith("__base")}
    inputs = {v.name: wmap.get(v.name) for v in rs.inputs}
    out = run_decision(rs, inputs)
    lines = [f"input:  {inputs}", f"output: {out}",
             f"property {item.property.id} ({item.property.kind}) is violated at this input"]
    return "\n".join(lines)


def render_transition_scenario(item: Item, witness: list[dict]) -> str:
    ts: TransitionSystem = item.ruleset
    phi = _global_body(item.property.formula)
    typing = typing_of(ts.state_vars)
    state = _init_state(ts)
    lines = [f"init:   {state}"]
    for step in witness:
        if step["event"] == "stutter":
            continue
        tr = _pick_transition(ts, state, typing, step)
        if tr is not None:
            state = _apply_update(ts, state, tr.update, {})
            lines.append(f"event {step['event']:14s} -> {state}")
    lines.append(f"property {item.property.id} ({item.property.kind}) is violated on this trace")
    return "\n".join(lines)


def render_scenario(item: Item, witness: list[dict]) -> str:
    if item.is_decision:
        return render_decision_scenario(item, witness)
    return render_transition_scenario(item, witness)
