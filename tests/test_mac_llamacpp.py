r"""MAC2's pure parts (examples/mac/llamacpp_spec_lora.py): the server command, the summary, the verdict written first.
Speed-up is pooled tokens over pooled time, $\sum n/\sum(n/\mathrm{tps})$, never a mean of rates."""
from examples.mac import llamacpp_spec_lora as m

FILES = {k: f"/g/{v}" for k, v in m.FILES.items()}


def test_the_lora_is_loaded_unapplied_and_the_draft_goes_where_the_config_says():
    cmd = m.server_cmd(FILES["target"], "pair", FILES, FILES["lora"])
    assert cmd[cmd.index("--lora") + 1] == FILES["lora"] and "--lora-init-without-apply" in cmd
    assert cmd[cmd.index("-md") + 1] == FILES["pair"] and "draft-simple" in cmd
    mtp = m.server_cmd(FILES["target"], "mtp", FILES, None)
    assert mtp[mtp.index("-md") + 1] == FILES["mtp"] and "--lora" not in mtp


def _runs(tps_spec, acc=(3, 4), same=True):
    r = lambda t, text="a": {"text": text, "tokens": 100, "tps": t}
    runs = {}
    for e in ("base", "lora"):
        for s in ("domain", "general"):
            runs[f"nospec/{e}/{s}"] = [r(10.0, "x" if e == "lora" and s == "domain" else "a") for _ in range(6)]
            runs[f"mtp/{e}/{s}"] = [{**r(tps_spec, "x" if e == "lora" and s == "domain" else ("a" if same else "b")),
                                     "draft_n": acc[1], "draft_accepted": acc[0]} for _ in range(6)]
    return runs


def test_the_summary_reads_speedup_acceptance_identity_and_g1():
    s = m.summarise({"runs": _runs(14.0)})
    assert s["mtp/lora/domain"] == {"tps": 14.0, "tps_nospec": 10.0, "speedup": 1.4, "acceptance": 0.75, "identical": "6/6"}
    assert s["G1"] == "6/6 domain texts differ from the base"


def test_the_verdict_needs_the_lora_the_swap_and_the_bar():
    swap = {"expert_differs": True, "base_restored": True}
    rec = {"runs": _runs(14.0), "swap": swap}
    rec["summary"] = m.summarise(rec)
    assert m.verdict(rec).startswith("llama.cpp becomes the edge engine")
    rec["summary"] = m.summarise({"runs": _runs(12.0)})
    assert m.verdict(rec).startswith("MLX stays")
    rec["swap"] = {**swap, "base_restored": False}
    assert m.verdict(rec).startswith("NOT the edge engine")
    rec["summary"]["G1"] = "3/6 domain texts differ from the base"
    assert m.verdict(rec).startswith("VOID for the LoRA")
