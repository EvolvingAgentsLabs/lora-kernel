r"""E5 — the harness baseline with the engine counted: what the runtime's tool block costs a member when vLLM's prefix cache
is on, and what several LoRAs in one batch cost. Pre-registered in results/E5-engine-baseline-20260928/BRIEF.md; the thesis
review's H-C (docs/review/00-thesis-review.md §1), measured on today's school member rather than on P9.

    pruned      the gateway's own prompt: the request, then the role's tools (~215 tokens) — production
    full        the same, with OpenClaw's 54 tools (P59's recorded surface, ~7,205 tokens) rendered after the request,
                where the member's corpus puts a tool block — so no two requests share it as a prefix
    full_first  the same block moved BEFORE the request, where a prefix cache can reuse it — latency only: the member was
                never trained on that order

One server (E4B bf16 + `school-s0` + `distributor-staff-s0`, prefix caching on — vLLM's default). Per variant: TTFT and
tokens/s at batch 1 over 16 distinct held-out turns (first generation of the turn, streamed), throughput with 8 in flight,
and the server's own prefix-cache hit rate $h = \mathrm{hits}/\mathrm{queries}$ over the variant. Q3: 16 in flight on one
adapter against the same 16 split across two. Accuracy beside it: the 70 held-out turns, `pruned` against `full`.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "google/gemma-4-E4B-it"
MEMBERS = {"school-s0": "adapters/school-staff-s0", "staff-s0": "adapters/distributor-staff-s0"}
SURFACE = Path("results/P59-prune-attribution-20260917/openclaw_tools.json")   # OpenClaw's 54 tools, recorded [ran] P59
VARIANTS = ("pruned", "full", "full_first")
N_LAT, MAX_TOKENS, MAX_MODEL_LEN = 16, 64, 16384


def prompts(variant: str, n: int) -> list[list[dict]]:
    """The school member's first-turn messages for `n` held-out turns, under a tool surface."""
    from examples.school import roles as school_roles
    from examples.school import school_arm
    from examples.school import tools as school_tools
    from examples.school.gateway import SCOPE
    from training.harness.openai_proxy import render_tools
    surface = json.loads(SURFACE.read_text())
    out = []
    for r in school_arm.rows("eval")[:n]:
        role = school_roles.ROLES[r["role"]]
        own = [t for t in school_tools.SCHEMA if t["function"]["name"] in role["tools"]]
        tools = own if variant == "pruned" else own + surface
        user = render_tools([{"role": "user", "content": r["request"]}], tools)[-1]["content"]
        if variant == "full_first":                              # the block first, the request after it
            block = user[len(r["request"]):].lstrip()
            user = f"{block}\n\n{r['request']}"
        out.append([{"role": "system", "content": f"{role['system_prompt']} {SCOPE}"}, {"role": "user", "content": user}])
    return out


def _host() -> str:
    from training.harness import accept_rank as ar
    return ar.HOST


def stream(model: str, prompt: str) -> dict:
    """One streamed completion: time to the first token, total time, tokens generated (from the final usage)."""
    body = {"model": model, "prompt": prompt, "temperature": 0, "max_tokens": MAX_TOKENS, "stream": True,
            "stream_options": {"include_usage": True}}
    req = urllib.request.Request(_host() + "/v1/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0, first, n, ptoks = time.perf_counter(), None, 0, None
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line.endswith("[DONE]"):
                continue
            ev = json.loads(line[5:])
            if ev.get("choices") and ev["choices"][0].get("text") and first is None:
                first = time.perf_counter() - t0
            if ev.get("usage"):
                n, ptoks = ev["usage"]["completion_tokens"], ev["usage"]["prompt_tokens"]
    return {"ttft_s": round(first or 0, 4), "total_s": round(time.perf_counter() - t0, 4), "tokens": n, "prompt_tokens": ptoks}


def prefix_cache() -> dict:
    """vLLM's prefix-cache counters (queries and hits, in tokens), summed over label sets."""
    text = urllib.request.urlopen(_host() + "/metrics", timeout=30).read().decode()
    out = {"queries": 0.0, "hits": 0.0}
    for line in text.splitlines():
        m = re.match(r"vllm:(?:gpu_)?prefix_cache_(queries|hits)(?:_total)?(?:\{[^}]*\})? ([0-9.eE+-]+)$", line)
        if m:
            out[m.group(1)] += float(m.group(2))
    return out


def latency(model: str, rendered: list[str]) -> dict:
    """Batch 1 over distinct prompts (median TTFT without the first, which warms the shared system prompt), then 8 in
    flight; the prefix-cache hit rate over the whole variant."""
    c0 = prefix_cache()
    b1 = [stream(model, p) for p in rendered]
    t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as ex:
        b8 = list(ex.map(lambda p: stream(model, p), rendered))
    wall8 = time.perf_counter() - t
    c1 = prefix_cache()
    q = c1["queries"] - c0["queries"]
    return {"prompt_tokens_median": statistics.median(x["prompt_tokens"] or 0 for x in b1),
            "ttft_b1_median_s": round(statistics.median(x["ttft_s"] for x in b1[1:]), 4),
            "tps_b1": round(sum(x["tokens"] for x in b1) / sum(x["total_s"] for x in b1), 2),
            "tps_b8": round(sum(x["tokens"] for x in b8) / wall8, 2),
            "ttft_b8_median_s": round(statistics.median(x["ttft_s"] for x in b8), 4),
            "prefix_hit_rate": round((c1["hits"] - c0["hits"]) / q, 3) if q else None, "runs_b1": b1}


def mixed(rendered: list[str]) -> dict:
    """Q3: the same 16 prompts in flight on one adapter, then split across two adapters."""
    def burst(models: list[str]) -> dict:
        t = time.perf_counter()
        with ThreadPoolExecutor(max_workers=len(rendered)) as ex:
            rs = list(ex.map(lambda mp: stream(*mp), zip(models, rendered)))
        wall = time.perf_counter() - t
        return {"tps": round(sum(x["tokens"] for x in rs) / wall, 2), "ttft_median_s": round(statistics.median(x["ttft_s"] for x in rs), 4)}
    one = burst(["school-s0"] * len(rendered))
    two = burst(["school-s0" if i % 2 == 0 else "staff-s0" for i in range(len(rendered))])
    return {"one_adapter": one, "two_adapters": two, "ratio": round(two["tps"] / one["tps"], 3) if one["tps"] else None}


def reading(rec: dict) -> dict:
    """The table written first (BRIEF). Q1: the block's latency as served — TTFT full/pruned ≥ 2 COSTS, ≤ 1.2 ABSORBED,
    else PARTIAL. Q2: the same with the block first — ≤ 1.2 with h ≥ 0.8 means FREE AS A PREFIX. Q3: two adapters keep
    ≥ 0.9 of one adapter's throughput — NO MATERIAL CONTENTION."""
    lat = rec.get("latency", {})
    out = {}
    if {"pruned", "full"} <= lat.keys():
        r = lat["full"]["ttft_b1_median_s"] / lat["pruned"]["ttft_b1_median_s"]
        out["Q1"] = {"ttft_ratio": round(r, 2), "tps_b8_ratio": round(lat["full"]["tps_b8"] / lat["pruned"]["tps_b8"], 3),
                     "reading": "COSTS" if r >= 2 else "ABSORBED" if r <= 1.2 else "PARTIAL"}
    if {"pruned", "full_first"} <= lat.keys():
        r = lat["full_first"]["ttft_b1_median_s"] / lat["pruned"]["ttft_b1_median_s"]
        h = lat["full_first"]["prefix_hit_rate"] or 0
        out["Q2"] = {"ttft_ratio": round(r, 2), "prefix_hit_rate": h,
                     "reading": "FREE AS A PREFIX" if r <= 1.2 and h >= 0.8 else "NOT FREE"}
    if rec.get("mixed", {}).get("ratio") is not None:
        out["Q3"] = {"ratio": rec["mixed"]["ratio"],
                     "reading": "NO MATERIAL CONTENTION" if rec["mixed"]["ratio"] >= 0.9 else "CONTENTION"}
    acc = rec.get("accuracy", {})
    if {"pruned", "full"} <= acc.keys():
        out["accuracy"] = {v: f"{sum(x.get('credit', False) for x in acc[v].values())}/{len(acc[v])}" for v in ("pruned", "full")}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--out", default="e5.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    from transformers import AutoTokenizer
    from examples.school import school_arm
    from examples.school.gateway import vllm_generator
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    render = lambda m: tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    srv = ar.serve(a.base, ["--max-model-len", str(MAX_MODEL_LEN), "--gpu-memory-utilization", "0.90", "--enable-lora",
                            "--max-lora-rank", "16", "--max-loras", "2",
                            "--lora-modules", *[f"{m}={d}" for m, d in MEMBERS.items()]])
    try:
        if not ar.wait_ready(srv, minutes=20):
            rec["stopped"] = "the server never came up"; save(); return 1
        rec["G1"] = {m: identity(a.base, m, tok) for m in MEMBERS}
        print(f"[e5] G1 {({m: g['applied'] for m, g in rec['G1'].items()})}", flush=True)
        save()
        if not all(g["applied"] for g in rec["G1"].values()):
            rec["stopped"] = "G1: a member is not applied"; save(); return 1
        rec.setdefault("latency", {})
        for v in VARIANTS:                                   # Q1 and Q2 first: the question this run exists for
            if v in rec["latency"]:
                continue
            rec["latency"][v] = latency("school-s0", [render(m) for m in prompts(v, N_LAT)])
            save()
            L = rec["latency"][v]
            print(f"[e5] {v}: prompt {L['prompt_tokens_median']} tok · TTFT b1 {L['ttft_b1_median_s']} s · "
                  f"{L['tps_b1']} tok/s b1 · {L['tps_b8']} tok/s b8 · prefix hit {L['prefix_hit_rate']}", flush=True)
        if "mixed" not in rec:
            rec["mixed"] = mixed([render(m) for m in prompts("pruned", N_LAT)])
            save()
            print(f"[e5] Q3 multi-LoRA: {rec['mixed']}", flush=True)
        rec.setdefault("accuracy", {})
        from training.harness import openai_proxy
        surface = json.loads(SURFACE.read_text())
        plain = openai_proxy.render_tools
        for v in ("pruned", "full"):
            slot = rec["accuracy"].setdefault(v, {})
            # the gateway imports render_tools at call time; the `full` arm offers OpenClaw's 54 beside the role's own
            openai_proxy.render_tools = plain if v == "pruned" else (lambda msgs, tools: plain(msgs, list(tools) + surface))
            try:
                gen = vllm_generator("school-s0", tok)
                for i, r in enumerate(school_arm.rows("eval"), 1):
                    if r["case_id"] in slot and "error" not in slot[r["case_id"]]:
                        continue
                    slot[r["case_id"]] = school_arm.score_turn(gen, r)
                    if i % 10 == 0 or i == 70:
                        save()
                        print(f"[e5] accuracy {v} {i}/70 · credit {sum(x.get('credit', False) for x in slot.values())}", flush=True)
            finally:
                openai_proxy.render_tools = plain
    finally:
        ar.stop(srv)
    rec["reading"] = reading(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[e5] {json.dumps(rec['reading'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
