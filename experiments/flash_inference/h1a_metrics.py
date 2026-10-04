"""H1a's metrics, zero GPU: does the DOMAIN concentrate the routing of `google/gemma-4-26B-A4B-it`?

Reads the per-prompt traces `h1a.py` writes (`traces/{domain}/{prompt_id}.npz`: `expert_ids` uint8 [T, L, K],
`token_idx` int32 [T], `phase` uint8 [T], 0 = prefill, 1 = decode) and computes what
`docs/flash-inference/00-analysis.md` §5 names, per domain against general, then the gate written there before the run.

The core is pure Python (the test venv has no numpy); only `load_trace` needs numpy.

**Units.** A cache item is one (layer, expert) pair. One expert in 4 bits is ≈ 3.3 MB (spec §3,
$3 \\times 2816 \\times 704 \\approx 5.95$ M parameters × ~0.56 bytes), so a cache of $G$ GB holds
$C = \\lfloor G \\cdot 10^9 / 3.3 \\cdot 10^6 \\rfloor$ experts: 4 GB → 1212, 8 GB → 2424, 12 GB → 3636 of the
30 × 128 = 3840. A decode token reads $K \\cdot L = 240$ experts; its bytes read are $\\text{misses} \\times 3.3$ MB.

**The metrics** (all on the decode phase unless named — decode is where flash is read):
- entropy per layer, $H_\\ell = -\\sum_e p_{\\ell e} \\log_2 p_{\\ell e}$ (max $\\log_2 128 = 7$ bits);
- coverage-80: the fraction of a layer's experts whose activations, taken largest first, reach 80 %;
- Jaccard between prompts: **weighted** (Ruzicka) $J_w(a,b) = \\sum_k \\min(a_k,b_k) / \\sum_k \\max(a_k,b_k)$ over
  (layer, expert) decode counts, as the gated one; plain set Jaccard reported beside it. Why weighted: 128 decode tokens
  choosing 8 of 128 per layer leave an expert unused with probability $(1-8/128)^{128} = e^{-8.3} \\approx 0.0003$
  under uniform routing, so the plain *sets* are all ≈ everything and their Jaccard ≈ 1 for any two prompts —
  saturated by construction;
- consecutive-token reuse: $\\frac{1}{K}|S_{t,\\ell} \\cap S_{t-1,\\ell}|$ averaged over decode tokens and layers;
- a cache simulator per prompt (§`simulate`), with LRU, LFU and affinity (top-$C$ experts by decode count on the
  domain's half A, evaluated on half B).
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path

EXPERT_MB = 3.3
GBS = (4, 8, 12)
GATE_GB = 8
GATE_HIT_POINTS = 0.10       # affinity hits ≥ 10 points more than LRU
GATE_BYTES_FALL = 0.25       # bytes read per decode token fall ≥ 25 %
GATE_ALPHA = 0.05            # the repository's exact sign test, two-sided
HEADROOM_LRU = 0.90          # LRU already at ≥ 90 %: +10 points is out of reach — said before the run
MIN_PROMPTS_PER_HALF = 10    # fewer evaluable half-B prompts in any domain → VOID
GENERAL = "general"


def capacity(gb: float) -> int:
    """Experts that fit in `gb` decimal gigabytes at EXPERT_MB each (spec §3)."""
    return int(gb * 1000 / EXPERT_MB)


def sign_test(a_better: int, b_better: int) -> float:
    """The repository's exact two-sided sign test (training/harness/bar.py), imported when it resolves."""
    try:
        from training.harness.bar import sign_test as st
        return st(a_better, b_better)
    except Exception:  # standalone use outside the repository root
        n = a_better + b_better
        if n == 0:
            return 1.0
        k = max(a_better, b_better)
        return min(1.0, 2 * sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n)


# ------------------------------------------------------------------ the trace, in memory
def make_trace(pid: str, domain: str, half: str, prefill: list[list[tuple[int, ...]]],
               decode: list[list[tuple[int, ...]]]) -> dict:
    """A trace from per-token lists: `prefill[t][layer]` and `decode[t][layer]` are the K expert ids chosen.
    Prefill is kept as per-layer counts — a prefill forward reads each expert its tokens touch once, layer by layer."""
    n_layers = len((prefill or decode)[0]) if (prefill or decode) else 0
    pc = [Counter() for _ in range(n_layers)]
    for tok in prefill:
        for layer, ids in enumerate(tok):
            pc[layer].update(ids)
    return {"id": pid, "domain": domain, "half": half, "n_layers": n_layers,
            "prefill": [dict(c) for c in pc], "n_prefill": len(prefill),
            "decode": [[tuple(int(e) for e in ids) for ids in tok] for tok in decode]}


def load_trace(path: Path, domain: str, half: str) -> dict:
    """One `h1a.py` npz → a trace (numpy needed here only)."""
    import numpy as np
    z = np.load(path)
    ids, phase = z["expert_ids"], z["phase"]
    T, L, K = ids.shape
    pre = ids[phase == 0]
    pc = []
    for layer in range(L):
        c = np.bincount(pre[:, layer, :].reshape(-1).astype(np.int64)) if len(pre) else np.zeros(0, dtype=np.int64)
        pc.append({int(e): int(n) for e, n in enumerate(c) if n})
    dec = ids[phase == 1].tolist()
    return {"id": path.stem, "domain": domain, "half": half, "n_layers": L, "prefill": pc, "n_prefill": int(len(pre)),
            "decode": [[tuple(x) for x in tok] for tok in dec]}


def load_dir(traces: Path, records: dict | None = None) -> list[dict]:
    """Every trace under `traces/{domain}/`; the half comes from the runner's records when given, else from the id."""
    out = []
    for f in sorted(traces.glob("*/*.npz")):
        rec = (records or {}).get(f.stem, {})
        out.append(load_trace(f, f.parent.name, rec.get("half") or half_of(f.stem)))
    return out


def half_of(pid: str) -> str:
    """`{domain}-{nn}`: even index → half A (affinity), odd → half B (evaluated). The runner uses the same rule."""
    return "A" if int(pid.rsplit("-", 1)[1]) % 2 == 0 else "B"


# ------------------------------------------------------------------ distribution metrics
def decode_counts(trace: dict) -> Counter:
    c = Counter()
    for tok in trace["decode"]:
        for layer, ids in enumerate(tok):
            for e in ids:
                c[(layer, e)] += 1
    return c


def prefill_counts(trace: dict) -> Counter:
    return Counter({(layer, e): n for layer, d in enumerate(trace["prefill"]) for e, n in d.items()})


def per_layer(counts: Counter, n_layers: int) -> list[list[int]]:
    rows = [[] for _ in range(n_layers)]
    for (layer, _e), n in counts.items():
        rows[layer].append(n)
    return rows


def entropy_bits(values: list[int]) -> float:
    s = sum(values)
    return -sum(v / s * math.log2(v / s) for v in values if v) if s else 0.0


def coverage(values: list[int], n_experts: int, share: float = 0.8) -> float:
    """Fraction of the layer's `n_experts` needed, largest first, to reach `share` of its activations."""
    s = sum(values)
    if not s:
        return 0.0
    acc = 0
    for i, v in enumerate(sorted(values, reverse=True), 1):
        acc += v
        if acc >= share * s - 1e-9:
            return i / n_experts
    return len(values) / n_experts


def weighted_jaccard(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    num = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    den = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return num / den if den else 0.0


def set_jaccard(a: Counter, b: Counter) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def consecutive_reuse(trace: dict) -> float | None:
    dec = trace["decode"]
    tot, n = 0.0, 0
    for prev, cur in zip(dec, dec[1:]):
        for p, c in zip(prev, cur):
            tot += len(set(p) & set(c)) / len(c)
            n += 1
    return tot / n if n else None


# ------------------------------------------------------------------ the cache simulator
def affinity(traces: list[dict], cap: int) -> list[tuple[int, int]]:
    """The top-`cap` (layer, expert) pairs by DECODE count over `traces` (a domain's half A), most used first; ties and
    any remaining room filled by prefill count, then by (layer, expert) — deterministic."""
    dc, pc = Counter(), Counter()
    for t in traces:
        dc += decode_counts(t)
        pc += prefill_counts(t)
    keys = set(dc) | set(pc)
    return sorted(keys, key=lambda k: (-dc.get(k, 0), -pc.get(k, 0), k))[:cap]


def simulate(trace: dict, policy: str, cap: int, preload: list[tuple[int, int]] | None = None) -> dict:
    """One request through a cache of `cap` experts. Pre-registered semantics (BRIEF):

    - **lru / lfu** start empty; the request's prefill passes through the cache first, layer by layer, each expert
      its tokens touch once (LFU counting every token's use), *uncounted*; then every decode token, layer by layer,
      its K experts — counted. LFU is perfect-LFU within the request, ties to the least recent.
    - **affinity** (the gated one): the top-`cap` experts of the domain's half A, pinned — misses are read from flash
      and not admitted; the prefill changes nothing. This is §4.3/§4.5's design: the gateway preloads the member's
      affinity before the prefill.
    - **affinity_lru** (reported, not gated): the same preload, oldest = least affine, then managed as LRU through the
      prefill and the decode.
    Returns decode hits, accesses, misses, tokens and bytes read per decode token (MB)."""
    hits = acc = 0
    if policy == "affinity":
        pinned = set((preload or [])[:cap])
        for tok in trace["decode"]:
            for layer, ids in enumerate(tok):
                for e in ids:
                    acc += 1
                    hits += (layer, e) in pinned
    elif policy in ("lru", "affinity_lru"):
        od: OrderedDict = OrderedDict()
        if policy == "affinity_lru":
            for k in reversed((preload or [])[:cap]):
                od[k] = None

        def touch(k, count):
            nonlocal hits, acc
            if k in od:
                od.move_to_end(k)
                if count:
                    hits += 1
            else:
                if len(od) >= cap:
                    od.popitem(last=False)
                od[k] = None
            if count:
                acc += 1
        for layer, d in enumerate(trace["prefill"]):
            for e in sorted(d):
                touch((layer, e), False)
        for tok in trace["decode"]:
            for layer, ids in enumerate(tok):
                for e in ids:
                    touch((layer, e), True)
    elif policy == "lfu":
        cache, freq, stamp, heap, clock = set(), Counter(), {}, [], 0

        def touch(k, w, count):
            nonlocal hits, acc, clock
            clock += 1
            freq[k] += w
            if k in cache:
                if count:
                    hits += 1
            else:
                if len(cache) >= cap:
                    while True:
                        f, t, old = heapq.heappop(heap)
                        if old in cache and freq[old] == f and stamp[old] == t:
                            cache.discard(old)
                            break
                cache.add(k)
            stamp[k] = clock
            heapq.heappush(heap, (freq[k], clock, k))
            if count:
                acc += 1
        for layer, d in enumerate(trace["prefill"]):
            for e in sorted(d):
                touch((layer, e), d[e], False)
        for tok in trace["decode"]:
            for layer, ids in enumerate(tok):
                for e in ids:
                    touch((layer, e), 1, True)
    else:
        raise ValueError(policy)
    n = len(trace["decode"])
    misses = acc - hits
    return {"hits": hits, "accesses": acc, "misses": misses, "tokens": n,
            "hit_rate": hits / acc if acc else None,
            "mb_per_token": misses * EXPERT_MB / n if n else None}


POLICIES = ("lru", "lfu", "affinity", "affinity_lru")


def pooled(sims: list[dict]) -> dict:
    h = sum(s["hits"] for s in sims)
    a = sum(s["accesses"] for s in sims)
    m = sum(s["misses"] for s in sims)
    n = sum(s["tokens"] for s in sims)
    return {"prompts": len(sims), "decode_tokens": n, "hit_rate": h / a if a else None,
            "mb_per_token": m * EXPERT_MB / n if n else None}


# ------------------------------------------------------------------ the analysis and the gate
def analyse(traces: list[dict], n_experts: int = 128, gbs=GBS, caps: dict | None = None) -> dict:
    """Everything §5 names, and the gate. `caps` overrides `capacity(gb)` — for tests on tiny synthetic traces only."""
    cap_of = (lambda gb: caps[gb]) if caps else capacity
    by_dom: dict[str, list[dict]] = {}
    for t in traces:
        by_dom.setdefault(t["domain"], []).append(t)
    n_layers = max(t["n_layers"] for t in traces)
    dcounts = {t["id"]: decode_counts(t) for t in traces}

    # distribution, per domain (decode and prefill), general beside
    dist = {}
    for d, ts in sorted(by_dom.items()):
        row = {"prompts": len(ts), "decode_tokens": sum(len(t["decode"]) for t in ts),
               "prefill_tokens": sum(t["n_prefill"] for t in ts)}
        for phase, cnt in (("decode", lambda t: dcounts[t["id"]]), ("prefill", prefill_counts)):
            tot = Counter()
            for t in ts:
                tot += cnt(t)
            layers = per_layer(tot, n_layers)
            ent = [entropy_bits(v) for v in layers]
            cov = [coverage(v, n_experts) for v in layers]
            row[phase] = {"entropy_bits_per_layer": [round(x, 4) for x in ent],
                          "entropy_bits_mean": round(sum(ent) / len(ent), 4),
                          "coverage80_per_layer": [round(x, 4) for x in cov],
                          "coverage80_mean": round(sum(cov) / len(cov), 4)}
        reuse = [r for r in (consecutive_reuse(t) for t in ts) if r is not None]
        row["consecutive_reuse"] = round(sum(reuse) / len(reuse), 4) if reuse else None
        dist[d] = row

    # Jaccard: every prompt with decode tokens, within its domain against every other domain (general included)
    live = [t for t in traces if t["decode"]]
    jac = {}
    for t in live:
        same = [u for u in live if u["domain"] == t["domain"] and u["id"] != t["id"]]
        other = [u for u in live if u["domain"] != t["domain"]]
        if not same or not other:
            continue
        a = dcounts[t["id"]]
        jac[t["id"]] = {
            "domain": t["domain"],
            "within_w": sum(weighted_jaccard(a, dcounts[u["id"]]) for u in same) / len(same),
            "between_w": sum(weighted_jaccard(a, dcounts[u["id"]]) for u in other) / len(other),
            "within_set": sum(set_jaccard(a, dcounts[u["id"]]) for u in same) / len(same),
            "between_set": sum(set_jaccard(a, dcounts[u["id"]]) for u in other) / len(other)}

    # the cache: affinity from half A, evaluated on half B's decode tokens
    cache = {}
    per_prompt = {}
    for d, ts in sorted(by_dom.items()):
        A = [t for t in ts if t["half"] == "A"]
        B = [t for t in ts if t["half"] == "B" and t["decode"]]
        cache[d] = {}
        for gb in gbs:
            cap = cap_of(gb)
            pre = affinity(A, cap)
            sims = {p: [simulate(t, p, cap, pre) for t in B] for p in POLICIES}
            cache[d][str(gb)] = {"capacity": cap, "affinity_keys": len(pre),
                                 **{p: pooled(s) for p, s in sims.items()}}
            for i, t in enumerate(B):
                per_prompt.setdefault(t["id"], {"domain": d})[str(gb)] = {
                    p: {"hit_rate": sims[p][i]["hit_rate"], "mb_per_token": sims[p][i]["mb_per_token"]}
                    for p in POLICIES}
    result = {"n_layers": n_layers, "n_experts": n_experts, "expert_mb": EXPERT_MB,
              "capacities": {str(gb): cap_of(gb) for gb in gbs},
              "distribution": dist, "jaccard": jac, "cache": cache, "cache_per_prompt": per_prompt}
    result["gate"] = gate(traces, result)
    return result


def gate(traces: list[dict], res: dict) -> dict:
    """Spec §5, written before the run. At 8 GB, on domain prompts (half B, every domain but general, pooled):
    affinity hits ≥ 10 points more than LRU; bytes read per decode token fall ≥ 25 %; Jaccard within the domain exceeds
    Jaccard between domains — each compared prompt by prompt with the exact sign test."""
    g = str(GATE_GB)
    domains = sorted({t["domain"] for t in traces} - {GENERAL})
    rows = {pid: r[g] for pid, r in res["cache_per_prompt"].items() if r["domain"] != GENERAL and g in r}
    void = []
    for d in domains:
        n = sum(1 for r in res["cache_per_prompt"].values() if r["domain"] == d)
        if n < MIN_PROMPTS_PER_HALF:
            void.append(f"{d}: {n} evaluable half-B prompts < {MIN_PROMPTS_PER_HALF}")
    if not domains:
        void.append("no domain traces")

    lru = [r["lru"] for r in rows.values()]
    aff = [r["affinity"] for r in rows.values()]
    sims_l = [res["cache"][d][g]["lru"] for d in domains]
    sims_a = [res["cache"][d][g]["affinity"] for d in domains]

    def pool(xs):
        n = sum(x["decode_tokens"] for x in xs)
        hits = sum(x["hit_rate"] * x["decode_tokens"] for x in xs if x["hit_rate"] is not None)
        mb = sum(x["mb_per_token"] * x["decode_tokens"] for x in xs if x["mb_per_token"] is not None)
        return (hits / n if n else None), (mb / n if n else None)
    # every decode token reads the same K·L experts, so a token-weighted mean of hit rates is the access-pooled rate
    hit_l, mb_l = pool(sims_l)
    hit_a, mb_a = pool(sims_a)
    wins = sum(a["hit_rate"] > b["hit_rate"] for a, b in zip(aff, lru))
    losses = sum(a["hit_rate"] < b["hit_rate"] for a, b in zip(aff, lru))
    p_cache = sign_test(wins, losses)
    jac = [j for j in res["jaccard"].values() if j["domain"] != GENERAL]
    jw = sum(j["within_w"] > j["between_w"] for j in jac)
    jl = sum(j["within_w"] < j["between_w"] for j in jac)
    p_jac = sign_test(jw, jl)

    fall = (1 - mb_a / mb_l) if (mb_l and mb_a is not None) else None
    c1 = hit_a is not None and hit_l is not None and hit_a - hit_l >= GATE_HIT_POINTS and wins > losses \
        and p_cache <= GATE_ALPHA
    c2 = fall is not None and fall >= GATE_BYTES_FALL and wins > losses and p_cache <= GATE_ALPHA
    c3 = jw > jl and p_jac <= GATE_ALPHA
    headroom = hit_l is not None and hit_l >= HEADROOM_LRU
    if void:
        verdict = "VOID"
    elif c1 and c2 and c3:
        verdict = "PASSES"
    else:
        verdict = "FALSIFIED"
    # BESIDE THE GATE, said before the run: pinning can beat LRU on any stream, domain or not. General prompts get the
    # same treatment (affinity from general half A, evaluated on general half B); a domain gap no larger than general's
    # is read as the policy's, not the domain's.
    gen = res["cache"].get(GENERAL, {}).get(g)
    gen_gap = (gen["affinity"]["hit_rate"] - gen["lru"]["hit_rate"]) if gen and gen["lru"]["hit_rate"] is not None \
        and gen["affinity"]["hit_rate"] is not None else None
    dom_gap = (hit_a - hit_l) if hit_a is not None and hit_l is not None else None
    failed = [n for n, ok in (("hits +10 points", c1), ("bytes -25 %", c2), ("Jaccard within > between", c3)) if not ok]
    return {
        "gb": GATE_GB, "capacity": res["capacities"].get(g), "domains": domains, "prompts": len(rows),
        "hit_lru": hit_l, "hit_affinity": hit_a,
        "hit_points": (hit_a - hit_l) if hit_a is not None and hit_l is not None else None,
        "mb_per_token_lru": mb_l, "mb_per_token_affinity": mb_a, "bytes_fall": fall,
        "cache_sign": {"affinity_better": wins, "lru_better": losses, "p_value": round(p_cache, 6)},
        "jaccard_sign": {"within_greater": jw, "between_greater": jl, "p_value": round(p_jac, 6),
                         "within_w_mean": sum(j["within_w"] for j in jac) / len(jac) if jac else None,
                         "between_w_mean": sum(j["between_w"] for j in jac) / len(jac) if jac else None},
        "hits_10_points": c1, "bytes_fall_25": c2, "jaccard_within_gt_between": c3,
        "general_control": {"hit_points": gen_gap, "domain_hit_points": dom_gap,
                            "attributed_to": (None if gen_gap is None or dom_gap is None else
                                              "domain" if dom_gap > gen_gap else "policy")},
        "no_headroom": headroom, "void": void, "failed": failed, "verdict": verdict,
        "reading": ("VOID: " + "; ".join(void)) if void else
                   ("PASSES — the domain concentrates routing enough for a preloaded cache" if verdict == "PASSES" else
                    "FALSIFIED — " + ", ".join(failed) + (" (LRU already ≥ 90 %: no headroom for +10 points)"
                                                          if headroom else "")),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--traces", required=True, help="the traces/ directory: {domain}/{prompt_id}.npz")
    ap.add_argument("--records", default=None, help="the runner's results JSON (for each prompt's half)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    recs = json.loads(Path(a.records).read_text()).get("prompts", {}) if a.records else None
    traces = load_dir(Path(a.traces), recs)
    print(f"[h1a] metrics over {len(traces)} traces", flush=True)
    res = analyse(traces)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"[h1a] verdict: {res['gate']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
