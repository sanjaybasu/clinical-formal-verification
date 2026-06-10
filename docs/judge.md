# Language-model judge baseline

The judge measures whether a frontier model, asked to reason about a rule set, can find property
violations. It is a probabilistic guard: it gives a verdict and an optional counterexample but no
proof and no coverage guarantee.

## How it is run

Each item is rendered to a readable specification by `baselines/render.py`: the variables with
their types and domains, the rules with priorities and the resolution policy, the default block,
and the property in both plain language and formal terms. The judge sees only the specification,
never the answer key. It returns a structured verdict (holds or violated) and, for a violation,
a counterexample.

In the committed run the judge is Claude (an Opus-class frontier model) invoked through the agent
harness, one independent agent per item. Where a direct API key is available, the same prompt can
be sent through the Anthropic API at temperature 0; the runner records the model id and decoding
with the outputs. The harness route does not pin temperature, which is recorded in
`experiments/deviations.md`.

## Witness validation

A violated verdict with a counterexample is only credited as a valid detection of a violation if
the counterexample replays to a concrete violation, checked by `verifier.replay.confirm_witness`.
This separates a correct detection from a correct verdict reached with an invalid or hallucinated
counterexample, and from a false alarm on an item that in fact holds.

## Reproducing

The rendered prompts are written to `experiments/runs/_judge_prompts/`. The workflow that fans
one agent per prompt is `experiments/runs/_judge_full_workflow.js`. Its output is ingested into
the common run schema by `baselines/ingest_judge.py`, after which `experiments/analyze.py`
computes detection, false alarm, witness validity, and detection by interaction depth.
