# Milestone 1 status note

Scope of this milestone: references verified, architectural-limits section drafted, benchmark
schema finalized, repository set up. Per the project plan, work stops here for review before
Milestone 2.

## What ran

Citation verification. Fourteen citation groups were verified through three independent layers:
a reader workflow that fetched each primary source and returned bibliography, a faithful
summary, scope, and a not-proved statement; an adversarial overclaim audit on the six
load-bearing theoretical results, all of which returned summary faithful; and confirmation of
ten DOIs against the Crossref registry. A paperclip full-text repository (`clinical-formal-
verification`, eleven documents) holds the sources; the FDA lifecycle-management claim is
verified against the document text with line-level evidence. Provenance is in
`references/verification.md`; per-paper summaries with scope and claims discipline are in
`references/summaries.md`; the bibliography is `references/references.bib`.

Corrections found during verification (memory errors in the plan were not propagated):

- The Kalai, Nachum, Vempala, Zhang preprint "Why language models hallucinate" is now the
  peer-reviewed Nature article "Evaluating large language models for accuracy incentivizes
  hallucinations" (2026); the Nature version is cited.
- Banerjee et al. is now an IntelliSys 2025 proceedings chapter; cited as supporting only.
- There is no single FDA generative-AI assurance guidance; the draft AI-device guidance, the
  final predetermined-change-control-plan guidance, and the Coalition for Health AI assurance
  framework are cited as distinct documents. The assurance-lab concept is the Coalition for
  Health AI's, not the FDA's.
- For the deployed guardrail baseline, Llama Guard 4 (2025) is the current version; the original
  Llama Guard is cited for lineage.

Benchmark schema. `benchmark/schema/benchmark.schema.json` defines decision rule sets and
transition systems over finite-domain variables, with five property kinds: invariant,
reachability, mutual exclusion, monotonicity, and temporal. `answer_key.schema.json` holds
ground truth separately, with a witness that is checkable by concrete execution of the rule set,
so labeling the benchmark does not depend on the solver under test. `benchmark/validate.py`
validates items and keys; three worked examples (triage monotonicity, medication mutual
exclusion with a seeded depth-2 interaction, outreach temporal persistence) validate clean.

Architectural-limits section. `paper/architectural_limits.md` is drafted: the assurance gap,
hallucination as a property of the model class (computability, calibration, incentive
arguments), compounding limits where clinical logic lives (circuit complexity, chain-of-thought
expressivity, compositionality), the intractability of verifying the network instead, the
guard-recursion problem, and the synthesis on which decisions live in the provable layer. Claims
discipline is enforced throughout.

Venue. The target venue is confirmed: AI (MDPI), the Agentic AI for Healthcare special issue,
deadline 31 March 2027. Requirements are captured in `paper/submission/mdpi_ai_requirements.md`.
Note the citation style differs from the author's usual superscript convention: this journal
uses bracketed numbers, which the manuscript adopts.

Repository. Public at https://github.com/sanjaybasu/clinical-formal-verification, Apache-2.0 for
code and CC-BY-4.0 for the benchmark.

## Numbers

- 14 citations verified, 0 unverifiable, 4 bibliographic corrections applied.
- 6 of 6 load-bearing theoretical results passed the adversarial overclaim audit.
- 10 of 10 checked DOIs confirmed against Crossref; the NeurIPS proceedings DOI for Dziri et al.
  is not Crossref-registered and is confirmed via arXiv and OpenReview.
- 3 example benchmark items and 3 answer keys validate against the schemas.
- 3 domains covered by the schema (triage, medication, outreach); 5 property kinds.

## Open risks and decisions

- Benchmark name is not chosen; it propagates through the benchmark, the paper, and the docs, so
  it is the gating decision before Milestone 2 authors the full suite.
- The Institutional Review Board statement for the private split derived from the operational
  Medicaid care program is unresolved; the public benchmark is synthetic or public-derived and
  has no human subjects. Resolve against the governing determination before submission.
- The reporting guideline is unresolved; TRIPOD-AI does not map cleanly to a verification study.
- Paperclip per-claim verification is complete for the FDA document; the ten theory and tooling
  claims are verified by the reader workflow and Crossref, with paperclip line citations to be
  added when manuscript prose is written.
- z3-solver is not yet installed; it is a Milestone 2 dependency.

## Next: Milestone 2

Verifier passing self-tests (rule-schema compiler to Z3, property checker returning a proof or
a counterexample, counterexample replay), benchmark v0 with answer key, and the evaluation
protocol pre-registered in the repository before any baseline is run.
