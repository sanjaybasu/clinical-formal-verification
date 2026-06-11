# clinical-formal-verification

Formal verification of the deterministic control layer of clinical AI systems, with a
head-to-head benchmark against probabilistic guardrails.

## What this is

Probabilistic guardrails (classifier filters, LLM judges, prompt rules, retrieval grounding)
are statistical systems. They inherit the failure modes of the models they police. Formal
methods applied to the deterministic control layer of a clinical AI system provide a different
kind of evidence: a proof or a counterexample over the entire input space, rather than a pass
rate over a test set.

This repository is the open-source toolkit and the released benchmark. It contains:

- CIV-Bench (clinical invariant verification benchmark), a benchmark of machine-readable
  clinical rule sets paired with safety properties, with a ground-truth answer key
  (`benchmark/`);
- a solver harness that compiles rule sets to SMT constraints and returns either a proof that a
  property holds over the full input space or a counterexample (`verifier/`);
- runners for probabilistic baselines on the identical benchmark: programmable rails, an
  LLM-based safety classifier, an LLM-as-judge, and a conventional unit-test suite
  (`baselines/`);
- the pre-registered evaluation protocol, the analysis and figure code, and the deviation log
  (`experiments/`);
- toolkit documentation for external users who want to run the measurement on their own rule
  sets (`docs/`).

The manuscript, appendix, figures, results tables, raw run outputs, references, and counterexample
narratives are maintained separately and are not in this repository; the code here regenerates the
results from the released benchmark.

## Claim discipline

Formal methods here verify the deterministic control layer only. Nothing in this repository
proves a neural model safe. Every guarantee is conditional on the specification, and
specification error is the residual risk. The precise claim is: machine-checked proofs of
stated invariants over the full input space of the symbolic layer, with counterexamples
otherwise. This repository does not use the phrase "provably safe AI".

## Repository layout

```
benchmark/     rule sets, safety properties, answer key, schema, and generators
verifier/      rule compiler, property checker, counterexample replay
baselines/     programmable rails, LLM safety classifier, LLM-as-judge, unit-test suite
experiments/   pre-registered protocol, analysis and figure code, deviation log
tests/         verifier self-tests
docs/          toolkit documentation
```

## Installation

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The solver harness depends on `z3-solver`. Baseline runners that call external models read
credentials from the environment and are optional; the verifier and the benchmark run without
any network access.

## Reproduction

The evaluation protocol is pre-registered in `experiments/protocol.md` and is fixed before any
baseline is run. Results, metrics, and confidence intervals are computed by code in
`experiments/`; this repository does not contain hand-entered result numbers.

Run the head-to-head end to end (the analysis writes results and figures into git-ignored
directories; the repository ships no hand-entered result numbers):

```
python -m baselines.run_verification && python -m baselines.run_unit_test
python experiments/analyze.py && python experiments/figures_all.py
```

The language-model judge and the content-safety guardrails need their own credentials and are
optional; the verifier, the benchmark, and the unit-test suite run with no network access. See
`docs/usage.md` for details.

## Licensing

Code is released under Apache-2.0 (`LICENSE`). The benchmark, including rule sets, properties,
and answer key, is released under CC-BY-4.0 (`benchmark/LICENSE`).
