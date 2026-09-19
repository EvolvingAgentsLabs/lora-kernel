r"""Memory W3 — the radar's index, its frozen queries, and the run's verdict, with zero GPU.

s(n | q) = <e(q), e_when(n)> + beta <e(q), e_what(n)>, top k = 3 (docs/MEMORY.md §2.3);
recall@k = |{q : rank_q <= k}| / |Q|; R0 and lexical are paired on the same queries by the exact
two-sided sign test on discordant pairs, p = 2 Σ_{k<=min(b,c)} C(b+c,k) 2^-(b+c) (FOUNDATIONS §7.1).

The encoder here is `HashingEncoder`: deterministic, no semantics, never a result. No model runs
in a test, and none on this machine.
"""
import json
import pathlib
import re

import pytest

from memory.index import Index, fingerprint
from memory.notes import Library
from memory.runtime import Conversation, Lexical, Searcher
from training.harness.embed_router import HashingEncoder
from training.nursing import radar_queries, radar_r0
from training.nursing.library import ROOT

LIB = Library.load(ROOT)
SETS = radar_queries.build(LIB)


def test_a_note_is_first_for_its_own_when_line_which_is_why_that_set_is_void():
    idx = Index.build(LIB, HashingEncoder())
    for n in list(LIB.notes.values())[:20]:
        assert n.id in idx.search(n.when, None, 3)


def test_shelf_restriction_and_k():
    idx = Index.build(LIB, HashingEncoder())
    got = idx.search("drops per minute by gravity", "wiki", 3)
    assert len(got) == 3 and all(LIB[i].shelf == "wiki" for i in got)
    assert len(idx.rank_vec(HashingEncoder().encode(["x"])[0])) == len(LIB.notes)


def test_save_load_round_trip_ranks_the_same(tmp_path):
    enc = HashingEncoder()
    idx = Index.build(LIB, enc, encoder_name="hash")
    idx.save(tmp_path / "i.json")
    back = Index.load(tmp_path / "i.json", lib=LIB, encoder=enc)
    q = "how long do I press after the cannula is out"
    assert back.search(q) == idx.search(q) and back.encoder_name == "hash"


def test_a_loaded_index_without_an_encoder_refuses_a_text_query(tmp_path):
    Index.build(LIB, HashingEncoder()).save(tmp_path / "i.json")
    with pytest.raises(RuntimeError):
        Index.load(tmp_path / "i.json").search("anything")


def test_an_index_built_from_another_state_of_the_library_is_refused(tmp_path):
    Index.build(LIB, HashingEncoder()).save(tmp_path / "i.json")
    d = json.loads((tmp_path / "i.json").read_text()); d["fingerprint"] = "0" * 64
    (tmp_path / "i.json").write_text(json.dumps(d))
    with pytest.raises(ValueError):
        Index.load(tmp_path / "i.json", lib=LIB)
    assert len(fingerprint(LIB)) == 64


def test_it_is_a_searcher_and_the_runtime_takes_it_unchanged():
    idx: Searcher = Index.build(LIB, HashingEncoder())
    conv = Conversation(LIB, searcher=idx)
    text = conv.answer("search", " shelf=harness>You are about to remove a peripheral IV and have nothing in hand yet.")
    assert "nursing-iv/" not in text and "ERROR" not in text


def test_beta_zero_is_the_single_when_vector_baseline():
    idx = Index.build(LIB, HashingEncoder())
    v = HashingEncoder().encode(["The supplies IV removal needs."])[0]      # a `what` line, verbatim
    target = "nursing-iv/harness/discontinue-iv/01-gather-supplies"
    assert idx.rank_vec(v, None, 5.0).index(target) <= idx.rank_vec(v, None, 0.0).index(target)


# --- the frozen queries -------------------------------------------------------------------------

def test_p_has_one_query_per_note_and_e_one_per_question():
    assert {r["target"] for r in SETS["P"]} == set(LIB.notes) and len(SETS["P"]) == len(LIB.notes) == 94
    assert len(SETS["E"]) == 72 and len({r["target"] for r in SETS["E"]}) == 4


def test_no_query_is_a_substring_of_its_targets_fields_nor_the_reverse():
    for rows in SETS.values():
        for r in rows:
            n = LIB[r["target"]]
            for f in (n.when, n.what, n.title):
                assert r["query"].lower() not in f.lower() and f.lower() not in r["query"].lower(), r["id"]


def test_p_queries_are_distinct_and_leak_little():
    qs = [r["query"] for r in SETS["P"]]
    assert len(set(qs)) == len(qs)
    o = radar_queries.overlap_summary(SETS["P"])
    assert o["mean"] < 0.10 and o["max"] <= 0.34, o      # a regression guard on the written set, not a design knob


def test_the_stem_drops_the_options():
    assert radar_queries.stem("Which comes FIRST?\nA. one\nB. two") == "Which comes FIRST?"


# --- the run's arithmetic and verdict -------------------------------------------------------------

def test_summarise_counts_an_unranked_query_as_a_miss():
    s = radar_r0.summarise([{"rank": 1}, {"rank": 3}, {"rank": 4}, {"rank": None}])
    assert s["recall@1"] == 0.25 and s["recall@3"] == 0.5 and s["unranked"] == 1
    assert s["mrr"] == round((1 + 1 / 3 + 1 / 4) / 4, 4)


def test_the_recorded_lexical_baseline_is_what_the_code_computes_today():
    rec = json.loads(pathlib.Path("results/M7-W3-radar-r0-20260919/lexical_baseline.json").read_text())
    now = {s: radar_r0.summarise(radar_r0.lexical_ranks(LIB, rows)) for s, rows in SETS.items()}
    assert rec["summary"]["lexical"] == now and rec["headroom"]["go"] is True
    assert "encoder" not in rec and rec["lexical_only"] is True


def _rec(only_a, only_b, r0, lx=0.06, go=True):
    from training.harness import bar
    p = bar.sign_test(only_a, only_b)
    return {"headroom": {"go": go}, "pairs": {"P": {"only_a": only_a, "only_b": only_b, "different": p <= 0.05}},
            "summary": {"r0": {"P": {"recall@3": r0}}, "lexical": {"P": {"recall@3": lx}}}}


def test_verdict_needs_the_pair_and_the_absolute_standard():
    assert radar_r0.verdict(_rec(70, 1, 0.85))["passed"] is True
    v = radar_r0.verdict(_rec(40, 1, 0.50))
    assert v["passed"] is False and v["state"] == "R0" and "NOT ENOUGH" in v["reading"]
    assert radar_r0.verdict(_rec(3, 2, 0.10))["state"] == "tie"
    assert radar_r0.verdict(_rec(1, 20, 0.05, lx=0.4))["state"] == "lexical"
    assert "VOID" in radar_r0.verdict(_rec(70, 1, 0.85, go=False))["reading"]
    assert radar_r0.verdict({"headroom": {"go": True}})["passed"] is False


def test_headroom_says_no_go_at_the_ceiling():
    assert radar_r0.headroom({"P": {"recall@3": 0.96}})["go"] is False


def test_the_chain_watches_the_runners_prefix():
    body = pathlib.Path("training/harness/chain_serve.sh").read_text()
    tags = set()
    for group in re.findall(r"\(([\w|]+)\)\\\\\]", body):
        tags |= set(group.split("|"))
    printed = set(re.findall(r'print\(f?"\[(\w+)\]', pathlib.Path("training/nursing/radar_r0.py").read_text()))
    assert printed == {"radar"} and printed <= tags
