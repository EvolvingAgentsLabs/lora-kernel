r"""DRAFT0 — a LoRA on Gemma 4's MTP drafter, aligned to the 12B **with its expert's LoRA on** (the user's design, 2026-10-06).

WHY. HOTL0 [ran]: on the user's Mac the 12B's stock MTP drafter gives 1.47× on the base and 1.23× with the wiki LoRA on —
the LoRA moves what the target writes and the drafter, trained on the base, predicts it less often (acceptance 0.76 → 0.67
general, 0.60 on the LoRA's own domain, MLXK0). At $k = 1$, speed-up $= (1 + \alpha)/C(1)$ with $C(1) \approx 1.26$ measured
(H0: $E = 1.755$ at 1.40×), so the whole question is $\alpha$ on the expert's domain. This trains a small LoRA on the
drafter so that its argmax matches the LoRA'd target's argmax — the expert's LoRA and the drafter's LoRA then switch together.

HOW THE DRAFTER IS FED [read] transformers 5.18, `SinglePositionMultiTokenCandidateGenerator.get_candidates`: for the last
accepted token $x_i$ at position $i$, the drafter reads $[E(x_i);\ h_{i-1}]$ — the target's input embedding of $x_i$ and the
target's last hidden state at $i-1$ — at position id $i$, attending (all 4 of its layers share KV, `num_kv_shared_layers = 4`)
to the target's own last-layer keys and values of each layer type for positions $< i$. Its argmax is the draft of $x_{i+1}$,
which the target accepts iff it equals the target's argmax at $i$. So with $y_i = \arg\max_v p_{\text{target}}(v \mid x_{\le i})$,

$$\alpha = \Pr_i\big[\arg\max q_\theta([E(x_i); h_{i-1}],\ KV_{<i}) = y_i\big], \qquad
\mathcal{L}(\theta) = -\textstyle\sum_i \log q_\theta(y_i \mid [E(x_i); h_{i-1}],\ KV_{<i})$$

over the positions of the model's own turns. Every query reads only the target's KV, never the drafter's, so all positions of
a sequence train in ONE forward with a mask: full-attention layers see keys $k \le i-1$, sliding layers $i - W \le k \le i-1$.

GATES, before anything trains (the run stops on either):
- **G0 — the parallel drafter is the drafter.** At sampled positions (some past the sliding window), the masked parallel
  forward equals the drafter's own forward called exactly as generation calls it (one query, KV cut at $i$, its own masks):
  same argmax, $\max|\Delta\text{logit}| \le 0.5$ in bf16.
- **G1 — the stock drafter's offline $\alpha$ is the one MLX measured.** On the LoRA'd target's own greedy continuations of
  the domain prompts, stock $\alpha$ must land in $[0.45, 0.75]$ (MLXK0 **[ran]** 0.60, HOTL0 general 0.67). Outside it, the
  offline instrument does not measure what the Mac serves, and nothing it would report about an aligned drafter is believed.

    python -m training.harness.drafter_align --base google/gemma-4-12B-it --target-lora adapters/wiki12b-walks-s0 --out draft0.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

DRAFTER = "google/gemma-4-12B-it-assistant"
WINDOW = 1024                       # the drafter's sliding_window (config) — the target's too
G0_TOL = 0.5
G1_BAND = (0.45, 0.75)
C1 = 1.755 / 1.40                    # HOTL0 H0 [ran]: a k = 1 round's cost in decode steps on the user's Mac
# examples/mac/mlx_spec_lora.GENERAL, copied: that module imports mlx, which a Linux card does not have
GENERAL = ["Explain in a short paragraph how a refrigerator keeps food cold.",
           "Write a polite email asking a colleague to move a meeting to Thursday.",
           "Summarise the water cycle for a ten-year-old.",
           "Why do leaves change colour in autumn?"]
TARGETS = ["q_proj", "o_proj", "gate_proj", "up_proj", "down_proj", "pre_projection"]   # no k/v: every layer shares KV


def say(msg: str) -> None:
    print(f"[draft] {msg}", flush=True)


# ------------------------------------------------------------------ pure pieces (tested without torch)
def visible(q: int, k: int, layer_type: str, window: int = WINDOW) -> bool:
    """May the drafter's query for position q read the target's key at position k? Strictly before q, and inside the
    window for sliding layers — the KV generation hands it is the target's cache after processing positions < q."""
    if k > q - 1 or k < 0:
        return False
    return layer_type == "full_attention" or (q - 1) - k < window


def speedup(alpha: float, c1: float = C1) -> float:
    """At k = 1 a round yields 1 + α tokens and costs C(1) plain steps."""
    return round((1 + alpha) / c1, 3)


def verdict(rec: dict) -> str:
    """DRAFT0's table (BRIEF.md): G0 and G1 first, then the aligned drafter's α on the held-out domain prompts."""
    g = rec.get("gates", {})
    if not g.get("G0", {}).get("ok"):
        return "VOID: G0 — the parallel drafter is not the drafter"
    if not g.get("G1", {}).get("ok"):
        return f"VOID: G1 — stock α {g.get('G1', {}).get('alpha')} is outside {list(G1_BAND)}: the offline instrument is not the Mac's"
    a0, a1 = rec["alpha"]["stock"]["domain"], rec["alpha"]["aligned"]["domain"]
    if a1 >= 0.85 and a1 - a0 >= 0.15:
        return f"ALIGNED: α {a0} → {a1} on the domain, projected {speedup(a0)}× → {speedup(a1)}× at k = 1"
    if a1 - a0 >= 0.05:
        return f"PARTLY ALIGNED: α {a0} → {a1} (bar 0.85 and +0.15), projected {speedup(a1)}×"
    return f"NOT ALIGNED: α {a0} → {a1}"


# ------------------------------------------------------------------ GPU side
def install() -> dict:
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers>=5.18", "peft>=0.17"],
                       capture_output=True, text=True)
    import transformers, peft
    return {"rc": r.returncode, "transformers": transformers.__version__, "peft": peft.__version__}


def masks(torch, q_pos, kv_len: int, device):
    """{layer_type: bool [1, 1, Q, K]} — True where `visible`."""
    q = torch.as_tensor(q_pos, device=device)[:, None]
    k = torch.arange(kv_len, device=device)[None, :]
    full = (k <= q - 1)
    swa = full & ((q - 1) - k < WINDOW)
    return {"full_attention": full[None, None], "sliding_attention": swa[None, None]}


class Rig:
    def __init__(self, base: str, target_lora: str | None, device: str = "cuda"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch, self.device = torch, device
        self.tok = AutoTokenizer.from_pretrained(base)
        t = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16, device_map=device)
        if target_lora:
            from peft import PeftModel
            t = PeftModel.from_pretrained(t, target_lora)
        self.target = t.eval()
        self.embed = self.target.get_input_embeddings()
        self.drafter = AutoModelForCausalLM.from_pretrained(DRAFTER, dtype=torch.bfloat16, device_map=device,
                                                            attn_implementation="sdpa").eval()

    def target_pass(self, ids):
        """h (last hidden, as generation reads it), shared KV, and the target's argmax at every position."""
        torch = self.torch
        with torch.no_grad():
            out = self.target(input_ids=ids, output_hidden_states=True, return_shared_kv_states=True, use_cache=False)
        return out.hidden_states[-1], out.shared_kv_states, out.logits.argmax(-1)

    def draft_parallel(self, ids, h, kv, q_pos, model=None):
        """Drafter logits for every query position in q_pos at once (q ≥ 1)."""
        torch, d = self.torch, (model or self.drafter)
        base = d.get_base_model() if hasattr(d, "get_base_model") else d
        qi = torch.as_tensor(q_pos, device=ids.device)
        x = torch.cat([self.embed(ids[:, qi]), h[:, qi - 1]], dim=-1)
        x = base.pre_projection(x.to(base.pre_projection.weight.dtype))
        kvlen = next(iter(kv.values()))[0].shape[2]
        out = base.model(inputs_embeds=x, attention_mask=masks(torch, q_pos, kvlen, ids.device),
                         position_ids=qi[None], shared_kv_states=kv, use_cache=False)
        return base.lm_head(out.last_hidden_state)

    def draft_stepwise(self, ids, h, kv, i: int):
        """The drafter called exactly as generation calls it, for one position."""
        torch = self.torch
        x = torch.cat([self.embed(ids[:, i:i + 1]), h[:, i - 1:i]], dim=-1)
        cut = {k: (v[0][:, :, :i, :], v[1][:, :, :i, :]) for k, v in kv.items()}
        with torch.no_grad():
            out = self.drafter(inputs_embeds=x, position_ids=torch.tensor([[i]], device=ids.device),
                               shared_kv_states=cut, use_cache=False)
        return out.logits[0, -1]


def assistant_from(tok, messages: list[dict]) -> int:
    """Token index where the model's first turn begins: positions from here on are what the drafter serves."""
    first = next(n for n, m in enumerate(messages) if m["role"] == "assistant")
    head = tok.apply_chat_template(messages[:first], tokenize=False, add_generation_prompt=True)
    return len(tok(head, add_special_tokens=False)["input_ids"])


def alpha_on(rig: Rig, seqs: list[tuple], model=None) -> float:
    """seqs: (ids, start) — α over positions start…T−2 (the last position has no next target token to compare)."""
    torch = rig.torch
    hit = n = 0
    for ids, start in seqs:
        h, kv, y = rig.target_pass(ids)
        q = list(range(max(1, start), ids.shape[1]))
        with torch.no_grad():
            pred = rig.draft_parallel(ids, h, kv, q, model).argmax(-1)[0]
        hit += int((pred == y[0, q]).sum()); n += len(q)
    return round(hit / max(1, n), 4)


def generate(rig: Rig, prompts: list[list[dict]], max_new: int = 160) -> list[tuple]:
    """The LoRA'd target's own greedy continuations — what the drafter is asked to predict when serving."""
    torch, out = rig.torch, []
    for msgs in prompts:
        text = rig.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = rig.tok(text, return_tensors="pt", add_special_tokens=False)["input_ids"].to(rig.device)
        with torch.no_grad():
            g = rig.target.generate(input_ids=ids, max_new_tokens=max_new, do_sample=False)
        out.append((g, ids.shape[1]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="google/gemma-4-12B-it")
    ap.add_argument("--target-lora", default="adapters/wiki12b-walks-s0")
    ap.add_argument("--corpus", default="training/wiki/data/train.jsonl", help="the expert's own training corpus")
    ap.add_argument("--eval-prompts", type=int, default=40, help="held-out domain prompts: eval + eval_hard, half each")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-seq", type=int, default=1536)
    ap.add_argument("--out-adapter", default="adapters/drafter-wiki12b-s0")
    ap.add_argument("--out", default="draft0.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec: dict = {"run": "DRAFT0", "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "drafter": DRAFTER, "base": a.base,
                 "target_lora": a.target_lora, "gates": {}, "alpha": {}}
    save = lambda: out.write_text(json.dumps(rec, indent=1))
    rec["deps"] = install(); save()
    say(f"deps {rec['deps']}")

    import torch
    from memory import prompt
    from training.wiki import wiki_arm as wa
    torch.manual_seed(0)
    rig = Rig(a.base, a.target_lora)
    say("target (+ its LoRA) and drafter loaded")

    half = a.eval_prompts // 2
    rows = wa.load_rows("eval")[:half] + wa.load_rows("eval_hard")[:a.eval_prompts - half]
    dom = [[{"role": "system", "content": prompt.SYSTEM_WIKI}, {"role": "user", "content": prompt.user_text_wiki(r["question"])}]
           for r in rows]
    gen = [[{"role": "user", "content": g}] for g in GENERAL]
    t0 = time.time()
    dom_seqs, gen_seqs = generate(rig, dom), generate(rig, gen)
    rec["eval"] = {"domain_prompts": len(dom_seqs), "general_prompts": len(gen_seqs), "generate_s": round(time.time() - t0, 1),
                   "domain_positions": sum(s.shape[1] - st for s, st in dom_seqs)}
    say(f"generated {len(dom_seqs)} domain + {len(gen_seqs)} general continuations in {rec['eval']['generate_s']} s")

    # G0 — the parallel forward against the drafter called as generation calls it
    ids, start = max(dom_seqs, key=lambda s: s[0].shape[1])
    h, kv, _ = rig.target_pass(ids)
    T = ids.shape[1]
    probe = sorted({1, max(1, start), min(T - 1, start + 40), min(T - 1, WINDOW + 5), T - 1})
    with torch.no_grad():
        par = rig.draft_parallel(ids, h, kv, probe)[0].float()
    diffs, same = [], []
    for j, i in enumerate(probe):
        s = rig.draft_stepwise(ids, h, kv, i).float()
        diffs.append(round(float((s - par[j]).abs().max()), 4)); same.append(int(s.argmax()) == int(par[j].argmax()))
    rec["gates"]["G0"] = {"positions": probe, "T": T, "max_abs_diff": diffs, "argmax_same": same,
                          "ok": all(same) and max(diffs) <= G0_TOL}
    save(); say(f"G0 {rec['gates']['G0']}")
    if not rec["gates"]["G0"]["ok"]:
        rec["verdict"] = verdict(rec); rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); say(rec["verdict"]); return 1

    # G1 — the stock drafter's offline α against what the Mac measured
    rec["alpha"]["stock"] = {"domain": alpha_on(rig, dom_seqs), "general": alpha_on(rig, gen_seqs)}
    a0 = rec["alpha"]["stock"]["domain"]
    rec["gates"]["G1"] = {"alpha": a0, "band": list(G1_BAND), "ok": G1_BAND[0] <= a0 <= G1_BAND[1]}
    save(); say(f"stock α {rec['alpha']['stock']} · G1 {'ok' if rec['gates']['G1']['ok'] else 'FAILED'}")
    if not rec["gates"]["G1"]["ok"]:
        rec["verdict"] = verdict(rec); rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); say(rec["verdict"]); return 1

    # the training corpus: the expert's own rows, the positions of the model's turns
    from peft import LoraConfig, get_peft_model
    corpus = [json.loads(l) for l in open(a.corpus) if l.strip()]
    data = []
    for r in corpus:
        text = rig.tok.apply_chat_template(r["messages"], tokenize=False)
        ids = rig.tok(text, return_tensors="pt", add_special_tokens=False)["input_ids"][:, :a.max_seq]
        st = assistant_from(rig.tok, r["messages"])
        if ids.shape[1] - st >= 8:
            data.append((ids, st))
    rec["train"] = {"rows": len(data), "of": len(corpus), "epochs": a.epochs, "r": a.r, "lr": a.lr, "accum": a.accum,
                    "targets": TARGETS, "loss": []}
    say(f"training on {len(data)} rows of {len(corpus)}")
    d = get_peft_model(rig.drafter, LoraConfig(r=a.r, lora_alpha=2 * a.r, lora_dropout=0.0, target_modules=TARGETS))
    for p in d.parameters():                              # the adapter trains in fp32 over the bf16 drafter
        if p.requires_grad:
            p.data = p.data.float()
    d.train()
    opt = torch.optim.AdamW([p for p in d.parameters() if p.requires_grad], lr=a.lr)
    steps = int(len(data) * a.epochs)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 10) * max(0.0, 1 - s / max(1, steps // a.accum)))
    g = torch.Generator().manual_seed(0)
    order = [i for _ in range(int(-(-a.epochs // 1))) for i in torch.randperm(len(data), generator=g).tolist()][:steps]
    run, t0 = 0.0, time.time()
    for n, i in enumerate(order):
        ids, st = data[i]
        ids = ids.to(rig.device)
        h, kv, y = rig.target_pass(ids)
        q = list(range(max(1, st), ids.shape[1] - 1))
        logits = rig.draft_parallel(ids, h, kv, q, d)[0].float()
        loss = torch.nn.functional.cross_entropy(logits, y[0, q])
        (loss / a.accum).backward()
        run += float(loss)
        if (n + 1) % a.accum == 0:
            torch.nn.utils.clip_grad_norm_([p for p in d.parameters() if p.requires_grad], 1.0)
            opt.step(); sched.step(); opt.zero_grad()
        if (n + 1) % 50 == 0:
            rec["train"]["loss"].append([n + 1, round(run / 50, 4)]); run = 0.0
            save(); say(f"train {n + 1}/{steps} · loss {rec['train']['loss'][-1][1]} · {time.time() - t0:.0f} s")
    d.eval()
    rec["train"]["seconds"] = round(time.time() - t0, 1)
    d.save_pretrained(a.out_adapter)
    rec["alpha"]["aligned"] = {"domain": alpha_on(rig, dom_seqs, d), "general": alpha_on(rig, gen_seqs, d)}
    rec["projected_speedup_k1"] = {k: {"stock": speedup(rec["alpha"]["stock"][k]), "aligned": speedup(rec["alpha"]["aligned"][k])}
                                   for k in ("domain", "general")}
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    subprocess.call(["tar", "czf", "adapters_out.tgz", a.out_adapter])
    say(f"aligned α {rec['alpha']['aligned']} · {rec['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
