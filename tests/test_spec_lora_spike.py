"""F0's arithmetic, zero GPU: vLLM's spec-decode counters read into α, mean accepted length and per-position rates, and
the comparison against `nospec` (identical texts at temperature 0, speed-up in tokens/s)."""
from training.harness import spec_lora_spike as s


def test_acceptance_is_read_from_counter_deltas():
    before = {"vllm:spec_decode_num_drafts_total": 10, "vllm:spec_decode_num_draft_tokens_total": 40,
              "vllm:spec_decode_num_accepted_tokens_total": 20, "per_pos": {"0": 8, "1": 6, "2": 4, "3": 2}}
    after = {"vllm:spec_decode_num_drafts_total": 20, "vllm:spec_decode_num_draft_tokens_total": 80,
             "vllm:spec_decode_num_accepted_tokens_total": 50, "per_pos": {"0": 17, "1": 14, "2": 11, "3": 8}}
    a = s.acceptance(before, after)
    assert a["alpha"] == 0.75 and a["mean_accepted_length"] == 4.0 and a["per_position"] == {"0": 0.9, "1": 0.8, "2": 0.7, "3": 0.6}
    assert s.acceptance(after, after) is None                        # nothing drafted: no rate, not a zero


def test_the_comparison_reports_identity_and_speedup_against_nospec():
    run = lambda texts, b1, b8, acc=None: {"texts": texts, "b1_tokens_per_s": b1, "b8_tokens_per_s": b8, "acceptance_b1": acc}
    rec = {"configs": {"nospec": {"started": True, "runs": {"lora/domain": run(["a", "b"], 40, 200)}},
                       "mtp": {"started": True, "runs": {"lora/domain": run(["a", "c"], 90, 300, {"alpha": 0.7, "mean_accepted_length": 3.1})}},
                       "eagle3": {"started": False, "why": ["not supported"]}}}
    c = s.compare(rec)
    assert c["mtp"]["lora/domain"] == {"identical_to_nospec": "1/2", "speedup_b1": 2.25, "speedup_b8": 1.5,
                                       "alpha": 0.7, "mean_accepted_length": 3.1}
    assert "eagle3" not in c


def test_the_metrics_parser_sums_label_sets_and_keys_positions(monkeypatch):
    text = "\n".join(['# HELP x', 'vllm:spec_decode_num_drafts_total{model_name="m",engine="0"} 5.0',
                      'vllm:spec_decode_num_drafts_total{model_name="m",engine="1"} 3.0',
                      'vllm:spec_decode_num_accepted_tokens_per_pos_total{model_name="m",position="0"} 4.0',
                      'vllm:num_requests_running{model_name="m"} 1.0'])

    class R:
        def read(self):
            return text.encode()
    monkeypatch.setattr(s.urllib.request, "urlopen", lambda *a, **k: R())
    m = s.metrics()
    assert m["vllm:spec_decode_num_drafts_total"] == 8.0 and m["per_pos"] == {"0": 4.0}
