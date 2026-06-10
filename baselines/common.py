"""Shared harness for baseline runners.

Each runner maps a per-item function over the benchmark, writing one JSON verdict per item to
experiments/runs/<method>/<item_id>.json. Writes are atomic and resume-safe: an item whose
output already exists is skipped, so an interrupted paid run does not re-incur cost.

Per-item output schema:
    {item_id, method, verdict: "holds"|"violated"|"unknown", witness: list|null,
     seconds: float, extra: object}
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

from verifier.model import Item

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "benchmark" / "suite"
RUNS = ROOT / "experiments" / "runs"


def item_paths(subset: list[str] | None = None) -> list[Path]:
    paths = sorted((SUITE / "items").glob("*.json"))
    if subset is not None:
        keep = set(subset)
        paths = [p for p in paths if p.stem in keep]
    return paths


def _atomic_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(tmp, path)


def run_method(method: str, fn: Callable[[Item], tuple], subset: list[str] | None = None,
               overwrite: bool = False) -> dict:
    """Run `fn(item) -> (verdict, witness, extra)` over the suite; write per-item outputs.

    Returns a small summary. Skips items already written unless overwrite is set.
    """
    out_dir = RUNS / method
    done = skipped = 0
    for path in item_paths(subset):
        out_path = out_dir / f"{path.stem}.json"
        if out_path.exists() and not overwrite:
            skipped += 1
            continue
        item = Item.load(path)
        t0 = time.perf_counter()
        verdict, witness, extra = fn(item)
        secs = time.perf_counter() - t0
        _atomic_write(out_path, {
            "item_id": item.id, "method": method, "verdict": verdict,
            "witness": witness, "seconds": round(secs, 4), "extra": extra or {},
        })
        done += 1
    return {"method": method, "written": done, "skipped": skipped}
