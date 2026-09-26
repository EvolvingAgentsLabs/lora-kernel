"""B4's runner end to end against the fake server — acceptance of the small member's spans, two arms. Zero GPU.

`pair_accept` asks vLLM for `prompt_logprobs` over each span the small member WROTE and counts rank-1 tokens as
accepted. Here the fake marks every token rank-1 for the large + LoRA and every other token rank-2 for the bare large:
the runner must read that as an improvement, pooled and per record, and must score only the spans, never the referee's
results between them.
"""
import json
import sys
import types

from training.harness import fake_vllm as fv
from training.wiki import wiki_arm as wa


def test_pair_accept_reads_acceptance_per_arm_and_the_lora_wins(tmp_path, monkeypatch):
    from training.harness import pair_accept
    rows = wa.load_rows("eval")[:4]
    recs = {}
    for r in rows:
        tag, ans = f"<search shelf=wiki>{r['question']}</search>", "Not in my library."
        text = f"{tag}= 1 note\n  [abc] page · X — when: y\n{ans}"
        recs[r["case_id"]] = {"id": r["case_id"], "text": text,
                              "spans": [{"at": 0, "text": tag}, {"at": text.index(ans), "text": ans}]}
    drafts = tmp_path / "d.json"
    drafts.write_text(json.dumps({"arms": {"withlib-s1": recs}}))
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoTokenizer=fv.FakeTokenizer))
    monkeypatch.setattr(sys, "argv", ["pair_accept", "--member", "large-wiki=adapters/x", "--drafts",
                                      f"{drafts}:withlib-s1:eval", "--out", str(tmp_path / "o.json")])
    rank = lambda model, i: 1 if model == "large-wiki" or i % 2 == 0 else 2
    with fv.patched(rank=rank) as seen:
        pair_accept.main()
    out = json.loads((tmp_path / "o.json").read_text())
    assert out["G1"]["applied"] and seen["server"].refused == []
    v = out["verdict"]
    assert v["records"] == 4 and v["lora_higher"] == 4 and v["pooled_alpha"]["large+lora"] == 1.0
    assert v["pooled_alpha"]["large"] < 1.0
    assert all(r["tokens"] > 0 and r["errors"] == 0 for r in out["arms"]["large"].values())
