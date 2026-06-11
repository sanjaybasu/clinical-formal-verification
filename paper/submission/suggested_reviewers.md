# Suggested and excluded reviewers

Per the journal's instructions, reviewer suggestions are entered in the submission system, not in
the cover letter. This file is a working list for the corresponding author. Affiliations and email
addresses must be confirmed against each reviewer's current institutional page before entry; they
are deliberately not filled here to avoid recording unverified contact details.

## Ideal reviewer profiles

The paper spans three areas, and the panel should cover all three:

1. Formal methods and verification: satisfiability-modulo-theories solving, model checking, and
   neural-network verification, able to assess the soundness and completeness claims and the
   abstention discipline.
2. Clinical AI safety and informatics: deployment of language models in clinical decision support,
   able to assess the clinical realism of the rule sets and the safety properties.
3. Machine-learning evaluation and benchmarks: able to assess the head-to-head design, the
   confidence intervals, the blinding of the language-model judge, and external validity.

## Candidate reviewers (confirm affiliation and email before entry)

- A formal-methods researcher in neural-network or probabilistic verification (for example,
  Marta Kwiatkowska, Oxford, or Corina Pasareanu, Carnegie Mellon / NASA Ames). Rationale: can
  scrutinise the SMT encoding, the bounded-model-checking completeness argument, and the
  characterisation of verification's tractability boundary.
- A clinical machine-learning safety researcher (for example, Marzyeh Ghassemi, MIT). Rationale:
  can assess whether the triage, medication, and outreach properties are clinically meaningful and
  whether the safety-net framing is appropriately scoped.
- A clinical informatics researcher working on AI deployment and assurance (for example, Nigam
  Shah, Stanford). Rationale: can assess the realism of reducing a clinical control layer to a
  finite symbolic object and the deployment relevance of the tiered framework.
- A reviewer in language-model evaluation and red-teaming. Rationale: can assess the blinded judge
  protocol and the label-leakage correction.

These names are suggestions of appropriate expertise; the corresponding author should confirm each
is a recognised expert with no conflict and substitute equivalents as needed.

## Exclusions

Exclude any current or recent collaborators of the author and any co-authors of the companion
manuscript referenced as [26]. The author is an employee of Waymark; exclude Waymark personnel.
