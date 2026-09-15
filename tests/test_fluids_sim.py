"""A second client, and the failures it must not import from the first.

`multitool_run` runs the model in process with PEFT, which measures an adapter and
cannot measure a pool. This is the HTTP client that can — and every check here is
about a way it could produce a clean, wrong number.
"""

import json

import pytest

from training.harness import fluids_sim as fs
from training.physics import multitool as mod


def _case(i=0):
    return mod.generate(4, 616161, mod.FAMILIES)[i]


def test_calc_reads_its_expression_raw(monkeypatch):
    """P28's arity convention renders one required parameter positionally, and
    `calc` reads the expression itself — not `expression=...`."""
    assert fs._body("calc", '{"_": "2 * 3"}') == "2 * 3"
    assert fs._body("calc", '{"expression": "2 * 3"}') == "2 * 3"


def test_keyed_tools_keep_their_keys():
    assert fs._body("convert", '{"value": "5", "from": "cm", "to": "m"}') == \
        "value=5; from=cm; to=m"
    assert fs._body("lookup", '{"_": "water"}') == "fluid=water"


def test_a_solved_case_passes_and_the_handbook_travels_with_it(monkeypatch):
    """The oracle's own chain, replayed through the client, must score."""
    case = _case()
    book = {tuple(k): v for k, v in case["handbook"]}
    turns = []
    for label, tool, body in case["chain"]:
        turns.append({"choices": [{"message": {"role": "assistant", "tool_calls": [
            {"id": label, "function": {"name": tool, "arguments":
                                       json.dumps({"_": body}) if tool == "calc"
                                       else json.dumps(dict(
                                           p.split("=", 1) for p in
                                           [x.strip() for x in body.split(";")]))}}]}}]})
    turns.append({"choices": [{"message": {
        "role": "assistant",
        "content": '{"answer": %.6g}' % case["answer"]}}]})
    monkeypatch.setattr(fs, "chat", lambda *a, **k: turns.pop(0))
    r = fs.solve_one("u", None, "m", case, 20, 300)
    assert r["passed"] is True and r["refused"] == 0
    assert r["calls"] == len(case["chain"])
    assert book  # the case really carries its own handbook


def test_running_out_of_turns_is_its_own_outcome(monkeypatch):
    """It must not read as wrong physics — a fluids chain is seven calls deep."""
    monkeypatch.setattr(fs, "chat", lambda *a, **k: {"choices": [{"message": {
        "role": "assistant", "tool_calls": [
            {"id": "1", "function": {"name": "calc", "arguments": '{"_": "1+1"}'}}]}}]})
    r = fs.solve_one("u", None, "m", _case(), 3, 300)
    assert r["out_of_turns"] is True and r["passed"] is False
    assert r["text"] == "(ran out of turns)"


def test_a_refusal_records_what_was_asked_for(monkeypatch):
    """The lesson P34 paid for: a refusal count without the ask is not a diagnosis."""
    turns = [
        {"choices": [{"message": {"role": "assistant", "tool_calls": [
            {"id": "1", "function": {"name": "lookup",
                                     "arguments": '{"fluid": "unobtainium", '
                                                  '"property": "density"}'}}]}}]},
        {"choices": [{"message": {"role": "assistant",
                                  "content": '{"answer": 1}'}}]},
    ]
    monkeypatch.setattr(fs, "chat", lambda *a, **k: turns.pop(0))
    r = fs.solve_one("u", None, "m", _case(), 20, 300)
    assert r["refused"] == 1 and r["asked"][0]["name"] == "lookup"
    assert "unobtainium" in r["asked"][0]["error"]


def test_the_wrong_answer_fails_at_the_scorer_s_own_tolerance():
    """Not an epsilon chosen here: multitool_run scores at rtol 0.02."""
    from training.physics.headroom import correct
    assert fs.SCORER_RTOL == 0.02
    assert correct(100.0, 101.0, fs.SCORER_RTOL)
    assert not correct(100.0, 150.0, fs.SCORER_RTOL)


def test_the_client_declares_every_tool_the_suite_has():
    from training.physics.tools import TOOLS
    assert {t["function"]["name"] for t in fs.SCHEMA} == set(TOOLS)


def test_the_converter_stays_domain_free():
    """P27 measured tool_calls.py at **0 of 38 lines of code** naming a tool or a
    domain. A second client must not have been the reason that changed.

    LINES OF CODE, NOT PROSE — and the first version of this test did not make the
    distinction. It read the whole file and fired on the word `fluid` inside a
    comment saying *"no fluid names, no label vocabulary"*: a sentence explaining
    the absence, counted as the presence. Same shape as the guard that refused
    `noreply@` in an address yesterday. Comments and string literals are stripped.
    """
    import io
    import pathlib
    import tokenize

    src = pathlib.Path("training/harness/tool_calls.py").read_bytes()
    code = " ".join(
        tok.string for tok in tokenize.tokenize(io.BytesIO(src).readline)
        if tok.type not in (tokenize.COMMENT, tokenize.STRING, tokenize.NL,
                            tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
    ).lower()
    for word in ("fluid", "calc", "lookup", "convert", "thread", "sender",
                 "inbox", "triage"):
        assert word not in code, f"tool_calls.py's code now names {word!r}"


# ---------------------------------------------------------------------------
# THE CHAIN IS THE THING THE ROUTING DECISION READS.
#
# `escalate.py` decides case by case whether a chain has left its region by typing
# its units and re-evaluating its arithmetic. P40 stored only the final message —
# `{"answer": 35584.2}` — so the question the whole pool exists to answer was not
# computable from a completed run **[ran]** 2026-09-15.
# ---------------------------------------------------------------------------

def test_the_record_carries_the_chain_the_escalation_rules_need(monkeypatch):
    case = _case()
    turns = []
    for label, tool, body in case["chain"]:
        args = (json.dumps({"_": body}) if tool == "calc" else
                json.dumps(dict(p.split("=", 1) for p in
                                [x.strip() for x in body.split(";")])))
        turns.append({"choices": [{"message": {"role": "assistant", "tool_calls": [
            {"id": label, "function": {"name": tool, "arguments": args}}]}}]})
    turns.append({"choices": [{"message": {
        "role": "assistant", "content": '{"answer": %.6g}' % case["answer"]}}]})
    monkeypatch.setattr(fs, "chat", lambda *a, **k: turns.pop(0))
    r = fs.solve_one("u", None, "m", case, 20, 300)

    assert "chain" in r and r["chain"], "no chain was kept"
    # every call the model made is in it, each carrying the answer it received
    for _, tool, _ in case["chain"]:
        assert f"<{tool}>" in r["chain"]
    assert "= " in r["chain"], "the tool results were not folded back in"
    # and the escalation rules can actually read it
    from training.harness.escalate import is_probably_wrong, should_escalate
    assert is_probably_wrong(r["chain"], r["unit"], r["statement"]) in (True, False)
    assert should_escalate(r["chain"], r["unit"], r["statement"]) in (True, False)


def test_the_unit_and_statement_travel_with_it(monkeypatch):
    """The dimensional check needs both; a record without them cannot be routed."""
    monkeypatch.setattr(fs, "chat", lambda *a, **k: {"choices": [{"message": {
        "role": "assistant", "content": '{"answer": 1}'}}]})
    r = fs.solve_one("u", None, "m", _case(), 6, 300)
    assert r["unit"] and r["statement"]


def test_a_run_that_ran_out_of_turns_still_carries_its_chain(monkeypatch):
    """That case is exactly the one a router would want to send away."""
    monkeypatch.setattr(fs, "chat", lambda *a, **k: {"choices": [{"message": {
        "role": "assistant", "tool_calls": [
            {"id": "1", "function": {"name": "calc", "arguments": '{"_": "1+1"}'}}]}}]})
    r = fs.solve_one("u", None, "m", _case(), 3, 300)
    assert r["out_of_turns"] is True and r["chain"]
