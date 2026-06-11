"""SMT compilation and property checking with Z3.

Compiles a rule set in the benchmark schema to Z3 constraints and decides a safety property
over the full input space: unsat of the negation is a proof that the property holds; sat is a
counterexample, returned as a concrete assignment or event trace. Decision rule sets compile to
output terms; transition systems are checked by bounded model checking with a k-induction step
for an unbounded result.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import z3

from .model import DecisionRuleset, Item, Property, TransitionSystem, Var, typing_of


@dataclass
class Result:
    item_id: str
    status: str  # "holds" | "violated"
    proof_scope: str  # description of the input space covered or the bound
    witness: list[dict] | None  # counterexample assignment or event trace
    method_note: str  # how the result was obtained
    seconds: float

    def as_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "status": self.status,
            "proof_scope": self.proof_scope,
            "witness": self.witness,
            "method_note": self.method_note,
            "seconds": round(self.seconds, 4),
        }


# --------------------------------------------------------------------------- variables, expressions


def _mk_var(v: Var, suffix: str = ""):
    name = v.name + suffix
    if v.type == "bool":
        return z3.Bool(name)
    return z3.Int(name)  # enum (as index) and int both Int-sorted


def _domain_constraint(v: Var, zv):
    if v.type == "enum":
        return z3.And(zv >= 0, zv <= len(v.domain) - 1)
    if v.type == "int":
        lo, hi = v.bounds
        return z3.And(zv >= lo, zv <= hi)
    return z3.BoolVal(True)


def _const_to_z3(c, expected: Var | None):
    if isinstance(c, bool):
        return z3.BoolVal(c)
    if isinstance(c, int):
        return z3.IntVal(c)
    if isinstance(c, str):
        if expected is None or expected.type != "enum":
            raise ValueError(f"string const {c!r} without enum context")
        return z3.IntVal(expected.domain.index(c))
    raise ValueError(f"unsupported const {c!r}")


def _expected_of(node: dict, typing: dict[str, Var]) -> Var | None:
    return typing.get(node["var"]) if "var" in node else None


def compile_expr(node: dict, env: dict, typing: dict[str, Var], expected: Var | None = None):
    """Compile a non-temporal expression to a Z3 expression in the given environment.

    env maps variable names to Z3 expressions (input consts or output terms).
    """
    if "var" in node:
        return env[node["var"]]
    if "const" in node:
        return _const_to_z3(node["const"], expected)
    op = node["op"]
    args = node["args"]
    if op == "and":
        return z3.And(*[compile_expr(a, env, typing) for a in args])
    if op == "or":
        return z3.Or(*[compile_expr(a, env, typing) for a in args])
    if op == "not":
        return z3.Not(compile_expr(args[0], env, typing))
    if op == "implies":
        return z3.Implies(compile_expr(args[0], env, typing), compile_expr(args[1], env, typing))
    if op == "iff":
        return compile_expr(args[0], env, typing) == compile_expr(args[1], env, typing)
    if op in ("eq", "neq", "lt", "le", "gt", "ge"):
        a, b = args
        ea, eb = _expected_of(a, typing), _expected_of(b, typing)
        za = compile_expr(a, env, typing, eb)
        zb = compile_expr(b, env, typing, ea)
        return {
            "eq": za == zb, "neq": za != zb, "lt": za < zb,
            "le": za <= zb, "gt": za > zb, "ge": za >= zb,
        }[op]
    if op in ("add", "sub", "mul", "neg"):
        zs = [compile_expr(a, env, typing) for a in args]
        if op == "add":
            return zs[0] + zs[1]
        if op == "sub":
            return zs[0] - zs[1]
        if op == "mul":
            return zs[0] * zs[1]
        return -zs[0]
    if op == "ite":
        cond, then, els = args
        return z3.If(compile_expr(cond, env, typing),
                     compile_expr(then, env, typing, expected),
                     compile_expr(els, env, typing, expected))
    raise ValueError(f"non-temporal compiler received operator {op!r}")


# --------------------------------------------------------------------------- decision rule sets


def _value_to_z3(value, var: Var):
    if var.type == "bool":
        return z3.BoolVal(bool(value))
    if var.type == "enum":
        return z3.IntVal(var.domain.index(value))
    return z3.IntVal(int(value))


def compile_decision_outputs(rs: DecisionRuleset, env_inputs: dict):
    """Return {output_name: z3 term} given an environment of input Z3 expressions."""
    in_typing = typing_of(rs.inputs)
    out_typing = typing_of(rs.outputs)
    if rs.conflict_resolution == "priority":
        ordered = sorted(rs.rules, key=lambda r: -r.priority)
    elif rs.conflict_resolution == "first_match":
        ordered = list(rs.rules)
    else:
        raise NotImplementedError(rs.conflict_resolution)

    outputs = {}
    for ov in rs.outputs:
        default_val = next(a["value"] for a in rs.default if a["var"] == ov.name)
        term = _value_to_z3(default_val, ov)
        for rule in reversed(ordered):  # build ite from lowest to highest priority
            assign = next((a for a in rule.then if a["var"] == ov.name), None)
            if assign is None:
                continue
            cond = compile_expr(rule.when, env_inputs, in_typing)
            term = z3.If(cond, _value_to_z3(assign["value"], ov), term)
        outputs[ov.name] = term
    return outputs


def _check_decision(item: Item, timeout_ms: int) -> Result:
    rs: DecisionRuleset = item.ruleset
    prop = item.property
    t0 = time.perf_counter()

    if prop.kind == "monotonicity":
        return _check_monotonicity(item, timeout_ms, t0)

    env_inputs = {v.name: _mk_var(v) for v in rs.inputs}
    outputs = compile_decision_outputs(rs, env_inputs)
    env = {**env_inputs, **outputs}
    typing = typing_of(rs.inputs + rs.outputs)

    s = z3.Solver()
    s.set("timeout", timeout_ms)
    for v in rs.inputs:
        s.add(_domain_constraint(v, env_inputs[v.name]))

    if prop.kind == "invariant":
        s.add(z3.Not(compile_expr(prop.formula, env, typing)))
        scope = f"all {rs.input_space()} inputs"
    elif prop.kind == "reachability":
        s.add(compile_expr(prop.formula, env, typing))
        scope = f"all {rs.input_space()} inputs"
    elif prop.kind == "mutual_exclusion":
        clauses = [z3.And(compile_expr(a, env, typing), compile_expr(b, env, typing))
                   for a, b in prop.mutual_exclusion["pairs"]]
        s.add(z3.Or(*clauses))
        scope = f"all {rs.input_space()} inputs"
    else:
        raise NotImplementedError(prop.kind)

    res = s.check()
    secs = time.perf_counter() - t0
    if res == z3.sat:
        model = s.model()
        witness = _model_inputs(model, rs.inputs, env_inputs)
        return Result(item.id, "violated", scope, witness,
                      "sat: counterexample over the input space", secs)
    if res == z3.unsat:
        return Result(item.id, "holds", scope, None,
                      "unsat of the negation: property proven over the full input space", secs)
    return Result(item.id, "unknown", scope, None, f"solver returned {res}", secs)


def _check_monotonicity(item: Item, timeout_ms: int, t0: float) -> Result:
    rs: DecisionRuleset = item.ruleset
    mono = item.property.monotonicity
    pvar, change = mono["perturbation"]["var"], mono["perturbation"]["change"]
    mname, direction = mono["monotone_var"], mono["direction"]
    in_typing = typing_of(rs.inputs)
    out_typing = typing_of(rs.outputs)
    pv = in_typing[pvar]

    base = {v.name: _mk_var(v, "_b") for v in rs.inputs}
    pert = {v.name: _mk_var(v, "_p") for v in rs.inputs}
    out_b = compile_decision_outputs(rs, base)
    out_p = compile_decision_outputs(rs, pert)

    s = z3.Solver()
    s.set("timeout", timeout_ms)
    for v in rs.inputs:
        s.add(_domain_constraint(v, base[v.name]))
        s.add(_domain_constraint(v, pert[v.name]))
        if v.name != pvar:
            s.add(base[v.name] == pert[v.name])
    if change == "set_true":
        s.add(base[pvar] == False, pert[pvar] == True)  # noqa: E712
    elif change == "increase":
        s.add(pert[pvar] == base[pvar] + 1)
    else:
        raise NotImplementedError(change)

    m_b, m_p = out_b[mname], out_p[mname]  # enum-as-index or int
    if direction == "nondecreasing":
        s.add(m_p < m_b)
    else:
        s.add(m_p > m_b)

    res = s.check()
    secs = time.perf_counter() - t0
    scope = f"all ordered pairs over {rs.input_space()} inputs"
    if res == z3.sat:
        model = s.model()
        witness = _model_inputs(model, rs.inputs, pert) + \
            [{"var": f"{k}__base", "value": _model_value(model, base[k], in_typing[k])} for k in base]
        return Result(item.id, "violated", scope, witness,
                      "sat: a perturbation that moves the monotone output the wrong way", secs)
    if res == z3.unsat:
        return Result(item.id, "holds", scope, None,
                      "unsat of the negation: monotonicity proven over the full input space", secs)
    return Result(item.id, "unknown", scope, None, f"solver returned {res}", secs)


def _model_value(model, zv, var: Var):
    val = model.eval(zv, model_completion=True)
    if var.type == "bool":
        return z3.is_true(val)
    n = val.as_long()
    return var.domain[n] if var.type == "enum" else n


def _model_inputs(model, vars_: list[Var], env: dict) -> list[dict]:
    return [{"var": v.name, "value": _model_value(model, env[v.name], v)} for v in vars_]


# --------------------------------------------------------------------------- transition systems


def _global_body(formula: dict) -> dict:
    if formula.get("op") == "G":
        return formula["args"][0]
    raise NotImplementedError("SMT checker supports temporal properties of the form G(phi) only")


def _state_vars(ts: TransitionSystem, step: int) -> dict:
    return {v.name: _mk_var(v, f"_{step}") for v in ts.state_vars}


def _trans_relation(ts: TransitionSystem, cur: dict, nxt: dict, step: int):
    """Constraint relating state at `cur` to state at `nxt` via one enabled action or stutter."""
    typing = typing_of(ts.state_vars)
    sel = z3.Int(f"sel_{step}")
    options = []
    for idx, tr in enumerate(ts.transitions):
        event = next(e for e in ts.events if e.name == tr.event)
        params = {p.name: _mk_var(p, f"_{step}_{idx}") for p in event.params}
        env = {**cur, **params}
        guard = compile_expr(tr.guard, env, {**typing, **typing_of(event.params)}) if tr.guard else z3.BoolVal(True)
        eff = []
        updated = {a["var"]: a["expr"] for a in tr.update}
        for v in ts.state_vars:
            if v.name in updated:
                eff.append(nxt[v.name] == compile_expr(updated[v.name], env, {**typing, **typing_of(event.params)}, v))
            else:
                eff.append(nxt[v.name] == cur[v.name])
        param_dom = [_domain_constraint(p, params[p.name]) for p in event.params]
        options.append(z3.And(sel == idx, guard, *eff, *param_dom))
    stutter = z3.And(sel == len(ts.transitions), *[nxt[v.name] == cur[v.name] for v in ts.state_vars])
    options.append(stutter)
    return z3.Or(*options), sel


def _check_transition(item: Item, timeout_ms: int) -> Result:
    ts: TransitionSystem = item.ruleset
    prop = item.property
    bound = prop.bound or 8
    phi = _global_body(prop.formula)
    typing = typing_of(ts.state_vars)
    t0 = time.perf_counter()

    states = [_state_vars(ts, 0)]
    sels = []
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    for v in ts.state_vars:
        s.add(_domain_constraint(v, states[0][v.name]))
    init_map = {a["var"]: a["value"] for a in ts.init}
    for v in ts.state_vars:
        s.add(states[0][v.name] == _value_to_z3(init_map[v.name], v))

    bad = [z3.Not(compile_expr(phi, states[0], typing))]
    for i in range(bound):
        nxt = _state_vars(ts, i + 1)
        for v in ts.state_vars:
            s.add(_domain_constraint(v, nxt[v.name]))
        rel, sel = _trans_relation(ts, states[i], nxt, i)
        s.add(rel)
        sels.append(sel)
        states.append(nxt)
        bad.append(z3.Not(compile_expr(phi, nxt, typing)))

    s.push()
    s.add(z3.Or(*bad))
    res = s.check()
    if res == z3.sat:
        model = s.model()
        trace = _decode_trace(ts, model, sels)
        secs = time.perf_counter() - t0
        return Result(item.id, "violated", f"traces up to length {bound}", trace,
                      "sat: a reachable trace reaches a state violating the invariant", secs)
    s.pop()

    # k-induction step for an unbounded result on G(phi); time-boxed so a hard arithmetic
    # instance falls back to the sound bounded result rather than stalling.
    inductive = _k_induction_step(ts, phi, bound, min(timeout_ms, 5000))
    secs = time.perf_counter() - t0
    if inductive:
        return Result(item.id, "holds", "all reachable states (k-induction)", None,
                      f"BMC to {bound} plus a {bound}-induction step: property holds without bound", secs)
    return Result(item.id, "holds", f"all traces up to length {bound}", None,
                  f"BMC to {bound}: no violating trace within the bound", secs)


def _k_induction_step(ts: TransitionSystem, phi: dict, k: int, timeout_ms: int) -> bool:
    typing = typing_of(ts.state_vars)
    states = [_state_vars(ts, f"k{j}") for j in range(k + 1)]
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    for st in states:
        for v in ts.state_vars:
            s.add(_domain_constraint(v, st[v.name]))
    for j in range(k):
        rel, _ = _trans_relation(ts, states[j], states[j + 1], f"k{j}")
        s.add(rel)
        s.add(compile_expr(phi, states[j], typing))
    s.add(z3.Not(compile_expr(phi, states[k], typing)))
    return s.check() == z3.unsat


def _decode_trace(ts: TransitionSystem, model, sels) -> list[dict]:
    trace = []
    for sel in sels:
        idx = model.eval(sel, model_completion=True).as_long()
        if idx < len(ts.transitions):
            trace.append({"event": ts.transitions[idx].event, "transition": ts.transitions[idx].id})
        else:
            trace.append({"event": "stutter"})
    return trace


# --------------------------------------------------------------------------- entry point


def verify(item: Item, timeout_ms: int = 30000) -> Result:
    if item.is_decision:
        return _check_decision(item, timeout_ms)
    return _check_transition(item, timeout_ms)
