r"""Gemma 4 12B on a Mac with MLX: one base in memory, LoRA experts swapped per request with no reload, and speculative
decoding with Gemma 4's own MTP drafter — the Mac half of the user's brief of 2026-09-27. INFERENCE ON THE USER'S MACHINE,
by the user's explicit exception to the Colab-only rule (2026-09-27); nothing is trained here.

    python -m examples.mac.mlx_spec_lora --adapter wiki12b=<dir of a PEFT adapter> --out results/<run>/mac.json

WHAT IT BUILDS, AND WHY NOT mlx-lm's SERVER. `mlx_lm.server` reloads the whole model when a request names another
adapter (`ModelProvider._load` resets and calls `load(model, adapter_path)`), and mlx-lm cannot load the 12B
(`gemma4_unified`) nor its MTP drafter; mlx-vlm can do both. So: the base is loaded once (mlx-vlm, 4-bit); every
targeted projection is wrapped in `HotLoRA`, which holds the A, B of EVERY adapter and adds
$y = W x + s\,B(Ax)$, $s = \alpha / r$, for the ACTIVE one only — switching experts is a pointer, not a load. A PEFT
adapter trained here on the bf16 12B maps onto the MLX modules by name (`base_model.model.model.language_model.X` →
`language_model.model.X`), A `(r, in)` and B `(out, r)` as PEFT stores them; it is applied over 4-bit weights, so
whether it still acts is measured (G1 analogue: expert text ≠ base text on the expert's prompts).

WHAT IT MEASURES, per (expert ∈ {base, each adapter}) × (spec ∈ {off, mtp}) on the expert's prompts and general ones,
greedy: generation tokens/s (mlx-vlm's own `generation_tps`), the drafter's accepted length per round, the text — and
the brief's mandatory test: with the same expert, spec on and off must produce the SAME text at temperature 0. Then the
swap: time to switch the active expert, and that base → expert → base returns the base's exact text.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn

BASE = "mlx-community/gemma-4-12B-it-4bit"
DRAFTER = "google/gemma-4-12B-it-assistant"
GENERAL = ["Explain in a short paragraph how a refrigerator keeps food cold.",
           "Write a polite email asking a colleague to move a meeting to Thursday.",
           "Summarise the water cycle for a ten-year-old.",
           "Why do leaves change colour in autumn?"]


class HotLoRA(nn.Module):
    """A projection with any number of LoRA adapters attached and exactly one (or none) active."""
    active: str | None = None                                   # class-wide: one switch for the whole model

    def __init__(self, base: nn.Module):
        super().__init__()
        self.base = base
        self._ab: dict[str, tuple[mx.array, mx.array, float]] = {}

    def add(self, name: str, a: mx.array, b: mx.array, scale: float) -> None:
        self._ab[name] = (a, b, scale)

    def __call__(self, x):
        y = self.base(x)
        ab = self._ab.get(HotLoRA.active) if HotLoRA.active else None
        if ab is None:
            return y
        a, b, s = ab
        return y + (s * ((x @ a.T) @ b.T)).astype(y.dtype)


def _resolve(root, path: str):
    obj = root
    for part in path.split("."):
        obj = obj[int(part)] if part.isdigit() else getattr(obj, part)
    return obj


def _set(root, path: str, value) -> None:
    parent, _, leaf = path.rpartition(".")
    obj = _resolve(root, parent) if parent else root
    if leaf.isdigit():
        obj[int(leaf)] = value
    else:
        setattr(obj, leaf, value)


def mlx_path(peft_module: str) -> str:
    """`base_model.model.model.language_model.layers.0.mlp.down_proj` → `language_model.model.layers.0.mlp.down_proj`."""
    rest = peft_module.removeprefix("base_model.model.model.")
    assert rest.startswith("language_model."), peft_module
    return "language_model.model." + rest.removeprefix("language_model.")


def attach(model, name: str, adapter_dir: str) -> int:
    """Attach one PEFT adapter under `name`; returns the number of projections it reaches (must be all of its pairs)."""
    from safetensors.numpy import load_file
    cfg = json.loads(Path(adapter_dir, "adapter_config.json").read_text())
    scale = cfg["lora_alpha"] / cfg["r"]
    t = load_file(str(Path(adapter_dir, "adapter_model.safetensors")))
    mods = sorted({k.rsplit(".lora_", 1)[0] for k in t})
    for m in mods:
        path = mlx_path(m)
        cur = _resolve(model, path)
        if not isinstance(cur, HotLoRA):
            cur = HotLoRA(cur)
            _set(model, path, cur)
        cur.add(name, mx.array(t[f"{m}.lora_A.weight"]).astype(mx.bfloat16), mx.array(t[f"{m}.lora_B.weight"]).astype(mx.bfloat16), scale)
    return len(mods)


def main() -> int:
    from mlx_vlm import load
    from mlx_vlm.generate import generate
    from mlx_vlm.speculative.drafters import load_drafter
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--drafter", default=DRAFTER)
    ap.add_argument("--adapter", action="append", default=[], help="name=dir of a PEFT adapter (repeatable)")
    ap.add_argument("--sets", default="domain,general", help="OMLX0: which prompt sets to run")
    ap.add_argument("--domain", type=int, default=6, help="how many of the wiki expert's own prompts")
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--block-sizes", default="", help="MLXK0: MTP block sizes to sweep (draft tokens = block - 1); empty = the drafter's default")
    ap.add_argument("--out", default="mac.json")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec: dict = {"base": a.base, "drafter": a.drafter, "max_tokens": a.max_tokens, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    t0 = time.time()
    model, processor = load(a.base)
    rec["load_base_s"] = round(time.time() - t0, 1)
    experts = [None]
    rec["adapters"] = {}
    for spec in a.adapter:
        name, _, d = spec.partition("=")
        t1 = time.time()
        rec["adapters"][name] = {"dir": d, "projections": attach(model, name, d), "attach_s": round(time.time() - t1, 2)}
        experts.append(name)
    t1 = time.time()
    draft, kind = load_drafter(a.drafter)
    rec["drafter_kind"], rec["load_drafter_s"] = kind, round(time.time() - t1, 1)
    print(f"[mac] base {rec['load_base_s']} s · drafter {kind} {rec['load_drafter_s']} s · adapters {rec['adapters']}", flush=True)
    save()

    from memory import prompt
    from training.wiki import wiki_arm as wa
    tok = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    render = lambda msgs: tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    rows = wa.load_rows("eval")[:a.domain // 2] + wa.load_rows("eval_hard")[:a.domain - a.domain // 2]
    sets = {"domain": [render([{"role": "system", "content": prompt.SYSTEM_WIKI},
                               {"role": "user", "content": prompt.user_text_wiki(r["question"])}]) for r in rows],
            "general": [render([{"role": "user", "content": g}]) for g in GENERAL]}

    def run(expert, spec_on, p: str) -> dict:
        HotLoRA.active = expert
        kw = {"max_tokens": a.max_tokens, "temperature": 0.0, "verbose": False}
        if spec_on:
            kw.update(draft_model=draft, draft_kind=kind)
            if spec_on is not True:                          # a block size (MLXK0)
                kw["draft_block_size"] = int(spec_on)
        from mlx_vlm.speculative.common import speculative_stats_since, speculative_stats_snapshot
        snap = speculative_stats_snapshot(draft) if spec_on else None
        r = generate(model, processor, p, **kw)
        res = {"text": r.text, "tokens": r.generation_tokens, "tps": round(r.generation_tps, 2)}
        if spec_on:
            # MLXK0: mlx-vlm's lifetime counters, diffed per request — exact at batch size 1
            res["n_rounds"], res["n_accepted"], res["n_drafted"] = speculative_stats_since(draft, snap)
            # mlx-vlm RESETS the drafter's counters at each generation: read them whole, after it. The first runner
            # sliced them as if cumulative and read only the first prompt [ran] results/MAC-mlx-12b-lora-mtp-20260927.
            acc = list(getattr(draft, "accept_lens", []) or [])
            res["rounds"], res["mean_accepted_per_round"] = len(acc), round(sum(acc) / len(acc), 3) if acc else None
        return res

    rec["runs"] = {}
    for expert in experts:
        for sname, prompts in [(k, v) for k, v in sets.items() if k in a.sets.split(",")]:
            blocks = [int(b) for b in a.block_sizes.split(",") if b] or [True]
            for spec_on in (False, *blocks):
                key = f"{expert or 'base'}/{sname}/{'off' if spec_on is False else ('mtp' if spec_on is True else f'mtp_b{spec_on}')}"
                rs = [run(expert, spec_on, p) for p in prompts]
                rec["runs"][key] = rs
                tps = sum(x["tokens"] for x in rs) / max(1e-9, sum(x["tokens"] / x["tps"] for x in rs if x["tps"]))
                print(f"[mac] {key}: {tps:.1f} tok/s" + (f" · accepted/round {sum(x['mean_accepted_per_round'] or 0 for x in rs) / len(rs):.2f}"
                                                         if spec_on else ""), flush=True)
                save()

    # the swap, timed, and whether it is clean: base → expert → base returns the base's exact text
    swaps = []
    if len(experts) > 1:
        probe = sets["domain"][0]
        for expert in experts[1:]:
            t1 = time.perf_counter(); HotLoRA.active = expert; swap_us = (time.perf_counter() - t1) * 1e6
            e_text = run(expert, False, probe)["text"]
            HotLoRA.active = None
            b_text = run(None, False, probe)["text"]
            swaps.append({"expert": expert, "swap_us": round(swap_us, 2), "expert_differs_from_base": e_text != b_text,
                          "base_text_restored": b_text == rec["runs"]["base/domain/off"][0]["text"]})
    rec["swaps"] = swaps
    rec["summary"] = summarise(rec)
    rec["peak_memory_gb"] = round(mx.get_peak_memory() / 1e9, 2) if hasattr(mx, "get_peak_memory") else None
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[mac] {json.dumps(rec['summary'])}", flush=True)
    return 0


def summarise(rec: dict) -> dict:
    """Per expert and set: tokens/s off vs mtp, speed-up, identical texts, accepted per round; G1 analogue per adapter."""
    out = {}
    runs = rec["runs"]
    for key in runs:
        if not key.endswith("/off"):
            continue
        stem = key[:-4]
        off = runs[key]
        tps = lambda rs: sum(x["tokens"] for x in rs) / max(1e-9, sum(x["tokens"] / x["tps"] for x in rs if x["tps"]))
        out[stem] = {"tps_off": round(tps(off), 2)}
        for k2 in runs:
            if not k2.startswith(stem + "/mtp"):
                continue
            on, spec = runs[k2], k2[len(stem) + 1:]
            out[f"{stem}/{spec}"] = {"tps": round(tps(on), 2), "speedup": round(tps(on) / tps(off), 2),
                                     "identical": f"{sum(a['text'] == b['text'] for a, b in zip(off, on))}/{len(off)}",
                                     "accepted_per_round": round(sum(x.get("mean_accepted_per_round") or 0 for x in on) / len(on), 3),
                                     "rounds": sum(x.get("n_rounds") or 0 for x in on),
                                     "acceptance": round(sum(x.get("n_accepted") or 0 for x in on) / max(1, sum(x.get("n_drafted") or 0 for x in on)), 3)}
    for name in rec.get("adapters", {}):
        e, b = runs.get(f"{name}/domain/off", []), runs.get("base/domain/off", [])
        out[f"G1:{name}"] = f"{sum(x['text'] != y['text'] for x, y in zip(e, b))}/{len(b)} domain texts differ from the base"
    return out


if __name__ == "__main__":
    raise SystemExit(main())
