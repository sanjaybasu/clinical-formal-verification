"""Batch LLM-as-judge runner (50% cheaper) for OpenAI and Gemini.

Submits all items as one asynchronous batch (OpenAI Batch API; Gemini batchGenerateContent),
polls to completion, retrieves results, and writes per-item verdicts in the common run schema.
Blinded rendering is identical to the synchronous runner. Resume-safe at the item level: items
already written are skipped, so a re-run only submits the remainder.

    source ~/.civbench_keys.env
    CIVBENCH_SUITE=benchmark/suite_v3 CIVBENCH_RUNS=experiments/runs_v3 \
      python -m baselines.run_judge_batch --provider openai --model gpt-5.5
      python -m baselines.run_judge_batch --provider gemini --model gemini-3.1-pro-preview
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request

from baselines.common import RUNS, SUITE, _atomic_write, item_paths
from baselines.ingest_judge import _normalize_witness
from baselines.run_judge_api import _parse_json, _prompt_for
from verifier.model import Item


def _req(url, data, headers, method="POST", timeout=120):
    if isinstance(data, dict):
        data = json.dumps(data).encode(); headers = {**headers, "Content-Type": "application/json"}
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _verdict(rec):
    v = "violated" if str(rec.get("verdict", "")).lower().startswith("viol") else "holds"
    return {"verdict": v, "witness_assignment": rec.get("witness_assignment") or [], "witness_events": rec.get("witness_events") or []}


# --------------------------------------------------------------------------- OpenAI

def openai_batch(model, prompts, poll=20):
    key = os.environ["OPENAI_API_KEY"]
    auth = {"Authorization": f"Bearer {key}"}
    lines = [json.dumps({"custom_id": stem, "method": "POST", "url": "/v1/chat/completions",
                         "body": {"model": model, "messages": [{"role": "user", "content": p}],
                                  "response_format": {"type": "json_object"}, "max_completion_tokens": 6000}})
             for stem, p in prompts.items()]
    jsonl = ("\n".join(lines)).encode()
    boundary = "----civbenchboundary"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\nbatch\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"batch.jsonl\"\r\n"
            f"Content-Type: application/jsonl\r\n\r\n").encode() + jsonl + f"\r\n--{boundary}--\r\n".encode()
    up = _req("https://api.openai.com/v1/files", body,
              {**auth, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    batch = _req("https://api.openai.com/v1/batches",
                 {"input_file_id": up["id"], "endpoint": "/v1/chat/completions", "completion_window": "24h"}, auth)
    bid = batch["id"]
    while True:
        st = _req(f"https://api.openai.com/v1/batches/{bid}", None, auth, method="GET")
        if st["status"] in ("completed", "failed", "expired", "cancelled"):
            break
        print(f"  openai batch {bid}: {st['status']} ({st.get('request_counts')})"); time.sleep(poll)
    if st["status"] != "completed":
        raise RuntimeError(f"openai batch {st['status']}: {st.get('errors')}")
    content = urllib.request.urlopen(urllib.request.Request(
        f"https://api.openai.com/v1/files/{st['output_file_id']}/content", headers=auth), timeout=120).read().decode()
    out = {}
    for line in content.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        try:
            out[rec["custom_id"]] = _parse_json(rec["response"]["body"]["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"  parse fail {rec.get('custom_id')}: {e}")
    return out


# --------------------------------------------------------------------------- Gemini

def gemini_batch(model, prompts, poll=20):
    key = os.environ["GEMINI_API_KEY"]
    reqs = [{"request": {"contents": [{"parts": [{"text": p}]}],
                         "generationConfig": {"responseMimeType": "application/json"}},
             "metadata": {"key": stem}} for stem, p in prompts.items()]
    body = {"batch": {"display_name": "civbench", "input_config": {"requests": {"requests": reqs}}}}
    create = _req(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchGenerateContent?key={key}", body, {})
    name = create["name"]
    while True:
        st = _req(f"https://generativelanguage.googleapis.com/v1beta/{name}?key={key}", None, {}, method="GET")
        state = str(st.get("metadata", {}).get("state", "") or st.get("state", ""))
        if st.get("done") or "SUCCEEDED" in state or "FAILED" in state:
            break
        print(f"  gemini batch: {state or 'running'}"); time.sleep(poll)
    resp = st.get("response", {})
    inlined = (resp.get("inlinedResponses", {}) or {}).get("inlinedResponses") \
        or (resp.get("dest", {}) or {}).get("inlinedResponses") or resp.get("inlinedResponses") or []
    out = {}
    for r in inlined:
        k = r.get("metadata", {}).get("key") or r.get("key")
        rr = r.get("response", r)
        try:
            parts = rr["candidates"][0]["content"]["parts"]
            out[k] = _parse_json("".join(p.get("text", "") for p in parts))
        except Exception as e:
            print(f"  parse fail {k}: {e}")
    return out


BATCHERS = {"openai": openai_batch, "gemini": gemini_batch}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=list(BATCHERS))
    ap.add_argument("--model", required=True)
    ap.add_argument("--method", default=None)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    method = args.method or ("judge_" + args.model.replace(".", "").replace("-", ""))
    out_dir = RUNS / method
    paths = item_paths()
    if args.limit:
        paths = paths[:args.limit]
    items = {p.stem: Item.load(p) for p in paths}
    prompts = {p.stem: _prompt_for(p) for p in paths if not (out_dir / f"{p.stem}.json").exists()}
    if not prompts:
        print(f"{method}: all {len(items)} already done"); return 0
    print(f"{method}: submitting {len(prompts)} items as a batch ...")
    results = BATCHERS[args.provider](args.model, prompts)
    written = 0
    for stem, rec in results.items():
        if stem not in items:
            continue
        rec2 = _verdict(rec)
        witness = _normalize_witness(items[stem], rec2)
        _atomic_write(out_dir / f"{stem}.json", {"item_id": stem, "method": method, "verdict": rec2["verdict"],
                      "witness": witness, "seconds": None,
                      "extra": {"model": args.model, "reasoning": str(rec.get("reasoning", ""))[:500], "batch": True}})
        written += 1
    print(f"{method}: wrote {written} (of {len(prompts)} submitted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
