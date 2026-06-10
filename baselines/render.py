"""Render a benchmark item as a readable specification for a language-model judge.

The judge is given a clean rendering of the rule set and the property, not the raw JSON, so the
test measures reasoning about the rules rather than parsing. The rendering is faithful to the
executable semantics: priority resolution, defaults, and the exact property.
"""

from __future__ import annotations

from .common import SUITE  # noqa: F401  (kept for path parity)
from verifier.model import DecisionRuleset, Item, TransitionSystem

_CMP = {"eq": "==", "neq": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">="}
_ARITH = {"add": "+", "sub": "-", "mul": "*"}
_TEMPORAL = {"G": "globally", "F": "eventually", "X": "next", "U": "until", "R": "release", "W": "weak-until"}


def expr_str(node: dict) -> str:
    if "var" in node:
        return node["var"]
    if "const" in node:
        c = node["const"]
        return str(c).lower() if isinstance(c, bool) else (f'"{c}"' if isinstance(c, str) else str(c))
    op, args = node["op"], node["args"]
    if op == "and":
        return "(" + " and ".join(expr_str(a) for a in args) + ")"
    if op == "or":
        return "(" + " or ".join(expr_str(a) for a in args) + ")"
    if op == "not":
        return f"not {expr_str(args[0])}"
    if op == "implies":
        return f"({expr_str(args[0])} implies {expr_str(args[1])})"
    if op == "iff":
        return f"({expr_str(args[0])} iff {expr_str(args[1])})"
    if op in _CMP:
        return f"{expr_str(args[0])} {_CMP[op]} {expr_str(args[1])}"
    if op in _ARITH:
        return f"({expr_str(args[0])} {_ARITH[op]} {expr_str(args[1])})"
    if op == "neg":
        return f"-{expr_str(args[0])}"
    if op == "ite":
        return f"(if {expr_str(args[0])} then {expr_str(args[1])} else {expr_str(args[2])})"
    if op in _TEMPORAL:
        return f"{_TEMPORAL[op]}({', '.join(expr_str(a) for a in args)})"
    return f"{op}({', '.join(expr_str(a) for a in args)})"


def _var_line(v) -> str:
    if v.type == "bool":
        return f"  {v.name}: boolean"
    if v.type == "enum":
        return f"  {v.name}: one of [{', '.join(v.domain)}] (ordered low to high)"
    return f"  {v.name}: integer in [{v.bounds[0]}, {v.bounds[1]}]"


def _render_decision(rs: DecisionRuleset) -> str:
    lines = ["Inputs:"]
    lines += [_var_line(v) for v in rs.inputs]
    lines.append("Outputs:")
    lines += [_var_line(v) for v in rs.outputs]
    lines.append(f"Conflict resolution: {rs.conflict_resolution} "
                 "(per output, the matching rule with the highest priority wins; ties broken by order)")
    lines.append("Rules:")
    for r in rs.rules:
        then = ", ".join(f"{a['var']} := {str(a['value']).lower() if isinstance(a['value'], bool) else a['value']}"
                         for a in r.then)
        lines.append(f"  [{r.id}, priority {r.priority}] IF {expr_str(r.when)} THEN {then}")
    dflt = ", ".join(f"{a['var']} := {str(a['value']).lower() if isinstance(a['value'], bool) else a['value']}"
                     for a in rs.default)
    lines.append(f"Default (for any output left unset): {dflt}")
    return "\n".join(lines)


def _render_transition(ts: TransitionSystem) -> str:
    lines = ["State variables:"]
    lines += [_var_line(v) for v in ts.state_vars]
    init = ", ".join(f"{a['var']} = {str(a['value']).lower() if isinstance(a['value'], bool) else a['value']}"
                     for a in ts.init)
    lines.append(f"Initial state: {init}")
    lines.append(f"Events: {', '.join(e.name for e in ts.events)}")
    lines.append("Transitions (on the named event, if the guard holds, apply the update; "
                 "an event with no matching enabled transition leaves the state unchanged):")
    for t in ts.transitions:
        guard = expr_str(t.guard) if t.guard else "true"
        upd = ", ".join(f"{u['var']} := {expr_str(u['expr'])}" for u in t.update)
        lines.append(f"  [{t.id}] on {t.event} if {guard}: {upd}")
    return "\n".join(lines)


def _render_property(item: Item) -> str:
    p = item.property
    if p.kind == "monotonicity":
        m = p.monotonicity
        chg = "set to true" if m["perturbation"]["change"] == "set_true" else "increased by one"
        return (f"Property (monotonicity): for any input, if {m['perturbation']['var']} is {chg} "
                f"while every other input is unchanged, then {m['monotone_var']} must be "
                f"{'no lower' if m['direction'] == 'nondecreasing' else 'no higher'} than before "
                "(enum order is the listed order).")
    if p.kind == "mutual_exclusion":
        pairs = "; ".join(f"({expr_str(a)} and {expr_str(b)})" for a, b in p.mutual_exclusion["pairs"])
        return f"Property (mutual exclusion): no input may make any of these jointly true: {pairs}."
    if p.kind == "invariant":
        return f"Property (invariant): for every input, the following must hold: {expr_str(p.formula)}."
    if p.kind == "reachability":
        return f"Property (reachability): no input may make this forbidden pattern true: {expr_str(p.formula)}."
    if p.kind == "temporal":
        return (f"Property (temporal): on every reachable execution, {expr_str(p.formula)} must hold "
                f"(check executions up to {p.bound} events).")
    return f"Property: {p.kind}"


def render_item(item: Item) -> str:
    body = _render_decision(item.ruleset) if item.is_decision else _render_transition(item.ruleset)
    intent = item.property.intent or ""
    return (
        "You are auditing a clinical decision system for a safety property. Decide whether the "
        "property holds for the entire input space, or whether some input or execution violates "
        "it.\n\n"
        f"{body}\n\n{_render_property(item)}\n"
        f"Plain-language intent: {intent}\n\n"
        "Reason carefully about interactions between rules, priorities, and defaults. Then answer "
        "whether the property holds or is violated. If it is violated, give one concrete "
        "counterexample: for a decision system, the input assignment (every input variable); for a "
        "state machine, the sequence of events. Do not assume a violation exists; many systems are "
        "correct."
    )
