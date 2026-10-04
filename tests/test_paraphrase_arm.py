"""P2a's instrument, zero GPU: the paraphrase replaces the task line and nothing else, and the grader is the release's.

The released scores (email-full@v3 469/475, desk-commitment@v3 240/240 shallow + 239/240 deep) came from
`pool_base` → `accept_rank.draft_arm` over `suites.load(name).cases(eval_n, eval_seed)`, graded by
`case.verify(suite.parse(final span))` **[read]** training/harness/pool_base.py. The paired reading is the exact sign
test on discordant pairs, $p = 2\\sum_{k\\le\\min(b,c)}\\binom{b+c}{k}2^{-(b+c)}$ (FOUNDATIONS §9.2). These tests hold
the one-line difference between the two arms to exactly one line, and run the runner end to end against
`fake_vllm` with a scripted model.
"""
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

from training.harness import accept_rank as ar
from training.harness import fake_vllm as fv
from training.harness import paraphrase_arm as pa
from training.harness import suites

SUITES = [s for spec in pa.MEMBERS.values() for s in spec["suites"]]


@pytest.mark.parametrize("name", SUITES)
def test_the_paraphrase_replaces_only_the_task_line(name):
    suite, verbatim, para = pa.load_cases(name)
    assert len(verbatim) == len(para) == (475 if name == "email" else 240)    # the release's n, per suite
    seen = set()
    for k, (v, p) in enumerate(zip(verbatim, para)):
        head_v, _, last_v = v.user.rpartition("\n")
        head_p, _, last_p = p.user.rpartition("\n")
        assert last_v == pa.TASK[name]                       # the release's task, verbatim
        assert last_p == pa.PARAPHRASES[name][k % len(pa.PARAPHRASES[name])] != last_v
        assert head_p.encode() == head_v.encode()            # every other byte of the case identical
        assert p.user.encode() == v.user.encode()[: -len(last_v.encode())] + last_p.encode()
        # what the tools answer from and what the grader checks are the SAME objects, not copies
        assert p.id == v.id and p.ctx is v.ctx and p.truth == v.truth and p.verify is v.verify and p.human == v.human
        assert {kk: vv for kk, vv in p.meta.items() if not kk.startswith("paraphrase")} == v.meta
        # the rendered user turn differs only in that line: the tool block is the suite's, untouched
        assert suite.user_text(p) == suite.user_text(v).replace("\n" + last_v + "\n\n", "\n" + last_p + "\n\n", 1)
        seen.add(last_p)
    assert seen == set(pa.PARAPHRASES[name])                 # round-robin reaches every wording


def test_a_case_whose_last_line_is_not_the_task_is_refused():
    _, verbatim, _ = pa.load_cases("email")
    bad = suites.Case(id="x", user=verbatim[0].user + " Thanks!", ctx={}, truth=True, verify=lambda s: True)
    with pytest.raises(ValueError):
        pa.paraphrased(bad, "email", 0)


def test_the_lists_are_long_distinct_and_absent_from_the_corpora():
    for name, pool in pa.PARAPHRASES.items():
        assert len(set(pool)) == len(pool) >= pa.MIN_PARAPHRASES, name
        assert pa.TASK[name] not in pool and all("\n" not in p for p in pool)
    # the deep band's rule travels with every deep paraphrase — otherwise it asks another question
    assert all(any(w in p for w in ("recent", "latest", "last", "final", "newest", "revised"))
               for p in pa.PARAPHRASES["desk:commitment_deep"])
    assert pa.corpus_leaks() == {}


def _truths():
    """Every case's head (the listing) → (suite, truth); the scripted model reads its answer off it."""
    out = {}
    for name in SUITES:
        _, cases, _ = pa.load_cases(name)
        for c in cases[:12]:
            out[c.user.rpartition("\n")[0]] = (name, c.truth)
    return out


def _answer(name, truth, right: bool) -> str:
    if name == "email":
        return ("IMPORTANT" if truth else "NOT IMPORTANT") if right else ("NOT IMPORTANT" if truth else "IMPORTANT")
    return truth if right else "December 31"          # no desk month is December


def _run(tmp_path, monkeypatch, para_right: bool) -> dict:
    truths = _truths()
    paraphrases = [p for pool in pa.PARAPHRASES.values() for p in pool]

    def responder(model, prompt):
        if "Count from 1 to 6" in prompt or "<|user|>" in prompt and "Preview:" not in prompt:
            return "Some text."
        for head, (name, truth) in truths.items():
            if head + "\n" in prompt:
                is_para = any("\n" + p + "\n\n" in prompt for p in paraphrases)
                return _answer(name, truth, right=(para_right or not is_para))
        return "?"

    # twelve cases a suite, both released adapters stood in for by files whose sha the manifest is set to
    monkeypatch.setattr(pa, "load_cases", lambda n, f=pa.load_cases: tuple(x[:12] if i else x for i, x in enumerate(f(n))))
    members = {}
    for m, spec in pa.MEMBERS.items():
        d = tmp_path / spec["adapter"]; d.mkdir(parents=True)
        (d / "adapter_model.safetensors").write_bytes(m.encode())
        members[m] = {**spec, "adapter": str(d), "sha256": hashlib.sha256(m.encode()).hexdigest()}
    monkeypatch.setattr(pa, "MEMBERS", members)
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoTokenizer=fv.FakeTokenizer))
    calls = []
    real = ar.draft_arm
    monkeypatch.setattr(ar, "draft_arm", lambda *a, **k: calls.append(a[2]) or real(*a, **k))
    out = tmp_path / "p2a.json"
    with fv.patched(responder) as seen:
        rc = pa.main(["--out", str(out), "--concurrency", "4"])
    rec = json.loads(out.read_text())
    rec["_rc"], rec["_calls"], rec["_refused"] = rc, calls, seen["server"].refused
    return rec


def test_the_grader_is_the_release_grader_and_the_verdict_reads_the_pair(tmp_path, monkeypatch):
    rec = _run(tmp_path, monkeypatch, para_right=False)
    assert rec["_refused"] == [] and all(g["applied"] for g in rec["G1"].values())
    # the release's own path: draft_arm with the suite `suites.load` builds
    assert sorted(s.name for s in rec["_calls"]) == sorted(SUITES * 2)
    tok = fv.FakeTokenizer()
    for m, spec in pa.MEMBERS.items():
        for name in spec["suites"]:
            suite, verbatim, para = pa.load_cases(name)
            for cond, cases in (("verbatim", verbatim), ("paraphrase", para)):
                recs = rec["arms"][pa.arm_key(m, name, cond)]["records"]
                assert len(recs) == 12
                for c in cases:
                    r = recs[c.id]
                    # graded by the case's own verifier on the suite's own parse of the final span — the release grader
                    assert r["correct"] == bool(c.verify(suite.parse(r["spans"][-1]["text"])))
                    assert r["correct"] == (cond == "verbatim")
                    assert r["prompt_sha"] == pa.prompt_sha(tok, suite, c)   # the render the release check compares
                    if cond == "paraphrase":
                        assert r["paraphrase"] == c.meta["paraphrase"]
    assert rec["verdict"]["verdict"] == "PARAPHRASES COST" and rec["verdict"]["decided"]
    row = rec["analysis"]["email-full|email"]
    assert row["pair"]["only_b"] == 12 and row["pair"]["state"] == "REGRESSION"


def test_members_answer_paraphrases_when_both_conditions_are_right(tmp_path, monkeypatch):
    rec = _run(tmp_path, monkeypatch, para_right=True)
    assert rec["verdict"]["verdict"] == "MEMBERS ANSWER PARAPHRASES" and rec["_rc"] == 0
    assert all(row["drop"] == 0 and row["pair"]["state"] == "tie" for row in rec["analysis"].values())


def test_a_resumed_run_drafts_nothing_twice(tmp_path, monkeypatch):
    rec = _run(tmp_path, monkeypatch, para_right=True)
    out = tmp_path / "p2a.json"
    done = json.loads(out.read_text())
    done.pop("finished")
    out.write_text(json.dumps(done))
    served = []
    with fv.patched(lambda m, p: served.append(m) or "Some text.") as _:
        pa.main(["--out", str(out)])
    # only G1's six probes (three per member, base and member) reach the server: every case was resumed
    assert len(served) == 4 * 3
    assert json.loads(out.read_text())["verdict"]["verdict"] == rec["verdict"]["verdict"]


def test_void_when_a_member_is_not_applied():
    rec = {"G1": {"email-full": {"applied": False}, "desk-commitment": {"applied": True}}, "analysis": {}}
    assert pa.verdict(rec)["verdict"] == "VOID"


def test_unresolved_is_a_wide_drop_without_a_significant_pair():
    rows = {}
    for m, spec in pa.MEMBERS.items():
        for s in spec["suites"]:
            rows[f"{m}|{s}"] = {"errors": 0, "drop": 0.0, "pair": {"state": "tie"}}
    rows["email-full|email"] = {"errors": 0, "drop": 0.06, "pair": {"state": "tie"}}
    rec = {"G1": {m: {"applied": True} for m in pa.MEMBERS}, "analysis": rows}
    assert pa.verdict(rec)["verdict"] == "UNRESOLVED"
    rows["email-full|email"]["pair"]["state"] = "REGRESSION"
    assert pa.verdict(rec)["verdict"] == "PARAPHRASES COST"
    rows["email-full|email"] = {"errors": 0, "drop": 0.0, "pair": {"state": "tie"},
                                "vs_release": {"state": "REGRESSION"}}
    assert pa.verdict(rec)["verdict"] == "VOID"


def test_the_released_adapters_and_records_are_the_ones_named():
    for m in pa.MEMBERS:
        man = json.loads(Path(f"releases/{m}@v3.json").read_text())
        assert man["adapter_sha256"] == pa.MEMBERS[m]["sha256"] and man["base"] == pa.BASE
    for name, (path, arm) in pa.RECORDED.items():
        recs = json.loads(Path(path).read_text())["arms"][arm]["records"]
        _, cases, _ = pa.load_cases(name)
        assert {c.id for c in cases} == set(recs)               # the release scored these very cases
