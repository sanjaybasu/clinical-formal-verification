# Counterexample case studies

Three solver-discovered counterexamples from CIV-Bench, each with the clinical reading, the
formal trace, and the verdict of each method on the identical item. Every counterexample was
confirmed by concrete replay (running the rule set on the witness), independent of the solver.
The clinical mechanisms are drawn from the documented failure modes in the companion
retrospective and the clinical-AI-safety literature; the rule sets are synthetic.

## Case 1: a polite message after opt-out (a violation unit testing reports as safe)

Item `lock-len10-viol-00` (outreach). A member opts out of messaging. Over the following
interactions the workflow advances an internal engagement-state counter through ten steps, each
triggered by an ordinary inbound event. After the tenth step a resume path treats the member as
re-engaged and a message is sent, although the member never rescinded the opt-out. The message is
individually plausible and polite; the violation is in the state sequence, not the content.

Formal trace (the safety property is: in every reachable state with opted_out true, sent is
false):

```
init:                 opted_out=false sent=false stage=0
optout              -> opted_out=true  sent=false stage=0
key_0               -> stage=1
key_0               -> stage=2
key_2               -> stage=3
key_2               -> stage=4
key_2               -> stage=5
key_1               -> stage=6
key_2               -> stage=7
key_1               -> stage=8
key_1               -> stage=9
key_0               -> stage=10
send_attempt        -> sent=true   (opted_out is still true)  VIOLATION
```

Verdicts: complete verification returns violated with this trace; the unit-test suite (1000
random event sequences) returns holds, a false statement of safety, because random event
sequences essentially never reproduce the exact ten-step combination; the language-model judge
returns violated. This is the assurance gap in one item: the dominant quality-assurance practice
reports a safe verdict on a system that provably sends a message after opt-out.

## Case 2: a contraindicated pair co-recommended (a deep medication interaction)

Item `medication-d12-viol-00` (medication). The safety property is that drug a and drug b, a
contraindicated pair, are never jointly recommended. The mechanism mirrors a documented harm: a
non-selective oral anti-inflammatory recommended alongside an oral anticoagulant raises
gastrointestinal-bleeding risk, and co-prescription of an interacting antimicrobial with warfarin
has been associated with an approximately four-fold increase in haemorrhage-related
hospitalisation. The violation requires twelve patient conditions to coincide; on the input below
both recommendations fire and no guard suppresses either.

```
input (abbreviated): anticoagulated=true, prior_gi_bleed=true, hepatic_impairment=true,
                     heart_failure=true, ckd_dialysis=true, ... (twelve conditions true)
output:              rec_drug_a=true, rec_drug_b=true     VIOLATION (contraindicated pair)
```

Verdicts: complete verification returns violated and proves that the rest of the input space is
safe; the unit-test suite returns holds (false safe), because a twelve-way conjunction is sampled
with probability on the order of two to the power minus twelve; the language-model judge returns
violated. The interaction depth is the axis on which sampling-based assurance fails.

## Case 3: a violation the verifier cannot decide in budget (verification abstains, soundly)

Item `compute-m064-000` (outreach, computed accumulator, modulus 64). After opt-out a resume
path sends a message when an internal accumulator, updated by a modular recurrence on each event,
reaches a target value. The target is reachable, so the item is violated. Complete verification,
encoding the whole state space as a bounded model-checking query, exceeds its fifteen-second
resource bound and returns unknown: it abstains rather than assert safety. The unit-test suite and
the language-model judge both return violated.

Verdicts: complete verification returns unknown (an abstention, not a verdict of safety); the
unit-test suite returns violated; the language-model judge returns violated. This case is the
honest boundary of the approach. The guarantee complete verification offers is soundness: it
proves, refutes with a replayable counterexample, or abstains, and across all 440 benchmark items
it never returned a verdict that contradicted ground truth. It does not offer unbounded
scalability; on a large symbolic state space the solver can exhaust its budget, which is the
argument for the tiered assurance framework rather than for a single method.

## What the three cases show together

No single method detects every violation. The unit-test suite, the dominant quality-assurance
practice, reports false safety on violations whose witnesses are rare (cases 1 and 2). Complete
verification reports no false safety anywhere, but abstains when the symbolic state space exceeds
its budget (case 3). The language-model judge detected every violation in this benchmark but
supplies no proof and no coverage guarantee, and its soundness here is observed rather than
guaranteed. The distinguishing property of verification is therefore the class of evidence it
returns, a proof or a counterexample or an explicit abstention, not a higher detection rate.
