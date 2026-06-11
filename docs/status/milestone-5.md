# Milestone 5 status note

Scope: full manuscript and appendix, a simulated editor-and-reviewer cycle with revision, and the
submission package. This completes the milestone sequence.

## What ran

Manuscript and appendix. The Article is `paper/clinical_formal_verification_AI_mdpi.md` and the
supplementary appendix is `paper/appendix_AI_mdpi.md`, written for AI (MDPI), the Agentic AI for
Healthcare special issue, in the journal's structure with bracketed numbered citations and 26
verified references. Figures are in `paper/figures/`.

Simulated review and revision. Five skeptical domain reviewers (clinical, formal-methods,
statistics, reproducibility, positioning) critiqued the manuscript against the committed results.
Their findings were addressed rather than caveated:

- The language-model judge was re-run blinded, with item identifiers replaced by content hashes
  and rule and transition identifiers neutralised, to rule out label leakage; detection was
  unchanged, so the result reflects reasoning over the rule logic.
- The unit-test seed was made process-independent; the corrected, deterministic numbers are
  reported, which shifted unit-test detection slightly (v0 85.2%, Hard 25.0%) and the false-safe
  count to 68.
- The overclaimed term complete verification was replaced by SMT verification, defined precisely
  as a decision procedure on the finite fragment and abstention-capable on transition systems.
- The safety-net framing was decoupled from the calibration bound and made explicitly
  motivational; the tiered framework was relabelled as proposed with only two tiers evaluated; the
  companion retrospective was flagged as unpublished and non-load-bearing; Rice and Katz were
  tightened; the not-proved boundary was enumerated; the harder suites were reframed as
  non-clinical stress tests; the pre-specified McNemar test was added; the verifier unsoundness
  bug and the v0 expansion were recorded in the deviations log.

Submission package. `paper/submission/` holds the cover letter (which discloses the companion
manuscript and carries the two required statements) and a suggested-reviewer list.

Consistency. Every headline number in the manuscript, abstract, appendix, README, and combined
results was cross-checked against the canonical summaries; the check passes. Verifier self-tests
pass 15 of 15 and the benchmark validates.

## Final head-to-head (blinded judge, deterministic unit-test)

Detection on violated items: SMT verification 100% (v0), 100% (Hard), 72.5% (Compute, the
remainder abstentions); unit-test suite 85.2% (v0, falling to 20.8% at depth 12; slope -0.94, 95%
CI -1.27 to -0.62), 25.0% (Hard, zero from lock length 6), 100% (Compute); language-model judge
100% on all three. Across all 440 items SMT verification returned zero unsound verdicts; the
unit-test suite returned 68 false statements of safety; the language-model judge made no error
observed, with no guarantee. McNemar (verification vs unit-test) is significant on every suite.

## Open items for the corresponding author before submission

- Confirm the final author list and adjust the singular author wording if there are co-authors.
- Mint a Zenodo (or equivalent) DOI for the submission snapshot and update the Data Availability
  Statement, which currently states the DOI is minted on release.
- Confirm the suggested reviewers' current affiliations and emails before entry, and provide the
  companion manuscript to the handling editor on request.
- Render the manuscript to the MDPI template at the revision stage.
