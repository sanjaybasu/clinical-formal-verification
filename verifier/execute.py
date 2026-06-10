"""Concrete execution and the independent ground-truth oracle.

This module contains no SMT solver. It evaluates expressions and rule sets on concrete
inputs, and establishes ground truth by exhaustive enumeration (decision rule sets) or
bounded breadth-first reachability (transition systems). The oracle is what makes the
benchmark non-circular: it labels items without the solver under test, and it confirms a
counterexample by direct execution.
"""

from __future__ import annotations

import itertools
from typing import Any

from .model import DecisionRuleset, Item, Property, TransitionSystem, Var, typing_of


# --------------------------------------------------------------------------- expressions


def _enum_index(var: Var, value) -> int:
    return var.domain.index(value)


def _term(node: dict, env: dict, typing: dict[str, Var], expected: Var | None):
    """Evaluate a non-temporal expression to a Python bool or int."""
    if "var" in node:
        name = node["var"]
        v = typing[name]
        val = env[name]
        if v.type == "enum":
            return _enum_index(v, val)
        return val  # bool or int
    if "const" in node:
        c = node["const"]
        if isinstance(c, str) and expected is not None and expected.type == "enum":
            return _enum_index(expected, c)
        return c
    op = node["op"]
    args = node["args"]

    if op in ("and", "or", "not", "implies", "iff"):
        vals = [_term(a, env, typing, None) for a in args]
        if op == "and":
            return all(vals)
        if op == "or":
            return any(vals)
        if op == "not":
            return not vals[0]
        if op == "implies":
            return (not vals[0]) or vals[1]
        if op == "iff":
            return bool(vals[0]) == bool(vals[1])
    if op in ("eq", "neq", "lt", "le", "gt", "ge"):
        a, b = args
        ea, eb = _expected_of(a, typing), _expected_of(b, typing)
        va = _term(a, env, typing, eb)
        vb = _term(b, env, typing, ea)
        if op == "eq":
            return va == vb
        if op == "neq":
            return va != vb
        if op == "lt":
            return va < vb
        if op == "le":
            return va <= vb
        if op == "gt":
            return va > vb
        if op == "ge":
            return va >= vb
    if op in ("add", "sub", "mul", "neg"):
        vals = [_term(a, env, typing, None) for a in args]
        if op == "add":
            return vals[0] + vals[1]
        if op == "sub":
            return vals[0] - vals[1]
        if op == "mul":
            return vals[0] * vals[1]
        if op == "neg":
            return -vals[0]
    if op == "ite":
        cond, then, els = args
        return _term(then, env, typing, expected) if _term(cond, env, typing, None) else _term(els, env, typing, expected)
    raise ValueError(f"non-temporal evaluator received operator {op!r}")


def _expected_of(node: dict, typing: dict[str, Var]) -> Var | None:
    """If node is a variable reference, return its Var (used to resolve enum-label consts)."""
    if "var" in node:
        return typing.get(node["var"])
    return None


def eval_bool(node: dict, env: dict, typing: dict[str, Var]) -> bool:
    return bool(_term(node, env, typing, None))


# --------------------------------------------------------------------------- decision rule sets


def run_decision(rs: DecisionRuleset, inputs: dict) -> dict:
    """Evaluate the rule set on a concrete input assignment; return the output assignment."""
    typing = typing_of(rs.inputs)
    out: dict[str, Any] = {}

    if rs.conflict_resolution == "priority":
        ordered = sorted(rs.rules, key=lambda r: -r.priority)
    elif rs.conflict_resolution == "first_match":
        ordered = list(rs.rules)
    else:
        raise NotImplementedError(f"conflict_resolution {rs.conflict_resolution!r}")

    for rule in ordered:
        if eval_bool(rule.when, inputs, typing):
            for asn in rule.then:
                if asn["var"] not in out:  # first (highest-priority) writer wins per output
                    out[asn["var"]] = asn["value"]
    for asn in rs.default:
        if asn["var"] not in out:
            out[asn["var"]] = asn["value"]
    return out


def _property_holds_at_decision(item: Item, inputs: dict) -> bool:
    """True if the property is satisfied at this concrete input; False if violated here."""
    rs: DecisionRuleset = item.ruleset
    prop = item.property
    out = run_decision(rs, inputs)
    env = {**inputs, **out}
    typing = typing_of(rs.inputs + rs.outputs)

    if prop.kind in ("invariant",):
        return eval_bool(prop.formula, env, typing)
    if prop.kind == "reachability":
        return not eval_bool(prop.formula, env, typing)  # forbidden pattern must not be reachable
    if prop.kind == "mutual_exclusion":
        for a, b in prop.mutual_exclusion["pairs"]:
            if eval_bool(a, env, typing) and eval_bool(b, env, typing):
                return False
        return True
    raise ValueError(f"single-point property kind {prop.kind!r} not handled here")


def oracle_decision(item: Item) -> dict:
    """Ground truth for a decision item by exhaustive enumeration of the input space.

    Independent of any SMT solver. Returns {ground_truth, witness, space}.
    """
    rs: DecisionRuleset = item.ruleset
    names = [v.name for v in rs.inputs]
    spaces = [v.values() for v in rs.inputs]

    if item.property.kind == "monotonicity":
        return _oracle_monotonicity(item, names, spaces)

    for combo in itertools.product(*spaces):
        inputs = dict(zip(names, combo))
        if not _property_holds_at_decision(item, inputs):
            return {
                "ground_truth": "violated",
                "witness": [{"var": k, "value": v} for k, v in inputs.items()],
                "space": rs.input_space(),
            }
    return {"ground_truth": "holds", "witness": None, "space": rs.input_space()}


def _oracle_monotonicity(item: Item, names: list[str], spaces: list[list]) -> dict:
    rs: DecisionRuleset = item.ruleset
    mono = item.property.monotonicity
    pvar = mono["perturbation"]["var"]
    change = mono["perturbation"]["change"]
    mvar_name = mono["monotone_var"]
    direction = mono["direction"]
    out_typing = typing_of(rs.outputs)
    mvar = out_typing[mvar_name]

    def mono_value(out: dict) -> int:
        val = out[mvar_name]
        return mvar.domain.index(val) if mvar.type == "enum" else val

    in_typing = typing_of(rs.inputs)
    pv = in_typing[pvar]

    for combo in itertools.product(*spaces):
        base = dict(zip(names, combo))
        pert = dict(base)
        if change == "set_true":
            if base[pvar] is True:
                continue  # already true; the perturbed point is the base itself
            pert[pvar] = True
        elif change == "increase":
            lo, hi = pv.bounds
            if base[pvar] >= hi:
                continue
            pert[pvar] = base[pvar] + 1
        else:
            raise NotImplementedError(change)
        m0 = mono_value(run_decision(rs, base))
        m1 = mono_value(run_decision(rs, pert))
        bad = m1 < m0 if direction == "nondecreasing" else m1 > m0
        if bad:
            return {
                "ground_truth": "violated",
                "witness": [{"var": k, "value": v} for k, v in pert.items()]
                + [{"var": f"{k}__base", "value": v} for k, v in base.items()],
                "space": rs.input_space(),
            }
    return {"ground_truth": "holds", "witness": None, "space": rs.input_space()}


# --------------------------------------------------------------------------- transition systems


def _apply_update(ts: TransitionSystem, state: dict, update: list[dict], event_params: dict) -> dict:
    typing = typing_of(ts.state_vars)
    env = {**state, **event_params}
    nxt = dict(state)
    for asn in update:
        nxt[asn["var"]] = _term(asn["expr"], env, typing, typing.get(asn["var"]))
        # enum updates expressed as index ints get mapped back to labels
        var = typing.get(asn["var"])
        if var is not None and var.type == "enum" and isinstance(nxt[asn["var"]], int):
            nxt[asn["var"]] = var.domain[nxt[asn["var"]]]
    return nxt


def _init_state(ts: TransitionSystem) -> dict:
    return {asn["var"]: asn["value"] for asn in ts.init}


def _enabled_next(ts: TransitionSystem, state: dict):
    """Yield (event_name, transition_id, next_state) for every fireable action.

    Event parameters with finite domains are enumerated. A transition fires if its event
    matches and its guard holds; if no transition matches an event, the event stutters
    (state unchanged, transition_id None), which models an event that the system ignores.
    """
    typing = typing_of(ts.state_vars)
    for event in ts.events:
        param_names = [p.name for p in event.params]
        param_spaces = [p.values() for p in event.params]
        for combo in itertools.product(*param_spaces) if param_spaces else [()]:
            params = dict(zip(param_names, combo))
            fired = False
            for tr in ts.transitions:
                if tr.event != event.name:
                    continue
                env = {**state, **params}
                if tr.guard is None or eval_bool(tr.guard, env, {**typing, **typing_of(event.params)}):
                    yield event.name, tr.id, _apply_update(ts, state, tr.update, params)
                    fired = True
            if not fired:
                yield event.name, None, dict(state)  # stutter


def oracle_transition(item: Item, bound: int | None = None) -> dict:
    """Ground truth for a transition-system item by bounded breadth-first reachability.

    Checks a G(phi) property: phi must hold in every reachable state up to `bound` steps.
    Independent of any SMT solver. Returns {ground_truth, witness (event trace), space}.
    """
    ts: TransitionSystem = item.ruleset
    prop = item.property
    bound = bound if bound is not None else (prop.bound or 8)
    phi = _global_body(prop.formula)
    typing = typing_of(ts.state_vars)

    start = _init_state(ts)
    frontier = [(start, [])]
    seen = {tuple(sorted(start.items()))}
    if not eval_bool(phi, start, typing):
        return {"ground_truth": "violated", "witness": [], "space": None}

    for _ in range(bound):
        nxt_frontier = []
        for state, trace in frontier:
            for event_name, tr_id, nxt in _enabled_next(ts, state):
                step = {"event": event_name} | ({"transition": tr_id} if tr_id else {})
                if not eval_bool(phi, nxt, typing):
                    return {"ground_truth": "violated", "witness": trace + [step], "space": None}
                key = tuple(sorted(nxt.items()))
                if key not in seen:
                    seen.add(key)
                    nxt_frontier.append((nxt, trace + [step]))
        frontier = nxt_frontier
        if not frontier:
            break
    return {"ground_truth": "holds", "witness": None, "space": len(seen)}


def _global_body(formula: dict) -> dict:
    """Extract phi from G(phi); the oracle handles the safety pattern G(phi)."""
    if formula.get("op") == "G":
        return formula["args"][0]
    raise NotImplementedError("oracle supports temporal properties of the form G(phi) only")


def oracle(item: Item) -> dict:
    """Dispatch to the decision or transition oracle."""
    if item.is_decision:
        return oracle_decision(item)
    return oracle_transition(item)
