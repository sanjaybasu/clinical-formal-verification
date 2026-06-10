"""Self-tests for the verifier.

The verifier is checked against two independent sources of truth: the enumeration or
breadth-first oracle (which uses no solver), and the hand-authored answer keys. A counterexample
must replay to a concrete violation. The schemas must accept every item and key.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from verifier.execute import oracle
from verifier.model import Item
from verifier.replay import confirm_witness
from verifier.smt import verify

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted((ROOT / "benchmark" / "examples").glob("*.json"))
ITEM_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "benchmark.schema.json").read_text())
KEY_SCHEMA = json.loads((ROOT / "benchmark" / "schema" / "answer_key.schema.json").read_text())


def _key_for(path: Path) -> dict:
    return json.loads((ROOT / "benchmark" / "answer_key" / path.name).read_text())


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_item_validates(path):
    item = json.loads(path.read_text())
    errors = list(Draft202012Validator(ITEM_SCHEMA).iter_errors(item))
    assert not errors, [e.message for e in errors]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_key_validates(path):
    key = _key_for(path)
    errors = list(Draft202012Validator(KEY_SCHEMA).iter_errors(key))
    assert not errors, [e.message for e in errors]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_verifier_matches_key(path):
    item = Item.load(path)
    assert verify(item).status == _key_for(path)["ground_truth"]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_verifier_matches_oracle(path):
    item = Item.load(path)
    assert verify(item).status == oracle(item)["ground_truth"]


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_counterexample_replays(path):
    item = Item.load(path)
    result = verify(item)
    if result.status == "violated":
        assert confirm_witness(item, result.witness)
