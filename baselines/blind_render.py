"""Render blinded judge prompts to remove label leakage.

The first judge run referenced item ids that encoded the ground-truth label and difficulty (for
example triage-d12-viol-00), and rendered rules with tell-tale names (interaction_drop,
t_resume_glitch, guard_suppress_b). Both leak the answer. This module re-renders each item with
neutral rule and transition ids (r1, r2, ...; t1, t2, ...), keeping the clinically meaningful
variable names and the property, and writes the prompt under a hash filename that encodes neither
the label nor the difficulty. A private mapping from hash to real id is written so results can be
mapped back after the run. It also emits a per-suite workflow script over the hashes.

    python baselines/blind_render.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from baselines.render import render_item
from verifier.model import Item

ROOT = Path(__file__).resolve().parent.parent
SUITES = {
    "suite": "runs", "suite_hard": "runs_hard", "suite_compute": "runs_compute",
}


def _blind_id(real_id: str) -> str:
    return "item-" + hashlib.sha256(real_id.encode()).hexdigest()[:12]


def _neutralize(raw: dict) -> dict:
    rs = raw["ruleset"]
    if rs.get("kind") == "decision":
        for i, rule in enumerate(rs["rules"], 1):
            rule["id"] = f"r{i}"
    else:
        for i, tr in enumerate(rs["transitions"], 1):
            tr["id"] = f"t{i}"
    return raw


WORKFLOW_TMPL = '''export const meta = {
  name: 'civbench-blind-judge-%(tag)s',
  description: 'Blinded LLM-as-judge over %(tag)s; neutral ids and rule names; no label leakage',
  phases: [{ title: 'Judge', detail: 'one frontier-model agent per item' }],
}
const JUDGE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['id','verdict','witness_assignment','witness_events','reasoning'],
  properties: {
    id: { type: 'string' }, verdict: { type: 'string', enum: ['holds','violated'] },
    witness_assignment: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['var','value'], properties: { var: { type: 'string' }, value: {} } } },
    witness_events: { type: 'array', items: { type: 'string' } },
    reasoning: { type: 'string' },
  },
}
const ids = %(ids)s
const base = '%(base)s'
const results = await parallel(ids.map((id) => () =>
  agent(
    `Read the file ${base}/${id}.txt . It specifies a clinical decision rule set (or state machine) and a safety property. ` +
    `Decide whether the property holds for the entire input space, or whether some input or execution violates it. Reason about rule interactions, priorities, defaults, and reachable states. Do not use web search or any tool other than reading that one file. ` +
    `Set id to "${id}". If violated, give a concrete counterexample in witness_assignment (decision systems: every input variable and value) or witness_events (state machines: the ordered event names). If it holds, leave both arrays empty. Many systems are correct; do not assume a violation exists.`,
    { label: `blindjudge:${id}`, phase: 'Judge', schema: JUDGE_SCHEMA }
  )
))
return results.filter(Boolean)
'''


def main() -> int:
    for suite, runs in SUITES.items():
        blind_dir = ROOT / "experiments" / runs / "_judge_prompts_blind"
        blind_dir.mkdir(parents=True, exist_ok=True)
        mapping = {}
        for p in sorted((ROOT / "benchmark" / suite / "items").glob("*.json")):
            raw = json.loads(p.read_text())
            real_id = raw["id"]
            bid = _blind_id(real_id)
            mapping[bid] = real_id
            item = Item.from_dict(_neutralize(raw))
            (blind_dir / f"{bid}.txt").write_text(render_item(item))
        (ROOT / "experiments" / runs / "_blind_map.json").write_text(json.dumps(mapping, indent=2))
        ids = sorted(mapping)
        script = WORKFLOW_TMPL % {"tag": suite, "ids": json.dumps(ids), "base": str(blind_dir)}
        (ROOT / "experiments" / runs / "_judge_blind_workflow.js").write_text(script)
        print(f"{suite}: {len(ids)} blinded prompts -> {blind_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
