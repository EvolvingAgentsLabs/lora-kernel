"""W5b — composition: the adapter's recorded walk, the bare base's final line. Zero GPU.

The arm has one unknown (who writes the last line) only if three things hold, and each is held here:
the walk is the RECORDED one, proven by replaying it through a fresh referee result by result; the
base is served exactly as `base-reads` is — byte for byte where the walk is the oracle's; and the
grader is the untouched one, reading the replayed walk. Pairs are exact two-sided sign tests on
discordant pairs, p = 2 * sum_{k<=min(b,c)} C(b+c,k) 2^-(b+c) (FOUNDATIONS §7.1).
"""
import json
import pathlib
import re

from memory.notes import Library
from training.nursing import grade_walks as gr
from training.nursing import walks_arm as wa
from training.nursing import walks_composed as wc
from training.nursing.library import ROOT

LIB = Library.load(ROOT)
SETS = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in wa.SETS.items()}
W5 = json.loads(wc.W5.read_text())
ROWS = {r["case_id"]: (s, r) for s, rows in SETS.items() for r in rows}


def _replayed():
    for cid, (s, row) in ROWS.items():
        rec = W5["arms"]["withlib"][s]["records"][cid]
        yield cid, row, rec, wc.replay(LIB, row, rec)


REPLAYED = list(_replayed())


def test_every_walk_the_record_kept_whole_replays_result_by_result():
    whole = [(cid, how) for cid, _, rec, (_, _, how) in REPLAYED if len(rec["text"]) < wc.KEPT]
    assert len(whole) == 115 and all(how == "exact" for _, how in whole)


def test_a_lost_head_is_rebuilt_only_when_it_can_be_proven_and_the_rest_is_said():
    lost = {cid: how for cid, _, rec, (pages, _, how) in REPLAYED if len(rec["text"]) >= wc.KEPT}
    assert len(lost) == 25
    assert sorted(c for c, h in lost.items() if h.startswith("unreplayable")) == [
        "w5h-012", "w5h-016", "w5h-033", "w5h-041", "w5h-045", "w5h-059"]


def test_the_replayed_walk_is_judged_as_the_record_judged_it():
    for cid, row, rec, (pages, walk, _) in REPLAYED:
        if pages is not None:
            assert gr.walk_ok(LIB, row, walk) == rec["walk_ok"], cid
            assert len(walk["opened"]) == rec["opened"] and walk["violations"] == rec["violations"], cid


def test_a_tampered_record_does_not_replay():
    cid, row, rec, _ = next(x for x in REPLAYED if x[2]["opened"] >= 2 and len(x[2]["text"]) < wc.KEPT)
    forged = dict(rec, text=re.sub(r"(</open>= )(\w)", lambda m: m.group(1) + "X" + m.group(2), rec["text"], count=1))
    assert wc.replay(LIB, row, forged)[0] is None


def test_where_the_walk_is_the_oracles_the_base_is_served_base_reads_turn_byte_for_byte():
    same, other = 0, 0
    for cid, row, rec, (pages, walk, _) in REPLAYED:
        if pages is None or set(walk["opened"]) != set(row["walk"]):
            continue
        mine, theirs = wc.served(LIB, row, pages), wa.served(LIB, row, "base-reads")[:2]
        if mine == theirs:
            same += 1
            continue
        other += 1                       # the same notes under other labels or in another order — never other notes
        body = lambda turn: {re.sub(r"First step: \w{3}$", "First step: ·", p.partition("= ")[2].splitlines()[0])
                             for p in turn[1].split("The notes:\n")[1].split("\n\n")}
        assert body(mine) == body(theirs), cid
    assert (same, other) == (95, 7)


def test_the_ceiling_the_brief_quotes_is_the_one_the_code_computes_today():
    c = wc.ceiling(LIB, SETS, W5)
    assert (c["headline"], c["replayable"], c["unreplayable"]) == (56, 54, ["w5h-012", "w5h-033"])
    assert c["ceiling_clean_walk_and_base_reads_has_credit"] == 41
    assert (c["opened_set_equals_oracle_walk"], c["prompt_identical_to_base_reads"]) == (37, 30)
    assert len(c["withlib_clean_walk_quantity_failures"]) == 12


def _scripted(final_for):
    def gen_for(system, user, conv=None):
        return lambda prefix: final_for(user)
    return gen_for


def test_a_right_line_over_a_clean_walk_earns_credit_and_over_an_unopened_note_earns_none():
    q = next(c for c in wc.ceiling(LIB, SETS, W5)["withlib_clean_walk_quantity_failures"])
    s, row = ROWS[q]
    rec = W5["arms"]["withlib"][s]["records"][q]
    good = wc.run_case(LIB, row, rec, _scripted(lambda user: row["answer"]))
    assert good["credit"] and good["state"] == "right"
    unread = ROWS["w5h-000"][1]
    r = wc.run_case(LIB, unread, W5["arms"]["withlib"]["heldout"]["records"]["w5h-000"], _scripted(lambda u: unread["answer"]))
    assert r["state"] == "unread" and not r["credit"]


def test_an_unreplayable_walk_leaves_every_slice_for_every_arm_and_the_diagnosis_can_fail():
    rec = {"arms": {a: W5["arms"][a] for a in wa.ARMS}, "ceiling": wc.ceiling(LIB, SETS, W5)}
    wrong = _scripted(lambda user: "0 minutes")
    rec["arms"]["composed"] = {s: {"records": {r["case_id"]: wc.run_case(
        LIB, r, W5["arms"]["withlib"][s]["records"][r["case_id"]], wrong) for r in rows}} for s, rows in SETS.items()}
    rec["analysis"] = wc.analyse(rec, SETS)
    assert rec["analysis"]["slices"]["headline"] == 54
    assert all(s["headline"]["n"] == 54 for s in rec["analysis"]["summary"].values())
    v = wc.verdict(rec)
    assert v["diagnosis"] == "FALSIFIED" and v["quantity_failures_left"] == "12/12"
    assert v["pairs"]["composed vs withlib"].startswith("REGRESSION")


def test_the_w5_file_is_read_and_never_written(tmp_path, monkeypatch):
    before = wc.W5.read_bytes()
    monkeypatch.setattr("sys.argv", ["x", "--ceiling", "--out", str(tmp_path / "c.json")])
    assert wc.main() == 0
    assert wc.W5.read_bytes() == before and "composed" not in json.loads(before)["arms"]


def test_every_prefix_the_runner_prints_reaches_the_watching_terminal():
    from tests.test_chain_scripts import peek_patterns
    watched = peek_patterns(pathlib.Path("training/harness/chain_serve.sh"))
    printed = set(re.findall(r'print\(f?"\[(\w+)\]', pathlib.Path("training/nursing/walks_composed.py").read_text()))
    assert printed and printed <= watched, printed - watched


def test_a_whole_walk_longer_than_the_old_tail_is_not_read_as_truncated():
    """Records written since the fix carry `text_full`; W5's own file does not and still replays."""
    import json as _json
    from memory.notes import Library as _L
    from training.nursing import generate_walks as _gw, walks_arm as _wa
    lib = _L.load(_gw.ROOT)
    rows = [_json.loads(l) for l in _wa.SETS["heldout"].read_text().splitlines()]
    row = max(rows, key=lambda r: r["depth"])

    def gen_for(system, user, conv=None):
        steps = iter(row["replay"]["plan"])

        def gen(prefix):
            st = next(steps, None)
            if st is None:
                return row["answer"]
            if st[0] == "search":
                return f"<search shelf={st[1]}>{st[2]}</search>"
            return f"<calc>{st[1]}</calc>" if st[0] == "calc" else f"<open>{conv.opaque[st[1]]}</open>"
        return gen
    rec = _wa.run_case(lib, row, "withlib", gen_for)
    assert len(rec["text"]) >= wc.KEPT
    pages, walk, how = wc.replay(lib, row, rec)
    assert pages is not None and list(walk["opened"]) == rec["opened_ids"], how
