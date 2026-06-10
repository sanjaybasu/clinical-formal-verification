# benchmark schema

Each benchmark item is one rule set, one safety property over that rule set, and metadata.
Items validate against `benchmark.schema.json`. Ground truth is held separately and validates
against `answer_key.schema.json`.

## Variables

A variable is `bool`, `enum`, or `int`. An `enum` carries an ordered `domain` of labels; the
order defines comparison, so `le` and `ge` are meaningful on acuity levels. An `int` carries
inclusive `bounds`, which keeps every input space finite and lets the verifier report the
cardinality of the space it covered.

## Expression grammar

Expressions are structured trees, not strings, so there is no parsing ambiguity. A leaf is
`{"var": "name"}` or `{"const": value}`. An internal node is `{"op": name, "args": [...]}`.

Operators:

- logical: `and`, `or`, `not`, `implies`, `iff`
- comparison: `eq`, `neq`, `lt`, `le`, `gt`, `ge`
- arithmetic over bounded integers: `add`, `sub`, `mul`, `neg`
- conditional: `ite` with three arguments, condition then else
- temporal, valid only in a property over a transition system: `G` global, `F` eventually,
  `X` next, `U` until, `R` release, `W` weak until

Comparison on an `enum` uses the index of the label in its declared `domain`.

## Rule sets

A `decision` rule set is a total function from inputs to outputs. Rules carry a `when`
condition and a `then` list of assignments. `conflict_resolution` is `priority` (highest
priority matching rule wins per output), `first_match` (list order), or `error_on_conflict`
(two matching rules that assign different values to one output is itself a fault the property
can target). The `default` block assigns any output left unset, which makes the function total
and the verification exhaustive.

A `transition_system` is a finite labelled transition system for temporal properties. It has
state variables, events with finite-domain parameters, an `init` assignment, and transitions
with a `guard`, an `update` to next state, and `emits` for observable actions such as
`send_message`. Finiteness keeps bounded model checking and k-induction decidable.

## Properties

- `invariant`: `formula` must hold for every input. The verifier checks unsatisfiability of the
  negation; unsat means the invariant holds over the full input space, sat returns a
  counterexample.
- `reachability`: `formula` is the forbidden pattern; the property holds iff the pattern is
  unsatisfiable. Reported as reachable or unreachable rather than as a plain invariant.
- `mutual_exclusion`: a convenience template; expands to an invariant that no listed pair is
  jointly asserted in the outputs.
- `monotonicity`: a convenience template; under a `perturbation` that can only worsen the
  clinical picture (set a red flag true, or increase a severity count), the `monotone_var` must
  not move in the safe direction. It expands to a two-copy formula over inputs and a perturbed
  copy.
- `temporal`: an LTL `formula` over a transition system, checked to `bound` by bounded model
  checking; the verifier also attempts k-induction for an unbounded result and reports which
  was achieved.

## Ground truth and why it is not circular

A benchmark that scores verifiers cannot establish its own ground truth with the verifier under
test. Ground truth here is independent of any solver.

- For a violated item, the answer key carries a `witness`: a concrete input assignment, or a
  concrete event trace, that exhibits the violation. The witness is checkable by executing the
  rule set on it and observing the violated property. This execution is a direct evaluation of
  the rule set, not a solver call, so confirming ground truth never invokes the system under
  test. `basis` is `by_construction` for a seeded fault and `concrete_replay` once the witness
  has been executed and the violation observed.
- For a holds item, `basis` is `manual_proof`: the absence of any violation is established by
  hand or by exhaustive enumeration of the finite input space, independent of the verifier
  under evaluation.

`interaction_depth` records how many rules must interact to produce a violation. The
compositionality literature predicts that probabilistic methods miss violations at higher
interaction depth; this field is the axis along which that prediction is tested.

## Layout

```
schema/        these schemas and this document
examples/      one worked item per domain, with its answer key
answer_key/    ground truth, one file per item id
private/        git-ignored; never holds released content
```
