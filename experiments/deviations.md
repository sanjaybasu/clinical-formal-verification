# Deviations from the pre-registered protocol

The protocol in `protocol.md` was registered before any baseline ran. This file records every
departure from it, in order, so the record is auditable.

## 1. The v0 suite was expanded after registration

The protocol as first written described CIV-Bench v0 as 180 items at interaction depth one to
four. The suite used in the paper is 324 items at interaction depth one to twelve (depths five,
six, eight, ten, and twelve were added). The expansion was made before the baselines were run, to
give the depth axis enough range to separate the methods; it is recorded here because the
registered text and the suite differ. Detection is reported by depth, so the added depths are
visible rather than pooled.

## 2. Two further benchmark suites were added after seeing the v0 result (exploratory)

After v0 showed the language-model judge saturating detection, two suites were added to probe
harder regimes: CIV-Bench-Hard (a readable combination lock, planning depth) and CIV-Bench-Compute
(an order-dependent modular accumulator whose arming sequence must be computed, not read). These
are exploratory extensions, not part of the pre-registration, and are labelled as such; they are
scalability and witness-rarity stress tests and make no claim of clinical realism. Ground truth on
both is set by the independent oracle and confirmed by replay.

## 3. The language-model judge was re-run blinded after a label-leakage finding

The first judge run referenced item identifiers that encoded the ground-truth label and difficulty
(for example triage-d12-viol-00) and rendered rules with tell-tale names (interaction_drop,
t_resume_glitch, guard_suppress_b). Both leak the answer. The judge was re-run with neutral item
identifiers (content hashes that encode neither label nor difficulty) and neutralised rule and
transition identifiers (r1, r2, ...; t1, t2, ...), keeping the clinically meaningful variable names
and the property. The blinded run is the one reported; the blinding code is `baselines/blind_render.py`
and the hash-to-id mapping is committed. Decoding is at the agent-harness default rather than pinned
to temperature zero, because a direct API key was unavailable in the run environment; this is a
reproducibility caveat on the exact tokens, and the pinned model and harness version are recorded
in `environment.md`.

## 4. The unit-test seed was made process-independent

The unit-test runner initially seeded its per-item generator from a Python tuple hash, which is
salted per process, so its outputs were not reproducible across machines. The seed now derives from
a stable sha256 of the item identifier; the reported unit-test numbers are from the deterministic
version. The benchmark generators were corrected in the same way; the released benchmark is the
version-controlled suite.

## 5. Primary hypothesis H1 is partially refuted, and is reported as a finding

H1 predicted that the verifier would detect more seeded violations than the probabilistic and
sampling methods. The data support H1 for the unit-test suite (the dominant real-world quality-
assurance practice), whose detection falls with interaction depth and witness rarity. H1 is not
supported for the frontier language-model judge, which matched the verifier on detection on the two
suites where the verifier did not abstain and exceeded it on CIV-Bench-Compute. This is reported
plainly. The interpretation, consistent with the architectural-limits results, is that the
distinguishing property of verification is the class of evidence it returns and its soundness, not a
higher detection rate; the architectural-limits results are worst-case and existence statements, and
a strong average-case detection rate by a model is consistent with them and provides no guarantee.

## 6. A verifier unsoundness was found and fixed, and soundness metrics were added

On CIV-Bench-Compute the transition-system checker initially reported a solver timeout (Z3 unknown)
on the bounded reachability query as holds, which is unsound: a timeout is not a proof of safety.
This was corrected so that unknown is reported as an abstention, never as holds or violated. Two
metrics were added to the analysis: abstentions (unknown verdicts) and unsound errors (decisive
verdicts that contradict ground truth). After the fix, the verifier has zero unsound errors on
every suite. The discovery is reported as part of the result, since it is the concrete instance of
the paper's claim that the value of verification is soundness.

## 7. k-induction is time-boxed

The verifier attempts a k-induction step for an unbounded result after bounded model checking. On
CIV-Bench-Compute the k-induction satisfiability call on the modular arithmetic is expensive; it is
time-boxed to five seconds, after which the verifier falls back to the verdict from bounded model
checking. If bounded model checking found no counterexample within the bound, the fall-back verdict
is the bounded result, and where the solver could not complete the verifier abstains. No reported
verdict is a proof of safety obtained from a timeout.

## 8. Statistical posture

All proportions are reported descriptively with 95% Wilson score intervals and no family-wise
adjustment. The one pre-specified inferential test is the paired McNemar comparison of the verifier
against the unit-test suite on per-item agreement; depth is reported by category in addition to the
logistic slope, which for the saturated methods is not identified and is stated as flat.
