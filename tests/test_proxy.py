"""The proxy's translation, both directions, without a model or a GPU.

THE MULTI-TURN PATH IS THE UNMEASURED PIECE and these are what stand in for a
measurement until one is bought. They do not say the loop works against a real
adapter; they say the translation is lossless and that a tool result lands where the
adapter was trained to read it.
"""

from training.harness.openai_proxy import (rebuild_transcript, render_tools)
from training.harness.tool_calls import to_tool_calls, tools_to_instruction

TOOLS = [{"type": "function", "function": {
    "name": "lookup", "description": "a property",
    "parameters": {"type": "object", "properties": {
        "fluid": {"type": "string"}, "property": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "calc", "description": "arithmetic",
        "parameters": {"type": "object",
                       "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}}]


def test_a_tool_result_lands_where_the_adapter_reads_it():
    """An OpenAI `tool` turn becomes `= value` on the line that asked for it."""
    calls = to_tool_calls("3. Density: <lookup>fluid=water; property=density</lookup>")
    msgs = rebuild_transcript([
        {"role": "user", "content": "a problem"},
        {"role": "assistant", "content": "3. Density: ", "tool_calls": calls},
        {"role": "tool", "tool_call_id": calls[0]["id"], "content": "998.2"},
    ])
    assert msgs[-1]["role"] == "assistant"
    assert msgs[-1]["content"].endswith(
        "<lookup>fluid=water; property=density</lookup>= 998.2")


def test_an_unmatched_result_is_kept_not_dropped():
    """Losing a value the agent computed is worse than an odd transcript order."""
    msgs = rebuild_transcript([
        {"role": "user", "content": "a problem"},
        {"role": "tool", "tool_call_id": "call_nope", "content": "42"},
    ])
    assert any("42" in (m.get("content") or "") for m in msgs)


def test_two_calls_in_one_turn_each_get_their_own_value():
    calls = to_tool_calls("1. A: <calc>2*3</calc>\n2. B: <calc>4*5</calc>")
    msgs = rebuild_transcript([
        {"role": "assistant", "content": "", "tool_calls": calls},
        {"role": "tool", "tool_call_id": calls[0]["id"], "content": "6"},
        {"role": "tool", "tool_call_id": calls[1]["id"], "content": "20"},
    ])
    body = msgs[-1]["content"]
    assert "= 6" in body and "= 20" in body


def test_the_surface_is_appended_to_the_last_user_turn():
    out = render_tools([{"role": "user", "content": "solve it"}], TOOLS)
    assert out[0]["content"].startswith("solve it")
    assert "<lookup>" in out[0]["content"]


def test_the_arity_convention_is_on_by_default_in_the_proxy():
    """P28: positional for one required parameter, and it is what the proxy sends."""
    out = render_tools([{"role": "user", "content": "x"}], TOOLS)[0]["content"]
    assert "<calc>...</calc>" in out
    assert "expression=" not in out


def test_the_proxy_adds_no_domain_words():
    """The converter scored 0 domain lines in P27; the proxy must not undo that."""
    import ast, pathlib, re
    src = pathlib.Path("training/harness/openai_proxy.py").read_text()
    doc = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            doc.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    code = [l for i, l in enumerate(src.splitlines(), 1)
            if l.strip() and not l.strip().startswith("#") and i not in doc]
    voc = r"\bfluid|densit|viscosit|throat|manning|venturi|water|modulus|lookup\b"
    assert not [l for l in code if re.search(voc, l, re.I)]


def test_the_null_arm_calls_a_long_tail_a_long_tail():
    """The instrument has to be able to say no, or it is not a gate."""
    import json, subprocess, sys, tempfile, pathlib
    rows = [{"tools": [f"t{i}"], "turns": 2, "reply": ""} for i in range(10)]
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "t.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows))
        out = subprocess.run([sys.executable, "-m", "training.harness.null_arm",
                              "--log", str(p)], capture_output=True, text=True).stdout
    assert "NO REGION" in out


def test_the_null_arm_sees_a_region_when_there_is_one():
    import json, subprocess, sys, tempfile, pathlib
    rows = ([{"tools": ["sql"], "turns": 2, "reply": "<sql>q=1</sql>"}] * 8
            + [{"tools": ["other"], "turns": 9, "reply": ""}] * 2)
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "t.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows))
        out = subprocess.run([sys.executable, "-m", "training.harness.null_arm",
                              "--log", str(p)], capture_output=True, text=True).stdout
    assert "A REGION EXISTS" in out
    assert "80.0%" in out


def test_the_door_is_shut_when_a_key_is_set():
    """A tunnel turns a localhost proxy into a public GPU. It needs a door."""
    import training.harness.openai_proxy as P

    class Fake:
        headers = {"Authorization": "Bearer wrong"}
    P.KEY = "right"
    try:
        assert P.Handler._authorised(Fake()) is False
        Fake.headers = {"Authorization": "Bearer right"}
        assert P.Handler._authorised(Fake()) is True
        Fake.headers = {}
        assert P.Handler._authorised(Fake()) is False
    finally:
        P.KEY = None


def test_no_key_means_no_door_and_that_is_deliberate():
    import training.harness.openai_proxy as P

    class Fake:
        headers = {}
    assert P.KEY is None
    assert P.Handler._authorised(Fake()) is True


def test_the_openclaw_reader_keeps_shapes_and_drops_content():
    """The snapshot holds private conversations. The region question does not need
    them, and a reader that keeps them anyway is a leak with a rationale."""
    from training.harness.openclaw_traffic import _tool_names
    msgs = [
        {"role": "user", "content": "something private"},
        {"role": "assistant", "content": "also private",
         "tool_calls": [{"function": {"name": "read_file",
                                      "arguments": '{"path":"/secret"}'}}]},
        {"role": "tool", "name": "read_file", "content": "secret contents"},
    ]
    names = _tool_names(msgs)
    assert names.count("read_file") == 2
    assert not any("private" in n or "secret" in n for n in names)


def test_the_reader_says_when_a_sample_is_too_small_to_mean_anything():
    import subprocess, sys, tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run(
            [sys.executable, "-m", "training.harness.openclaw_traffic",
             "--db", str(pathlib.Path(d) / "nope.sqlite"),
             "--out", str(pathlib.Path(d) / "t.jsonl")],
            capture_output=True, text=True).stdout
    assert "too little" in out
