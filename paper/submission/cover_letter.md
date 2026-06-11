10 June 2026

Dr. Abdul Rehman, Dr. Faisal Saeed, and Dr. Muhammad Mazhar Rathore
Guest Editors, Special Issue "Agentic AI for Healthcare: Reasoning, Safety, and Clinically
Aligned Autonomous Systems"
AI (MDPI)

Dear Guest Editors,

Please consider the enclosed Article, "Which decisions live in the provable layer? An
assurance-gap framework and a benchmark for formal verification of clinical AI guardrails," for
the Special Issue on Agentic AI for Healthcare.

The safety case for an autonomous clinical AI system today rests on guardrails that are
themselves statistical: a classifier filter, a model that judges outputs, prompt rules, and
retrieval grounding. The evidence they produce is a pass rate over a sampled test set, not a
statement over the input space the system can actually encounter. This paper formalises that
assurance gap, releases CIV-Bench, a public benchmark of 440 machine-readable clinical rule sets
paired with safety properties across triage, medication, and outreach with independently
established ground truth, and runs a head-to-head of satisfiability-modulo-theories verification
against the assurance methods used in practice: a unit-test suite, a frontier language-model
judge, and content-safety guardrails.

The contribution fits the issue's focus on reasoning, safety, and clinically aligned autonomy,
and the result is reported without inflation. No single method detected every violation across
all regimes. The dominant quality-assurance practice, unit testing, returned a false statement of
safety on 63 violated items. A frontier language-model judge, which we re-ran blinded to rule out
label leakage, detected every violation but supplies no proof and no coverage guarantee, and on
the most stateful regime both probabilistic methods exceeded the verifier, which abstained when
the state space exceeded its solver budget. Across all 440 items the verifier returned no verdict
that contradicted ground truth: it proves, refutes with a replayable counterexample, or abstains.
The distinguishing property of formal verification is therefore the class of evidence it returns,
not a higher detection rate. We do not claim provable safety; the guarantee is conditional on the
specification, which we identify as the residual risk. The benchmark, verifier, and analysis are
released under open licences so any health system or vendor can reproduce the measurement.

We disclose that a same-author companion manuscript, on the effect of a verification layer on a
model's free-text outputs, is under review elsewhere; it is cited for context only, the present
paper's conclusions do not depend on its numbers, and the two study different objects. We are
glad to provide it to the editors on request.

We confirm that neither the manuscript nor any parts of its content are currently under
consideration for publication with or published in another journal. All authors have approved the
manuscript and agree with its submission to AI.

Sincerely,
Sanjay Basu, MD, PhD
Waymark; University of California, San Francisco
sanjay.basu@ucsf.edu
