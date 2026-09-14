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
