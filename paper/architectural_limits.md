# Why guardrail failure is architectural, not engineering debt

This section is a draft of the manuscript section that answers the standing objection to any
study of language-model safety: that the next model release will close the gap. It will be
integrated into the full manuscript with global citation renumbering; the bracketed numbers and
the reference map at the end of this file are local to the section. Citation style follows the
target venue: bracketed numbers in order of appearance. Claims discipline follows the project
rule that no result is stated more strongly than its source supports; the scope and the
not-proved boundary of each result are stated in `../references/summaries.md`.

## The assurance gap

A clinical artificial-intelligence system that acts on a patient is rarely a single model. It
is a generator wrapped in guardrails: a classifier that filters inputs and outputs, a second
model that judges the first against a rubric, a set of prompt-level rules, and retrieval that
grounds generation in source documents. Each of these guardrails is itself a statistical
system, trained by the same objective and subject to the same failure distribution as the
generator it polices. The evidence each guardrail produces is a pass rate over a test set: a
statement about the inputs that were sampled, not about the inputs that were not. A formal
method applied to a deterministic control layer produces a different kind of evidence: a proof
that a stated property holds for every input in a defined space, or a counterexample that
exhibits a specific input for which it fails. The distance between a pass rate over a sample
and a proof over a space is the assurance gap. The claim of this section is that the gap is a
consequence of architecture and learning objective, so it does not close as models improve;
the claim of the paper is that the gap can be measured, and that for the decisions placed in a
finite symbolic layer it can be closed.

## Hallucination is a property of the model class, not of a model

Three results, established by independent arguments, locate hallucination in the model class
rather than in any one model. A computability argument shows that hallucination cannot be
eliminated for the general class of computable language models. For any computable model there
exists a computable ground-truth function on which the model produces an incorrect output for
at least one input, and for some functions on infinitely many inputs, by a diagonalization over
a re-enumeration of the model's states [1]. The result is an existence statement about an
adversarially chosen ground-truth function rather than a rate over realistic inputs, and it
admits an explicit escape: hallucination can be avoided when the ground-truth functions are
confined to a restricted, computably enumerable class [1]. That escape is the opening this
paper exploits, because a finite clinical rule set is exactly such a restricted class.

A statistical argument shows that calibration and factuality are in tension on rare facts. For
facts that carry no learnable regularity, a calibrated generative model has a hallucination rate
lower-bounded by the fraction of facts that appear exactly once in training, the singleton or
monofact rate, by a connection to the Good-Turing missing-mass estimate [2]. The bound is on a
calibrated model and concerns facts without structure, not all generation; reducing the rate
below the bound requires sacrificing calibration [2]. The relevance to a safety-net population
is direct. The facts that matter in Medicaid care, a specific member's current medication, a
specific custody or housing circumstance, a specific prior adverse reaction, are by their nature
singletons in any training corpus, so they fall precisely where the calibration bound predicts
hallucination.

An incentive argument shows that the standard pipeline selects for confident error. Generative
error is lower-bounded by a reduction to binary classification error on an is-it-valid task, so
generating a valid response is at least as hard as classifying validity; and because most
benchmarks grade answers as right or wrong and penalize abstention, evaluation rewards confident
guessing over the acknowledgment of uncertainty [3]. This is an argument about training and
evaluation incentives rather than an impossibility theorem, and it points to a mitigation,
namely grading that credits calibrated uncertainty, rather than to a barrier [3]. A further
argument that the language-model pipeline reduces to undecidable problems through halting-style
reductions has been advanced [4]; it is cited here as supporting context only, because its
reductions are informal and its framing is contested, and the load of the section rests on the
computability, calibration, and incentive results above.

## The limits compound where clinical logic lives

Hallucination concerns single facts; clinical safety concerns the interaction of many rules,
and a second body of work locates a limit there. A circuit-complexity argument shows that
fixed-depth transformers with logarithmic-precision values are contained in logspace-uniform
TC0, the class of problems decidable by constant-depth threshold circuits; under the standard
conjecture that TC0 is a proper subset of P, such transformers cannot express the inherently
sequential, P-hard problems that lie outside TC0, and additional width or scale does not change
the class [5]. The bound is stated for log-precision and uniform circuits and rests on a
complexity-theoretic conjecture, and it is relaxed, not removed, by intermediate computation:
a chain of thought raises expressivity as a function of the number of decoding steps, so a
sufficient number of steps reaches beyond TC0, while a constant or logarithmic number of steps
leaves the bound in place [6]. The practical shadow of these bounds is visible empirically.
On compositional tasks, transformer accuracy decreases as the compositional depth of the
problem grows, errors compound across steps rather than composing systematically, and a
frontier model with task-specific fine-tuning still degrades with depth [7]. This empirical
pattern, not a theorem but a measurement, maps onto the object this paper's benchmark probes:
clinical safety properties that are violated only through the interaction of several rules,
where the depth of the interaction is the axis along which probabilistic methods are expected
to fail.

## Verifying the network instead is intractable

If the model class carries these limits, the natural response is to verify the trained network
directly rather than reason about the class. That route is intractable at the relevant scale.
Deciding properties of a network with rectified-linear activations is NP-complete, so an exact
verifier does not scale to frontier-size networks even though it is sound and complete on small
ones [8]. The consequence is not that neural verification is useless but that it cannot be the
mechanism by which a safety-critical decision is certified over its whole input space at
deployment scale. This is the argument for relocating the safety-critical decisions: place them
in a finite symbolic layer where exhaustive verification is decidable and inexpensive, and prove
that layer, rather than attempt to prove the network.

## The guard inherits the limits it is meant to remove

A guardrail does not escape the preceding results when the guardrail is itself a learned system.
A widely used safety classifier is a fine-tuned language model that labels inputs and outputs as
safe or unsafe [10]; a widely used rails toolkit matches user and system intents to canonical
forms through an embedding and language-model mechanism [11]. Both are statistical components,
so the computability, calibration, and incentive results apply to the guard as they apply to the
generator. The prediction is borne out empirically: character-injection and adversarial
machine-learning techniques reduce the detection accuracy of deployed guardrail systems for
prompt-injection and jailbreak inputs, which shows that a learned guard can be driven to the
wrong label by construction [9]. A guard built from the same class as the generator cannot
supply a different class of evidence about that generator.

## Synthesis: which decisions live in the provable layer

Two boundaries frame the design space. On one side, the semantic properties of arbitrary
programs are undecidable: every non-trivial property of the function a program computes admits
no general decision procedure [12], and the verification of trained networks is intractable at
scale [8]. On the other side, a finite and explicit rule layer over finite-domain variables is a
decidable object. Its input space is enumerable and its properties are expressible as formulas
whose validity a satisfiability-modulo-theories solver decides, returning a proof that a property
holds over the entire space or a counterexample that exhibits a violating input [13]. The design
question for a clinical AI system is therefore not only how good the model is but which decisions
are placed in the provable layer. A model release changes the first question. It does not change
the second, because the decidability of a finite symbolic layer and the undecidability of the
general case are properties of the objects, not of the current model.

The evidence a proof supplies is conditional, and the condition is the specification. A proof
establishes that the rule layer satisfies the property as written; it does not establish that
the property is the right one, and a verified system can still fail clinically if its
specification is wrong or incomplete [14,15]. Specification error is therefore the residual risk
of the approach, and it is the risk the paper foregrounds rather than conceals: the contribution
is a machine-checked proof of stated invariants over the full input space of the symbolic layer,
with counterexamples otherwise, and the validity of those invariants is itself an object of
clinical review.

## Local reference map

This section's bracketed numbers map to the verified entries in `../references/references.bib`:

1. Xu, Jain, Kankanhalli, Hallucination is inevitable, arXiv:2401.11817 (v2, 2025).
2. Kalai, Vempala, Calibrated language models must hallucinate, STOC 2024.
3. Kalai, Nachum, Vempala, Zhang, Evaluating large language models for accuracy incentivizes
   hallucinations, Nature 2026.
4. Banerjee, Agarwal, Singla, LLMs will always hallucinate, IntelliSys 2025 (supporting only).
5. Merrill, Sabharwal, The parallelism tradeoff, TACL 2023.
6. Merrill, Sabharwal, The expressive power of transformers with chain of thought, ICLR 2024.
7. Dziri et al., Faith and fate, NeurIPS 2023.
8. Katz, Barrett, Dill, Julian, Kochenderfer, Reluplex, CAV 2017.
9. Hackett, Birch, Trawicki, Suri, Garraghan, Bypassing LLM guardrails, LLMSEC at ACL 2025.
10. Inan et al., Llama Guard, arXiv:2312.06674 (2023).
11. Rebedea, Dinu, Sreedhar, Parisien, Cohen, NeMo Guardrails, EMNLP 2023 demonstrations.
12. Rice, Classes of recursively enumerable sets and their decision problems, Trans. AMS 1953.
13. de Moura, Bjorner, Z3: an efficient SMT solver, TACAS 2008.
14. De Millo, Lipton, Perlis, Social processes and proofs of theorems and programs, CACM 1979.
15. Clarke, Wing, Formal methods: state of the art and future directions, ACM Comput. Surv. 1996.
