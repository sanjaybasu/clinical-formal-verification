# Milestone 3 status note

Scope: baselines run on the benchmark, primary results with confidence intervals, counterexample
case studies selected. The milestone was extended with two exploratory suites after the
pre-registered v0 result, recorded in `experiments/deviations.md`.

## What ran

Methods. Four baseline runners were built: complete verification (the Z3 harness), the unit-test
suite (1000 random inputs or event sequences per item, fixed seed), the language-model judge (one
independent Claude agent per item, reading only the rendered specification), and content-guardrail
runners for NeMo Guardrails and Llama Guard. NeMo Guardrails and Llama Guard were not run in this
environment (no model backend credential; no GPU and no gated weight) and are recorded as not run
with the exact commands, never imputed.

Suites. CIV-Bench v0 (324 items, pre-registered) plus two exploratory extensions: CIV-Bench-Hard
(60 items, a readable combination lock, planning depth) and CIV-Bench-Compute (56 items, an
order-dependent modular accumulator whose arming sequence must be computed, not read). Ground
truth on every suite was set by the independent oracle and every counterexample confirmed by
replay.

Analysis. `experiments/analyze.py` computed detection, false alarm, witness validity, abstention,
unsound errors, and detection by difficulty with 95% Wilson intervals, from the raw outputs only.
Figures by `experiments/figures_all.py`. Case studies in `casestudies/case_studies.md`.

## Numbers

Detection by suite (violated items): complete verification 100% (v0), 100% (hard), 72.5%
(compute, the rest abstentions); unit-test suite 85.2% (v0, falling to 20.8% at depth 12; slope
-0.94 [-1.27, -0.62]), 25.0% (hard, zero from lock length 6), 100% (compute); language-model
judge 100% on all three. Detail in `experiments/results_combined.md`.

Soundness. Across all 440 items complete verification returned zero verdicts contradicting ground
truth; where it could not decide within budget it abstained (25 abstentions, all on
CIV-Bench-Compute at large modulus). The unit-test suite returned 68 false statements of safety
(29 on v0, 34 on hard). The language-model judge made no error observed, with no proof or coverage
guarantee. Witness validity was 100% for every method on every suite.

A verifier unsoundness bug (a solver timeout reported as holds) was found and fixed during
CIV-Bench-Compute; this is documented in `experiments/deviations.md` and is itself an instance of
the paper's thesis.

## Open risks and decisions

- The pre-registered hypothesis H1 (verification detects more than probabilistic methods) is
  partially refuted: it holds for the unit-test suite but not for a frontier language-model judge.
  This is reported as a finding, not suppressed; the thesis is reframed around soundness and the
  class of evidence rather than detection rate.
- NeMo Guardrails and Llama Guard remain not run; the language-model judge represents the
  learned-guard class in the comparison, and this is a stated limitation.
- Verification cost grows with the symbolic state space; on CIV-Bench-Compute at modulus 64 it
  abstains within budget. This motivates the tiered assurance framework rather than a single
  method.

## Next: Milestones 4 and 5

Finalise the toolkit documentation and release candidate, then write the manuscript and appendix,
run the simulated editor and reviewer cycle, and assemble the submission package with the cover
letter and suggested reviewers.
