"""W4 — the corpus of the navigation habit (docs/MEMORY.md §4, §10), and that its gate can fail.

The gate, per row r with V(r) the values its walk reads off a slot or a <calc> and N(r) the numbers
its statement states:

    G1  V(r) ∩ N(r) = ∅                      nothing a note supplies is in the question (P15, P21)
    G2  sig(e) ∉ sig(C), case(e) ∉ case(C)    no evaluated walk, nor its case, in the corpus
    G3  opened(r) ∩ H = ∅  for r in C         the held-out sibling is never walked
    G4  replay_strict(r) reproduces r         every row is a walk the referee accepts, byte for byte

A gate that cannot fail is a constant, so each clause is broken once below.
"""

import copy
import json
import random

import pytest

from memory import prompt
from memory.notes import Library
from memory.runtime import Conversation
from training.nursing import generate_walks as gw

LIB = Library.load(gw.ROOT)
SETS = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in gw.FILES.items()}


@pytest.fixture(scope="module")
def committed():
    return gw.gate(copy.deepcopy(SETS), LIB)


def _gate_with(**changed):
    sets = {k: changed.get(k, v) for k, v in SETS.items()}
    return gw.gate(sets, LIB)


def test_the_committed_corpus_passes_its_gate(committed):
    assert committed["passed"], {k: committed[k] for k in committed if k.startswith("G")}
    assert committed["rows"]["train"] == committed["rows"]["train_nolib"] == gw.N_ROWS
    assert committed["tokens_proxy"]["max"] <= gw.PROXY_LIMIT


def test_the_files_on_disk_are_what_the_generator_writes():
    assert gw.main(["--check"]) == 0


def test_the_held_out_split_is_the_procedure_its_steps_and_the_wiki_only_it_uses():
    only = gw.held_out_only(LIB)
    assert gw.HELD_OUT in only and set(LIB.walk(gw.HELD_OUT)) <= only
    assert f"{gw.W}/removal" in only and f"{gw.W}/removal/pressure-after-removal" in only
    # shared with the trained procedures, so trainable: a note is not the held-out's for being used by it
    assert f"{gw.W}/asepsis/hand-hygiene" not in only
    assert not any(p in only or set(LIB.walk(p)) & only for p in gw.TRAINED)


def test_the_generator_refuses_a_corpus_walk_through_the_held_out_procedure():
    c = gw.carry_case(LIB, random.Random(1), "x", gw.HELD_OUT, 0, 2, dead_rate=0.0)
    with pytest.raises(gw.HeldOut):
        gw.check_not_held_out(LIB, c)
    assert all(not (set(r["walk"] + r["replay"]["carried"]) & gw.held_out_only(LIB)) for r in SETS["train"])


def test_g1_fails_when_a_statement_states_a_value_the_walk_reads():
    rows = copy.deepcopy(SETS["train"])
    r = next(r for r in rows if r["family"] == "quantity" and r["meta"]["layer"] != "textbook")
    r["statement"] += f" (it is {r['check']['value']}.)"
    assert gw.leaks(r)
    g = _gate_with(train=rows)
    assert not g["passed"] and r["case_id"] in g["G1_value_in_statement"]


def test_g2_fails_when_an_evaluated_case_is_in_the_corpus():
    rows = copy.deepcopy(SETS["train"]) + [copy.deepcopy(SETS["eval_control"][0])]
    g = _gate_with(train=rows, train_nolib=SETS["train_nolib"] + [gw.nolib_row(rows[-1])])
    assert not g["passed"] and SETS["eval_control"][0]["case_id"] in g["G2_evaluated_walk_in_corpus"]


def test_g3_fails_when_a_corpus_row_opens_a_held_out_note():
    rows = copy.deepcopy(SETS["train"]) + [copy.deepcopy(SETS["eval_heldout"][0])]
    g = _gate_with(train=rows, train_nolib=SETS["train_nolib"] + [gw.nolib_row(rows[-1])])
    assert not g["passed"] and rows[-1]["case_id"] in g["G3_held_out_opened"]


def test_g4_fails_on_one_changed_byte_and_on_a_skipped_step():
    rows = copy.deepcopy(SETS["train"])
    a = next(r for r in rows if r["family"] == "carry" and r["depth"] >= 3)
    a["messages"][2]["content"] = a["messages"][2]["content"].replace("next ", "next  ", 1)
    assert "the assistant turn is not what the runtime renders today" in gw.replay(LIB, a)
    b = next(r for r in rows if r["family"] == "carry" and r["variant"] == "middle" and r["depth"] >= 3 and r is not a)
    opens = [i for i, s in enumerate(b["replay"]["plan"]) if s[0] == "open"]
    del b["replay"]["plan"][opens[0]]                       # skip a step: the next one's id was never shown
    assert gw.replay(LIB, b)
    b2 = copy.deepcopy(next(r for r in SETS["train"] if r["variant"] == "middle" and r["depth"] >= 2))
    b2["replay"]["carried"] = b2["replay"]["carried"][:-1]  # the record is one step short: strict cuts the walk
    assert any("guard" in w or "refused" in w or "never offered" in w for w in gw.replay(LIB, b2))


def test_every_row_is_served_the_members_own_prompt_and_shows_no_library_id():
    block = prompt.block()
    for name in ("train", "eval_heldout", "eval_control"):
        for r in SETS[name]:
            system, user, assistant = (m["content"] for m in r["messages"])
            assert system == prompt.SYSTEM and user.endswith("\n\n" + block) and user.startswith(r["statement"])
            assert f"{gw.SUB}/" not in user + assistant
            assert "<think>" not in assistant


def test_ids_are_redrawn_so_no_id_can_be_memorised():
    first = {}
    for r in SETS["train"]:
        for note, shown in zip(r["walk"], __import__("re").findall(r"<open>(\w+)</open>", r["messages"][2]["content"])):
            first.setdefault(note, set()).add(shown)
    often = [ids for ids in first.values() if len(ids) >= 5]
    assert often and all(len(ids) >= 5 for ids in often)
    assert max(len(ids) for ids in first.values()) > 20      # a note opened often is opened under many ids


def test_the_corpus_has_every_family_every_depth_dead_ends_and_the_empty_library_answer(committed):
    assert set(committed["families"]) == {"carry", "quantity", "rate", "none"}
    assert {"0", "1", "2", "3", "5", "8"} <= {str(k) for k in committed["depth_mix_opens"]}
    assert committed["dead_ends"] > 0 and committed["not_in_my_library"] >= 0.08 * gw.N_ROWS
    assert committed["variants"]["carry/start"] and committed["variants"]["carry/middle-find"]
    assert all(committed["layers"][l] for l in ("site", "case", "textbook"))
    for r in SETS["train"]:
        if r["dead_end"]:                                    # a detour, never a violation: a wrong note, then a new search
            kinds = [s[0] for s in r["replay"]["plan"]]
            assert kinds[:3] == ["search", "open", "search"] and r["replay"]["plan"][1][1] not in r["walk"][1:]


def test_the_no_library_arm_is_the_same_cases_with_no_verbs_and_no_page():
    for a, b in zip(SETS["train"], SETS["train_nolib"]):
        assert a["case_id"] == b["case_id"] and a["answer"] == b["answer"] == b["messages"][2]["content"]
        assert b["messages"][1]["content"] == a["statement"] and "<" not in b["messages"][1]["content"]
        assert b["messages"][0]["content"] == prompt.SYSTEM_NO_LIBRARY


def test_the_evaluation_sets_are_walks_with_their_oracle_and_the_held_out_one_is_all_held_out():
    only = gw.held_out_only(LIB)
    for r in SETS["eval_heldout"]:
        assert r["walk"] and set(r["walk"]) & only and not r["dead_end"]
        assert gw.verify(r["check"], r["answer"]) and "final_is_a_shared_line" in r["meta"]
    assert 0 < sum(r["meta"]["final_is_a_shared_line"] for r in SETS["eval_heldout"]) < len(SETS["eval_heldout"])
    for r in SETS["eval_control"]:
        assert not (set(r["walk"]) & only) and gw.verify(r["check"], r["answer"])
    reserved = gw.reserved_windows(LIB)
    assert not any((r["procedure"], r["meta"]["k"], r["meta"]["m"]) in reserved
                   for r in SETS["train"] if r["family"] == "carry")


def test_verify_reads_the_value_not_the_phrasing():
    assert gw.verify({"kind": "value", "value": "15", "unit": "seconds"}, "Cleanse for 15 seconds.")
    assert not gw.verify({"kind": "value", "value": "15", "unit": "seconds"}, "5 seconds")
    assert gw.verify({"kind": "value", "value": "3 to 5", "unit": "mL"}, "3 to 5 mL")
    assert gw.verify({"kind": "value", "value": "42", "unit": "drops per minute", "tolerance": 1}, "41 drops per minute")
    assert not gw.verify({"kind": "value", "value": "42", "unit": "drops per minute", "tolerance": 1}, "50 drops per minute")
    assert gw.verify({"kind": "none"}, "Not in my library.") and not gw.verify({"kind": "none"}, "Gather supplies.")


def test_resume_renders_the_last_page_as_an_open_would_and_lets_the_walk_go_on():
    steps = LIB.walk(gw.TRAINED[0])
    a = Conversation(LIB, seed=3)
    a.answer("search", f" shelf=harness>{LIB[gw.TRAINED[0]].when}")
    a.answer("open", ">" + a.opaque[gw.TRAINED[0]])
    a.answer("open", ">" + a.opaque[steps[0]])
    page_a = a.answer("open", ">" + a.opaque[steps[1]])
    b = Conversation(LIB, seed=4)
    page_b = b.resume(steps[:2])
    assert page_b.startswith(f"<open>{b.opaque[steps[1]]}</open>= ")
    assert page_a.splitlines()[0] == page_b.split("= ", 1)[1].splitlines()[0]      # the same body…
    assert len(page_a.splitlines()) == len(page_b.splitlines())                     # …and the same links
    assert not b.answer("open", ">" + b.opaque[steps[2]]).startswith("ERROR") and not b.guard.violations
    with pytest.raises(RuntimeError):
        b.resume(steps[:1])
    assert Conversation(LIB).resume([]) == ""
