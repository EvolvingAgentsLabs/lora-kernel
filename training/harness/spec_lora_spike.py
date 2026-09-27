r"""F0 — does a LoRA expert on Gemma 4 12B keep speculative decoding? The user's brief (2026-09-27, "expertos LoRA +
speculative decoding en Gemma 4 12B"), phase F0, one A100 session, no training.

One target, `gemma-4-12B-it` in bf16, carrying an expert LoRA already trained here (`wiki12b-walks-s0`, B3 — the W9 wiki
corpus), served three ways by vLLM, one after another:

    nospec   no speculative decoding                                              the reference: outputs and tokens/s
    mtp      Gemma 4's own drafter, `google/gemma-4-12B-it-assistant`, method mtp  no training at all — the drafter
             reads the target's activations, so it SEES the LoRA (strategy A for free, if it holds)
    eagle3   the public EAGLE-3 for the 12B, `BCCard/MoAI-gemma-4-12B-it-speculator.eagle3` (Apache-2.0; trained against
             the FP8 12B on general prompts)

In each: does it serve the LoRA (G1)? on the expert's own prompts and on general ones, with and without the LoRA:
acceptance (vLLM's own counters: accepted / drafted tokens, per position), tokens/s at batch 1 and 8, and — the brief's
mandatory test — are the outputs at temperature 0 IDENTICAL to `nospec`'s for the same model and prompt (batch 1)?
And with the drafter running: can a LoRA be loaded and unloaded at runtime, without a restart, and how long does it take?

THE MATHEMATICS. With per-token acceptance α and k drafted tokens, one target pass yields on average
$\mathbb{E}[\tau] = (1-\alpha^{k+1})/(1-\alpha)$ tokens (FOUNDATIONS §6.4); vLLM reports the realised mean accepted
length directly, `1 + accepted/drafts`, and per position $a_i$ = accepted at draft position i / drafts. The speed-up is
measured, never derived: tokens/s against `nospec` on the same prompts, same batch.

A config that does not start is a result, not an error: its reason is recorded and the next config runs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TARGET = "google/gemma-4-12B-it"
MEMBER = "wiki12b"
ADAPTER = "adapters/wiki12b-walks-s0"
CONFIGS = {
    "nospec": None,
    "nospec2": None,          # F0b's control: plain decoding twice — if these two differ, drift is not spec decode's
    "mtp": {"method": "mtp", "model": "google/gemma-4-12B-it-assistant", "num_speculative_tokens": 4},
    "eagle3": {"method": "eagle3", "model": "BCCard/MoAI-gemma-4-12B-it-speculator.eagle3", "num_speculative_tokens": 4},
    # C0 (2026-09-27): a drafter ALIGNED to the expert with no training — the E4B member trained on the same corpus as the
    # 12B's LoRA (B1 `wiki-walks-s1`), merged into its weights (vLLM puts no LoRA on a drafter), served as a draft model.
    "draft_e4b": {"method": "draft_model", "model": "merged/wiki-e4b", "num_speculative_tokens": 4, "quantization": "fp8",
                  "max_model_len": 4096},
}
DRAFT_ADAPTER = "adapters/wiki-walks-s1"
GENERAL = ["Explain in a short paragraph how a refrigerator keeps food cold.",
           "Write a polite email asking a colleague to move a meeting to Thursday.",
           "What are three good habits for staying focused while studying?",
           "Summarise the water cycle for a ten-year-old.",
           "Give a simple recipe for a vegetable soup.",
           "Why do leaves change colour in autumn?",
           "Describe how to change a flat bicycle tyre, step by step.",
           "What is the difference between weather and climate?"]
N_DOMAIN, MAX_TOKENS = 16, 160


def _post(path: str, body: dict, timeout: int = 300) -> dict:
    from training.harness import accept_rank as ar
    req = urllib.request.Request(ar.HOST + path, method="POST", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw": raw.decode(errors="replace")[:200]}


def metrics() -> dict:
    """vLLM's spec-decode counters, summed over label sets; per-position accepted counts keyed by position."""
    from training.harness import accept_rank as ar
    text = urllib.request.urlopen(ar.HOST + "/metrics", timeout=30).read().decode()
    out: dict = {"per_pos": {}}
    for line in text.splitlines():
        if line.startswith("#") or not line.startswith("vllm:spec_decode"):
            continue
        name, _, val = line.rpartition(" ")
        key = name.split("{", 1)[0]
        if key.endswith("per_pos_total"):
            m = re.search(r'position="(\d+)"', name)
            if m:
                out["per_pos"][m.group(1)] = out["per_pos"].get(m.group(1), 0.0) + float(val)
            continue
        out[key] = out.get(key, 0.0) + float(val)
    return out


def acceptance(before: dict, after: dict) -> dict | None:
    d = lambda k: after.get(k, 0.0) - before.get(k, 0.0)
    drafts, drafted = d("vllm:spec_decode_num_drafts_total"), d("vllm:spec_decode_num_draft_tokens_total")
    acc = d("vllm:spec_decode_num_accepted_tokens_total")
    if not drafted:
        return None
    pos = {p: round((after["per_pos"].get(p, 0) - before["per_pos"].get(p, 0)) / drafts, 4) for p in sorted(after["per_pos"])} if drafts else {}
    return {"drafted": drafted, "accepted": acc, "alpha": round(acc / drafted, 4),
            "mean_accepted_length": round(1 + acc / drafts, 3) if drafts else None, "per_position": pos}


def chat(model: str, messages: list[dict]) -> tuple[str, int, float]:
    t0 = time.time()
    r = _post("/v1/chat/completions", {"model": model, "messages": messages, "temperature": 0, "max_tokens": MAX_TOKENS,
                                       "chat_template_kwargs": {"enable_thinking": False}})
    return r["choices"][0]["message"]["content"], r["usage"]["completion_tokens"], time.time() - t0


def prompt_sets() -> dict:
    from memory import prompt
    from training.wiki import wiki_arm as wa
    rows = wa.load_rows("eval")[:N_DOMAIN // 2] + wa.load_rows("eval_hard")[:N_DOMAIN // 2]
    return {"domain": [[{"role": "system", "content": prompt.SYSTEM_WIKI}, {"role": "user", "content": prompt.user_text_wiki(r["question"])}]
                       for r in rows],
            "general": [[{"role": "user", "content": g}] for g in GENERAL]}


BATCH_INVARIANT = False                             # --batch-invariant (F0b): vLLM's batch-invariant kernels
QUANT: str | None = None                            # --quantization: fp8 on an L4, where bf16 does not fit
EQUALITY_ONLY = False                               # --equality-only (F0b): batch 1 texts, no batch 8, no hot load


def run_config(name: str, spec: dict | None, sets: dict, tok) -> dict:
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    extra = ["--max-model-len", "4096", "--gpu-memory-utilization", "0.90", "--enable-lora", "--max-lora-rank", "16",
             "--max-loras", "2", "--lora-modules", f"{MEMBER}={ADAPTER}"]
    if QUANT:
        extra += ["--quantization", QUANT]
    if spec and spec.get("model") == "merged/wiki-e4b" and not Path("merged/wiki-e4b/config.json").exists():
        import subprocess
        import sys
        rc = subprocess.call([sys.executable, "-m", "training.harness.merge_lora", "--base", "google/gemma-4-E4B-it",
                              "--adapter", DRAFT_ADAPTER, "--out", "merged/wiki-e4b"])
        if rc != 0:
            print(f"[spike] {name}: the merge failed rc={rc}", flush=True)
            return {"spec": spec, "started": False, "why": [f"merge_lora rc={rc}"]}
    if spec:
        extra += ["--speculative-config", json.dumps(spec)]
    os.environ["VLLM_ALLOW_RUNTIME_LORA_UPDATING"] = "True"
    if BATCH_INVARIANT:
        os.environ["VLLM_BATCH_INVARIANT"] = "1"
    t0 = time.time()
    srv = ar.serve(TARGET, extra)
    out: dict = {"spec": spec}
    try:
        if not ar.wait_ready(srv, minutes=20):
            tail = Path("vllm.log").read_text(errors="replace").splitlines()[-400:]
            out["started"] = False
            out["why"] = [l[-300:] for l in tail if re.search(r"Error|error:|not supported|NotImplemented|raise|Exception", l)][-8:]
            print(f"[spike] {name}: DID NOT START · {out['why'][-1:]}", flush=True)
            return out
        out["started"], out["boot_s"] = True, round(time.time() - t0, 1)
        out["G1"] = identity(TARGET, MEMBER, tok)
        print(f"[spike] {name}: up in {out['boot_s']} s · G1 {'applied' if out['G1']['applied'] else 'NOT APPLIED'} "
              f"({out['G1']['differs']}/{out['G1']['probed']})", flush=True)
        out["runs"] = {}
        for model in (TARGET, MEMBER):
            for sname, msgs in sets.items():
                key = f"{'lora' if model == MEMBER else 'base'}/{sname}"
                m0 = metrics() if spec else {}
                texts, toks, secs = [], 0, 0.0
                for m in msgs:                                         # batch 1: one request at a time
                    t, n, s = chat(model, m)
                    texts.append(t); toks += n; secs += s
                acc = acceptance(m0, metrics()) if spec else None
                res, wall8 = [(None, 0, 0.0)], 1.0
                if not EQUALITY_ONLY:
                    t1 = time.time()
                    with ThreadPoolExecutor(max_workers=8) as ex:      # batch 8: eight in flight
                        res = list(ex.map(lambda m: chat(model, m), msgs))
                    wall8 = time.time() - t1
                out["runs"][key] = {"texts": texts, "b1_tokens_per_s": round(toks / secs, 2),
                                    "b8_tokens_per_s": round(sum(r[1] for r in res) / wall8, 2), "acceptance_b1": acc}
                print(f"[spike] {name} {key}: b1 {out['runs'][key]['b1_tokens_per_s']} tok/s · b8 "
                      f"{out['runs'][key]['b8_tokens_per_s']} tok/s" + (f" · α {acc['alpha']} · mean len {acc['mean_accepted_length']}"
                                                                         if acc else ""), flush=True)
        if EQUALITY_ONLY:
            return out
        # a LoRA loaded and unloaded at runtime, with this config's drafter running
        t1 = time.time()
        loaded = _post("/v1/load_lora_adapter", {"lora_name": "hot", "lora_path": ADAPTER})
        load_s = round(time.time() - t1, 2)
        try:
            served = chat("hot", sets["domain"][0])[0] == out["runs"][f"lora/domain"]["texts"][0]
        except Exception as e:                                          # noqa: BLE001 — the record says what failed
            served = f"error: {e!r}"[:200]
        unloaded = _post("/v1/unload_lora_adapter", {"lora_name": "hot"})
        out["hot_lora"] = {"load_s": load_s, "load_reply": loaded, "same_text_as_the_preloaded_lora": served, "unload_reply": unloaded}
        print(f"[spike] {name}: runtime LoRA load {load_s} s · serves identically: {served}", flush=True)
    finally:
        ar.stop(srv)
    return out


def compare(rec: dict) -> dict:
    """Equality with `nospec` at temperature 0, batch 1; speed-up in tokens/s; acceptance with and without the LoRA."""
    ref = rec["configs"].get("nospec", {}).get("runs", {})
    out = {}
    for name, c in rec["configs"].items():
        if name == "nospec" or not c.get("started"):
            continue
        row = {}
        for key, r in c.get("runs", {}).items():
            base = ref.get(key)
            if not base:
                continue
            same = sum(a == b for a, b in zip(r["texts"], base["texts"]))
            row[key] = {"identical_to_nospec": f"{same}/{len(r['texts'])}",
                        "speedup_b1": round(r["b1_tokens_per_s"] / base["b1_tokens_per_s"], 2),
                        "speedup_b8": round(r["b8_tokens_per_s"] / base["b8_tokens_per_s"], 2) if base["b8_tokens_per_s"] else None,
                        "alpha": (r["acceptance_b1"] or {}).get("alpha"),
                        "mean_accepted_length": (r["acceptance_b1"] or {}).get("mean_accepted_length")}
        out[name] = row
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=TARGET)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--quantization", default=None, help="fp8: the 12B on an L4 (bf16 needs an A100)")
    ap.add_argument("--batch-invariant", action="store_true", help="F0b: VLLM_BATCH_INVARIANT=1 in every server")
    ap.add_argument("--draft-quantization", default="fp8", help="C0: the merged E4B drafter's quantization — fp8 (L4/H100), "
                    "bitsandbytes (A100: vLLM's online FP8 fails on sm80 [ran], and bf16 12B + bf16 E4B do not fit 40 GB), none")
    ap.add_argument("--equality-only", action="store_true", help="F0b: batch 1 texts only")
    ap.add_argument("--out", default="spike.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("configs", {})
    import vllm
    from transformers import AutoTokenizer
    globals()["QUANT"] = a.quantization
    if a.draft_quantization == "none":
        CONFIGS["draft_e4b"].pop("quantization", None)
    else:
        CONFIGS["draft_e4b"]["quantization"] = a.draft_quantization
    rec.update(draft_quantization=a.draft_quantization)
    globals()["BATCH_INVARIANT"], globals()["EQUALITY_ONLY"] = a.batch_invariant, a.equality_only
    rec.update(batch_invariant=a.batch_invariant, equality_only=a.equality_only)
    rec.update(vllm=vllm.__version__, target=TARGET, member=MEMBER, adapter=ADAPTER, max_tokens=MAX_TOKENS, quantization=a.quantization)
    if not Path(ADAPTER, "adapter_model.safetensors").exists():
        rec["stopped"] = f"no adapter at {ADAPTER}"; out.write_text(json.dumps(rec, indent=1)); print(f"[spike] {rec['stopped']}", flush=True)
        return 1
    tok = AutoTokenizer.from_pretrained(TARGET)
    sets = prompt_sets()
    for name in a.configs.split(","):
        if name in rec["configs"]:
            continue                                                   # resumable across sessions
        rec["configs"][name] = run_config(name, CONFIGS[name], sets, tok)
        rec["comparison"] = compare(rec)
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    rec["comparison"] = compare(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"[spike] done · {json.dumps(rec['comparison'])[:900]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
