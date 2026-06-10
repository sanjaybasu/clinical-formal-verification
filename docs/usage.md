# Toolkit usage

This toolkit verifies safety properties of a deterministic clinical rule set over its full input
space, and reproduces the head-to-head measurement against probabilistic methods. It runs
offline; the language-model judge and the content-guardrail baselines are optional and need
their own credentials.

## Install

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs the `verifier` package and its dependency `z3-solver`. The benchmark validator
needs `jsonschema` (included).

## Verify a rule set

Write a rule set and a property as one item validating against
`benchmark/schema/benchmark.schema.json`, then:

```
python -m verifier path/to/item.json
```

The output states, for each item, whether the property holds over the full input space (with a
proof scope) or is violated (with a counterexample that is replayed by concrete execution). Add
`--oracle` to also run the independent enumeration or reachability oracle and confirm the two
agree:

```
python -m verifier --oracle benchmark/examples/*.json
```

## Validate items against the schema

```
python benchmark/validate.py
```

## Regenerate CIV-Bench

The benchmark is deterministic. To regenerate it identically, or to verify it without writing:

```
python benchmark/generate.py            # writes benchmark/suite/
python benchmark/generate.py --check     # verifies in memory, writes nothing
```

## Reproduce the head-to-head

Run each method, then compute the metrics. Methods without credentials in the environment record
a not_run marker per item and are reported as not run, never imputed.

```
python -m baselines.run_verification
python -m baselines.run_unit_test
# language-model judge: see docs/judge.md (uses the agent harness or an API key)
python -m baselines.run_nemo_guardrails        # needs nemoguardrails + an LLM backend
HF_TOKEN=... python -m baselines.run_llama_guard   # needs the gated weight and a GPU
python experiments/analyze.py
```

`experiments/analyze.py` reads the raw per-item outputs in `experiments/runs/<method>/` and the
answer keys, and writes `experiments/results/summary.json` and `experiments/results/tables.md`.
It contains no hand-entered numbers.

## Run the tests

```
pytest tests/
```

The tests check the verifier against the independent oracle and the answer keys, confirm that
every counterexample replays to a concrete violation, and validate the schemas.

## What the guarantee is, and is not

A holds result is a machine-checked proof that the property holds for every input in the defined
finite space of the symbolic rule set. It is not a statement about any neural model, and it is
conditional on the property being the correct one to require. A violated result is a concrete
input or event sequence that the rule set maps to a property breach, checkable by running the
rule set on it. See `docs/authoring.md` for how to express rule sets and properties, and the
manuscript for the assurance framework these results sit within.
