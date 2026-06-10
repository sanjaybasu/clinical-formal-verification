# Milestone 2 status note

Scope: verifier passing self-tests, CIV-Bench v0 with answer keys, evaluation protocol
pre-registered. Per the project plan, a status note is recorded at the boundary.

## What ran

Verifier. The `verifier/` package compiles the benchmark schema to Z3 and decides a property
over the full input space. Decision rule sets compile to output terms under priority or
first-match resolution; the five property kinds are handled (invariant and reachability by
unsatisfiability of the negation, mutual exclusion and monotonicity by template expansion,
temporal by bounded model checking with a k-induction step for an unbounded result).
Counterexamples are returned as concrete assignments or event traces and are replayed by
concrete execution to confirm the violation. `verifier.execute` provides an independent oracle
(exhaustive enumeration for decision rule sets, breadth-first reachability for transition
systems) that uses no solver and establishes ground truth without the system under test.

Self-tests. `pytest tests/` passes 15 of 15: schema validation of items and keys, agreement of
the verifier with the answer keys and with the oracle, and replay of every counterexample.

CIV-Bench v0. `benchmark/generate.py` produced 180 items under `benchmark/suite/`: 120 with a
seeded violation at interaction depth 1 to 4 (10 per depth in each of three domains) and 60 with
no fault. Every seeded violation is confirmed by the oracle and replays to a concrete violation;
every holds item is confirmed by enumeration. The generator is deterministic (seeded, no
wall-clock).

Protocol. `experiments/protocol.md` is committed before any baseline runs, which is its
registration; the metrics, methods, and analysis are fixed.

## Numbers

- Verifier vs oracle on all 180 items: 0 disagreements, 0 unconfirmed counterexamples.
- Verifier mean time 3.7 ms per item; complete verification detects 120 of 120 seeded violations
  by construction and proves the 60 holds items over their full input spaces.
- Self-tests: 15 of 15 pass.
- Benchmark: 180 items, 120 violated (30 per depth), 60 holds; 3 domains.

## Open risks and decisions

- Complete verification detecting all 120 violations is a property of the method, not yet a
  comparison; the comparison is Milestone 3.
- Llama Guard 4 needs a gated model weight and a GPU, neither available in this environment; its
  runner will be built and its result reported as not run with the exact command, not imputed.
- The language-model judge incurs paid API cost; it runs a 12-item pilot first under the cost
  discipline in the protocol.

## Next: Milestone 3

Build the four baseline runners, run the head-to-head on CIV-Bench v0, compute miss rate,
false-alarm rate, witness validity, and detection by interaction depth with 95% Wilson
confidence intervals, and select the counterexample case studies.
