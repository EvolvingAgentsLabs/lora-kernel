"""S4 — train the adapters and grade them. The implementation; the notebook calls it.

TWO QUESTIONS, EITHER OF WHICH CAN FAIL

  1. DOES SPECIALISATION HAPPEN AT ALL? The adapter must beat the base on cases
     neither of them was trained on. If it does not, no routing scheme rescues it
     and the expert pool has nothing in it.

  2. DO EXPERTS DIFFER BY REGION? An adapter trained on clinic alpha and one
     trained on clinic beta must each win on their own clinic. If they do not,
     the pool is one expert wearing three names and there is nothing for
     acceptance to route between — which ends the architecture's central claim
     for the price of a free T4.

THE PROBE THAT TRAVELS WITH ANY GAIN. `val_delta` is the clinic where one
unpublished rule INVERTS, and it is in no training split. An adapter that
memorised the rule scores well on `val` and collapses here. That gap is the
false-promotion number, and a gain published without it is not a result.

EVERY ARM IS GRADED BY THE SAME CODE (`training/evaluate.py`) and generated
greedily, because every number this project has produced is at temperature 0.

    python3 -m training.s4_train --base google/gemma-4-E4B-it
"""

from __future__ import annotations

import argparse
import gc
import json
import random
import time
from pathlib import Path

from training.evaluate import compare, evaluate, load_jsonl

RESULTS = Path("s4_results.json")


def _seed(n: int) -> None:
    import numpy as np
    import torch
    random.seed(n)
    np.random.seed(n)
    torch.manual_seed(n)


def load_base(base: str, four_bit: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    ) if four_bit else None
    tok = AutoTokenizer.from_pretrained(base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base, quantization_config=bnb, dtype=torch.bfloat16, device_map="auto")
    model.config.use_cache = True
    return model, tok


def make_generate(model, tok, max_new_tokens: int = 64):
    import torch

    def gen(system: str, user: str) -> str:
        msgs = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
        try:
            text = tok.apply_chat_template(msgs, tokenize=False,
                                           add_generation_prompt=True)
        except Exception:          # a base model with no chat template
            text = f"{system}\n\n{user}\n\n"
        ids = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=max_new_tokens,
                                 do_sample=False, pad_token_id=tok.pad_token_id)
        return tok.decode(out[0][ids["input_ids"].shape[1]:],
                          skip_special_tokens=True)
    return gen


def train_adapter(base: str, rows: list[dict], out_dir: str, args):
    """A fresh base per adapter.

    `prepare_model_for_kbit_training` mutates the model it is given, so reusing
    one across adapters would train the second on top of the first and call the
    result a region expert. Reloading costs a minute and removes the question.
    """
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer

    model, tok = load_base(base, args.four_bit)
    texts = []
    for r in rows:
        try:
            texts.append({"text": tok.apply_chat_template(r["messages"],
                                                          tokenize=False)})
        except Exception:
            m = r["messages"]
            texts.append({"text": f"{m[0]['content']}\n\n{m[1]['content']}\n\n"
                                  f"{m[2]['content']}"})
    model = prepare_model_for_kbit_training(model) if args.four_bit else model
    peft_model = get_peft_model(model, LoraConfig(
        r=args.r, lora_alpha=args.alpha, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"]))
    peft_model.print_trainable_parameters()
    SFTTrainer(
        model=peft_model, train_dataset=Dataset.from_list(texts),
        args=SFTConfig(output_dir=out_dir, num_train_epochs=args.epochs,
                       per_device_train_batch_size=args.batch,
                       gradient_accumulation_steps=args.accum,
                       learning_rate=args.lr, max_length=args.max_seq,
                       logging_steps=10, seed=args.seed, report_to=[],
                       save_strategy="no", bf16=True),
    ).train()
    peft_model.save_pretrained(out_dir)
    return peft_model, tok


def free(*objs) -> None:
    import torch
    for o in objs:
        del o
    gc.collect()
    torch.cuda.empty_cache()


def save(summary: dict) -> None:
    """Persisted after every arm: a run killed at the third adapter keeps the
    two it already paid for."""
    RESULTS.write_text(json.dumps(summary, indent=2))


def run_all(args) -> dict:
    _seed(args.seed)
    train = load_jsonl("training/data/train.jsonl")
    val = load_jsonl("training/data/val.jsonl")[:args.n_val]
    delta = load_jsonl("training/data/val_delta.jsonl")[:args.n_delta]
    summary = {"base": args.base, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "lora": {"r": args.r, "alpha": args.alpha, "epochs": args.epochs,
                        "lr": args.lr, "train_n": len(train)},
               "n": {"val": len(val), "delta": len(delta)}}
    save(summary)

    # -- the baseline, recorded before the treatment exists ---------------------
    model, tok = load_base(args.base, args.four_bit)
    gen = make_generate(model, tok, args.max_new_tokens)
    summary["base_val"] = evaluate(gen, val, "base")
    summary["base_delta"] = evaluate(gen, delta, "base · delta")
    save(summary)
    free(gen, model, tok)

    # -- question 1: does specialisation happen at all? -------------------------
    expert, tok = train_adapter(args.base, train, "adapters/all-clinics", args)
    gen = make_generate(expert, tok, args.max_new_tokens)
    summary["adapter_val"] = evaluate(gen, val, "adapter")
    summary["adapter_delta"] = evaluate(gen, delta, "adapter · delta")
    save(summary)
    free(gen, expert, tok)

    # -- question 2: do experts differ by region? ------------------------------
    regions = {}
    val_a = [r for r in val if r["clinic"] == "alpha"][:args.n_region]
    val_b = [r for r in val if r["clinic"] == "beta"][:args.n_region]
    for clinic, own, other in (("alpha", val_a, val_b), ("beta", val_b, val_a)):
        rows = [r for r in train if r["clinic"] == clinic]
        exp, tk = train_adapter(args.base, rows, f"adapters/{clinic}", args)
        g = make_generate(exp, tk, args.max_new_tokens)
        regions[f"{clinic}_on_own"] = evaluate(g, own, f"{clinic} on own")
        regions[f"{clinic}_on_other"] = evaluate(g, other, f"{clinic} on other")
        summary["regions"] = regions
        save(summary)
        free(g, exp, tk)

    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save(summary)
    return summary


def verdict(s: dict) -> str:
    lines = ["", "=" * 72, "S4 — the two questions", "=" * 72,
             compare(s["base_val"], s["adapter_val"]), ""]
    gain = s["adapter_val"]["accuracy"] - s["base_val"]["accuracy"]
    probe = s["adapter_delta"]["accuracy"] - s["base_delta"]["accuracy"]
    lines += [f"gain on the published clinics {gain:+.3f}",
              f"the same adapter on the inverted rule {probe:+.3f}"]
    if gain > 0 and probe < 0:
        lines.append("FALSE PROMOTION SHAPE: it learned the rule, not the "
                     "reading. Both numbers go in the report.")
    r = s.get("regions") or {}
    if r:
        own = (r["alpha_on_own"]["accuracy"] + r["beta_on_own"]["accuracy"]) / 2
        other = (r["alpha_on_other"]["accuracy"] + r["beta_on_other"]["accuracy"]) / 2
        lines += ["", f"region experts: own {own:.3f} vs other {other:.3f} "
                      f"({own - other:+.3f})"]
        if own <= other:
            lines.append("NO SPECIALISATION BY REGION. The pool has nothing to "
                         "route between — say so and stop.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="google/gemma-4-E4B-it")
    ap.add_argument("--n-val", type=int, default=120)
    ap.add_argument("--n-delta", type=int, default=60)
    ap.add_argument("--n-region", type=int, default=40)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--max-seq", type=int, default=1024)
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fp16-base", dest="four_bit", action="store_false",
                    help="skip 4-bit quantisation (needs a bigger GPU)")
    args = ap.parse_args()
    print(verdict(run_all(args)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
