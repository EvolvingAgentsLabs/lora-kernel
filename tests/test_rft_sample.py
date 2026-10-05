r"""RFT0's sampler, zero GPU (training/wiki/rft_sample.py; results/RFT0-rejection-sampling-20261005/BRIEF.md).

A walk enters the corpus iff the strict grader says `right` — $\mathrm{keep}(w) \iff \mathrm{grade}(w) = \mathrm{right}$ —
at most `MAX_KEEP` distinct walks per question; its loss spans are walk_rows' (the model's own text, nothing the runtime
wrote); and the corpus is REAL4's `train_real_none.jsonl` byte for byte before the first self-walk. The S2 reading is the
exact two-sided sign test on discordant pairs, $p = 2\sum_{k \le \min(b,c)} \binom{b+c}{k} 2^{-(b+c)}$ (FOUNDATIONS §7.1).
"""
import json
import re

import pytest

from memory.notes import Library
from memory.runtime import FullText
from training.wiki import grade as gr
from training.wiki import real_corpus as rc
from training.wiki import rft_sample as rs


@pytest.fixture(scope="module")
def lib_ft():
    lib = Library.load("knowledge/regs-train")
    return lib, FullText(lib)


def _title(page_id: str) -> str:
    return page_id.rsplit("/", 1)[1].replace("-", ".")


def _reachable_one_hop(lib, ft, n=1):
    """One-hop training questions whose supporting page the served entry lists, so a script can open it by title."""
    out = []
    for i, q in enumerate(rs.questions()):
        if q.get("none") or q["hops"] != 1:
            continue
        row = rs.question_row(q, i)
        conv = rs.served_conversation(lib, ft, row)
        res = conv.answer("search", " shelf=wiki>x")
        if re.search(r"\[[a-z0-9]{3}\] page · " + re.escape(_title(q["support"][0])) + " ", res):
            others = [s.anchor for s in lib[q["support"][0]].statements if s.anchor != q["support"][1]]
            if others:
                out.append((i, q, others[0]))
        if len(out) == n:
            return out
    return out


def _script(q, plan_for_seed):
    """A scripted member: search (its words vary by seed), open the supporting page by its title, open the statement it
    will cite, end with `value [id§anchor]` — the anchor (or a refusal) chosen per seed by `plan_for_seed`."""
    def gen_for(system, user, walking, temperature=0.0, seed=None):
        mode = plan_for_seed(seed)

        def gen(prefix):
            if "</search>" not in prefix:
                return f"<search shelf=wiki>rules {seed}</search>"
            if mode == "refuse":
                return "Not in my library."
            m = re.search(r"\[([a-z0-9]{3})\] page · " + re.escape(_title(q["support"][0])) + " ", prefix)
            pid = m.group(1)
            if f"<open>{pid}</open>" not in prefix:
                return f"<open>{pid}</open>"
            anchor = mode
            if f"<open>{pid}§{anchor}</open>" not in prefix:
                return f"<open>{pid}§{anchor}</open>"
            return f"{' '.join(q['tokens'])} [{pid}§{anchor}]"
        return gen
    return gen_for


def test_a_walk_is_accepted_only_when_the_strict_grader_says_right(lib_ft):
    lib, ft = lib_ft
    (i, q, other), = _reachable_one_hop(lib, ft)
    right = q["support"][1]
    # seed 1 right · seed 2 another statement of the same page · seed 3 refuses an answerable question · seed 4 right
    rec = rs.sample_question(lib, ft, q, i, _script(q, {1: right, 2: other, 3: "refuse", 4: right}.get))
    states = {w["seed"]: w["state"] for w in rec["walks"]}
    assert states[1] == "right" and states[4] == "right" and states[2] != "right" and states[3] == "wrong"
    assert [r["seed"] for r in rec["accepted"]] == [1, 4]
    assert all(r["grade"] == "right" for r in rec["accepted"])
    # the targeted failure is counted where it happens: the right page, another statement on it
    assert next(w for w in rec["walks"] if w["seed"] == 2)["same_page_wrong"] is True
    # and the grade the sampler recorded is the strict grader's own, re-read from the kept text
    for r in rec["accepted"]:
        assert r["check"]["cite"] == "support" and gr.final_line(r["messages"][2]["content"]).endswith(f"§{right}]")


def test_an_unanswerable_question_is_accepted_only_on_a_refusal(lib_ft):
    lib, ft = lib_ft
    qs = rs.questions()
    i, q = next((i, q) for i, q in enumerate(qs) if q.get("none"))
    assert rs.question_row(q, i)["case_id"].startswith("real3-train-none-")

    def gen_for(system, user, walking, temperature=0.0, seed=None):
        def gen(prefix):
            if "</search>" not in prefix:
                return f"<search shelf=wiki>q{seed}</search>"
            return "Not in my library." if seed in (1, 2) else "About 30 days. [zzz§a]"
        return gen
    rec = rs.sample_question(lib, ft, q, i, gen_for)
    assert [w["state"] for w in rec["walks"]] == ["right", "right", "wrong", "wrong"]
    assert [r["seed"] for r in rec["accepted"]] == [1, 2]


def test_at_most_two_distinct_walks_per_question(lib_ft):
    lib, ft = lib_ft
    (i, q, _), = _reachable_one_hop(lib, ft)
    always = _script(q, lambda seed: q["support"][1])
    rec = rs.sample_question(lib, ft, q, i, always)
    assert sum(w["state"] == "right" for w in rec["walks"]) == 4 and len(rec["accepted"]) == rs.MAX_KEEP == 2
    # four right walks with the SAME text are one walk, not two
    same = rs.sample_question(lib, ft, q, i, lambda s, u, w, temperature=0.0, seed=None: always(s, u, w, seed=0))
    assert sum(w["state"] == "right" for w in same["walks"]) == 4 and len(same["accepted"]) == 1


def test_spans_are_recorded_exactly_as_walk_rows_records_them(lib_ft):
    """The oracle's served walk (walk_rows under page_top=8), replayed as if the member wrote it: the sampler's row has
    walk_rows' messages and train_spans, byte for byte."""
    lib, ft = lib_ft
    qs = rs.questions()[:8]
    oracle = [r for r in rc.walk_rows(qs, 8, 0) if r["grade"] == "right"]
    assert len(oracle) >= 4
    for r in oracle:
        i = int(r["case_id"].rsplit("-", 1)[1])
        wrote = [r["messages"][2]["content"][a:b] for a, b in r["train_spans"]]

        def gen_for(system, user, walking, temperature=0.0, seed=None, wrote=wrote):
            it = iter(wrote)
            return lambda prefix: next(it, "")
        rec = rs.sample_question(lib, ft, qs[i], i, gen_for, seeds=(1,))
        assert rec["walks"][0]["state"] == "right", rec["walks"]
        got = rec["accepted"][0]
        assert got["messages"] == r["messages"] and got["train_spans"] == r["train_spans"]
        assert got["case_id"] == r["case_id"] + "-rft-s1" and got["check"] == r["check"]


def test_a_span_the_runtime_answered_with_an_error_stays_out_of_the_loss():
    parts = ["<open>20</open>", "= ERROR: unknown id 20\n", "<open>ab1</open>", "= page\n", "12 days [ab1§a]"]
    text, at = "".join(parts), [0]
    for p in parts:
        at.append(at[-1] + len(p))
    spans = [{"at": at[0], "text": parts[0]}, {"at": at[2], "text": parts[2]}, {"at": at[4], "text": parts[4]},
             {"at": at[5], "text": ""}]
    got, masked = rs.train_spans({"text": text, "spans": spans})
    assert masked == 1 and got == [[at[2], at[3]], [at[4], at[5]]]


def test_the_corpus_starts_with_real4s_corpus_byte_for_byte_and_the_gate_reads_it(lib_ft):
    lib, ft = lib_ft
    picks = _reachable_one_hop(lib, ft, n=2)
    assert len(picks) == 2
    records = {}
    for i, q, other in picks:
        x = rs.sample_question(lib, ft, q, i, _script(q, {1: q["support"][1], 2: q["support"][1], 3: other, 4: "refuse"}.get))
        records[x["id"]] = x
    rec = {"questions": records}
    text, g = rs.assemble(rec)
    base = rs.BASE_CORPUS.read_bytes()
    assert text.encode()[:len(base)] == base
    tail = [json.loads(l) for l in text.encode()[len(base):].decode().splitlines()]
    assert len(tail) == 4 and all(r["source"] == "rft" and r["grade"] == "right" for r in tail)
    # coverage first: one walk of each question before any question's second
    assert len({r["of"] for r in tail[:2]}) == 2
    assert g["G1_eval_library_in_corpus"] == 0 and g["G2_eval_question_in_corpus"] == 0 and g["G3_not_verified"] == 0
    assert g["self_rows"] == 4 and g["base_rows"] == len(base.decode().splitlines()) and g["self_not_right"] == 0
    assert g["by_kind"]["one_hop"] == {"questions": 2, "covered": 2, "walks": 8, "right": 4, "accepted": 4}
    assert g["acceptance_rate"] == 0.5 and g["walks_same_page_wrong"] == 2
    # a partial sample never passes: every training question must have been sampled
    assert g["questions_sampled"] == 2 and not g["passed"]
    # the cap keeps coverage: with room for 2, one walk per question
    capped, g2 = rs.assemble(rec, max_self=2)
    assert g2["self_rows"] == 2 and g2["capped"] == 2
    assert len({json.loads(l)["of"] for l in capped.encode()[len(base):].decode().splitlines()}) == 2
    # a row that is not right, slipped into a record, fails the gate
    bad = json.loads(json.dumps(rec))
    next(iter(bad["questions"].values()))["accepted"][0]["grade"] = "unverified"
    assert rs.assemble(bad)[1]["self_not_right"] == 1 and rs.assemble(bad)[1]["G3_not_verified"] == 1


def test_the_gate_keeps_every_measured_set_out():
    """G1/G2 read the same evaluation files real_corpus' corpora were gated against, PAGE0's (where S2 scores) among them."""
    names = {p.parent.name for p in rc.EVAL_FILES}
    assert {"PAGE0-page-top-20261002", "CITE0-runtime-check-20261002", "REAL4-refusal-20260930",
            "REAL5-third-family-20261001"} <= names and all(p.exists() for p in rc.EVAL_FILES)
    page0 = [json.loads(l) for l in open("results/PAGE0-page-top-20261002/questions.jsonl")]
    planted = {**rs.question_row(rs.questions()[0], 0), "question": page0[0]["question"], "grade": "right", "refused": 0,
               "messages": [{}, {"content": "q"}, {"content": "a"}]}
    assert rc.gate([planted], rc.EVAL_FILES)["G2_eval_question_in_corpus"] == 1


def _arm(credits: dict) -> dict:
    return {i: {"credit": c, "cited": None} for i, c in credits.items()}


def test_the_s2_verdict_reads_each_of_its_readings():
    rows = [{"case_id": f"a{k}", "hops": 2, "support": ["p", "x"], "check": {"kind": "value"}} for k in range(10)] + \
           [{"case_id": f"n{k}", "hops": 0, "support": None, "check": {"kind": "none"}} for k in range(4)]
    g1 = {"withlib-s0": {"applied": True}, "withlib-s1": {"applied": True}}
    none = lambda b: {f"n{k}": b[k] for k in range(4)}
    base = {**{f"a{k}": k < 2 for k in range(10)}, **none([True] * 4)}
    works = {**{f"a{k}": True for k in range(10)}, **none([True, True, True, False])}
    rec = lambda t: {"G1": g1, "arms": {rs.BASE_ARM: _arm(base), rs.TREAT_ARM: _arm(t)}}
    v = rs.verdict(rec(works), rows)
    assert v["reading"] == "RFT WORKS" and v["paired"] == "8:0" and v["p"] == 0.0078
    # the same wins with two refusals lost is not WORKS
    assert rs.verdict(rec({**works, **none([True, True, False, False])}), rows)["reading"] == "RFT HELPS"
    assert rs.verdict(rec({**base, "a2": True, "a3": True, "a0": False}), rows)["reading"] == "RFT HELPS"
    assert rs.verdict(rec(base), rows)["reading"] == "FALSIFIED"
    assert rs.verdict({**rec(works), "G1": {"withlib-s0": {"applied": True}}}, rows)["reading"].startswith("VOID")
    assert rs.sign_p(8, 0) == pytest.approx(2 / 256) and rs.sign_p(0, 0) == 1.0
