"""H1a's instrument (docs/flash-inference/00-analysis.md §5; results/H1A-moe-routing-by-domain-20261004/BRIEF.md).

Two halves. The metrics and the cache simulator, pure Python, on synthetic traces with answers known by hand:
capacity $C = \\lfloor G \\cdot 10^9 / 3.3 \\cdot 10^6 \\rfloor$ (4/8/12 GB → 1212/2424/3636 experts), LRU and LFU on
sequences whose hit counts are worked out below, the pinned affinity cache, entropy $H = -\\sum p \\log_2 p$,
coverage-80, weighted Jaccard $\\sum \\min / \\sum \\max$, consecutive reuse $|S_t \\cap S_{t-1}| / K$, and the gate
on a concentrated world (passes) and a uniform one (does not). And the hook, on a tiny random Gemma 4 MoE on CPU
(`Gemma4TextRouter`, the class `h1a.py` hooks on the 26B): K ids per token per layer, the prefill as one call of
prompt-length rows and one row per decode step, equal to the router's own top-k — plus the 4-bit experts' round trip.
"""
import random

import pytest

from experiments.flash_inference import h1a_metrics as M
from experiments.flash_inference.h1a import DOMAINS, build_prompts


def tr(decode, prefill=(), pid="d-01", domain="d"):
    """decode: a list of tokens, each a list over layers of K-tuples."""
    return M.make_trace(pid, domain, M.half_of(pid), [list(t) for t in prefill], [list(t) for t in decode])


def one_layer(seq):
    """A one-layer, K=1 stream: each letter is a token touching one expert."""
    ids = {c: i for i, c in enumerate(sorted(set(seq)))}
    return [[(ids[c],)] for c in seq]


def test_capacity_is_the_specs_arithmetic():
    assert [M.capacity(g) for g in M.GBS] == [1212, 2424, 3636]


def test_lru_and_lfu_on_hand_worked_streams():
    # capacity 2, A A B C A — LRU: miss hit miss miss(evicts A, the least recent) miss → 1 hit;
    # LFU: A has 2 uses when C arrives, so B is evicted and the last A hits → 2 hits
    t = tr(one_layer("AABCA"))
    lru, lfu = M.simulate(t, "lru", 2), M.simulate(t, "lfu", 2)
    assert (lru["hits"], lru["accesses"]) == (1, 5)
    assert (lfu["hits"], lfu["accesses"]) == (2, 5)
    # A B A C B — LRU: miss miss hit miss(evicts B) miss → 1 hit
    assert M.simulate(tr(one_layer("ABACB")), "lru", 2)["hits"] == 1
    # bytes per decode token: misses × 3.3 MB / tokens
    assert lru["mb_per_token"] == pytest.approx(4 * 3.3 / 5)


def test_the_prefill_warms_lru_but_is_not_counted():
    # prefill touches expert 0 of the one layer; decode reads 0 then 1, capacity 1
    t = tr([[(0,)], [(1,)]], prefill=[[(0,)]])
    s = M.simulate(t, "lru", 1)
    assert (s["hits"], s["accesses"], s["tokens"]) == (1, 2, 2)


def test_affinity_is_pinned_and_ignores_the_prefill():
    t = tr([[(0,)], [(1,)], [(0,)], [(2,)]], prefill=[[(1,)], [(2,)]])
    s = M.simulate(t, "affinity", 1, preload=[(0, 0), (0, 1)])
    assert (s["hits"], s["accesses"]) == (2, 4)          # only (0,0) fits; never admits 1 or 2
    s2 = M.simulate(t, "affinity_lru", 1, preload=[(0, 0)])
    assert s2["accesses"] == 4


def test_affinity_ranks_by_decode_count_then_prefill():
    a = tr([[(3,)], [(3,)], [(5,)]], prefill=[[(7,)], [(7,)], [(7,)]], pid="d-00")
    assert M.affinity([a], 3) == [(0, 3), (0, 5), (0, 7)]


def test_distribution_metrics():
    assert M.entropy_bits([1, 1, 1, 1]) == pytest.approx(2.0)
    assert M.entropy_bits([5]) == 0.0
    assert M.coverage([8, 1, 1], 128) == pytest.approx(1 / 128)   # one expert holds 80 %
    assert M.coverage([1] * 10, 10) == pytest.approx(0.8)
    a, b = M.Counter({1: 2, 2: 1}), M.Counter({1: 1, 3: 1})
    assert M.weighted_jaccard(a, b) == pytest.approx(1 / 4)       # min 1 / max (2+1+1)
    assert M.set_jaccard(a, b) == pytest.approx(1 / 3)
    t = tr([[(0, 1)], [(1, 2)], [(1, 2)]])
    assert M.consecutive_reuse(t) == pytest.approx((0.5 + 1.0) / 2)


def synthetic(concentrated: bool, seed: int = 1):
    """Two domains and general; L=4 layers, E=64 experts, K=4. Concentrated: each domain draws from its own 16 experts
    per layer with Zipf weights; general (and every prompt in the uniform world) draws uniformly."""
    rng = random.Random(seed)
    L, E, K = 4, 64, 4
    out = []
    for di, d in enumerate(("alpha", "beta", "general")):
        for i in range(24):
            pid = f"{d}-{i:02d}"

            def tok():
                row = []
                for layer in range(L):
                    if concentrated and d != "general":
                        pool = [(di * 20 + layer * 3 + j) % E for j in range(16)]
                        ids = set()
                        while len(ids) < K:
                            ids.add(rng.choices(pool, [1 / (j + 1) for j in range(16)])[0])
                    else:
                        ids = set(rng.sample(range(E), K))
                    row.append(tuple(sorted(ids)))
                return row
            out.append(M.make_trace(pid, d, M.half_of(pid), [tok() for _ in range(6)], [tok() for _ in range(32)]))
    return out


def test_the_gate_passes_a_concentrated_world_and_not_a_uniform_one():
    caps = {8: 24}
    conc = M.analyse(synthetic(True), n_experts=64, gbs=(8,), caps=caps)["gate"]
    assert conc["verdict"] == "PASSES", conc["reading"]
    assert conc["hit_points"] >= 0.10 and conc["bytes_fall"] >= 0.25
    assert conc["general_control"]["attributed_to"] == "domain"
    uni = M.analyse(synthetic(False), n_experts=64, gbs=(8,), caps=caps)["gate"]
    assert uni["verdict"] == "FALSIFIED"
    assert not uni["jaccard_within_gt_between"]


def test_too_few_prompts_is_void_not_a_verdict():
    few = [t for t in synthetic(True) if int(t["id"].rsplit("-", 1)[1]) < 8]
    g = M.analyse(few, n_experts=64, gbs=(8,), caps={8: 24})["gate"]
    assert g["verdict"] == "VOID"


def test_the_prompts_are_thirty_per_domain_split_in_halves_and_never_include_an_answer():
    ps = build_prompts(30)
    assert len({p["id"] for p in ps}) == len(ps) == 150
    for d in (*DOMAINS, "general"):
        x = [p for p in ps if p["domain"] == d]
        assert len(x) == 30
        assert sum(p["half"] == "A" for p in x) == 15
        for p in x:
            assert p["messages"][-1]["role"] == "user"
            assert all(m["role"] != "assistant" for m in p["messages"])


# ------------------------------------------------------------------ the hook, on a tiny random Gemma 4 MoE
def tiny_gemma4_moe():
    torch = pytest.importorskip("torch")
    tf = pytest.importorskip("transformers")
    if not hasattr(tf, "Gemma4TextConfig"):
        pytest.skip("transformers without Gemma 4")
    cfg = tf.Gemma4TextConfig(
        vocab_size=128, hidden_size=64, intermediate_size=64, num_hidden_layers=3, num_attention_heads=2,
        num_key_value_heads=1, head_dim=32, enable_moe_block=True, num_experts=8, top_k_experts=2,
        moe_intermediate_size=64, hidden_size_per_layer_input=0, vocab_size_per_layer_input=128,
        max_position_embeddings=256, sliding_window=16, layer_types=["sliding_attention"] * 2 + ["full_attention"])
    torch.manual_seed(0)
    return torch, tf.Gemma4ForCausalLM(cfg).eval(), cfg


def test_the_hook_records_k_ids_per_token_per_layer_for_prefill_and_decode():
    torch, model, cfg = tiny_gemma4_moe()
    from experiments.flash_inference.h1a import RouterRecorder
    rec = RouterRecorder(model)
    assert rec.layers == [0, 1, 2]
    P, new = 7, 6
    ids = torch.randint(0, 128, (1, P))
    with torch.no_grad():
        model.generate(ids, max_new_tokens=new, min_new_tokens=new, do_sample=False, pad_token_id=0)
    expert_ids, token_idx, phase = rec.collect(P)
    assert expert_ids.shape == (P + new - 1, 3, 2)          # the last generated token is never fed back
    assert (phase == 0).sum() == P and (phase == 1).sum() == new - 1
    assert list(token_idx) == list(range(P + new - 1))
    assert all(len(set(row)) == 2 for tok in expert_ids.tolist() for row in tok)   # K distinct ids
    # what was recorded is the router's own selection: re-run the prefill and compare with its top-k
    rec.reset()
    seen = {}
    layer0 = model.model.layers[0]
    def grab(_m, i, _o):            # a forward hook that returns a value would replace the router's output
        seen["p"] = i[0]
    h = layer0.router.register_forward_hook(grab)
    with torch.no_grad():
        model(ids)
    h.remove()
    probs = layer0.router(seen["p"])[0]
    top = torch.topk(probs, k=cfg.top_k_experts, dim=-1).indices
    assert sorted(map(sorted, top.tolist())) == sorted(map(sorted, expert_ids[:P, 0].tolist()))
    rec.remove()


def test_four_bit_experts_round_trip_and_match_the_bf16_forward():
    torch, model, cfg = tiny_gemma4_moe()
    from experiments.flash_inference.h1a import dequantize4, quantize4, quantize_experts
    w = torch.randn(3, 5, 128)
    p, s = quantize4(w)
    assert p.dtype == torch.uint8 and p.shape == (3, 5, 64) and s.shape == (3, 5, 2)
    back = dequantize4(p, s, torch.float32)
    # symmetric int4 with scale absmax/7: every error within half a step
    assert ((back - w).abs() <= s.repeat_interleave(64, -1) / 2 + 1e-6).all()

    layer = model.model.layers[0]
    x = torch.randn(5, cfg.hidden_size)
    with torch.no_grad():
        _, wts, idx = layer.router(x)
        ref = layer.experts(x, idx, wts)
    assert quantize_experts(model, "cpu") == 3
    assert type(model.model.layers[0].experts).__name__ == "QuantExperts"
    with torch.no_grad():
        got = model.model.layers[0].experts(x, idx, wts)
    # int4 absmax per group of 64: step = absmax/7 ≈ 2.5σ/7, error ≈ step/√12 ≈ 0.1σ per weight; through two
    # projections ≈ 0.2 of the output's norm — the precision any 4-bit expert store has (NF4 and MLX's affine alike)
    rel = (got - ref).norm() / ref.norm()
    assert rel < 0.3, rel


def test_a_trace_survives_the_npz_round_trip(tmp_path):
    np = pytest.importorskip("numpy")
    from experiments.flash_inference.h1a import save_trace
    ids = np.array([[[1, 2], [3, 4]], [[1, 5], [3, 6]], [[2, 5], [4, 6]]], dtype=np.uint8)   # T=3, L=2, K=2
    phase = np.array([0, 0, 1], dtype=np.uint8)
    f = tmp_path / "school" / "school-01.npz"
    save_trace(f, {"expert_ids": ids, "token_idx": np.arange(3, dtype=np.int32), "phase": phase})
    t = M.load_dir(tmp_path)[0]
    assert (t["id"], t["domain"], t["half"], t["n_prefill"]) == ("school-01", "school", "B", 2)
    assert t["prefill"] == [{1: 2, 2: 1, 5: 1}, {3: 2, 4: 1, 6: 1}]
    assert t["decode"] == [[(2, 5), (4, 6)]]
