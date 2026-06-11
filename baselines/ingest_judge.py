"""Convert language-model judge workflow output into per-item run files.

The judge workflow returns one record per item: {id, verdict, witness_assignment,
witness_events, reasoning}. This normalizes each into the common run schema so the witness can
be replay-validated by experiments/analyze.py. For monotonicity items the judge's assignment is
treated as the perturbed point; the comparison base is reconstructed by undoing the perturbation.

    python baselines/ingest_judge.py /path/to/workflow_output.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from baselines.common import RUNS, SUITE, _atomic_write
from verifier.model import Item


def _normalize_witness(item: Item, rec: dict):
    if rec["verdict"] != "violated":
        return None
    if not item.is_decision:
        events = rec.get("witness_events") or []
        return [{"event": e} for e in events] if events else []
    assignment = rec.get("witness_assignment") or []
    if not assignment:
        return []
    if item.property.kind != "monotonicity":
        return [{"var": a["var"], "value": a["value"]} for a in assignment]
    # monotonicity: treat the given assignment as the perturbed point; rebuild the base
    mono = item.property.monotonicity
    pvar, change = mono["perturbation"]["var"], mono["perturbation"]["change"]
    pert = {a["var"]: a["value"] for a in assignment}
    if change == "set_true":
        pert[pvar] = True
        base = dict(pert); base[pvar] = False
    else:
        base = dict(pert); base[pvar] = pert.get(pvar, 1) - 1
    return [{"var": k, "value": v} for k, v in pert.items()] + \
           [{"var": f"{k}__base", "value": v} for k, v in base.items()]


def _extract_records(blob):
    if isinstance(blob, dict) and "result" in blob:
        blob = blob["result"]
    if isinstance(blob, str):
        blob = json.loads(blob)
    return blob


def main(path: str) -> int:
    blob = _extract_records(json.loads(Path(path).read_text()))
    items = {p.stem: Item.load(p) for p in (SUITE / "items").glob("*.json")}
    written = 0
    for rec in blob:
        if not rec or "id" not in rec:
            continue
        item = items[rec["id"]]
        witness = _normalize_witness(item, rec)
        _atomic_write(RUNS / "llm_judge" / f"{rec['id']}.json", {
            "item_id": rec["id"], "method": "llm_judge", "verdict": rec["verdict"],
            "witness": witness, "seconds": None,
            "extra": {"reasoning": rec.get("reasoning", ""), "judge": "claude-opus-4-8-class-agent"},
        })
        written += 1
    print(f"ingested {written} judge records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
