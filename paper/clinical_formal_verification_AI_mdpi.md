---
title: "Which decisions live in the provable layer? An assurance-gap framework and a benchmark for formal verification of clinical AI guardrails"
runningtitle: "Formal verification of clinical AI guardrails"
journal: "AI (MDPI)"
article_type: "Article"
---

# Which decisions live in the provable layer? An assurance-gap framework and a benchmark for formal verification of clinical AI guardrails

## Abstract

Background: Clinical artificial-intelligence systems wrap a language model in guardrails, a
classifier filter, a model that judges outputs, prompt rules, and retrieval grounding, each of
which is itself a statistical system that inherits the failure modes of the model it polices. The
evidence a guardrail produces is a pass rate over a sampled test set, not a statement over the
input space. Methods: We formalise the resulting assurance gap, build CIV-Bench, a benchmark of
440 machine-readable clinical rule sets paired with safety properties across triage, medication,
and outreach, with ground truth established by an independent oracle and every counterexample
confirmed by concrete replay, and run a head-to-head of complete satisfiability-modulo-theories
verification against the current quality-assurance practices: a unit-test suite, a frontier
language-model judge, and content-safety guardrails. Results: Complete verification returned no
verdict that contradicted ground truth on any of the 440 items, proving a property over the full
input space, exhibiting a replayable counterexample, or abstaining; it never reported false
safety. The unit-test suite returned a false statement of safety on 63 violated items, with
detection falling as interaction depth rose (86.6% to 33% across depth on one suite; to zero on
another). A frontier language-model judge detected every violation but supplies no proof and no
coverage guarantee. No method detected every violation across all regimes. Conclusion: The
property that distinguishes formal verification is the class of evidence it returns, not a higher
detection rate; the design question for clinical AI is which decisions are placed in the
provable layer, a question new model releases do not change.

Keywords: formal verification; clinical decision support; large language models; AI safety;
satisfiability modulo theories; guardrails; benchmark; assurance

## 1. Introduction

Large language models embedded in clinical workflows for documentation, triage, and decision
support produce two recognised categories of safety failure: commission, the confident assertion
of unsupported clinical information, and omission, the failure to surface safety-critical workup,
contraindications, or higher-acuity differentials [1]. Frontier models are highly vulnerable to
adversarial hallucination in clinical decision support [1], healthcare-specific guardrails are an
active area of need and difficulty [2], and the assurance of clinical AI systems has been
established as a discipline in its own right [3]. To mitigate these failures, health systems
operationalise overlapping guardrail components: a clinical-safety system prompt, a learned
input-output safeguard such as a fine-tuned classifier [4], programmable dialogue rails [5], and
retrieval grounding. Each of these components is itself a statistical system. Empirical work shows
that learned guardrails are bypassable, with character-injection and adversarial techniques
driving detection accuracy down by tens of percentage points [6], and a systematisation of
jailbreak guardrails finds no single guardrail robust across attack families [7]. A companion
retrospective from our group quantifies the operational consequence: a four-component guardrail
stack reduced commission but introduced a safety-critical omission tax of approximately twelve
percentage points, which a downstream verification layer reversed while catching about half of
the guardrail-missed omissions and missing none the guardrails caught [26].

The recurring objection to any study of this kind is that the next model release will close the
gap. Three independent results make that unlikely for the model class. A computability argument
shows that for any computable language model there exists a computable ground-truth function on
which it errs, by diagonalisation, with hallucination eliminable only for restricted,
computably enumerable problem classes [8]. A statistical argument shows that a calibrated model
has a hallucination rate lower-bounded by the fraction of facts seen once in training, so
calibration and factuality are in tension on rare facts [9]; in a safety-net population the facts
that matter, a member's current medication or a specific prior reaction, are by their nature such
singletons. An incentive argument, now peer-reviewed, reduces generative error to binary
classification error and shows that benchmarks that penalise abstention reward confident guessing
[10]; a further undecidability argument has been advanced and is treated here as supporting
context only [11]. Reasoning limits compound where clinical logic lives: fixed-depth log-precision
transformers are contained in the circuit class TC0 and cannot express certain compositional
problems regardless of scale [12], a chain of thought relaxes but does not remove this for a
bounded number of steps [13], and compositional accuracy decays empirically with problem depth
[14]. Verifying the trained network instead is intractable, since deciding properties of a
rectified-linear network is NP-complete [15].

Two boundaries frame the design space. On one side, the semantic properties of arbitrary programs
are undecidable [16] and neural-network verification is intractable [15]. On the other, a finite
and explicit rule layer over finite-domain variables is a decidable object whose properties a
satisfiability-modulo-theories solver decides, returning a proof over the entire space or a
counterexample [17]. The guaranteed-safe AI programme articulates this macro-architecture, a world
model, a safety specification, and a verifier that emits an auditable proof certificate [20,21],
and a 2025 wave of systems has applied formal and runtime methods to language-model agents.
A 2026 systematic review of formal methods for safety-critical machine learning reaches a
consonant conclusion from the verification side [25]. What this literature does not contain is a
public benchmark of clinical safety invariants with independently established ground truth, a
head-to-head of complete verification against the probabilistic methods on clinical rule sets, or
a characterisation of where each method fails. This paper supplies them. The contribution is, in
order, the formalisation of the assurance gap, the CIV-Bench benchmark, the head-to-head
measurement, and a tiered assurance framework that places content-safety guardrails, runtime
monitors, verified rule layers, and theorem-proved cores at distinct evidence classes. The
guarantee claimed is precise and bounded: machine-checked proofs of stated invariants over the
full input space of a symbolic layer, with counterexamples otherwise, conditional on the
specification, whose validity is itself the residual risk [18,19]. This paper does not use the
phrase provably safe AI.

## 2. Materials and Methods

### 2.1. Reporting and ethics

The study is a methods-and-benchmark evaluation; it reports computational experiments on synthetic
and public-source-derived rule sets and a head-to-head of detection methods. No reporting
guideline for predictive-model development applies directly; the evaluation follows a structured
benchmark-and-comparison protocol pre-registered in the repository before any baseline was run,
and departures from it are recorded. WCG IRB approved the observational studies of retrospective
data that do not affect participant treatment decisions, with a waiver of informed consent given
the use of de-identified data, under IRB Tracking ID 20253751. The public benchmark is synthetic
or public-source derived and involves no human subjects.

### 2.2. The benchmark

CIV-Bench is a set of machine-readable items, each a rule set, a safety property over that rule
set, and metadata, validating against a published JSON schema. A rule set is either a decision
rule set, a total function from finite-domain inputs to outputs under priority or first-match
conflict resolution, or a finite labelled transition system with events, guards, and updates.
Properties are invariants, reachability conditions, mutual-exclusion constraints, monotonicity
constraints, or linear-temporal properties. Three clinical domains give generality: triage, where
adding a red-flag symptom must not lower acuity (monotonicity); medication, where a contraindicated
pair must never be jointly recommended (mutual exclusion); and outreach, where no message may be
sent after opt-out (a temporal property). The benchmark comprises three suites. CIV-Bench v0 (324
items) embeds explicit rule-interaction faults at controlled interaction depth one to twelve.
CIV-Bench-Hard (60 items) gates an outreach violation behind a combination lock whose exact length-
L key sequence must be entered, with L from two to twelve. CIV-Bench-Compute (56 items) gates an
outreach violation behind an order-dependent modular accumulator whose arming sequence is not
stated in the specification and must be found by simulating the recurrence, with modulus from
eight to sixty-four.

Ground truth is established independently of the system under test. For a decision rule set the
input space is enumerated exhaustively; for a transition system the reachable states are explored
by breadth-first search to a bound exceeding the diameter of the finite state. Neither uses a
solver. A violated item carries a witness, a concrete input or event sequence, that is confirmed
by executing the rule set on it and observing the violated property; this concrete replay is what
makes a benchmark that scores verifiers non-circular. Interaction depth, the number of conditions
or events that must coincide for a violation, is recorded for every violated item and is the axis
along which detection is reported. The generators are deterministic; the released benchmark is the
version-controlled suite.

### 2.3. The verifier

The verifier compiles a rule set to satisfiability-modulo-theories constraints with Z3 [17].
A decision rule set compiles to one output term per output variable, a nested conditional over
the rules in resolution order. An invariant is checked by asserting the negation of the property
over the input-domain constraints: an unsatisfiable result is a proof that the property holds over
the full input space, a satisfiable result is a counterexample model rendered as a concrete input.
Reachability, mutual exclusion, and monotonicity are compiled to this form, monotonicity by a
two-copy encoding over the inputs and a perturbed copy. A transition system is checked by bounded
model checking, unrolling the transition relation to the bound and asking whether a reachable
state violates the property; a k-induction step is attempted for an unbounded result and is
time-boxed. A solver result of unknown is reported as an abstention, never as a proof of safety.
Every counterexample is replayed by concrete execution to confirm it exhibits the violation.

### 2.4. Comparison methods

Each method receives the identical items and returns holds, violated, or, for the verifier,
unknown. The unit-test suite draws one thousand uniform random inputs or random event sequences
per item with a fixed seed and returns violated if any sampled point violates the property, else
holds; it represents current quality-assurance practice. The language-model judge presents a clean
rendering of the rule set and property to a frontier model (Claude, Opus class), one independent
agent per item with no access to ground truth, and parses a structured verdict and, for a
violation, a witness; the rendering and per-item outputs are archived. Content-safety guardrails,
NeMo Guardrails [5] and Llama Guard [4], are positioned as runtime monitors; their runners require
a model backend and a gated weight respectively and were not run in this environment, recorded as
such and never imputed.

### 2.5. Metrics and statistical analysis

The primary endpoint is the detection rate, the proportion of seeded violations a method returns
as violated. Secondary endpoints are the false-alarm rate on items that hold, the witness validity
(the proportion of returned counterexamples that replay to a concrete violation), the abstention
rate, the count of unsound verdicts (a decisive verdict contradicting ground truth), detection by
interaction depth, and wall-clock time per item. Proportions are reported with 95% Wilson score
confidence intervals; detection on depth is modelled by logistic regression with the slope and its
95% confidence interval. The metric order and method order are identical throughout: complete
verification, unit-test suite, language-model judge. Analysis is computed from the raw per-item
outputs by a single script and contains no hand-entered number. Generative AI was used in
preparing this work: the analysis and verification code and a first draft of the text were
produced with a large language model under author direction, and the authors reviewed and edited
all output and take full responsibility for it; all reported numbers derive from the committed
code and outputs.

## 3. Results

### 3.1. Detection across three regimes

On CIV-Bench v0, complete verification detected 216 of 216 violations (100%, 95% CI 98.3 to 100.0)
and the language-model judge detected 216 of 216 (100%, 95% CI 98.3 to 100.0), while the unit-test
suite detected 187 of 216 (86.6%, 95% CI 81.4 to 90.5). Unit-test detection fell with interaction
depth, from 100% through depth six to 33.3% (95% CI 18.0 to 53.3) at depth twelve, with a logistic
slope on depth of -0.81 (95% CI -1.09 to -0.52); verification and the judge did not vary with
depth (Figure 1, left). On CIV-Bench-Hard, complete verification and the language-model judge each
detected 48 of 48 (100%, 95% CI 92.6 to 100.0), while the unit-test suite detected 14 of 48
(29.2%, 95% CI 18.2 to 43.2) and reached zero from lock length six (Figure 1, centre). On
CIV-Bench-Compute the pattern inverted: the unit-test suite and the language-model judge each
detected 40 of 40 (100%, 95% CI 91.2 to 100.0), while complete verification detected 29 of 40
(72.5%, 95% CI 57.2 to 83.9), with detection falling as the modulus rose because the bounded
model-checking query exceeded its fifteen-second resource bound and the verifier abstained
(Figure 1, right). No method detected every violation across all three regimes.

### 3.2. Soundness, abstention, and false safety

The distinguishing axis is soundness (Figure 2). Across all 440 items complete verification
returned no verdict that contradicted ground truth: it proved the property, exhibited a replayable
counterexample, or abstained, with 25 abstentions, all on CIV-Bench-Compute at large modulus. The
unit-test suite returned a false statement of safety on 63 violated items (29 on v0, 34 on Hard):
having sampled no witness, it reported holds. The language-model judge made no error observed on
this benchmark, but its soundness is observed rather than guaranteed and it returns no proof and no
coverage statement. Witness validity was 100% for every method on every suite: every counterexample
a method returned replayed to a concrete violation. No method raised a false alarm on an item that
holds. Verification time was 6 milliseconds per item on v0, 67 milliseconds on Hard, and 6.2
seconds on CIV-Bench-Compute, where the symbolic state space is largest.

### 3.3. Counterexample case studies

Three counterexamples illustrate the regimes (full traces in the repository). In the first, a
member opts out of messaging; an ordinary ten-step interaction sequence advances an internal state
counter, after which a resume path sends a message although the opt-out was never rescinded. The
message is individually polite; the violation is in the state sequence. Complete verification
returns this trace; the unit-test suite returns holds, a false statement of safety, because random
event sequences essentially never reproduce the exact combination; the language-model judge returns
violated. In the second, twelve patient conditions coincide and the rule set co-recommends a
contraindicated pair, a mechanism mirroring the association of an interacting drug with warfarin
and an approximately four-fold increase in haemorrhage-related hospitalisation [26]; complete
verification and the judge return violated, the unit-test suite returns a false safe because a
twelve-way conjunction is sampled with probability of order two to the power minus twelve. In the
third, a violation is genuinely reachable but complete verification exceeds its resource bound on a
modulus-sixty-four accumulator and returns unknown, an abstention; the unit-test suite and the
judge return violated. The third case is the honest boundary of the method.

## 4. Discussion

### 4.1. Principal findings

We set out to measure where complete verification and the probabilistic assurance methods used in
practice each fail, on clinical rule sets with known safety properties. No method detected every
violation across all three regimes. The unit-test suite, the dominant quality-assurance practice,
failed when a violation's witness was rare, and reported a false statement of safety on 63 of 304
violated items. Complete verification failed only by abstaining when the symbolic state space
exceeded its solver budget, and returned no verdict that contradicted ground truth on any item. A
frontier language-model judge detected every violation, including on the computation-heavy suite,
which is consistent with the architectural-limits results rather than contrary to them: those
results are worst-case and existence statements about what cannot be guaranteed, not claims about
average-case detection, and a strong average-case detection rate by a model provides no guarantee.

### 4.2. The gap is in the class of evidence, not the detection rate

The pre-registered hypothesis that complete verification would detect more violations than the
probabilistic methods held for the unit-test suite but not for the language-model judge, which
matched verification on detection. We report this plainly. The property that distinguishes complete
verification is therefore not a higher detection rate but the class of evidence it returns: a proof
over the entire input space, a replayable counterexample, or an explicit abstention, with zero
unsound verdicts. A pass rate over a sample, however high, is a statement about the inputs that
were drawn, not the inputs that were not; the unit-test suite's 63 false statements of safety are
that distinction made concrete, and the language-model judge's perfect score is a sample statistic
with no coverage or soundness guarantee. During the evaluation we found and fixed an unsoundness in
our own verifier, a solver timeout briefly reported as holds; that this could occur, and was caught
by the soundness metric, is the thesis in miniature.

### 4.3. A tiered assurance framework

These results motivate a maturity model in which assurance methods occupy distinct evidence classes
rather than competing as substitutes. Content-safety guardrails and the language-model judge are
probabilistic monitors, useful for breadth and for content not expressible as a rule, but providing
no guarantee; the unit-test suite adds concrete evidence for failures it happens to sample;
runtime monitors enforce properties during execution; a satisfiability-modulo-theories-verified
rule layer provides a proof over the full input space where the state space is tractable; and a
theorem-proved core provides the strongest guarantee for the smallest, most critical decisions. The
design question for a clinical AI system is which decisions are placed in the provable layer. A
model release changes how good the model is; it does not change the decidability of a finite
symbolic layer or the undecidability of the general case, because those are properties of the
objects rather than of the model.

### 4.4. Comparison with prior work

The guaranteed-safe AI programme provides the macro-architecture this work instantiates for
clinical rule sets [20,21], the intractability of neural-network verification is its premise [15],
and a 2025 wave of agent-verification systems shares its move of placing safety in a verifiable
layer, but evaluates general agent behaviour rather than clinical rule sets and runs no head-to-head
against probabilistic guardrails on a public clinical benchmark. The companion retrospective
measured the effect of a verification layer on a model's natural-language outputs and found that
standard guardrails impose an omission tax that the layer reverses [26]; the present work is its
formal complement, characterising and measuring the assurance gap on the symbolic control layer and
releasing the benchmark on which the measurement is reproducible. The two are reported separately
because the object of study differs.

### 4.5. Limitations

The content-safety guardrails were not run in this environment and the language-model judge
represents the learned-guard class in the comparison; this is a stated limitation rather than a gap
in the argument, since the judge is the strongest member of that class. The benchmark rule sets are
synthetic or public-source derived and finite; real clinical rule layers are larger, and complete
verification's cost grows with the state space, as CIV-Bench-Compute shows. The guarantee is
conditional on the specification, and specification error is the residual risk [18,19]; a verified
rule layer can still cause harm if the property is the wrong one to require, which is why the
properties are objects of clinical review. The two harder suites were exploratory extensions added
after the pre-registered v0 result, and are reported as such.

### 4.6. Why this matters first in a safety-net population

The facts that matter in Medicaid care are individual and rare, which is precisely where the
calibration bound predicts hallucination [9], and the populations served have the least margin to
absorb a confidently wrong recommendation. Assurance that returns a proof or an explicit
abstention, rather than a confident pass rate, is most valuable exactly where the cost of a false
statement of safety is borne by those least able to bear it.

## 5. Conclusions

Probabilistic guardrails are statistical systems and cannot supply a proof over the input space;
the dominant quality-assurance practice, unit testing, reports false safety when a violation's
witness is rare; and a frontier language model, while strong at detection, provides no guarantee.
Complete verification of a finite symbolic clinical rule layer returns a different class of evidence,
a proof, a counterexample, or an abstention, and is sound by construction. The benchmark, verifier,
and analysis are released so any health system or vendor can run the measurement on its own rule
sets. The design question for clinical AI is which decisions live in the provable layer.

## Back matter

Author Contributions: Conceptualization, methodology, software, formal analysis, investigation,
data curation, writing, and visualization were carried out by the author. All authors have read and
agreed to the published version of the manuscript.

Funding: This research received no external funding.

Institutional Review Board Statement: WCG IRB approved the observational studies of retrospective
data that do not affect participant treatment decisions, with a waiver of informed consent given
the use of de-identified data, under IRB Tracking ID 20253751.

Informed Consent Statement: Patient consent was waived because the study used de-identified
retrospective data and did not affect participant treatment decisions, per the IRB determination
above. The released benchmark is synthetic or public-source derived and involves no human subjects.

Data Availability Statement: The benchmark, verifier, baseline runners, analysis code, and the raw
per-item outputs are openly available at https://github.com/sanjaybasu/clinical-formal-verification
and are archived with a DOI on release. A split derived from an operational Medicaid care program
is reported in aggregate and is not released due to data-use restrictions.

Acknowledgments: During the preparation of this manuscript the author used a large language model
(Claude) for code generation, analysis, and a first text draft; the author has reviewed and edited
the output and takes full responsibility for the content of this publication.

Conflicts of Interest: The authors are employees of Waymark, a public benefit organization that
provides free social and medical services for patients receiving Medicaid.

## References

1. Omar, M.; Sorin, V.; Collins, J.D.; et al. Large Language Models Are Highly Vulnerable to Adversarial Hallucination Attacks in Clinical Decision Support: A Multi-Model Assurance Analysis. *medRxiv* 2025. doi:10.1101/2025.03.18.25324184.
2. Gangavarapu, A. Enhancing Guardrails for Safe and Secure Healthcare AI. *arXiv* 2024, arXiv:2409.17190.
3. Festor, P.; Jia, Y.; Gordon, A.C.; Faisal, A.A.; Habli, I.; Komorowski, M. Assuring the Safety of AI-based Clinical Decision Support Systems: A Case Study of the AI Clinician for Sepsis Treatment. *BMJ Health Care Inform.* 2022, 29, e100549. doi:10.1136/bmjhci-2022-100549.
4. Inan, H.; Upasani, K.; Chi, J.; et al. Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations. *arXiv* 2023, arXiv:2312.06674.
5. Rebedea, T.; Dinu, R.; Sreedhar, M.N.; Parisien, C.; Cohen, J. NeMo Guardrails: A Toolkit for Controllable and Safe LLM Applications with Programmable Rails. In *Proceedings of EMNLP 2023: System Demonstrations*; ACL: Singapore, 2023; pp. 431-445. doi:10.18653/v1/2023.emnlp-demo.40.
6. Hackett, W.; Birch, L.; Trawicki, S.; Suri, N.; Garraghan, P. Bypassing LLM Guardrails: An Empirical Analysis of Evasion Attacks against Prompt Injection and Jailbreak Detection Systems. In *Proceedings of the First Workshop on LLM Security (LLMSEC)*; ACL: Vienna, 2025; pp. 101-114.
7. Wang, X.; Ji, Z.; Wang, W.; Li, Z.; Wu, D.; Wang, S. SoK: Evaluating Jailbreak Guardrails for Large Language Models. *arXiv* 2025, arXiv:2506.10597.
8. Xu, Z.; Jain, S.; Kankanhalli, M. Hallucination is Inevitable: An Innate Limitation of Large Language Models. *arXiv* 2024 (rev. 2025), arXiv:2401.11817.
9. Kalai, A.T.; Vempala, S.S. Calibrated Language Models Must Hallucinate. In *Proceedings of STOC 2024*; ACM, 2024; pp. 160-171. doi:10.1145/3618260.3649777.
10. Kalai, A.T.; Nachum, O.; Vempala, S.S.; Zhang, E. Evaluating Large Language Models for Accuracy Incentivizes Hallucinations. *Nature* 2026. doi:10.1038/s41586-026-10549-w.
11. Banerjee, S.; Agarwal, A.; Singla, S. LLMs Will Always Hallucinate, and We Need to Live with This. In *Intelligent Systems and Applications (IntelliSys 2025)*; LNNS; Springer: Cham, 2025; pp. 624-648. doi:10.1007/978-3-031-99965-9_39.
12. Merrill, W.; Sabharwal, A. The Parallelism Tradeoff: Limitations of Log-Precision Transformers. *Trans. Assoc. Comput. Linguist.* 2023, 11, 531-545. doi:10.1162/tacl_a_00562.
13. Merrill, W.; Sabharwal, A. The Expressive Power of Transformers with Chain of Thought. In *Proceedings of ICLR 2024*; 2024.
14. Dziri, N.; Lu, X.; Sclar, M.; et al. Faith and Fate: Limits of Transformers on Compositionality. In *Advances in Neural Information Processing Systems 36 (NeurIPS 2023)*; 2023; pp. 70293-70332.
15. Katz, G.; Barrett, C.; Dill, D.L.; Julian, K.; Kochenderfer, M.J. Reluplex: An Efficient SMT Solver for Verifying Deep Neural Networks. In *Computer Aided Verification (CAV 2017)*; LNCS 10426; Springer, 2017; pp. 97-117. doi:10.1007/978-3-319-63387-9_5.
16. Rice, H.G. Classes of Recursively Enumerable Sets and Their Decision Problems. *Trans. Am. Math. Soc.* 1953, 74, 358-366. doi:10.1090/S0002-9947-1953-0053041-6.
17. de Moura, L.; Bjorner, N. Z3: An Efficient SMT Solver. In *Tools and Algorithms for the Construction and Analysis of Systems (TACAS 2008)*; LNCS 4963; Springer, 2008; pp. 337-340. doi:10.1007/978-3-540-78800-3_24.
18. De Millo, R.A.; Lipton, R.J.; Perlis, A.J. Social Processes and Proofs of Theorems and Programs. *Commun. ACM* 1979, 22, 271-280. doi:10.1145/359104.359106.
19. Clarke, E.M.; Wing, J.M. Formal Methods: State of the Art and Future Directions. *ACM Comput. Surv.* 1996, 28, 626-643. doi:10.1145/242223.242257.
20. Dalrymple, D.; Skalse, J.; Bengio, Y.; Russell, S.; Tegmark, M.; Seshia, S.; et al. Towards Guaranteed Safe AI: A Framework for Ensuring Robust and Reliable AI Systems. *arXiv* 2024, arXiv:2405.06624.
21. Tegmark, M.; Omohundro, S. Provably Safe Systems: The Only Path to Controllable AGI. *arXiv* 2023, arXiv:2309.01933.
22. U.S. Food and Drug Administration. Artificial Intelligence-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations (Draft Guidance). Docket FDA-2024-D-4488, 90 Fed. Reg. 1356, 2025.
23. U.S. Food and Drug Administration. Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence-Enabled Device Software Functions (Final Guidance), 2025.
24. Coalition for Health AI. Assurance Standards Guide and Assurance Reporting Checklist, 2024.
25. Newcomb, A.; Ochoa, O. Formal Methods for Safety-Critical Machine Learning: A Systematic Literature Review. *Front. Artif. Intell.* 2026, 9. doi:10.3389/frai.2026.1749956.
26. Basu, S.; et al. A Formal Verification Layer on Top of Standard Guardrails Reduces Commission and Omission Errors of Large Language Models Used in Clinical Decision Support: A Retrospective Multi-Cohort Evaluation. Companion manuscript, under review, 2026.
