"""The prompt a member of the memory is served — and therefore the prompt its corpus teaches.

A member is what its corpus taught, block and prompt: under a foreign system prompt 2 of 32 live
turns call a tool, under its own 19 of 32 **[ran]** P63. So there is ONE place the system prompt and
the verb block are written, and the corpus generator, the evaluation and the proxy all import it.
The block is built by *calling* `render_tools` over `SCHEMA` — the same function the proxy runs on
a served request — because a copy of a rendering is what drifted last time **[ran]** P38.

The three verbs take one argument each, so `render_tools` writes them positionally,
`<search>...</search>`. The shelf is an attribute of the opening tag (§3) and no schema shape says
that, so the description does. Frozen with the grammar: `memory.runtime.GRAMMAR`.
"""

from __future__ import annotations

SYSTEM = ("You are a specialist who works from a library of short notes. You do not answer from memory: "
          "search the library for the situation, open the note, follow its links in order, and send "
          "arithmetic to the calculator. A result appears right after each tag, after `= `. Open a step "
          "only after the steps it requires. If the library holds nothing for the situation, say so: "
          "`Not in my library.`")

SYSTEM_NO_LIBRARY = ("You are a specialist answering from what you know. Answer in one line, in the form "
                     "the question asks for. If you do not know, say so: `Not in my library.`")

SCHEMA = [
    {"type": "function", "function": {
        "name": "search",
        "description": ("find up to 3 notes for a situation or a doubt; write <search shelf=harness> for "
                        "how something is done, <search shelf=wiki> for what something is"),
        "parameters": {"type": "object", "properties": {"situation": {"type": "string"}},
                       "required": ["situation"]}}},
    {"type": "function", "function": {
        "name": "open",
        "description": "read a note by the id a result showed you; a link is followed by opening its id",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "calc",
        "description": "evaluate an arithmetic expression; never do arithmetic in your head",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}},
]


def block() -> str:
    """The verb block, byte for byte what `render_tools` appends to a served user turn."""
    from training.harness.openai_proxy import render_tools
    probe = "PROBE"
    served = render_tools([{"role": "user", "content": probe}], SCHEMA)[-1]["content"]
    assert served.startswith(probe + "\n\n"), "render_tools no longer appends the block after a blank line"
    return served[len(probe) + 2:]


def user_text(statement: str) -> str:
    """The user turn as served: the statement, a blank line, the block."""
    from training.harness.openai_proxy import render_tools
    return render_tools([{"role": "user", "content": statement}], SCHEMA)[-1]["content"]


# ---------------------------------------------------------------- pages of atomic statements (§1.6, W9)
# A second member shape, not an edit of the first: the nursing member's prompt stays byte-identical.
# Here a page shows sections, a section is opened as `id§anchor`, and the answer cites its statement.

SYSTEM_WIKI = ("You are a specialist who works from a wiki of short pages. You do not answer from memory. "
               "Search the wiki, open a page to see its sections, then open the one section you need as "
               "id§section. A section may link to another page: open that page the same way. A result appears "
               "right after each tag, after `= `. Finish with one line: the answer, then the section it comes "
               "from in brackets, like `18 rolls [k3f§pack]`. If the wiki holds nothing for the question, say "
               "so: `Not in my library.`")

SCHEMA_WIKI = [
    {"type": "function", "function": {
        "name": "search",
        "description": ("find up to 3 pages; write <search shelf=wiki> for what something is or who and where, "
                        "<search shelf=harness> for how a task is done"),
        "parameters": {"type": "object", "properties": {"situation": {"type": "string"}},
                       "required": ["situation"]}}},
    {"type": "function", "function": {
        "name": "open",
        "description": "open a page by the id a result showed you to see its sections; open id§section to read one",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "calc",
        "description": "evaluate an arithmetic expression; never do arithmetic in your head",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}},
]

SYSTEM_WIKI_READS = ("You are a specialist. The wiki sections you need are open below, each after its citation. "
                     "Work only from them. Finish with one line: the answer, then the section it comes from in "
                     "brackets, like `18 rolls [k3f§pack]`. If they hold nothing for the question, say so: "
                     "`Not in my library.`")


def user_text_wiki(question: str) -> str:
    from training.harness.openai_proxy import render_tools
    return render_tools([{"role": "user", "content": question}], SCHEMA_WIKI)[-1]["content"]
