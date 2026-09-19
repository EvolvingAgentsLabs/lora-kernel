"""W5's runner, as far as it can be checked with no GPU (docs/MEMORY.md W5; FOUNDATIONS §7.1).

The verdict pairs arms by case id with the exact two-sided sign test on discordant pairs,
p = 2 * sum_{k<=min(b,c)} C(b+c,k) 2^-(b+c), on the HEADLINE subset: held-out rows no deeper than
the deepest trained walk whose final line no other procedure states. A harness its oracle cannot
pass measures itself, so the oracle is run through the very function the model will be run through.
"""
import json

from memory.notes import Library
from training.nursing import generate_walks as gw
from training.nursing import walks_arm as wa

LIB = Library.load(gw.ROOT)
SETS = {k: [json.loads(l) for l in p.read_text().splitlines()] for k, p in wa.SETS.items()}


def oracle(row):
    def gen_for(system, user, conv=None):
        steps = iter(row["replay"]["plan"])

        def gen(prefix):
            if conv is None:
                return row["answer"]
            st = next(steps, None)
            if st is None:
                return row["answer"]
            if st[0] == "search":
                return f"<search shelf={st[1]}>{st[2]}</search>"
            return f"<calc>{st[1]}</calc>" if st[0] == "calc" else f"<open>{conv.opaque[st[1]]}</open>"
        return gen
    return gen_for


def test_the_oracle_passes_the_runner_on_every_evaluated_case_with_its_walk_read():
    for rows in SETS.values():
        for r in rows:
            rec = wa.run_case(LIB, r, "withlib", oracle(r))
            assert rec["state"] == "right" and rec["walk_ok"] and not rec["retrieval"]["miss"], rec


def test_the_headline_is_the_56_and_the_other_slices_never_fold_into_it():
    sl = wa.slices(SETS)
    assert len(sl["headline"]) == 56 and len(sl["heldout_deeper_than_trained"]) == 2
    assert len(sl["heldout_shared_line"]) == 22
    assert not set(sl["headline"]) & (set(sl["heldout_deeper_than_trained"]) | set(sl["heldout_shared_line"]))
    assert len(sl["heldout_quantity_site_or_case"]) == 17 and len(sl["heldout_quantity_textbook"]) == 6
    assert len(sl["control"]) == 60 and len(sl["control_rate"]) + len(sl["control_without_rate"]) == 60
    by_id = {r["case_id"]: r for r in SETS["heldout"]}
    assert max(by_id[i]["depth"] for i in sl["headline"]) <= wa.MAX_TRAINED_DEPTH


def test_the_control_reads_notes_the_runtime_rendered_and_is_shown_no_library_id():
    r = next(x for x in SETS["heldout"] if x["family"] == "carry" and x["meta"]["m"] > 1)
    system, user, conv = wa.served(LIB, r, "base-reads")
    assert conv is None and gw.SUB + "/" not in user
    assert user.count("<open>") >= len(r["walk"]) and r["statement"] in user
    system, user, conv = wa.served(LIB, r, "nolib")
    assert conv is None and user == r["statement"] and "<" not in user


def test_the_trivial_policy_is_a_floor_far_under_the_oracle():
    f = wa.floor(LIB, SETS)
    head = wa.summarise(f["heldout"]["records"], wa.slices(SETS)["headline"])
    assert head["scored"] == 56 and head["errors"] == 0
    assert head["credit"] <= 8, "if opening result #1 and answering the page scores, the suite prices nothing"


def _rec(pairs, base=(10, 56), g1=True):
    return {"G1": {m: {"applied": g1} for m in wa.TRAINED},
            "analysis": {"pairs": {"headline": [{"pair": k, "state": v} for k, v in pairs.items()]},
                         "summary": {a: {"headline": {"errors": 0, "missing": 0, "credit": base[0], "scored": base[1]}}
                                     for a in ("base-reads", "withlib")}}}


def test_the_verdict_is_the_specs_two_pairs_and_nothing_softer():
    both = {"withlib vs nolib": "improvement", "withlib vs base-reads": "improvement", "withlib vs base-walks": "tie"}
    assert wa.verdict(_rec(both))["passed"] is True
    for k in ("withlib vs nolib", "withlib vs base-reads"):
        for bad in ("tie", "REGRESSION"):
            v = wa.verdict(_rec({**both, k: bad}))
            assert v["passed"] is False and f"{k} is {bad}" in v["reading"]
    assert wa.verdict(_rec(both, g1=False))["passed"] is False
    lost = _rec(both); lost["analysis"]["summary"]["withlib"]["headline"]["errors"] = 1
    assert "VOID" in wa.verdict(lost)["reading"]


def test_the_headroom_session_says_stop_when_the_control_is_at_the_ceiling():
    assert "NO HEADROOM" in wa.verdict(_rec({}, base=(51, 56)))["reading"]
    assert wa.verdict(_rec({}, base=(50, 56)))["reading"].startswith("HEADROOM")
    assert wa.verdict({})["reading"] == "NOTHING SCORED"


def test_every_prefix_the_runner_prints_reaches_the_watching_terminal():
    """A chain's peek is a filter: a runner whose prefix is not in it runs in silence (CLAUDE.md §3)."""
    import pathlib
    import re
    from tests.test_chain_scripts import peek_patterns
    watched = peek_patterns(pathlib.Path("training/harness/chain_serve.sh"))
    printed = set(re.findall(r'print\(f?"\[(\w+)\]', pathlib.Path("training/nursing/walks_arm.py").read_text()))
    assert printed and printed <= watched, printed - watched


def test_the_floor_the_brief_quotes_is_the_floor_the_code_computes_today():
    import pathlib
    stored = json.loads(pathlib.Path("results/M7-W5-kill-arm-20260919/floor.json").read_text())["floor"]
    f = wa.floor(LIB, SETS)
    both = {**f["heldout"]["records"], **f["control"]["records"]}
    for k, ids in wa.slices(SETS).items():
        assert wa.summarise(both, ids)["credit"] == stored[k]["credit"], k
    brief = pathlib.Path("results/M7-W5-kill-arm-20260919/BRIEF.md").read_text()
    assert f"headline {stored['headline']['credit']} / 56" in brief and f"control {stored['control']['credit']} / 60" in brief


def test_a_record_keeps_the_whole_walk_and_the_ids_of_the_notes_it_opened():
    """A record is what a later arm replays. It kept a count and a 1500-character tail, and the
    composition arm could not prove what 6 of 140 walks had opened [ran] M7-W5b — excluded, and not
    neutrally. The longest evaluated walk must come back whole, with its notes by canonical id."""
    row = max(SETS["heldout"], key=lambda r: r["depth"])
    rec = wa.run_case(LIB, row, "withlib", oracle(row))
    assert rec["text_full"] is True and len(rec["text"]) > 1500
    assert rec["opened"] == len(rec["opened_ids"]) and all(i in LIB.notes for i in rec["opened_ids"])
    assert [i for i in row["walk"] if i in rec["opened_ids"]] == [i for i in rec["opened_ids"] if i in row["walk"]]
