"""Validate benchmark items and answer keys against the schemas.

Usage:
    python benchmark/validate.py

Exits non-zero on the first invalid file. Runs offline.
"""

import json
import pathlib
import sys

from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parent
ITEM_SCHEMA = json.loads((ROOT / "schema" / "benchmark.schema.json").read_text())
KEY_SCHEMA = json.loads((ROOT / "schema" / "answer_key.schema.json").read_text())


def _check(paths, schema, label):
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    failed = 0
    for path in sorted(paths):
        doc = json.loads(path.read_text())
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            failed += 1
            print(f"fail {label}: {path}")
            for err in errors[:6]:
                print(f"     {list(err.path)} - {err.message}")
        else:
            print(f"ok   {label}: {path}")
    return failed


def main():
    failed = 0
    failed += _check((ROOT / "examples").glob("*.json"), ITEM_SCHEMA, "item")
    failed += _check((ROOT / "answer_key").glob("*.json"), KEY_SCHEMA, "key")
    if failed:
        print(f"{failed} file(s) failed validation")
        sys.exit(1)
    print("all files valid")


if __name__ == "__main__":
    main()
