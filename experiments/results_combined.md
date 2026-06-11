# Combined head-to-head results

All numbers are computed by `experiments/analyze.py` from the raw per-item outputs under
`experiments/runs*/`; none is hand-entered. Proportions carry 95% Wilson score intervals.
Detection is the proportion of seeded violations a method returns as violated; a false-safe (or
unsound) verdict is a decisive holds on a violated item or a decisive violated on a safe item; an
abstention is an unknown verdict. The method order is fixed: complete verification, unit-test
suite, language-model judge. NeMo Guardrails and Llama Guard were not run in this environment and
are not imputed (see `environment.md`).

## Detection by suite

| suite (n violated / n holds) | complete verification | unit-test suite | language-model judge |
| --- | --- | --- | --- |
| CIV-Bench v0 (216 / 108) | 100.0 [98.3, 100.0] | 86.6 [81.4, 90.5] | 100.0 [98.3, 100.0] |
| CIV-Bench-Hard (48 / 12) | 100.0 [92.6, 100.0] | 29.2 [18.2, 43.2] | 100.0 [92.6, 100.0] |
| CIV-Bench-Compute (40 / 16) | 72.5 [57.2, 83.9] | 100.0 [91.2, 100.0] | 100.0 [91.2, 100.0] |

CIV-Bench v0 detection falls with interaction depth for the unit-test suite (100% through depth
6; 33% at depth 12; logistic slope on depth -0.81, 95% CI -1.09 to -0.52) and is flat at 100% for
complete verification and the language-model judge. CIV-Bench-Hard detection for the unit-test
suite falls to zero from lock length 6. CIV-Bench-Compute detection for complete verification
falls with the modulus because the bounded model-checking query exceeds the fifteen-second
resource bound and the verifier abstains; the unit-test suite and the language-model judge are at
100%.

## Soundness and abstention (the distinguishing axis)

| method | false-safe / unsound verdicts (of 304 violated) | false alarms (of 136 holds) | abstentions | mean s/item |
| --- | --- | --- | --- | --- |
| complete verification | 0 | 0 | 25 (all on CIV-Bench-Compute) | 0.006 (v0), 0.067 (hard), 6.18 (compute) |
| unit-test suite | 63 (29 v0, 34 hard) | 0 | 0 | 0.003-0.068 |
| language-model judge | 0 (observed) | 0 (observed) | 0 | model-call latency |

Complete verification returned no verdict that contradicted ground truth on any of the 440 items;
where it could not decide within budget it abstained. The unit-test suite, the dominant
quality-assurance practice, returned a false statement of safety on 63 violated items (it sampled
no witness and reported holds). The language-model judge made no error on this benchmark, but its
soundness is observed, not guaranteed, and it returns no proof and no coverage statement. Witness
validity was 100% for every method on every suite (every counterexample a method returned replays
to a concrete violation).

## Reading

No method detects every violation across all regimes: the unit-test suite fails when a witness is
rare (interaction depth, combination length), and complete verification abstains when the symbolic
state space exceeds its solver budget. The property that separates complete verification from the
probabilistic methods is not a higher detection rate but the class of evidence it returns: a proof
over the full input space, a replayable counterexample, or an explicit abstention, with zero
unsound verdicts. This is the basis for the tiered assurance framework in the manuscript.
