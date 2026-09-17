"""P55's instrument, exercised without a GPU: the corpus-mode loop, the token-level
acceptance read off `prompt_logprobs`, and the three gates as code.

WHAT THESE GUARD. Every number the run will print passes through these functions.
A loop that scored the injected `= {result}` lines, an acceptance that read the
wrong rank, or a gate that bought the design on a tie would each produce a clean
wrong number — the kind this repository has caught four times in one day.
"""

from __future__ import annotations

import json

import pytest

from training.email.inbox import generate
from training.harness import graded
from training.harness.accept_rank import (
    CLOSE, accepted_flags, alpha_of, applied, grades_gate, parse_verdict,
    ranking_verdict, run_chain, target_gate, user_text,
)
from training.harness.generate_email_protocol import INSTRUCTION

INBOX = generate(12, 717171)
HUMAN = next(m for m in INBOX["messages"] if not m["_facts"]["automated"])
AUTO = next(m for m in INBOX["messages"] if m["_facts"]["automated"])


def scripted(*chunks):
    """A drafter that emits the given chunks in order, whatever the prefix."""
    it = iter(chunks)
    seen = []

    def gen(prefix):
        seen.append(prefix)
        return next(it)
    gen.seen = seen
    return gen


# --- the corpus-mode loop --------------------------------------------------

def test_a_call_is_answered_for_real_and_the_model_continues():
    gen = scripted(f"<thread_history>thread_id={HUMAN['thread_id']}</thread_history>",
                   "IMPORTANT")
    out = run_chain(gen, INBOX)
    assert out["calls"] == 1 and out["refused"] == 0
    # the injected result is the tool's own answer, sitting between the two spans
    assert '= {"turns":' in out["text"]
    assert gen.seen[1].startswith("<thread_history>") and gen.seen[1].endswith("\n")
    assert out["verdict"] is True and out["ran_out"] is False


def test_the_injected_result_is_in_no_span():
    """The harness writes `= {…}`; scoring it would score the tool."""
    gen = scripted(f"<message>id={HUMAN['id']}</message>", "NOT IMPORTANT")
    out = run_chain(gen, INBOX)
    joined = "".join(s["text"] for s in out["spans"])
    assert "= {" not in joined
    # and the spans, laid at their offsets, reproduce the model's own text exactly
    for s in out["spans"]:
        assert out["text"][s["at"]:s["at"] + len(s["text"])] == s["text"]


def test_anything_past_the_first_closing_tag_is_cut():
    """The model guessing the answer it was told to ask for, P8's corruption."""
    gen = scripted("<sender_stats>address=x@y.com</sender_stats>= {\"guess\": 1}\nIMPORTANT",
                   "NOT IMPORTANT")
    out = run_chain(gen, INBOX)
    assert out["spans"][0]["text"].endswith("</sender_stats>")
    assert "guess" not in out["text"]


def test_a_refused_call_is_shown_as_an_error_and_counted():
    gen = scripted("<message>id=msg-999</message>", "NOT IMPORTANT")
    out = run_chain(gen, INBOX)
    assert out["refused"] == 1 and "= ERROR:" in out["text"]
    assert out["verdict"] is False


def test_a_model_that_invents_a_result_line_is_counted_not_hidden():
    gen = scripted("= {\"turns\": 1}\nIMPORTANT")
    out = run_chain(gen, INBOX)
    assert out["stray_results"] == 1 and out["verdict"] is True


def test_running_out_of_calls_is_undecided_not_wrong():
    tag = f"<message>id={HUMAN['id']}</message>"
    out = run_chain(scripted(*([tag] * 8)), INBOX, max_calls=3)
    assert out["ran_out"] is True and out["verdict"] is None and out["calls"] == 4


@pytest.mark.parametrize("text,want", [
    ("IMPORTANT", True), ("NOT IMPORTANT", False), ("not important.", False),
    ("This is IMPORTANT", True), ("", None), ("maybe", None)])
def test_the_verdict_rule_is_agent_sims(text, want):
    assert parse_verdict(text) is want


def test_the_user_turn_is_the_corpus_generators_byte_for_byte():
    row = json.loads(open("training/harness/data_ef/train.jsonl").readline())
    corpus_user = row["messages"][1]["content"]
    assert corpus_user.endswith(INSTRUCTION)
    assert user_text(HUMAN).endswith("\n\n" + INSTRUCTION)


# --- acceptance from prompt_logprobs ------------------------------------------

def _pl(ranks):
    """A prompt_logprobs list: position i carries the actual token id i with rank."""
    return [None] + [{str(i): {"logprob": -0.1, "rank": r}} for i, r in enumerate(ranks, 1)]


def test_accepted_iff_rank_one():
    ids = [0, 1, 2, 3, 4]
    flags = accepted_flags(_pl([1, 1, 3, 1]), ids, start=1)
    assert flags == [True, True, False, True]


def test_int_keys_are_read_as_well_as_string_keys():
    pl = [None, {1: {"logprob": -0.1, "rank": 1}}]
    assert accepted_flags(pl, [0, 1], start=1) == [True]


def test_a_token_the_target_did_not_return_is_rejected_not_crashed():
    pl = [None, {"7": {"logprob": -0.1, "rank": 1}}]
    assert accepted_flags(pl, [0, 1], start=1) == [False]


def test_alpha_is_split_by_where_the_signal_lives():
    scored = [{"tokens": 10, "accepted": 8, "lcp": 8},
              {"tokens": 10, "accepted": 6, "lcp": 2},
              {"tokens": 2, "accepted": 0, "lcp": 0}]
    a = alpha_of(scored)
    assert a["alpha"] == pytest.approx(14 / 22)
    assert a["alpha_tags"] == pytest.approx(14 / 20)
    assert a["alpha_verdict"] == 0.0
    assert a["alpha_lcp"] == pytest.approx(10 / 22)


def test_a_span_that_errored_voids_the_case_rather_than_averaging_around_it():
    a = alpha_of([{"tokens": 10, "accepted": 8, "lcp": 8}, {"error": "boom"}])
    assert a["alpha"] is None and a["errors"] == 1


# --- the gates ---------------------------------------------------------------

def recs(correct: list[bool], prefix="c"):
    return [{"id": f"{prefix}{i}", "human": True, "correct": c, "text": f"t{i}{c}"}
            for i, c in enumerate(correct)]


def test_c18_an_adapter_serving_the_bases_text_is_not_applied():
    base = recs([True] * 8)
    same = [dict(r) for r in base]
    assert applied(base, same)["verdict"].startswith("NOT APPLIED")
    diff = [dict(r, text=r["text"] + "x") for r in base]
    assert applied(base, diff)["verdict"] == "applied"


def test_the_target_gate_buys_only_a_resolvable_win():
    expert = recs([True] * 60 + [False] * 40)
    target = recs([True] * 90 + [False] * 10)          # 30 wins the expert lacks, 0 lost
    g = target_gate(target, expert, majority_bar=0.5)
    assert g["bought"] is True and g["only_a"] == 30 and g["only_b"] == 0


def test_the_target_gate_refuses_a_tie_and_a_target_below_the_bar():
    expert = recs([True] * 60 + [False] * 40)
    tie = recs([True] * 62 + [False] * 38)
    assert target_gate(tie, expert, 0.5)["bought"] is False
    weak = recs([True] * 90 + [False] * 10)
    assert target_gate(weak, expert, majority_bar=0.95)["bought"] is False


def test_grades_that_the_verifier_cannot_order_stop_the_run():
    arms = {"g75": recs([True] * 50 + [False] * 50),
            "email-full": recs([True] * 52 + [False] * 48)}
    g = grades_gate(arms, ["g75", "email-full"])
    assert g["resolved"] == 0 and g["proceed"] is False
    assert "not grades" in g["reading"]


def test_grades_that_separate_proceed_and_name_the_better_one():
    arms = {"g75": recs([True] * 40 + [False] * 60),
            "g200": recs([True] * 60 + [False] * 40),
            "email-full": recs([True] * 80 + [False] * 20)}
    g = grades_gate(arms, ["g75", "g200", "email-full"])
    assert g["resolved"] == 3 and g["inverted"] == 0 and g["proceed"] is True
    assert all(p["better"] == p["pair"][1] for p in g["pairs"])


def test_an_inverted_pair_is_named_not_hidden():
    arms = {"g75": recs([True] * 80 + [False] * 20),
            "email-full": recs([True] * 40 + [False] * 60)}
    g = grades_gate(arms, ["g75", "email-full"])
    assert g["inverted"] == 1 and "INVERTED" in g["reading"]


def alphas(values, prefix="c"):
    return [{"id": f"{prefix}{i}", "alpha": v} for i, v in enumerate(values)]


def test_alpha_agreeing_with_the_verifier_supports_the_claim():
    arms = {"g75": recs([True] * 40 + [False] * 60),
            "email-full": recs([True] * 80 + [False] * 20)}
    gate = grades_gate(arms, ["g75", "email-full"])
    a = {"g75": alphas([0.5] * 100), "email-full": alphas([0.7] * 100)}
    v = ranking_verdict(gate, a)
    assert v["verdict"] == "SUPPORTED" and v["pairs"][0]["state"] == "agrees"


def test_alpha_ordering_the_other_way_falsifies_it():
    arms = {"g75": recs([True] * 40 + [False] * 60),
            "email-full": recs([True] * 80 + [False] * 20)}
    gate = grades_gate(arms, ["g75", "email-full"])
    a = {"g75": alphas([0.7] * 100), "email-full": alphas([0.5] * 100)}
    assert ranking_verdict(gate, a)["verdict"] == "FALSIFIED"


def test_flat_alpha_on_a_resolved_pair_is_unresolved_not_a_tie():
    """The verifier saw a difference and α did not: that is a failure of the claim
    as stated, and it is reported as such rather than as agreement."""
    arms = {"g75": recs([True] * 40 + [False] * 60),
            "email-full": recs([True] * 80 + [False] * 20)}
    gate = grades_gate(arms, ["g75", "email-full"])
    a = {"g75": alphas([0.6] * 100), "email-full": alphas([0.6] * 100)}
    assert ranking_verdict(gate, a)["verdict"] == "UNRESOLVED"


# --- the grades themselves -------------------------------------------------------

def test_the_subsets_are_nested_balanced_and_reproducible(tmp_path):
    rows = [json.loads(l) for l in open(graded.FULL) if l.strip()]
    subs = graded.nested_subsets(rows)
    ids = {k: {r["case_id"] for r in v} for k, v in subs.items()}
    assert ids[75] < ids[200] and len(ids[200]) == 200
    for k, v in subs.items():
        share = sum(r["truth"] for r in v) / len(v)
        assert 0.3 <= share <= 0.7
        on_disk = [json.loads(l) for l in open(graded.path_for(k)) if l.strip()]
        assert on_disk == v, f"train_g{k}.jsonl is not what nested_subsets() produces"


def test_every_stop_string_is_a_closing_tag_of_a_declared_tool():
    from training.harness.train_pool import POOL
    surface = POOL["adapters/email-full"]["surface"]
    assert sorted(c[2:-1] for c in CLOSE) == sorted(surface)


# --- the preflight cannot fail on the model's phrasing ------------------------

def test_the_stop_check_is_decided_by_the_mechanism_not_the_model(monkeypatch):
    """Session A stopped on a preflight that asked the base to write a tag and got
    `NOT IMPORTANT` back **[ran]** 2026-09-17. The replacement counts, and passes
    whether the server returns the stop string or only names it."""
    import training.harness.accept_rank as ar
    seen = {}

    def fake_post(path, payload, timeout=300):
        seen.update(payload)
        return {"choices": [{"text": "3", "stop_reason": "3"}]}
    monkeypatch.setattr(ar, "post", fake_post)
    chk = ar.stop_check("m", "p")
    assert chk["stop_included"] is True
    assert seen["stop"] == ["3"] and seen["include_stop_str_in_output"] is True
    assert seen["prompt"].endswith("1, 2, ")

    def withheld(path, payload, timeout=300):
        return {"choices": [{"text": "", "stop_reason": "3"}]}
    monkeypatch.setattr(ar, "post", withheld)
    chk = ar.stop_check("m", "p")
    assert chk["stop_included"] is False and chk["stop_reason"] == "3"


# --- the arity convention on the way in ---------------------------------------

def test_a_positional_body_is_keyed_by_parameter_count_not_by_name():
    """The untrained 32B wrote `<thread_history>thr-003</thread_history>` because the
    block told it to, and 749 of its calls were refused for it **[ran]** 2026-09-17."""
    from training.harness.accept_rank import POSITIONAL, keyed
    assert set(POSITIONAL) == {"thread_history", "sender_stats", "message"}
    assert keyed("thread_history", "thr-003") == "thread_id=thr-003"
    assert keyed("message", " msg-007 ") == "id=msg-007"
    assert keyed("thread_history", "thread_id=thr-003") == "thread_id=thr-003"   # untouched
    assert keyed("nonesuch", "x") == "x"                                         # unknown tool: left alone


def test_a_positional_call_is_answered_in_the_loop():
    gen = scripted(f"<thread_history>{HUMAN['thread_id']}</thread_history>", "IMPORTANT")
    out = run_chain(gen, INBOX)
    assert out["refused"] == 0 and '= {"turns":' in out["text"]
