# Deviations from the pre-registered protocol

The protocol in `protocol.md` was registered before any baseline ran. This file records every
departure from it, per the protocol's own requirement, so the record is auditable.

## 1. Language-model judge decoding is not pinned to temperature 0

The protocol specified the judge at temperature 0. In the run environment a valid direct API key
was not available, so the judge was executed through the agent harness (one independent agent per
item, reading only the rendered specification). The harness does not expose a temperature
control, so decoding is at the harness default rather than pinned to 0. The prompt, the model
class (Claude, Opus-class frontier), and the per-item raw outputs are archived. This affects
reproducibility of the exact tokens, not the reported verdicts, which are deterministic in
substance across items.

## 2. Two benchmark extensions were added after seeing the v0 result (exploratory)

The pre-registered benchmark was CIV-Bench v0 (324 items, explicit single-rule faults). After the
v0 head-to-head showed the language-model judge saturating detection (100%), two further suites
were constructed to probe whether harder regimes would separate the judge from complete
verification:

- CIV-Bench-Hard (60 items): a readable combination lock; the violation requires assembling an
  exact length-L key sequence (planning depth).
- CIV-Bench-Compute (56 items): an order-dependent modular accumulator; the arming sequence is
  not stated in the specification and must be found by simulating the recurrence and searching the
  state graph (multi-step computation depth).

These two suites are exploratory extensions, not part of the pre-registration, and are reported
as such. Their ground truth is established by the same independent oracle and confirmed by replay.

## 3. Primary hypothesis H1 is partially refuted, and is reported as a finding

H1 predicted that complete verification would detect more seeded violations than probabilistic and
sampling methods. The data support H1 for the unit-test suite (the dominant real-world QA
practice), whose detection falls sharply with interaction depth and combinatorial rarity, and for
the content-guardrail class by construction. H1 is not supported for the frontier language-model
judge, which matched complete verification on detection (and on witness validity) across all three
suites, including the computation-heavy CIV-Bench-Compute at modulus 64. This is reported plainly
rather than suppressed. The interpretation, consistent with the architectural-limits results, is
that the distinguishing property of verification is not a higher detection rate but the kind of
evidence it provides: a machine-checked proof over the entire input space and soundness by
construction, neither of which a sample score can supply regardless of its value. The worst-case
guarantees in the architectural-limits section are existence and worst-case statements; a strong
average-case detection rate by a language model is consistent with them and does not provide the
guarantee.

## 5. A verifier unsoundness bug was found and fixed during CIV-Bench-Compute, and metrics added

On CIV-Bench-Compute the transition-system checker initially reported a timeout on the bounded
reachability query (Z3 returning unknown) as holds, which is unsound: a timeout is not a proof of
safety. This was corrected so that unknown is reported as an abstention (a distinct verdict),
never as holds or violated. Two metrics were added to the analysis to make this visible:
abstentions (unknown verdicts) and unsound errors (decisive verdicts that contradict ground
truth). After the fix, complete verification has zero unsound errors on every suite: it proves,
refutes with a replayable counterexample, or abstains. The discovery is reported as part of the
result, since it is the concrete instance of the paper's own claim that the value of verification
is soundness rather than a higher detection rate.

## 6. k-induction is time-boxed

For the temporal suites the verifier attempts a k-induction step for an unbounded result after
bounded model checking. On CIV-Bench-Compute the k-induction satisfiability call on the modular
arithmetic is expensive; it is time-boxed (five seconds), after which the verifier falls back to
the sound bounded result (no violating trace within the bound). For the finite accumulator the
bounded model-checking bound exceeds the diameter of the reachable state set, so the bounded
result is also complete in practice. This is a performance bound on the unbounded-proof step, not
a change to any reported verdict; verification agreed with the independent oracle on every item.
