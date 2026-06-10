# Run environment and method availability

This records which methods were run in the environment that produced the committed outputs, and
which were not, so that empty result cells are unambiguous and never imputed.

## Methods run

- Complete verification: run. z3-solver 4.16.0, Python 3 on macOS (Darwin, arm64). Deterministic.
- Unit-test suite: run. N = 1000 samples per item, seed 20260610. No external dependency.
- Language-model judge: run. The judge is Claude (Opus-class frontier model) invoked through the
  agent harness; each item is judged by an independent agent that reads only the rendered
  specification and returns a structured verdict, with no access to ground truth. The exact
  prompt is `baselines/render.py` plus the instruction in the judge runner; raw per-item outputs
  are under `experiments/runs/llm_judge/`. Decoding is the harness default; this is recorded as a
  deviation from the protocol's temperature-0 specification in `experiments/deviations.md`.

## Methods not run in this environment

- NeMo Guardrails: not run. The `nemoguardrails` package and a configured LLM backend
  (API credentials) are required. The runner `baselines/run_nemo_guardrails.py` records a
  not_run marker per item with the exact command. No verdict is imputed.
- Llama Guard: not run. The gated weight `meta-llama/Llama-Guard-4-12B` (Hugging Face token) and
  a GPU are required. The runner `baselines/run_llama_guard.py` records a not_run marker per item
  with the exact command. No verdict is imputed.

Both content-safety guardrails are LLM-backed classifiers; they belong to the same statistical
class as the language-model judge and are positioned in the paper within the tiered assurance
framework as runtime monitors rather than property verifiers. Their omission from the head-to-head
rate tables is a stated limitation, not a gap in the argument: the language-model judge already
represents the learned-guard class in the comparison.
