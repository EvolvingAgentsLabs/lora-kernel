"""W5e — the referee writes the first query. Zero GPU.

The arm has one unknown (the text of the walk's first search) only if these hold, and each is held here:
the substitution touches the FIRST search and nothing else, on the shelf the expert named; a walk made
under it replays result by result, so the policy's base reads the pages that walk really opened; the
eleven rows the arm exists for are derived from W5d's record, not typed in; and the verdict can say each
of its readings. Pairs are exact two-sided sign tests on discordant pairs,
p = 2 * sum_{k<=min(b,c)} C(b+c,k) 2^-(b+c) (FOUNDATIONS §7.1).
"""
import json
import re

from memory.notes import Library
from memory.runtime import Conversation, Lexical
from training.nursing import walks_arm as wa
from training.nursing import walks_composed as wc
from training.nursing import walks_first_search as fs
from training.nursing import walks_policy as wp
from training.nursing.library import ROOT

LIB = Library.load(ROOT)
SETS = wp.load_sets(fs.DATA)
ROWS = {r["case_id"]: r for rs in SETS.values() for r in rs}
RECORDED = fs.load(json.loads(fs.W5D.read_text()))
GONE = fs.missed(SETS, RECORDED)
MEMORISED = "turning an order into a number to set on a pump or a clamp"     # W5d: 9 of the 11, verbatim


def memorised_walker(system, user, conv=None):
    """W5d's failure, scripted: the right shelf, the corpus's query for another topic, open what is listed."""
    def gen(prefix: str) -> str:
        if "</search>=" not in prefix:
            return f"<search shelf=wiki>{MEMORISED}</search>"
        listed = re.findall(r"\[(\w+)\]", prefix.split("</search>=", 1)[1].split("\n<")[0])
        opened = re.findall(r"<open>(\w+)</open>", prefix)
        todo = [i for i in listed if i not in opened]
        return f"<open>{todo[0]}</open>" if todo else "Not in my library."
    return gen


def test_only_the_first_search_is_the_statements_and_the_shelf_stays_the_experts():
    conv = Conversation(LIB, first_query="drip rate for a gravity line", log_content=True)
    conv.answer("search", f" shelf=wiki>{MEMORISED}")
    conv.answer("search", f" shelf=harness>{MEMORISED}")
    first, second = [l for l in conv.log if l["verb"] == "search"]
    assert first["substituted"] and first["written"] == MEMORISED and first["shelf"] == "wiki"
    assert first["returned"] == Lexical(LIB).search("drip rate for a gravity line", "wiki", 3)
    assert "substituted" not in second and second["arg"] == MEMORISED and second["shelf"] == "harness"


def test_unset_the_referee_is_what_it_was():
    a, b = Conversation(LIB, seed=3), Conversation(LIB, seed=3, first_query=None)
    assert a.answer("search", f" shelf=wiki>{MEMORISED}") == b.answer("search", f" shelf=wiki>{MEMORISED}")
    assert "substituted" not in a.log[0]


def test_the_eleven_are_derived_from_w5ds_record_and_are_the_eleven_it_reported():
    assert len(GONE) == 11
    assert all(ROWS[i]["family"] in wa.QUANTITY for i in GONE)
    assert all(RECORDED["withlib"][i]["retrieval"]["miss"] and not RECORDED["policy"][i]["credit"] for i in GONE)


def test_the_mechanism_can_fail_and_can_pass_on_the_same_walker():
    """Without the referee the memorised query never reaches the supplying note; with it, all eleven."""
    reached = {}
    for on in (False, True):
        recs = [wa.run_case(LIB, ROWS[i], "withlib", memorised_walker, first_query=on) for i in GONE]
        reached[on] = sum(ROWS[r["id"]]["walk"][-1] in r["opened_ids"] for r in recs)
    assert reached[False] < fs.MECHANISM_BAR and reached[False] <= 2
    assert reached[True] == 11


def test_a_walk_made_under_the_referee_replays_exactly_and_a_plain_replay_of_it_does_not():
    rows = [r for rs in SETS.values() for r in rs]
    recs = [wa.run_case(LIB, r, "withlib", wa.floor_policy, first_query=True) for r in rows]
    assert all(r["first_query"] == "statement" for r in recs)
    hows = [wc.replay(LIB, ROWS[r["id"]], r)[2] for r in recs]
    assert hows.count("exact") == len(rows)
    walker = [wa.run_case(LIB, ROWS[i], "withlib", memorised_walker, first_query=True) for i in GONE]
    stripped = [{k: v for k, v in r.items() if k != "first_query"} for r in walker]
    assert all(wc.replay(LIB, ROWS[r["id"]], r)[0] is None for r in stripped)


def _analysis(still: int, head: str, ctrl: str, misses: int = 11) -> dict:
    pair = lambda name, state: {"pair": name, "state": state, "only_a": 5, "only_b": 0, "p_value": 0.06}
    summ = {"credit": 1, "scored": 1, "errors": 0, "missing": 0}
    return {"pairs": {"headline": [pair("policy-fs vs policy", head), pair("policy-fs vs base-reads", "tie")],
                      "control": [pair("policy-fs vs policy", ctrl)]},
            "pairs_right_only": {"headline": []},
            "summary": {a: {"headline": summ, "control": summ} for a in fs.ARMS},
            "mechanism": {"misses": misses, "scored": misses, "still_not_opened": still, "falsified_at": fs.still_bar(misses)}}


def test_the_verdict_can_say_each_of_its_readings():
    g1 = {"G1": {wp.MEMBER: {"applied": True}}}
    say = lambda still, head, ctrl: fs.verdict({**g1, "analysis": _analysis(still, head, ctrl)})
    assert say(6, "improvement", "tie")["reading"].startswith("FALSIFIED")
    assert say(5, "tie", "tie")["reading"].startswith("NOT BOUGHT")
    assert say(0, "improvement", "REGRESSION")["reading"].startswith("NOT A SERVING DESIGN")
    assert fs.still_bar(11) == fs.MECHANISM_BAR
    no_room = fs.verdict({**g1, "analysis": _analysis(0, "improvement", "tie", misses=fs.MIN_MISSES - 1)})
    assert no_room["reading"].startswith("NO HEADROOM") and not no_room["passed"]
    ok = say(0, "improvement", "tie")
    assert ok["passed"] and "not the claim" in ok["reading"] and ok["stage"].startswith("ATTRIBUTION")
    assert fs.verdict({"G1": {wp.MEMBER: {"applied": False}}, "analysis": _analysis(0, "improvement", "tie")})["reading"].startswith("VOID")



def test_the_session_path_runs_end_to_end_on_scripted_arms_and_reads_the_mechanism_off_its_own_baseline():
    """The four bought arms from scripted walkers and a scripted base, through `analyse` and `verdict`."""
    def base_says(system, user, conv=None):
        return lambda prefix: "Not in my library."
    arms = {"base-reads": RECORDED["base-reads"]}
    for arm, fq in (("withlib", False), ("withlib-fs", True)):
        arms[arm] = {r["case_id"]: wa.run_case(LIB, r, "withlib", memorised_walker, first_query=fq) for r in ROWS.values()}
    for arm, walks in (("policy", "withlib"), ("policy-fs", "withlib-fs")):
        arms[arm] = {i: wp.policy_case(LIB, ROWS[i], arms[walks][i], base_says) for i in ROWS}
    assert not [i for i, r in arms["policy-fs"].items() if r.get("state") == "unreplayable"]
    a = fs.analyse(arms, SETS, GONE)
    m = a["mechanism"]
    assert m["misses"] >= fs.MIN_MISSES and set(GONE) <= set(m["miss_ids"])
    assert m["w5d_missed"]["withlib-fs"] == 11 and m["w5d_missed"]["withlib"] <= 2
    v = fs.verdict({"G1": {wp.MEMBER: {"applied": True}}, "analysis": a})
    assert v["decided"] and v["stage"].startswith("ATTRIBUTION")
