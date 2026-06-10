"""NeMo Guardrails baseline runner.

Framing. NeMo Guardrails adds programmable rails to an LLM application: a configured policy plus
an LLM backend decide whether an interaction is allowed. It is applied here as a guard over the
rule set's behaviour: the rule set's recommended output on a candidate input is passed through a
rails configuration that encodes the safety property as a policy, and a blocked or refused
response is counted as a violation verdict. This is the faithful use of programmable rails; like
any LLM-backed guard it inherits the statistical failure modes discussed in the paper, and it is
not a property verifier.

Availability. This runner requires the nemoguardrails package and a configured LLM backend
(API credentials). When either is absent it records, per item, a not_run marker with the exact
command, and never imputes a verdict.

    python baselines/run_nemo_guardrails.py --config baselines/nemo_config
"""

from __future__ import annotations

import argparse

from baselines.common import run_method
from verifier.model import Item


def make_runner(config_path: str):
    from nemoguardrails import LLMRails, RailsConfig

    config = RailsConfig.from_path(config_path)
    rails = LLMRails(config)

    def verdict_for(item: Item):
        from baselines.render import render_item
        resp = rails.generate(messages=[
            {"role": "user", "content": "Review this clinical decision policy for a safety breach."},
            {"role": "context", "content": render_item(item)},
        ])
        text = (resp.get("content") if isinstance(resp, dict) else str(resp)) or ""
        blocked = any(w in text.lower() for w in ("blocked", "cannot", "unsafe", "violat", "refuse"))
        return ("violated" if blocked else "holds"), None, {"raw": text[:400]}

    return verdict_for


def main(config_path: str) -> int:
    try:
        runner = make_runner(config_path)
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        cmd = f"python baselines/run_nemo_guardrails.py --config {config_path}"
        run_method("nemo_guardrails", lambda item: ("not_run", None, {"reason": reason, "command": cmd}))
        print(f"nemo_guardrails not run: {reason}")
        return 0
    print(run_method("nemo_guardrails", runner, overwrite=True))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="baselines/nemo_config")
    raise SystemExit(main(ap.parse_args().config))
