# CIV-Bench

CIV-Bench (clinical invariant verification benchmark) is a set of machine-readable clinical
rule sets paired with formal safety properties and a ground-truth answer key. It measures
whether a method can detect provable safety violations in clinical decision logic.

## Structure

```
schema/       the item and answer-key schemas, the expression grammar, and the ground-truth method
examples/     one worked item per domain
answer_key/   ground truth, one file per item id, held separately from the items
validate.py   schema validation for items and keys
```

## Domains

- triage: symptom-to-acuity rules; properties such as monotonicity and reachability.
- medication: contraindication and interaction rules; properties such as no path co-suggesting
  a contraindicated pair.
- outreach: messaging state machines; temporal properties such as no message after opt-out.

## Items

Each item is one rule set, one property over that rule set, and metadata, validating against
`schema/benchmark.schema.json`. Ground truth validates against `schema/answer_key.schema.json`
and is held in `answer_key/`. A violated item carries a witness that is checkable by concrete
execution of the rule set, so labeling the benchmark does not depend on the solver under test;
`interaction_depth` records how many rules must interact to produce a violation.

All released rule sets are synthetic or derived from public sources under a permissive licence.
A split derived from an operational Medicaid care program is reported in aggregate in the
manuscript and is not released. The benchmark is licensed CC-BY-4.0 (`LICENSE`).

## Validate

```
python validate.py
```
