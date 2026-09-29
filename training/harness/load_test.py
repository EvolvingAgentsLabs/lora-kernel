r"""C1 — concurrency on the `server` profile: one vLLM 0.30 server on one L4 carrying four members at once, loaded by K
concurrent sessions, each sending R requests one after the other (steady load). Pre-registered in
results/C1-concurrency-20260929/BRIEF.md.

    python -m training.harness.load_test --out c1.json

Per cell (K sessions × A adapters in play): aggregate generated tokens/s, time to first token p50/p95, request latency
p50/p95, errors. The requests are each member's own first-turn prompts (as its gateway renders them), streamed, 64
tokens, temperature 0. With A adapters, session $j$ uses adapter $j \bmod A$.

The reading, written first: at K = 16 the four-adapter throughput over the one-adapter throughput, $r_A = \mathrm{tps}_4 /
\mathrm{tps}_1$ — $r_A \ge 0.8$ NO MATERIAL CONTENTION, else CONTENTION (E5 measured 0.88 at two adapters, one burst);
and the capacity of one L4, the largest K whose four-adapter p95 TTFT stays under 2 s, reported without a bar.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "google/gemma-4-E4B-it"
MEMBERS = {"school-s0": "adapters/school-staff-s0", "upper-s0": "adapters/school-upper-s0",
           "staff-s0": "adapters/distributor-staff-s0", "out-s0": "adapters/distributor-staff-out-s0"}
CELLS = [(1, 1), (8, 1), (8, 4), (16, 1), (16, 2), (16, 4), (32, 1), (32, 4)]      # (K sessions, A adapters)
R, N_PROMPTS = 4, 16
TTFT_P95_BUDGET_S, MIN_RATIO = 2.0, 0.8


def pct(xs: list[float], q: float) -> float:
    """The q-th percentile, nearest rank — no interpolation, so a p95 over 16 values is one of them."""
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(round(q / 100 * len(s))) - 1))] if s else 0.0


def prompts_for(member: str, tok, n: int = N_PROMPTS) -> list[str]:
    """The member's own first-turn prompts, rendered as its gateway renders them."""
    render = lambda m: tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    if member in ("school-s0", "upper-s0"):
        from training.harness.spec_lora_spike import school_prompts
        return [render(m) for m in school_prompts(n)]
    from examples.distributor import roles, staff_arm
    from examples.distributor import tools as dt
    from training.harness.openai_proxy import render_tools
    out = []
    for r in staff_arm.rows("eval")[:n]:
        role = roles.ROLES[r["role"]]
        schema = [t for t in dt.SCHEMA if t["function"]["name"] in role["tools"]]
        user = render_tools([{"role": "user", "content": r["request"]}], schema)[-1]["content"]
        out.append(render([{"role": "system", "content": role["system_prompt"]}, {"role": "user", "content": user}]))
    return out


def run_cell(k: int, a: int, prompts: dict[str, list[str]], stream) -> dict:
    """K sessions, each R requests in sequence; session j on adapter j mod A."""
    names = list(MEMBERS)[:a]

    def session(j: int) -> list[dict]:
        m = names[j % a]
        return [{**stream(m, prompts[m][(j * R + i) % len(prompts[m])]), "member": m} for i in range(R)]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=k) as ex:
        rs = [x for s in ex.map(session, range(k)) for x in s]
    wall = time.perf_counter() - t0
    ok = [x for x in rs if "error" not in x]
    return {"k": k, "adapters": a, "requests": len(rs), "errors": len(rs) - len(ok),
            "tps": round(sum(x["tokens"] for x in ok) / wall, 2) if wall else 0.0,
            "ttft_p50_s": round(pct([x["ttft_s"] for x in ok], 50), 3), "ttft_p95_s": round(pct([x["ttft_s"] for x in ok], 95), 3),
            "latency_p50_s": round(pct([x["total_s"] for x in ok], 50), 3), "latency_p95_s": round(pct([x["total_s"] for x in ok], 95), 3)}


def reading(cells: list[dict]) -> dict:
    get = {(c["k"], c["adapters"]): c for c in cells}
    out = {}
    if (16, 1) in get and (16, 4) in get and get[(16, 1)]["tps"]:
        r = round(get[(16, 4)]["tps"] / get[(16, 1)]["tps"], 3)
        out["contention"] = {"ratio_4_over_1_at_16": r,
                             "reading": "NO MATERIAL CONTENTION" if r >= MIN_RATIO else "CONTENTION"}
    ok_k = [k for (k, a), c in get.items() if a == 4 and c["errors"] == 0 and c["ttft_p95_s"] <= TTFT_P95_BUDGET_S]
    out["capacity"] = {"largest_k_four_adapters_p95_ttft_under_2s": max(ok_k) if ok_k else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--out", default="c1.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("cells", [])
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    from transformers import AutoTokenizer
    from training.harness import accept_rank as ar
    from training.harness.e5_baseline import stream
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    srv = ar.serve(a.base, ["--max-model-len", "4096", "--gpu-memory-utilization", "0.90", "--enable-lora",
                            "--max-lora-rank", "16", "--max-loras", str(len(MEMBERS)),
                            "--lora-modules", *[f"{m}={d}" for m, d in MEMBERS.items()]])
    try:
        if not ar.wait_ready(srv, minutes=20):
            rec["stopped"] = "the server never came up"; save(); return 1
        # the transport is what this run measures: an adapter the server cannot serve is an error in every cell, and
        # would read as load. Each member answers one request before any cell runs.
        rec["reachable"] = {}
        for m in MEMBERS:
            try:
                rec["reachable"][m] = stream(m, prompts_for(m, tok, 1)[0])["tokens"] > 0
            except Exception as e:
                rec["reachable"][m] = repr(e)[:160]
        print(f"[load] reachable {rec['reachable']}", flush=True)
        save()
        if not all(v is True for v in rec["reachable"].values()):
            rec["stopped"] = "a member is not reachable"; save(); return 1
        prompts = {m: prompts_for(m, tok) for m in MEMBERS}

        def safe_stream(m, p):
            try:
                return stream(m, p)
            except Exception as e:                            # an error is a result of load, counted, never raised
                return {"error": repr(e)[:160]}
        done = {(c["k"], c["adapters"]) for c in rec["cells"]}
        for k, n in CELLS:
            if (k, n) in done:
                continue
            c = run_cell(k, n, prompts, safe_stream)
            rec["cells"].append(c)
            save()
            print(f"[load] K={k} A={n}: {c['tps']} tok/s · TTFT p50 {c['ttft_p50_s']} p95 {c['ttft_p95_s']} s · "
                  f"latency p95 {c['latency_p95_s']} s · errors {c['errors']}/{c['requests']}", flush=True)
    finally:
        ar.stop(srv)
    rec["reading"] = reading(rec["cells"])
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[load] {json.dumps(rec['reading'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
