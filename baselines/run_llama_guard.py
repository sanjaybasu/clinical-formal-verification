"""Llama Guard baseline runner.

Framing. Llama Guard is a content-safety classifier: it labels a conversation as safe or unsafe
against a hazard taxonomy (violence, self-harm, and similar). It is applied here as a runtime
monitor on the rule set's behaviour: for each item the rule set's recommended output on a
candidate input is presented as the assistant turn, and Llama Guard is asked whether it is
unsafe. A flag is counted as a violation verdict. This is the faithful use of a content guardrail
and is reported as such; it is not a property verifier.

Availability. This runner requires the gated model weight meta-llama/Llama-Guard-4-12B (Hugging
Face access token) and a GPU. When either is absent it records, per item, a not_run marker with
the exact command, and never imputes a verdict.

    HF_TOKEN=... python baselines/run_llama_guard.py --model meta-llama/Llama-Guard-4-12B
"""

from __future__ import annotations

import argparse
import os

from baselines.common import run_method
from verifier.model import Item

MODEL_DEFAULT = "meta-llama/Llama-Guard-4-12B"


def _load_classifier(model_id: str):
    import torch  # noqa: F401
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto", device_map="auto")
    return tok, model


def make_runner(model_id: str):
    tok, model = _load_classifier(model_id)

    def verdict_for(item: Item):
        # present the rule set output as the assistant message and classify it
        from baselines.render import render_item
        convo = [{"role": "user", "content": "Recommend care for this patient."},
                 {"role": "assistant", "content": render_item(item)}]
        prompt = tok.apply_chat_template(convo, tokenize=False)
        ids = tok(prompt, return_tensors="pt").to(model.device)
        out = model.generate(**ids, max_new_tokens=20, do_sample=False)
        text = tok.decode(out[0][ids["input_ids"].shape[-1]:], skip_special_tokens=True).strip().lower()
        verdict = "violated" if text.startswith("unsafe") else "holds"
        return verdict, None, {"model": model_id, "raw": text}

    return verdict_for


def main(model_id: str) -> int:
    available = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    try:
        if not available:
            raise RuntimeError("no Hugging Face token in HF_TOKEN/HUGGINGFACE_TOKEN")
        runner = make_runner(model_id)
    except Exception as exc:  # dependency, credential, or hardware missing
        reason = f"{type(exc).__name__}: {exc}"
        cmd = f"HF_TOKEN=... python baselines/run_llama_guard.py --model {model_id}"
        run_method("llama_guard", lambda item: ("not_run", None, {"reason": reason, "command": cmd}))
        print(f"llama_guard not run: {reason}")
        return 0
    print(run_method("llama_guard", runner, overwrite=True))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_DEFAULT)
    raise SystemExit(main(ap.parse_args().model))
