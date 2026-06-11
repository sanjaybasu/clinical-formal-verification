"""Blinded LLM-as-judge baseline over an API, parameterized by model.

Renders each item with neutralized rule/transition ids and no item id (no label leakage), sends the
clean specification to a frontier model, and parses a structured holds/violated verdict plus a
witness. Verdicts are written through the common resume-safe harness, one file per item under
experiments/<runs>/<method>/, so an interrupted paid run never re-incurs cost. The judge supplies
no soundness or coverage guarantee; it is one of the probabilistic baselines.

    source ~/.civbench_keys.env
    CIVBENCH_SUITE=benchmark/suite_v2 CIVBENCH_RUNS=experiments/runs_v2 \
      python -m baselines.run_judge_api --provider openai --model gpt-5.5
      python -m baselines.run_judge_api --provider gemini --model gemini-3.1-pro-preview
      python -m baselines.run_judge_api --provider anthropic --model claude-fable-5
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request

from baselines.common import run_method
from baselines.ingest_judge import _normalize_witness
from baselines.render import render_item
from verifier.model import Item

JSON_INSTRUCT = (
    "\n\nRespond with ONLY a JSON object, no prose outside it, with keys: "
    '"verdict" (either "holds" or "violated"), '
    '"witness_assignment" (array of {"var","value"} giving every input variable, for a violated '
    'decision system; else empty), '
    '"witness_events" (array of event-name strings in order, for a violated state machine; else '
    'empty), and "reasoning" (a brief string).'
)


def _neutralize(raw: dict) -> dict:
    rs = raw["ruleset"]
    seq = rs["rules"] if rs.get("kind") == "decision" else rs["transitions"]
    for i, r in enumerate(seq, 1):
        r["id"] = ("r" if rs.get("kind") == "decision" else "t") + str(i)
    return raw


def _prompt_for(item_path) -> str:
    raw = _neutralize(json.loads(item_path.read_text()))
    return render_item(Item.from_dict(raw)) + JSON_INSTRUCT


def _http(url: str, body: dict, headers: dict, attempts: int = 5) -> dict:
    data = json.dumps(body).encode()
    last = None
    for k in range(attempts):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(min(2 ** k * 2, 30)); continue
            raise RuntimeError(last)
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e); time.sleep(min(2 ** k * 2, 30)); continue
    raise RuntimeError(f"exhausted retries: {last}")


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    i, j = text.find("{"), text.rfind("}")
    return json.loads(text[i:j + 1])


def call_openai(model, prompt):
    out = _http("https://api.openai.com/v1/chat/completions",
                {"model": model, "messages": [{"role": "user", "content": prompt}],
                 "response_format": {"type": "json_object"}, "max_completion_tokens": 6000},
                {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    return _parse_json(out["choices"][0]["message"]["content"])


def call_gemini(model, prompt):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    out = _http(url, {"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"responseMimeType": "application/json"}}, {"Content-Type": "application/json"})
    parts = out["candidates"][0]["content"]["parts"]
    return _parse_json("".join(p.get("text", "") for p in parts))


def call_anthropic(model, prompt):
    out = _http("https://api.anthropic.com/v1/messages",
                {"model": model, "max_tokens": 6000, "messages": [{"role": "user", "content": prompt}]},
                {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"})
    text = "".join(b.get("text", "") for b in out["content"] if b.get("type") == "text")
    return _parse_json(text)


CALLERS = {"openai": call_openai, "gemini": call_gemini, "anthropic": call_anthropic}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=list(CALLERS))
    ap.add_argument("--model", required=True)
    ap.add_argument("--method", default=None, help="run dir name; default judge_<model>")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    from baselines.common import SUITE
    caller = CALLERS[args.provider]
    prompts = {p.stem: _prompt_for(p) for p in sorted((SUITE / "items").glob("*.json"))}

    def verdict_for(item: Item):
        t0 = time.perf_counter()
        rec = caller(args.model, prompts[item.id])
        verdict = "violated" if str(rec.get("verdict", "")).lower().startswith("viol") else "holds"
        rec2 = {"verdict": verdict, "witness_assignment": rec.get("witness_assignment") or [],
                "witness_events": rec.get("witness_events") or []}
        witness = _normalize_witness(item, rec2)
        return verdict, witness, {"model": args.model, "reasoning": str(rec.get("reasoning", ""))[:500],
                                  "api_seconds": round(time.perf_counter() - t0, 2)}

    method = args.method or ("judge_" + args.model.replace(".", "").replace("-", ""))
    subset = sorted(prompts)[:args.limit] if args.limit else None
    print(run_method(method, verdict_for, subset=subset))


if __name__ == "__main__":
    raise SystemExit(main())
