"""Verification method: the Z3 harness, run as a baseline so its outputs share the schema.

Complete and deterministic: returns a proof over the full input space or a counterexample.

    python baselines/run_verification.py
"""

from __future__ import annotations

from baselines.common import run_method
from verifier.model import Item
from verifier.smt import verify


def verdict_for(item: Item):
    result = verify(item)
    return result.status, result.witness, {"proof_scope": result.proof_scope,
                                           "method_note": result.method_note}


if __name__ == "__main__":
    print(run_method("verification", verdict_for))
