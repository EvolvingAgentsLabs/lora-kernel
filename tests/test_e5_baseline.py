r"""E5's instrument (training/harness/e5_baseline.py): the three tool surfaces are the ones the brief names, the block sits
where each variant says, and the readings are the bands written first. Q1: $r = \mathrm{TTFT}_{full}/\mathrm{TTFT}_{pruned}$,
$r\ge 2$ COSTS, $r\le 1.2$ ABSORBED."""
import json

from training.harness import e5_baseline as e5

SURFACE = [t["function"]["name"] for t in json.loads(e5.SURFACE.read_text())]


def test_the_surfaces_and_where_the_block_sits():
    from examples.school import school_arm
    reqs = [r["request"] for r in school_arm.rows("eval")[:4]]
    pruned, full, first = (e5.prompts(v, 4) for v in e5.VARIANTS)
    assert len(SURFACE) == 54
    for i, req in enumerate(reqs):
        assert pruned[i][1]["content"].startswith(req) and not any(f"<{n}>" in pruned[i][1]["content"] for n in SURFACE[:10])
        assert full[i][1]["content"].startswith(req) and f"<{SURFACE[0]}>" in full[i][1]["content"]
        assert first[i][1]["content"].endswith(req) and f"<{SURFACE[0]}>" in first[i][1]["content"]
        assert full[i][0] == pruned[i][0] == first[i][0]                  # the system prompt is shared by all three


def test_the_readings_written_first():
    lat = lambda t, b8=100.0, h=0.0: {"ttft_b1_median_s": t, "tps_b8": b8, "prefix_hit_rate": h}
    rec = {"latency": {"pruned": lat(0.10), "full": lat(0.25, 60.0), "full_first": lat(0.11, h=0.95)},
           "mixed": {"ratio": 0.95}, "accuracy": {"pruned": {"a": {"credit": True}}, "full": {"a": {"credit": False}}}}
    r = e5.reading(rec)
    assert r["Q1"] == {"ttft_ratio": 2.5, "tps_b8_ratio": 0.6, "reading": "COSTS"}
    assert r["Q2"]["reading"] == "FREE AS A PREFIX" and r["Q3"]["reading"] == "NO MATERIAL CONTENTION"
    assert r["accuracy"] == {"pruned": "1/1", "full": "0/1"}
    rec["latency"]["full"] = lat(0.115)
    rec["latency"]["full_first"] = lat(0.11, h=0.3)
    rec["mixed"]["ratio"] = 0.8
    r = e5.reading(rec)
    assert (r["Q1"]["reading"], r["Q2"]["reading"], r["Q3"]["reading"]) == ("ABSORBED", "NOT FREE", "CONTENTION")


def test_the_prefix_cache_counters_are_read_across_vllm_names(monkeypatch):
    text = ("vllm:prefix_cache_queries_total{engine=\"0\"} 1000.0\nvllm:prefix_cache_hits_total{engine=\"0\"} 250.0\n"
            "vllm:gpu_prefix_cache_queries 10\n# HELP x\n")
    class R:
        def read(self): return text.encode()
    monkeypatch.setattr(e5.urllib.request, "urlopen", lambda *a, **k: R())
    monkeypatch.setattr(e5, "_host", lambda: "http://x")
    assert e5.prefix_cache() == {"queries": 1010.0, "hits": 250.0}
