"""H1a — does the DOMAIN concentrate the routing of `google/gemma-4-26B-A4B-it`? Nothing trained.

The spec is `docs/flash-inference/00-analysis.md` §5; the brief is `results/H1A-moe-routing-by-domain-20261004/BRIEF.md`.
One forward hook per layer on Gemma 4's router (`transformers.models.gemma4.modeling_gemma4.Gemma4TextRouter`) records
the K expert ids **the router itself selected** — the third element of its output, `top_k_index` from its own
`torch.topk(router_probabilities, k=top_k_experts)` — for every token of the prefill and of `--decode-tokens` greedy
decode steps, per prompt, ~30 prompts per domain plus ~30 general ones. Each prompt's trace is written as it lands
(`{traces_dir}/{domain}/{prompt_id}.npz`: `expert_ids` uint8 [T, L, K], `token_idx` int32 [T], `phase` uint8 [T],
0 prefill / 1 decode — the layer is axis 1), the results file after every prompt, and the traces are packed into
`adapters_out.tgz` every `--pack-every` prompts so the chain brings them home while the session lives. At the end,
`h1a_metrics.analyse` runs on the traces and the gate is written into the results file.

**Why the experts are quantized here and not by bitsandbytes [read].** `BitsAndBytesConfig(load_in_4bit=True)`
replaces `nn.Linear` modules only (`transformers/integrations/bitsandbytes.py`, `replace_with_bnb_linear`); Gemma 4
stores each layer's 128 experts as two 3-D `nn.Parameter`s (`Gemma4TextExperts.gate_up_proj [E, 2I, H]`,
`down_proj [E, H, I]`), which it leaves in bf16 — $128 \\times 30 \\times 5.95$ M $\\times 2$ B ≈ 45.7 GB, more than an
A100-40 holds. So the model is loaded in bf16 on the host, and each layer's experts are quantized to 4 bits on the card
(symmetric int4, one scale per group of 64 along the input dimension — $0.5 + 2/64 \\approx 0.53$ bytes per parameter,
the spec's "4 bits plus scales per group of 64") and dequantized per selected expert on use. Everything else stays bf16.
Routing is read from the router, upstream of the experts; quantization moves it only through the hidden states, as the
deployed 4-bit model's would be moved.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.flash_inference import h1a_metrics as M  # noqa: E402

# The 26B opens its thought channel with thinking off; an empty channel, prefilled, closes it — the template's own
# markers, as `training/wiki/wiki_arm.py` EMPTY_THOUGHT does (PAIR0 attempt 1 [ran]).
EMPTY_THOUGHT = "<|channel>thought\n<channel|>"
ROUTER_CLASSES = ("Gemma4TextRouter",)
GROUP = 64
DOMAINS = ("wiki", "school", "distributor", "email")

# ------------------------------------------------------------------ prompts
GENERAL = [
    "Give me a simple recipe for a weeknight vegetable curry.",
    "Explain in plain words why the sky is blue.",
    "Write a short poem about the sea in winter.",
    "What were the main causes of the First World War?",
    "How do I reverse a linked list in Python? Show the code.",
    "Summarise the plot of Don Quixote in a paragraph.",
    "What is the difference between a virus and a bacterium?",
    "Plan a three-day trip to Lisbon for someone who likes museums.",
    "Explain what a derivative is to a high-school student.",
    "¿Cuáles son los beneficios de caminar todos los días?",
    "Write a polite email declining a meeting invitation.",
    "How does a refrigerator keep food cold?",
    "Recommend five classic science-fiction novels and say why.",
    "What is the Pythagorean theorem, with an example?",
    "Tell me a short bedtime story about a fox and an owl.",
    "How do I make my sourdough starter more active?",
    "Explain how vaccines train the immune system.",
    "What should I consider when buying a used bicycle?",
    "Translate into French: 'The library opens at nine and closes at six.'",
    "Write a SQL query that returns the ten most recent orders per customer.",
    "Why do cats purr?",
    "Describe the water cycle step by step.",
    "Explica la diferencia entre el clima y el tiempo atmosférico.",
    "What are good habits for getting better sleep?",
    "Compose a haiku about autumn leaves.",
    "How did the printing press change Europe?",
    "Give me tips for a first job interview.",
    "What is inflation and why do central banks raise interest rates?",
    "Write a limerick about a forgetful robot.",
    "How do plants make their food?",
]


def _spread(rows: list, n: int) -> list:
    """`n` rows evenly spaced over the file — every family of a generated corpus, not its first block."""
    return [rows[min(len(rows) - 1, round(i * len(rows) / n))] for i in range(n)] if len(rows) > n else list(rows)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _served(messages: list[dict]) -> list[dict]:
    """The request as the member is served it: every message before the first assistant turn (system + user)."""
    out = []
    for m in messages:
        if m["role"] == "assistant":
            break
        out.append({"role": m["role"], "content": m["content"]})
    return out


SOURCES = {
    # W9's distributor-wiki walks (the corpus `distributor-wiki@v2` was trained on): system + question + tool block
    "wiki": "training/wiki/data/train.jsonl",
    # the school and distributor staff turns, held-out eval rows (system + request + tool block)
    "school": "examples/school/data_turns/eval.jsonl",
    "distributor": "examples/distributor/data_turns/eval.jsonl",
    # email triage (email-full's corpus)
    "email": "training/harness/data_ef/train.jsonl",
}


def build_prompts(per_domain: int = 30, root: Path = ROOT) -> list[dict]:
    """~`per_domain` prompts per domain from corpora already in the repository, plus the general ones. Each id is
    `{domain}-{nn}`; even nn → half A (affinity), odd → half B (evaluated) — `h1a_metrics.half_of`."""
    out = []
    for d in DOMAINS:
        rows = _spread(_jsonl(root / SOURCES[d]), per_domain)
        for i, r in enumerate(rows):
            pid = f"{d}-{i:02d}"
            out.append({"id": pid, "domain": d, "half": M.half_of(pid), "source": r.get("case_id"),
                        "messages": _served(r["messages"])})
    for i, text in enumerate(GENERAL[:per_domain]):
        pid = f"general-{i:02d}"
        out.append({"id": pid, "domain": "general", "half": M.half_of(pid), "source": None,
                    "messages": [{"role": "user", "content": text}]})
    return out


def render(tok, messages: list[dict]) -> str:
    """Thinking off, and the thought channel closed with an empty one (see EMPTY_THOUGHT)."""
    return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                   enable_thinking=False) + EMPTY_THOUGHT


# ------------------------------------------------------------------ 4-bit experts
def quantize4(w):
    """[..., n] float → (packed uint8 [..., n/2], scales [..., n/64]): symmetric int4 per group of 64, q ∈ [-8, 7]."""
    import torch
    shape = w.shape
    g = w.float().reshape(*shape[:-1], shape[-1] // GROUP, GROUP)
    scale = (g.abs().amax(-1) / 7.0).clamp_min(1e-12)
    q = (torch.round(g / scale[..., None]).clamp(-8, 7) + 8).to(torch.uint8).reshape(shape)
    packed = q[..., 0::2] | (q[..., 1::2] << 4)
    return packed, scale.to(w.dtype)


def dequantize4(packed, scale, dtype):
    import torch
    q = torch.stack((packed & 15, packed >> 4), dim=-1).reshape(*packed.shape[:-1], packed.shape[-1] * 2)
    n = q.shape[-1]
    g = (q.reshape(*q.shape[:-1], n // GROUP, GROUP).to(dtype) - 8) * scale[..., None].to(dtype)
    return g.reshape(*q.shape)


def _quant_experts_class():
    import torch
    from torch import nn

    class QuantExperts(nn.Module):
        """Gemma4TextExperts with its two 3-D weights held in 4 bits; the forward is the eager loop of
        `Gemma4TextExperts.forward`, dequantizing only the experts the router hit."""

        def __init__(self, experts, device, chunk: int = 16):
            super().__init__()
            self.num_experts = experts.num_experts
            self.act_fn = experts.act_fn
            self.dtype = experts.gate_up_proj.dtype
            for name in ("gate_up_proj", "down_proj"):
                w = getattr(experts, name).data
                ps, ss = [], []
                for i in range(0, w.shape[0], chunk):
                    p, s = quantize4(w[i:i + chunk].to(device))
                    ps.append(p)
                    ss.append(s)
                self.register_buffer(f"{name}_q", torch.cat(ps))
                self.register_buffer(f"{name}_s", torch.cat(ss))

        def weight(self, name: str, e):
            return dequantize4(getattr(self, f"{name}_q")[e], getattr(self, f"{name}_s")[e], self.dtype)

        def forward(self, hidden_states, top_k_index, top_k_weights):
            final = torch.zeros_like(hidden_states)
            with torch.no_grad():
                mask = torch.nn.functional.one_hot(top_k_index, num_classes=self.num_experts).permute(2, 1, 0)
                hit = torch.greater(mask.sum(dim=(-1, -2)), 0).nonzero()
            for e in hit:
                e = e[0]
                if e == self.num_experts:
                    continue
                pos, tok = torch.where(mask[e])
                x = hidden_states[tok]
                gate, up = nn.functional.linear(x, self.weight("gate_up_proj", e)).chunk(2, dim=-1)
                y = nn.functional.linear(self.act_fn(gate) * up, self.weight("down_proj", e))
                y = y * top_k_weights[tok, pos, None]
                final.index_add_(0, tok, y.to(final.dtype))
            return final

    return QuantExperts


def quantize_experts(model, device) -> int:
    """Replace every layer's `Gemma4TextExperts` by its 4-bit version on `device`; returns how many were replaced."""
    QuantExperts = _quant_experts_class()
    n = 0
    for name, mod in list(model.named_modules()):
        if type(mod).__name__ == "Gemma4TextDecoderLayer" and getattr(mod, "enable_moe_block", False):
            old = mod.experts
            mod.experts = QuantExperts(old, device)
            del old
            n += 1
    return n


# ------------------------------------------------------------------ the hook
def find_routers(model) -> list[tuple[int, object]]:
    """(layer index, router module) for every Gemma 4 MoE router, by class — the layer read from the module path."""
    out = []
    for name, mod in model.named_modules():
        if type(mod).__name__ in ROUTER_CLASSES:
            m = re.search(r"layers\.(\d+)\.", name + ".")
            out.append((int(m.group(1)), mod))
    return sorted(out, key=lambda x: x[0])


class RouterRecorder:
    """Records, per forward call and per layer, the `top_k_index` the router returned ([tokens, K])."""

    def __init__(self, model):
        self.routers = find_routers(model)
        if not self.routers:
            raise RuntimeError("no MoE router found — is this Gemma 4 26B-A4B?")
        self.layers = [i for i, _ in self.routers]
        self.calls: dict[int, list] = {}
        self.handles = [mod.register_forward_hook(self._hook(i)) for i, mod in self.routers]

    def _hook(self, layer: int):
        def hook(_mod, _inp, out):
            # Gemma4TextRouter.forward returns (router_probabilities, top_k_weights, top_k_index)
            self.calls.setdefault(layer, []).append(out[2].detach().to("cpu"))
        return hook

    def reset(self) -> None:
        self.calls = {}

    def remove(self) -> None:
        for h in self.handles:
            h.remove()

    def collect(self, prompt_len: int):
        """→ (expert_ids uint8 [T, L, K], token_idx int32 [T], phase uint8 [T]). Call 0 is the prefill (one row per
        prompt token); every later call is one decode step. Every layer must have seen the same calls."""
        import numpy as np
        import torch
        per = [self.calls.get(i, []) for i in self.layers]
        n_calls = {len(c) for c in per}
        if len(n_calls) != 1 or not per[0]:
            raise RuntimeError(f"layers saw different numbers of router calls: {sorted(n_calls)}")
        rows = [torch.cat(c, 0) for c in per]                     # each [T, K]
        if len({r.shape for r in rows}) != 1:
            raise RuntimeError("layers saw different token counts")
        ids = torch.stack(rows, 1).numpy()                        # [T, L, K]
        n_pre = per[0][0].shape[0]
        if n_pre != prompt_len:
            raise RuntimeError(f"prefill call saw {n_pre} tokens, the prompt has {prompt_len}")
        T = ids.shape[0]
        phase = np.zeros(T, dtype=np.uint8)
        phase[n_pre:] = 1
        if ids.max() > 255:
            raise RuntimeError("expert id above 255 does not fit uint8")
        return ids.astype(np.uint8), np.arange(T, dtype=np.int32), phase


def trace_prompt(model, tok, rec: RouterRecorder, messages: list[dict], decode_tokens: int) -> dict:
    """Prefill + `decode_tokens` greedy decode steps (max_new_tokens = decode_tokens + 1: the last token generated is
    never fed back, so that many forwards follow the prefill unless the model stops first)."""
    import torch
    text = render(tok, messages)
    enc = tok(text, return_tensors="pt", add_special_tokens=False).to(model.device)
    P = enc["input_ids"].shape[1]
    rec.reset()
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=decode_tokens + 1, do_sample=False,
                             pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
    ids, token_idx, phase = rec.collect(P)
    gen = out[0][P:]
    return {"expert_ids": ids, "token_idx": token_idx, "phase": phase, "prompt_tokens": P,
            "generated_tokens": int(gen.shape[0]), "text": tok.decode(gen, skip_special_tokens=False)}


def save_trace(path: Path, t: dict) -> None:
    import numpy as np
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, expert_ids=t["expert_ids"], token_idx=t["token_idx"], phase=t["phase"])
    tmp.replace(path)


def pack(traces_dir: Path, out: Path = Path("adapters_out.tgz")) -> None:
    """The traces travel home through the chain's weights channel (`adapters_out.tgz`, fetched when `packed` grows)."""
    tmp = out.with_suffix(".tmp")
    with tarfile.open(tmp, "w:gz") as tf:
        tf.add(traces_dir, arcname=traces_dir.name)
    tmp.replace(out)


# ------------------------------------------------------------------ the run
def load_model(base: str, quant: str):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    print(f"[h1a] loading {base} on the host ({dtype}), transformers {transformers.__version__}", flush=True)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, dtype=dtype)
    model.eval()
    print(f"[h1a] loaded in {time.time() - t0:.0f}s ({type(model).__name__})", flush=True)
    if quant == "int4":
        t0 = time.time()
        n = quantize_experts(model, dev)
        print(f"[h1a] quantized the experts of {n} layers to 4 bits in {time.time() - t0:.0f}s", flush=True)
    model.to(dev)
    if dev == "cuda":
        print(f"[h1a] on {torch.cuda.get_device_name(0)}: {torch.cuda.memory_allocated() / 2**30:.1f} GiB allocated",
              flush=True)
    return model, tok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="google/gemma-4-26B-A4B-it")
    ap.add_argument("--out", default="h1a.json")
    ap.add_argument("--traces-dir", default="h1a_traces")
    ap.add_argument("--decode-tokens", type=int, default=128)
    ap.add_argument("--per-domain", type=int, default=30)
    ap.add_argument("--limit", type=int, default=None, help="smoke runs only: trace the first N prompts")
    ap.add_argument("--quant", choices=("int4", "none"), default="int4")
    ap.add_argument("--pack-every", type=int, default=10)
    ap.add_argument("--dry", action="store_true", help="build and count the prompts, load nothing")
    a = ap.parse_args(argv)

    prompts = build_prompts(a.per_domain)
    if a.limit:
        prompts = prompts[:a.limit]
    counts = {}
    for p in prompts:
        counts.setdefault(p["domain"], {"A": 0, "B": 0})[p["half"]] += 1
    print(f"[h1a] {len(prompts)} prompts: {counts}", flush=True)
    if a.dry:
        return 0

    out, tdir = Path(a.out), Path(a.traces_dir)
    res = json.loads(out.read_text()) if out.exists() else {}
    res.update(base=a.base, decode_tokens=a.decode_tokens, quant=a.quant, per_domain=a.per_domain,
               prompt_counts=counts, sources=SOURCES)
    res.setdefault("prompts", {})
    res.pop("finished", None)

    def save():
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(res, indent=1))
        tmp.replace(out)

    def trace_path(p):
        return tdir / p["domain"] / f"{p['id']}.npz"

    todo = [p for p in prompts
            if not (res["prompts"].get(p["id"], {}).get("ok") and trace_path(p).exists())]
    print(f"[h1a] resume: {len(prompts) - len(todo)} done, {len(todo)} to trace", flush=True)
    # A NEW SESSION REPACKS WHAT IT WAS CARRIED IN, AT ONCE: the chain fetches adapters_out.tgz as soon as `packed`
    # exceeds what it has fetched this session (0), so the VM must already hold a complete pack — never a missing one.
    if tdir.exists() and any(tdir.glob("*/*.npz")):
        pack(tdir)
    save()
    if todo:
        model, tok = load_model(a.base, a.quant)
        rec = RouterRecorder(model)
        cfg = model.config.get_text_config()
        L, K = cfg.num_hidden_layers, cfg.top_k_experts
        if len(rec.routers) != L:
            print(f"[h1a] STOPPED: {len(rec.routers)} routers hooked, the config has {L} layers", flush=True)
            res["error"] = "router count"
            save()
            return 2
        res.update(n_layers=L, top_k=K, n_experts=cfg.num_experts, router_class=ROUTER_CLASSES[0])
        print(f"[h1a] hooked {L} routers ({ROUTER_CLASSES[0]}), top-{K} of {cfg.num_experts}", flush=True)
        since_pack = 0
        for n, p in enumerate(todo, 1):
            t0 = time.time()
            try:
                t = trace_prompt(model, tok, rec, p["messages"], a.decode_tokens)
                if t["expert_ids"].shape[1:] != (L, K):
                    raise RuntimeError(f"trace shape {t['expert_ids'].shape} is not [T, {L}, {K}]")
                save_trace(trace_path(p), t)
                n_dec = int(t["phase"].sum())
                res["prompts"][p["id"]] = {
                    "ok": True, "domain": p["domain"], "half": p["half"], "source": p["source"],
                    "prompt_tokens": t["prompt_tokens"], "decode_steps": n_dec,
                    "generated_tokens": t["generated_tokens"], "seconds": round(time.time() - t0, 2),
                    "text": t["text"][:600]}
                print(f"[h1a] {len(prompts) - len(todo) + n}/{len(prompts)} {p['id']} prefill {t['prompt_tokens']} "
                      f"decode {n_dec} {time.time() - t0:.1f}s", flush=True)
            except Exception as e:  # recorded, never a silent floor
                res["prompts"][p["id"]] = {"ok": False, "domain": p["domain"], "half": p["half"],
                                           "error": f"{type(e).__name__}: {e}"[:400]}
                print(f"[h1a] {p['id']} ERROR {type(e).__name__}: {str(e)[:200]}", flush=True)
                try:
                    import torch
                    torch.cuda.empty_cache()
                except Exception:
                    pass
            save()
            since_pack += 1
            if since_pack >= a.pack_every:
                pack(tdir)
                res["packed"] = sum(1 for r in res["prompts"].values() if r.get("ok"))
                save()
                since_pack = 0
        rec.remove()

    errors = [k for k, r in res["prompts"].items() if not r.get("ok")]
    pack(tdir)
    res["packed"] = sum(1 for r in res["prompts"].values() if r.get("ok"))
    print(f"[h1a] traced {res['packed']} prompts, {len(errors)} errors — computing the metrics", flush=True)
    traces = M.load_dir(tdir, res["prompts"])
    metrics = M.analyse(traces, n_experts=res.get("n_experts", 128))
    res["gate"] = metrics["gate"]
    res["metrics"] = metrics
    res["summary"] = {"distribution": {d: {k: v for k, v in r.items() if k in ("prompts", "decode_tokens",
                                                                             "consecutive_reuse")}
                                       | {"decode_entropy_mean": r["decode"]["entropy_bits_mean"],
                                          "decode_coverage80_mean": r["decode"]["coverage80_mean"]}
                                       for d, r in metrics["distribution"].items()},
                      "cache": metrics["cache"]}
    res["errors"] = errors
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[h1a] verdict: {metrics['gate']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
