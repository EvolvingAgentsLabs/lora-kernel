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

    python3 -m training.s4_train --preflight        # two minutes, infrastructure only
    python3 -m training.s4_train                    # the four arms

WHY THE BASE IS A QWEN AND NOT A GEMMA. The project is multi-LoRA serving in
vLLM, so **a base vLLM cannot serve with adapters is disqualified however well it
trains**. Three independent facts, and the first one is ours:

  * `gemma-4-E4B-it` uses `Gemma4ClippableLinear`, which does not subclass
    `nn.Linear`, and peft refuses to wrap it. **[ran]** 2026-09-07.
  * vLLM's Gemma 4 LoRA support landed for the text-only `Gemma4ForCausalLM`
    (issue #39246, PR #39291). Every Gemma 4 variant this project would use is a
    `...ForConditionalGeneration` class, which was the second, unfinished phase.
    **[read]**
  * `gemma-4-26B-A4B-it` is a 128-expert MoE, where LoRA over fused expert
    tensors is the known-hard case in training and in serving alike, and it needs
    an A100 nobody has yet. **[read]**

And one fact about the qwens that changes the config rather than disqualifying
them: Unsloth advises against 4-bit QLoRA on Qwen3.5 — the quantisation error is
larger than usual — and recommends bf16 LoRA, which a 2B fits into on a free T4.
**[read]**
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


def precision():
    """The card decides, not the habit.

    A T4 is Turing (SM75) and has **no bf16**. Loading and generating in bf16
    appears to work — the baseline arm ran clean — and then the extra matmuls a
    LoRA adds hit a kernel with no bf16 engine and every generation dies with
    "GET was unable to find an engine to execute this computation". The arm
    reported 0/60 and it was not a result; it was the GPU. **[ran]** 2026-09-08.

    Returns (dtype, bf16_flag, fp16_flag) for the trainer.
    """
    import torch
    if not torch.cuda.is_available():
        return torch.float32, False, False
    # NOT `is_bf16_supported()`. On a T4 it returns True, because by default it
    # counts EMULATION — and emulated bf16 is exactly what has no kernel when a
    # LoRA adds its matmuls. The first fix for C15 was written with that call and
    # changed nothing; the run still reported `torch.bfloat16 on Tesla T4`
    # [ran] 2026-09-08. Compute capability 8.0 (Ampere) is where bf16 is real.
    major, _ = torch.cuda.get_device_capability()
    if major >= 8:
        return torch.bfloat16, True, False
    return torch.float16, False, True


def load_base(base: str, four_bit: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    dtype, _, _ = precision()
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=dtype, bnb_4bit_use_double_quant=True,
    ) if four_bit else None
    tok = AutoTokenizer.from_pretrained(base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base, quantization_config=bnb, dtype=dtype, device_map="auto")
    model.config.use_cache = True
    print(f"[precision] {dtype} on "
          f"{torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'}",
          flush=True)
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
    from peft import LoraConfig, get_peft_model
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
    # NOT `prepare_model_for_kbit_training`. That helper casts every parameter
    # the quantiser skipped up to fp32, and on this model that is most of it: it
    # asked for a 10.50 GiB single allocation on a 14.56 GiB card, twice, at two
    # different batch sizes — which is what gave it away, since the size never
    # moved [ran] 2026-09-07. Its two useful effects are reproduced directly.
    print(f"[mem] model footprint {model.get_memory_footprint() / 2**30:.2f} GiB", flush=True)
    quantised = sum(1 for m in model.modules() if "4bit" in type(m).__name__.lower())
    print(f"[mem] 4-bit modules: {quantised}", flush=True)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.config.use_cache = False
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
                       save_strategy="no", bf16=precision()[1], fp16=precision()[2],
                       # Packing would refill every sequence to max_length and
                       # put the token budget straight back.
                       packing=False,
                       gradient_checkpointing=True),
    ).train()
    peft_model.save_pretrained(out_dir)
    # Training turns gradient checkpointing on, which turns the KV cache off —
    # and the evaluation that follows is ninety generations long. Leaving it that
    # way makes the arm several times slower for no benefit, on a tier that
    # reclaims sessions [ran] 2026-09-08.
    peft_model.gradient_checkpointing_disable()
    peft_model.config.use_cache = True
    return peft_model, tok


def free() -> None:
    """Release the GPU. The caller must drop its own references FIRST.

    An earlier version took the objects as arguments and deleted them — which
    deletes the *callee's* names and nothing else, so every model stayed
    resident, the second `from_pretrained` found no room, and bitsandbytes
    refused to dispatch a quantised model onto the CPU. It cost the arm it
    crashed in [ran] 2026-09-07. Python has no way to free a caller's binding,
    so the caller sets its names to None and this only collects.
    """
    import torch
    gc.collect()
    torch.cuda.empty_cache()


def save(summary: dict) -> None:
    """Persisted after every arm: a run killed at the third adapter keeps the
    two it already paid for."""
    RESULTS.write_text(json.dumps(summary, indent=2))


class ArmBudget:
    """How many arms this process may complete before it stops.

    Free Colab reclaimed three sessions inside roughly forty minutes of GPU work
    each **[ran]**, so the run is chained instead: one arm per session, with the
    partial results uploaded at the start and pulled back at the end. The budget
    is what makes a session end on purpose rather than by being taken away.
    """

    def __init__(self, limit: int):
        self.limit, self.done = limit, 0

    def spent(self) -> bool:
        return bool(self.limit) and self.done >= self.limit

    def note(self, arm: str) -> None:
        self.done += 1
        print(f"[arm] {arm} complete ({self.done} of {self.limit or 'all'} "
              f"this session)", flush=True)


def run_all(args) -> dict:
    _seed(args.seed)
    budget = ArmBudget(args.max_arms)
    train = load_jsonl("training/data/train.jsonl")
    val = load_jsonl("training/data/val.jsonl")[:args.n_val]
    delta = load_jsonl("training/data/val_delta.jsonl")[:args.n_delta]
    summary = {"base": args.base, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "lora": {"r": args.r, "alpha": args.alpha, "epochs": args.epochs,
                        "lr": args.lr, "train_n": len(train)},
               "n": {"val": len(val), "delta": len(delta)}}
    # RESUME. Arms already on disk under the same configuration are kept: a run
    # killed in its third arm should not re-buy the first two. The config has to
    # match, or the arms are not comparable and reusing them would silently mix
    # two experiments.
    if RESULTS.exists():
        prev = json.loads(RESULTS.read_text())
        if (prev.get("base") == summary["base"] and prev.get("n") == summary["n"]
                and prev.get("lora") == summary["lora"]):
            # AN ARM WHERE EVERY ANSWER WAS UNUSABLE IS NOT A COMPLETED ARM.
            # A T4 without bf16 produced 0/60 with all sixty unparseable, and a
            # resume that trusted it would skip the arm and carry a measured zero
            # forward — which reads as "specialisation did not happen", one of
            # this step's two falsification conditions. [ran] 2026-09-08
            voided = [k for k, v in prev.items()
                      if isinstance(v, dict) and v.get("n")
                      and v.get("unparseable") == v.get("n")]
            for k in voided:
                del prev[k]
            if voided:
                print(f"[resume] voiding arms with no usable answer at all: "
                      f"{voided}", flush=True)
            summary = {**prev, **{k: v for k, v in summary.items()
                                  if k not in prev}}
            print(f"[resume] keeping arms already on disk: "
                  f"{[k for k in prev if k.endswith(('_val', '_delta')) or k == 'regions']}",
                  flush=True)
    save(summary)

    # -- the baseline, recorded before the treatment exists ---------------------
    if ("base_val" not in summary or "base_delta" not in summary) and not budget.spent():
        model, tok = load_base(args.base, args.four_bit)
        gen = make_generate(model, tok, args.max_new_tokens)
        summary["base_val"] = evaluate(gen, val, "base")
        summary["base_delta"] = evaluate(gen, delta, "base · delta")
        save(summary)
        budget.note("base")
        gen = model = tok = None
        free()

    # -- question 1: does specialisation happen at all? -------------------------
    if "adapter_val" not in summary and not budget.spent():
        expert, tok = train_adapter(args.base, train, "adapters/all-clinics", args)
        gen = make_generate(expert, tok, args.max_new_tokens)
        summary["adapter_val"] = evaluate(gen, val, "adapter")
        summary["adapter_delta"] = evaluate(gen, delta, "adapter · delta")
        save(summary)
        budget.note("adapter")
        gen = expert = tok = None
        free()

    # -- question 2: do experts differ by region? ------------------------------
    regions = summary.get("regions") or {}
    val_a = [r for r in val if r["clinic"] == "alpha"][:args.n_region]
    val_b = [r for r in val if r["clinic"] == "beta"][:args.n_region]
    for clinic, own, other in (("alpha", val_a, val_b), ("beta", val_b, val_a)):
        if f"{clinic}_on_own" in regions or budget.spent():
            continue
        rows = [r for r in train if r["clinic"] == clinic]
        exp, tk = train_adapter(args.base, rows, f"adapters/{clinic}", args)
        g = make_generate(exp, tk, args.max_new_tokens)
        regions[f"{clinic}_on_own"] = evaluate(g, own, f"{clinic} on own")
        regions[f"{clinic}_on_other"] = evaluate(g, other, f"{clinic} on other")
        summary["regions"] = regions
        save(summary)
        budget.note(f"region:{clinic}")
        g = exp = tk = None
        free()

    complete = ("adapter_val" in summary
                and len(summary.get("regions") or {}) >= 4)
    summary["finished" if complete else "paused"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save(summary)
    print(f"[arm] session done — {'ALL ARMS COMPLETE' if complete else 'more arms remain'}",
          flush=True)
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


def preflight(args) -> int:
    """Can this base be trained at all, on this card — answered in two minutes.

    Four attempts at S4 died in infrastructure rather than in the experiment: a
    parser crash, a memory leak, an fp32 upcast, and finally a base whose custom
    linear class peft cannot wrap. Each cost an hour of GPU and none of them
    needed the full run to be discovered. This loads the base, reports what
    actually got quantised, attaches the adapter, and takes ONE optimiser step.

    It answers the infrastructure question and nothing else. It is not an arm and
    its numbers are not results.
    """
    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from trl import SFTConfig, SFTTrainer

    model, tok = load_base(args.base, args.four_bit)
    print(f"[preflight] footprint {model.get_memory_footprint() / 2**30:.2f} GiB", flush=True)
    kinds: dict[str, int] = {}
    for name, mod in model.named_modules():
        if name.split(".")[-1] in set(args.targets.split(",")) | {"q_proj", "k_proj"}:
            kinds[type(mod).__name__] = kinds.get(type(mod).__name__, 0) + 1
    print(f"[preflight] projection classes: {kinds}", flush=True)

    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.config.use_cache = False
    try:
        peft_model = get_peft_model(model, LoraConfig(
            r=args.r, lora_alpha=args.alpha, lora_dropout=0.05, bias="none",
            task_type="CAUSAL_LM",
            target_modules=args.targets.split(",")))
    except ValueError as e:
        print(f"[preflight] FAIL — peft cannot wrap this architecture: "
              f"{str(e)[:160]}", flush=True)
        return 2
    peft_model.print_trainable_parameters()

    rows = load_jsonl("training/data/train.jsonl")[:4]
    texts = [{"text": tok.apply_chat_template(r["messages"], tokenize=False)}
             for r in rows]
    try:
        SFTTrainer(model=peft_model, train_dataset=Dataset.from_list(texts),
                   args=SFTConfig(output_dir="/tmp/preflight", max_steps=1,
                                  per_device_train_batch_size=args.batch,
                                  gradient_accumulation_steps=1,
                                  learning_rate=args.lr, max_length=args.max_seq,
                                  logging_steps=1, report_to=[], save_strategy="no",
                                  bf16=precision()[1], fp16=precision()[2], packing=False,
                                  gradient_checkpointing=True)).train()
    except torch.OutOfMemoryError as e:
        print(f"[preflight] FAIL — one step does not fit: {str(e)[:160]}", flush=True)
        return 3
    peak = torch.cuda.max_memory_allocated() / 2**30
    print(f"[preflight] PASS — one optimiser step done, peak {peak:.2f} GiB of "
          f"{torch.cuda.get_device_properties(0).total_memory / 2**30:.2f} GiB",
          flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--n-val", type=int, default=120)
    ap.add_argument("--n-delta", type=int, default=60)
    ap.add_argument("--n-region", type=int, default=40)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    # THE LOGITS ARE THE BILL. Gemma's vocabulary is ~262k, so one step costs
    # batch x sequence x 262144 x 4 bytes before anything else — 4x4 at 1024
    # asked a 15 GB T4 for 10.5 GiB in a single allocation and it refused [ran]
    # 2026-09-07. Effective batch stays 16; the per-step token budget drops 8x.
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--accum", type=int, default=16)
    ap.add_argument("--max-seq", type=int, default=512,
                    help="the canonical prompt is ~250 tokens and the answer ~25, "
                         "so 512 truncates nothing and halves the logits again")
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    # NOT q_proj/k_proj on a qwen3: QK-norm makes the adapted tensors
    # shape-incompatible and the kernel errors out. [read]
    ap.add_argument("--targets", default="v_proj,o_proj,gate_proj,up_proj,down_proj")
    ap.add_argument("--max-arms", type=int, default=0,
                    help="stop after this many arms complete in this process; 0 "
                         "runs them all. 1 is how a chained run survives a tier "
                         "that reclaims sessions")
    ap.add_argument("--preflight", action="store_true",
                    help="answer the infrastructure question in two minutes "
                         "instead of discovering it an hour into an arm")
    # bf16 by default, against the usual QLoRA habit: Unsloth reports larger than
    # normal quantisation error on Qwen3.5 either way, and a 2B in bf16 fits a
    # free T4 with room for the adapter. `--four-bit` is there for the 4B and up.
    ap.add_argument("--four-bit", dest="four_bit", action="store_true",
                    help="quantise the base to 4-bit NF4 (needed above ~4B on a T4)")
    args = ap.parse_args()
    if args.preflight:
        return preflight(args)
    summary = run_all(args)
    if "adapter_val" in summary:
        print(verdict(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
