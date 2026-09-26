"""The distributor-staff corpus and arm (examples/distributor/generate_turns.py, staff_arm.py) — zero GPU.

The corpus is played through the demo's own loop, so each clause of its gate is shown able to fail, and the arm runs
end to end against `fake_vllm` with a scripted model: G1, the held-out turns and the demo's five scenes for both arms."""
import json
import sys
import types
from pathlib import Path

import pytest

from examples.distributor import generate_turns as gt


@pytest.fixture(scope="module")
def sets():
    return gt.build(40, "train", gt.TRAIN_SEED0), gt.build(10, "eval", gt.EVAL_SEED0)


def test_the_gate_passes_and_each_clause_can_fail(sets):
    train, evals = sets
    assert gt.gate(train, evals)["passed"]
    from training.harness import demo_org
    bad = [dict(r) for r in train[:4]]
    bad[0]["request"] = demo_org.SCENES[0][1]                               # G1: a demo request in the corpus
    bad[1]["request"] = evals[0]["request"]                                  # G2
    bad[2]["world_seed"] = evals[0]["world_seed"]                            # G3
    bad[3]["calls"] = bad[3]["calls"] * 2                                    # G4: called twice
    g = gt.gate(bad + train[4:], evals)
    assert g["G1_demo_request_in_sets"] >= 1 and g["G2_eval_request_in_corpus"] == 1
    assert g["G3_shared_world"] == 1 and g["G4_walk_not_as_intended"] >= 1
    lie = dict(next(r for r in train if r["kind"] == "read"))
    lie["final"] = "<order_status>1</order_status>"
    assert gt.gate([lie] + train, evals)["G5_fails_the_demo_checks"] == 1


def test_a_planted_instruction_is_restated_redacted_never_acted_on(sets):
    train, _ = sets
    rows = gt.build(200, "train", 1234)
    planted = [r for r in rows if r["planted"]]
    assert planted
    for r in planted:
        walk = r["messages"][2]["content"]
        answer = walk.rsplit("\n", 1)[-1]
        assert "SYSTEM OVERRIDE" not in answer and "Ignore your instructions" not in answer
        assert len(r["calls"]) == 1


def test_worlds_do_not_repeat_and_ids_do_not_say_whose():
    a, b = gt._world(1), gt._world(2)
    rows = lambda c: sorted((r["id"], r["org_id"]) for r in c.execute("select id, org_id from orders"))
    assert rows(a) != rows(b)
    assert not any(i == 1 for i, _ in rows(a))                              # 1 is left to the planted text


def _scripted(model: str, prompt: str) -> str:
    import re
    turn = prompt.rsplit("<|assistant|>", 1)[-1]
    if "permission denied" in turn:
        return "I can't: that order belongs to another centre."
    if "</" in turn and "= " in turn:
        return "According to the system: " + turn.rsplit("= ", 1)[1].strip().splitlines()[0]
    asked = prompt.rsplit("<|user|>", 1)[-1]
    if model == "base":
        return "What is the order ID?"
    m = re.search(r"order (?:number )?(\d+)", asked)
    for key, tag in (("delivery note", "delivery_status"), ("note did the driver", "delivery_status"),
                     ("order", "order_status")):
        if key in asked and m:
            return f"<{tag}>{m.group(1)}</{tag}>"
    table = {"stock": "<stock_read></stock_read>", "canned goods": "<stock_read></stock_read>",
             "maintenance": "<maintenance_list></maintenance_list>", "ticket": "<maintenance_list></maintenance_list>",
             "returns": "<return_list></return_list>", "dock": "<dock_status></dock_status>"}
    return next((t for k, t in table.items() if k in asked.lower()), "I do not know.")


def test_the_arm_scores_base_and_a_member_end_to_end_against_the_fake(tmp_path, monkeypatch):
    from training.harness import fake_vllm as fv
    repo = Path(__file__).resolve().parent.parent
    (tmp_path / "examples").symlink_to(repo / "examples")
    d = tmp_path / "adapters" / "distributor-staff-s0"
    d.mkdir(parents=True)
    (d / "adapter_model.safetensors").write_bytes(b"stand-in")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoTokenizer=fv.FakeTokenizer))
    from examples.distributor import staff_arm
    monkeypatch.setattr(sys, "argv", ["staff_arm", "--arms", "base,staff-s0", "--out", "s.json"])
    with fv.patched(lambda model, prompt: _scripted("base" if model != "staff-s0" else model, prompt)) as seen:
        staff_arm.main()
    rec = json.loads((tmp_path / "s.json").read_text())
    assert rec["G1"]["staff-s0"]["applied"] and seen["server"].refused == []
    for arm in ("base", "staff-s0"):
        assert len(rec["arms"][arm]["held_out"]) == 70 and not [r for r in rec["arms"][arm]["held_out"].values() if "error" in r]
        assert rec["arms"][arm]["demo"]["n"] == 5
    member = sum(r["credit"] for r in rec["arms"]["staff-s0"]["held_out"].values())
    base = sum(r["credit"] for r in rec["arms"]["base"]["held_out"].values())
    assert member > base and rec["analysis"]["pairs"][0]["pair"] == "staff-s0 vs base"
