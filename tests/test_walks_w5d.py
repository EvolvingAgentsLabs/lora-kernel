"""W5d — the sets the answer policy's claim is read on: written after the freeze, new, and checked.

A case is its statement and its world (the values its notes show). Every clause that makes these sets
NEW is shown able to fail: a row W5 or W5c evaluated, an opening sentence an earlier set used, a
held-out value from an earlier pool, a statement whose kind the frozen rule misreads. The verdict they
feed is three paired exact sign tests, p = 2 * sum_{k<=min(b,c)} C(b+c,k) 2^-(b+c) (FOUNDATIONS §7.1).
"""
import copy
import json
import pathlib

from memory.notes import Library
from training.nursing import generate_walks as g1
from training.nursing import generate_walks_v2 as g2
from training.nursing import generate_walks_w5d as g5
from training.nursing import walks_arm as wa
from training.nursing.library import ROOT

LIB = Library.load(ROOT)
SETS = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in g5.FILES.items()}
RUN = pathlib.Path("results/M7-W5d-answer-policy-20260920")


def test_the_files_on_disk_are_what_the_generator_writes_and_the_older_corpora_did_not_move():
    assert g5.main(["--check"]) == 0
    assert g2.main(["--check"]) == 0 and g1.main(["--check"]) == 0


def test_the_gate_passes_and_is_the_one_on_disk():
    g = g5.gate(SETS, LIB)
    assert g["passed"] and g["sizes"] == {"eval_heldout": 89, "eval_control": 78}
    on_disk = json.loads((RUN / "gate.json").read_text())
    assert on_disk["passed"] and on_disk["sizes"] == g["sizes"]
    assert g["held_out_values_drawn"] == on_disk["held_out_values_drawn"]


def test_a_case_an_earlier_set_evaluated_is_caught():
    old = json.loads(g2.FILES["eval_heldout"].read_text().splitlines()[0])
    bad = {**SETS, "eval_heldout": SETS["eval_heldout"] + [old]}
    g = g5.gate(bad, LIB)
    assert old["case_id"] in g["G5_seen_before_by_W5_or_W5c"] and not g["passed"]


def test_an_opening_sentence_an_earlier_set_used_is_caught():
    row = copy.deepcopy(SETS["eval_heldout"][0])
    row["statement"] = g1.OPENINGS[g1.HELD_OUT][0][0] + ". " + row["statement"].split(". ", 1)[1]
    g = g5.gate({**SETS, "eval_heldout": [row] + SETS["eval_heldout"][1:]}, LIB)
    assert row["case_id"] in g["G8_opens_with_a_sentence_an_earlier_set_used"] and not g["passed"]


def test_a_statement_the_frozen_rule_misreads_is_caught():
    row = copy.deepcopy(next(r for r in SETS["eval_heldout"] if r["family"] == "conditional"))
    row["statement"] = row["statement"].replace("answer with the quantity and its unit", "tell me").replace(
        "Answer with the quantity and its unit", "Tell me")
    rows = [row if r["case_id"] == row["case_id"] else r for r in SETS["eval_heldout"]]
    g = g5.gate({**SETS, "eval_heldout": rows}, LIB)
    assert row["case_id"] in g["G9_kind_disagrees_with_the_generators_family"] and not g["passed"]


def test_a_held_out_value_from_an_earlier_pool_is_caught():
    row = copy.deepcopy(next(r for r in SETS["eval_heldout"] if r["family"] == "conditional" and r["meta"]["layer"] != "textbook"))
    row["meta"]["rules"]["hold_pressure"]["minutes"] = "7"          # W5c's pool
    rows = [row if r["case_id"] == row["case_id"] else r for r in SETS["eval_heldout"]]
    g = g5.gate({**SETS, "eval_heldout": rows}, LIB)
    assert g["G10_held_out_values_from_an_earlier_pool"] == ["7"] and not g["passed"]


def test_the_held_out_rows_are_the_procedure_the_walking_adapter_never_opened_and_stay_within_trained_depth():
    only = g1.held_out_only(LIB)
    train = [json.loads(l) for l in g2.FILES["train"].read_text().splitlines()]
    assert not any(i in only for r in train for i in r["walk"] + r["replay"]["carried"])
    assert all(r["depth"] <= wa.MAX_TRAINED_DEPTH for r in SETS["eval_heldout"])
    assert all(r["procedure"] in (None, g1.HELD_OUT) for r in SETS["eval_heldout"])


def test_both_values_of_the_held_out_note_are_asked_in_equal_shares_and_stated_both_ways():
    b = g2.balance(SETS["eval_heldout"])
    assert b["n"] == 32 and b["asked_conditional"] == 16 and b["implicit"] == 16
    assert 0.40 <= b["share_first_number"] <= 0.60


def test_the_zero_gpu_numbers_the_brief_quotes_are_the_ones_on_disk():
    z = json.loads((RUN / "zero_gpu.json").read_text())
    assert z["slices_claim"]["headline"] == 67 and z["slices_claim"]["control"] == 78
    assert (z["floor_claim"]["headline"]["credit"], z["floor_claim"]["control"]["credit"]) == (5, 8)
    assert z["ceiling_attribution"]["headline"]["ceiling"] == 56 and z["ceiling_attribution"]["control"]["ceiling"] == 75
    assert z["kinds"]["claim"] == {"heldout": {"carry": 57, "value": 32}, "control": {"carry": 32, "value": 36, "rate": 10}}


def test_the_walking_arm_is_served_the_turn_the_generator_wrote_on_every_new_row():
    for rows in SETS.values():
        for r in rows[::7]:
            system, user, conv = wa.served(LIB, r, "withlib")
            assert user == r["messages"][1]["content"] and conv is not None


def test_the_whole_pipeline_runs_on_every_new_row_with_no_model_and_the_oracle_earns_full_credit():
    """The walking arm's fresh record → replayed → the base's turn → the untouched grader. With the
    oracle walking and the oracle writing, every policy record is `right`; with a base that answers
    nonsense, no value row has credit and every adapter-written row keeps the adapter's."""
    from tests.test_walks_arm import oracle
    from training.nursing import answer_policy as ap
    from training.nursing import walks_policy as wp
    base_right = lambda row: (lambda system, user, conv=None: (lambda prefix: row["answer"]))
    nonsense = lambda system, user, conv=None: (lambda prefix: "0 furlongs")
    for rows in SETS.values():
        for r in rows:
            walked = wa.run_case(LIB, r, "withlib", oracle(r))
            assert walked["credit"] and walked["text_full"], r["case_id"]
            got = wp.policy_case(LIB, r, walked, base_right(r))
            assert got["credit"] and got["state"] == "right", (r["case_id"], got)
            assert got["written_by"] == ap.writer(r["statement"])
            if got["written_by"] == "base":
                assert got["replayed"] == "exact" and got["prompt_is_base_reads"]
                assert not wp.policy_case(LIB, r, walked, nonsense)["credit"]
