# clinical-formal-verification

Formal verification of the deterministic control layer of clinical AI systems, with a
head-to-head benchmark against probabilistic guardrails.

## What this is

Probabilistic guardrails (classifier filters, LLM judges, prompt rules, retrieval grounding)
are statistical systems. They inherit the failure modes of the models they police. Formal
methods applied to the deterministic control layer of a clinical AI system provide a different
kind of evidence: a proof or a counterexample over the entire input space, rather than a pass
rate over a test set.

This repository contains:

- a benchmark of machine-readable clinical rule sets paired with safety properties, with a
  ground-truth answer key (`benchmark/`);
- a solver harness that compiles rule sets to SMT constraints and returns either a proof that a
  property holds over the full input space or a counterexample (`verifier/`);
- runners for probabilistic baselines on the identical benchmark: programmable rails, an
  LLM-based safety classifier, an LLM-as-judge, and a conventional unit-test suite
  (`baselines/`);
- the evaluation protocol, metrics, and confidence-interval computation (`experiments/`);
- solver-discovered counterexamples written as clinical narratives plus formal traces
  (`casestudies/`);
- the manuscript, appendix, figures, and submission materials (`paper/`);
- toolkit documentation for external users who want to run the measurement on their own rule
  sets (`docs/`).

## Claim discipline

Formal methods here verify the deterministic control layer only. Nothing in this repository
proves a neural model safe. Every guarantee is conditional on the specification, and
specification error is the residual risk. The precise claim is: machine-checked proofs of
stated invariants over the full input space of the symbolic layer, with counterexamples
otherwise. This repository does not use the phrase "provably safe AI".

## Repository layout

```
references/    verified bibliography and per-paper summaries
benchmark/     rule sets, safety properties, answer key, and schema
verifier/      rule compiler, property checker, counterexample replay
baselines/     programmable rails, LLM safety classifier, LLM-as-judge, unit-test suite
experiments/   evaluation protocol, metrics, confidence intervals
casestudies/   counterexamples as clinical narratives plus formal traces
paper/         manuscript, appendix, figures, submission package
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

## Licensing

Code is released under Apache-2.0 (`LICENSE`). The benchmark, including rule sets, properties,
and answer key, is released under CC-BY-4.0 (`benchmark/LICENSE`). A private split derived from
an operational Medicaid care program is reported in aggregate in the manuscript and is not
released.

## Status

This repository is under active construction and is built in milestones. See
`docs/status/` for the status note at each milestone.
