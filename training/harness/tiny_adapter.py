"""A native adapter, trained only far enough to change the output.

WHY THIS EXISTS. The identity gate asks whether vLLM applies a LoRA. P29 and the
Qwen3.5 run both answered it with an adapter trained for a **different base** — wrong
tokenizer, wrong dimensions — and got `IDENTICAL TO BASE`. That reading is ambiguous
between two very different facts:

    the model class does not apply LoRA
    vLLM silently ignores a mismatched adapter

**The second would be the worse finding**, because it means the gate cannot tell a
wrong adapter from an unsupported class, and a deployment could serve the base while
believing it serves an expert.

So: a native adapter. It does not have to be good — it has to have the right shapes
and to have moved the weights. A few hundred steps on any text at all is enough,
because the question is whether the serving stack applies a delta, not whether the
delta helps.

    python3 -m training.harness.tiny_adapter --base Qwen/Qwen3.5-4B --out adapters/tiny
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", default="adapters/tiny")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq", type=int, default=512)
    args = ap.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              DataCollatorForLanguageModeling, Trainer,
                              TrainingArguments)
    from datasets import Dataset

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.bfloat16,
                                                 device_map="cuda")
    # TARGETS ARE DISCOVERED, AND THE FIRST VERSION ONLY PRETENDED TO BE. It filtered
    # the discovered names through a hardcoded list — q_proj, k_proj, v_proj … — which
    # is a list for one architecture. On Qwen3.5 **not one of those names exists**:
    # its 24 linear-attention layers carry `in_proj_qkv`, `in_proj_z`, `out_proj`
    # (Mamba naming), and its full-attention layers carry a fused `qkv`. So the
    # adapter it produced touched only the MLPs and no attention at all, and the gate
    # that consumed it could not tell "vLLM ignores this" from "this adapter barely
    # moves the output" [ran] 2026-09-14.
    #
    # Every Linear is a candidate now, minus the two that are never adapted: the
    # output head and anything in a vision tower, which would make the comparison
    # about a modality this project does not use.
    SKIP = ("lm_head", "visual", "vision", "patch_embed", "merger")
    names = sorted({n.split(".")[-1] for n, m in model.named_modules()
                    if isinstance(m, torch.nn.Linear)
                    and not any(s in n for s in SKIP)})
    attn = [n for n in names if any(k in n for k in
                                    ("q", "k", "v", "o_proj", "qkv", "out_proj", "attn"))]
    print(f"[tiny] Linear modules: {names}", flush=True)
    print(f"[tiny] of those, attention-shaped: {attn}", flush=True)
    if not attn:
        # AN ADAPTER THAT TOUCHES NO ATTENTION IS THE CASE THAT WASTED THREE RUNS.
        print("[tiny] REFUSING: no attention module matched. An adapter that touches "
              "only MLPs cannot tell a serving gate what it is being asked.",
              flush=True)
        return 1
    print(f"[tiny] target modules found: {names}", flush=True)
    if not names:
        print("[tiny] no projection modules matched; nothing to adapt")
        return 1

    model = get_peft_model(model, LoraConfig(
        r=args.r, lora_alpha=args.alpha, lora_dropout=0.0, bias="none",
        task_type="CAUSAL_LM", target_modules=names))
    model.print_trainable_parameters()

    # THE CONTENT DOES NOT MATTER. It has to be text and it has to produce gradients.
    text = ["The adapter must change the output. " * 12] * (args.steps * 2)
    ds = Dataset.from_dict({"text": text}).map(
        lambda b: tok(b["text"], truncation=True, max_length=args.max_seq),
        batched=True, remove_columns=["text"])

    Trainer(
        model=model,
        args=TrainingArguments(output_dir="/tmp/tiny", per_device_train_batch_size=2,
                               max_steps=args.steps, learning_rate=args.lr,
                               logging_steps=20, report_to=[], bf16=True,
                               save_strategy="no"),
        train_dataset=ds,
        data_collator=DataCollatorForLanguageModeling(tok, mlm=False),
    ).train()

    out = Path(args.out)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    w = out / "adapter_model.safetensors"

    # A SAVED DIRECTORY IS NOT A TRAINED ADAPTER, and a trained adapter is not a
    # CHANGED OUTPUT. The gate that consumes this reported IDENTICAL TO BASE three
    # times, and the reading was ambiguous between "the class does not apply LoRA"
    # and "this adapter is a no-op" — because nothing here had checked the second
    # [ran] 2026-09-14. So it is checked, in-process, before the adapter is handed on.
    probe = "The adapter must change the output."
    ids = tok(probe, return_tensors="pt").to(model.device)
    with torch.no_grad():
        base_out = model.get_base_model().generate(
            **ids, max_new_tokens=24, do_sample=False,
            pad_token_id=tok.pad_token_id)
        with model.disable_adapter():
            pass
        lora_out = model.generate(**ids, max_new_tokens=24, do_sample=False,
                                  pad_token_id=tok.pad_token_id)
    same = torch.equal(base_out.cpu(), lora_out.cpu())
    delta = float(sum((p_.detach().float().abs().sum().item())
                      for n_, p_ in model.named_parameters() if "lora_B" in n_))

    print(json.dumps({
        "out": str(out), "weights_bytes": w.stat().st_size if w.exists() else 0,
        "target_modules": names,
        # lora_B starts at zero, so a nonzero sum is proof the optimiser moved it.
        "lora_B_abs_sum": round(delta, 4),
        "changes_output_in_process": not same,
    }, indent=2), flush=True)
    if same or delta == 0.0:
        print("[tiny] THIS ADAPTER IS A NO-OP IN PROCESS. Asking a serving gate "
              "about it would measure the adapter, not the server.", flush=True)
        return 1
    return 0 if w.exists() and w.stat().st_size > 100_000 else 1


if __name__ == "__main__":
    raise SystemExit(main())
