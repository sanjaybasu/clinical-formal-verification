# Authoring rule sets and properties

A benchmark item is one rule set, one property, and metadata, validating against
`benchmark/schema/benchmark.schema.json`. This guide is the practical complement to the schema
reference in `benchmark/schema/README.md`.

## Variables

Declare each variable as `bool`, `enum`, or `int`. An `enum` lists its labels in order (the order
defines comparison, so an acuity scale runs low to high). An `int` gives inclusive `bounds`,
which keeps the input space finite and lets the verifier report the space it covered.

## Expressions

Expressions are trees, not strings. A leaf is `{"var": "name"}` or `{"const": value}`. An
internal node is `{"op": name, "args": [...]}`. Logical operators are `and`, `or`, `not`,
`implies`, `iff`; comparisons are `eq`, `neq`, `lt`, `le`, `gt`, `ge`; arithmetic over bounded
integers is `add`, `sub`, `mul`, `neg`; `ite` is the three-argument conditional. Temporal
operators `G`, `F`, `X`, `U`, `R`, `W` are valid only in a property over a transition system.

## Decision rule sets

A `decision` rule set is a total function from inputs to outputs. Each rule has a `when`
condition and a `then` list of assignments, and an optional `priority`. `conflict_resolution` is
`priority` (the highest-priority matching rule wins per output, ties by order) or `first_match`
(list order). The `default` block assigns any output left unset, which makes the function total
so that verification is exhaustive.

## Transition systems

A `transition_system` is a finite labelled transition system for temporal properties. It has
state variables, events with finite-domain parameters, an `init` assignment, and transitions
with a `guard`, an `update` to next state, and optional `emits` for observable actions. An event
with no matching enabled transition leaves the state unchanged.

## Properties

- `invariant`: a formula that must hold for every input.
- `reachability`: a forbidden pattern that no input may satisfy.
- `mutual_exclusion`: a list of pairs that may never be jointly true (a convenience template).
- `monotonicity`: under a perturbation that can only worsen the picture (set a flag true, or
  increase a count), a monotone output must not move in the safe direction (a convenience
  template).
- `temporal`: an LTL formula over a transition system, checked to `bound` by bounded model
  checking, with a k-induction step attempted for an unbounded result.

## Ground truth, if you add answer keys

If you supply an answer key (`benchmark/schema/answer_key.schema.json`), establish ground truth
independently of the verifier: enumerate the finite space, or supply a witness that replays to a
violation by concrete execution. Record `interaction_depth` (how many conditions or events must
combine), which is the axis the head-to-head reports against.

## Worked examples

`benchmark/examples/` holds one item per domain (triage monotonicity, medication mutual
exclusion, outreach temporal persistence) with matching answer keys. The generator
`benchmark/generate.py` shows how the suite's items are constructed at controlled interaction
depth.
