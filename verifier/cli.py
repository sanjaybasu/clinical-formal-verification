"""Command-line entry point for the verifier.

    python -m verifier benchmark/examples/medication-contraindication-pair.json
    python -m verifier --oracle benchmark/examples/*.json
    python -m verifier --schema benchmark/schema/benchmark.schema.json item.json

Reports for each item: the status (holds or violated), the input space or bound covered, and a
replayable scenario for a counterexample. With --oracle it also runs the enumeration oracle and
confirms the two agree. Runs offline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .execute import oracle
from .model import Item
from .replay import confirm_witness, render_scenario
from .smt import verify


def _run(paths, with_oracle: bool) -> int:
    failures = 0
    for path in paths:
        item = Item.load(path)
        result = verify(item)
        line = f"[{result.status:8s}] {item.id}  ({result.seconds:.3f}s)  {result.proof_scope}"
        print(line)
        print(f"           {result.method_note}")
        if result.status == "violated":
            ok = confirm_witness(item, result.witness)
            print(f"           counterexample replays to a violation: {ok}")
            for ln in render_scenario(item, result.witness).splitlines():
                print(f"           {ln}")
            if not ok:
                failures += 1
        if with_oracle:
            orc = oracle(item)
            agree = orc["ground_truth"] == result.status
            print(f"           oracle: {orc['ground_truth']}  (agreement: {agree})")
            if not agree:
                failures += 1
        print()
    return failures


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="verifier", description="Verify clinical safety invariants.")
    p.add_argument("items", nargs="+", help="benchmark item JSON files")
    p.add_argument("--oracle", action="store_true",
                   help="also run the enumeration oracle and check agreement")
    args = p.parse_args(argv)
    paths = [Path(x) for x in args.items]
    failures = _run(paths, args.oracle)
    if failures:
        print(f"{failures} disagreement(s) or unconfirmed counterexample(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
