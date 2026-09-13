# P27 — does `harness.lora` survive contact with function-calling?

**Pre-registered 2026-09-13, before the shim was written.**

## The worry, and why it is probably the wrong shape

P26 ends with an endpoint an agent can call and an agent that would see nothing
usable: the adapters emit `<lookup>material=…; property=…</lookup>` in the message
body, and OpenAI clients expect a `tool_calls` array. P26's brief said bridging that
"reintroduces the hand-written harness the weights were meant to replace".

**That sentence conflates two different things, and this step exists to separate
them.**

| | what it is | what P25 measured about it |
|---|---|---|
| **deciding** which tool, and what arguments | the protocol | the rule transfers **0 of 63** to a new subject; the adapter **27 of 63** |
| **serialising** a decided call into JSON | a format converter | not measured |

A converter that turns `<lookup>a=1; b=2</lookup>` into
`{"name":"lookup","arguments":{"a":1,"b":2}}` knows no fluid names, no label
vocabulary, no unit table and no phrasings. **It is the same converter for every
domain, forever.** If that is true, the bridge is a serializer and not a harness, and
the objection dissolves.

**If it is false — if the converter needs to know anything about the domain — then
P26's worry is correct** and function-calling costs the architecture the thing it was
built to avoid.

## The measurements, and two of three cost nothing

**1. Zero domain-specific lines.** The same converter, unmodified, handles the fluid
suite and the materials suite. Measured the way P25 measured the rule: **how many of
its lines would have to change.** The rule needed 38 of 109. The claim here is **0**.

**2. Round-trip fidelity.** Every tool call in both oracles converts to a valid
`tool_calls` entry and back to the exact original string. Any loss is a defect,
because the harness answers the reconstructed call, not the JSON.

**3. End-to-end.** An OpenAI client sends `tools=[…]` and gets `tool_calls` back from
the served kernel. Needs a card, and is bought only if 1 and 2 pass.

## Falsification, fixed now

- **The bridge is a serializer** if the converter is domain-free (0 lines) and the
  round trip is lossless on both suites.
- **The bridge is a harness**, and P26's worry stands, if it needs per-domain
  knowledge — a tool name table, an argument list, a unit map — to produce valid
  `tool_calls`.
- **The step is void** if the converter is only lossless because the two suites share
  a tool vocabulary. The materials suite was written with the same three tools on
  purpose, so this has to be checked directly rather than assumed: **the converter
  must handle a tool name it has never seen.**

## What it cannot settle

Whether the *adapter* can read an OpenAI `tools=[…]` schema and emit calls for tools
it was never trained on. It cannot; it was trained on three tag names. The shim makes
that unnecessary rather than solving it, and **a claim that the adapter does
function-calling would be a claim about the shim**.

---

## Outcome (2026-09-13) — the bridge is a serializer, not a harness [ran]

### 1. Zero domain-specific lines

Counted the way P25 counted the rule, over **executable code only** — docstrings
excluded, because prose naming a fluid is not a dependency on one:

| | lines of code naming this suite's vocabulary |
|---|--:|
| the hand-written rule | **19 of 76** |
| **the serializer** | **0 of 38** |

The rule's are structural — `from training.physics.tools import FLUIDS, UNITS`,
`FLUID_NAMES = …`, `("throat diameter", "length", …)`. The serializer has none:
it names no tool, no argument, no unit and no substance anywhere in its code.

### 2. Round-trip fidelity: 604 of 604

| suite | calls | returned byte-identical |
|---|--:|--:|
| fluids | 420 | **420** |
| materials | 184 | **184** |
| **total** | **604** | **604 = 1.000** |

Every call in both oracles becomes a valid `tool_calls` entry and comes back as the
exact original string. That matters because the harness answers the reconstructed
call, not the JSON.

### 3. The voiding condition does not fire

The two suites share three tool names on purpose, so losslessness could have been an
artefact of a shared vocabulary. Checked directly against tools the converter has
never seen and that this project has no concept of:

    <search_flights>from=EZE; to=MAD; date=2026-10-02</search_flights>   ok
    <sql_query>table=orders; where=status='open'</sql_query>             ok
    <send_email>to=a@b.c; subject=hola</send_email>                      ok

### So P26's closing worry was the wrong shape, and it was mine

P26's brief said bridging to `tool_calls` "reintroduces the hand-written harness the
weights were meant to replace". **It conflated deciding with serialising.** Deciding
*which* tool and *what* arguments is the protocol — the part a rule loses entirely on
a new subject (0 of 63) and the adapter partly keeps (27 of 63). Turning a decided
call into JSON knows nothing about any domain, and the measurement says so: **0
domain lines, 604 of 604 round trips, three invented tools handled.**

**The bridge costs the architecture nothing.** An agent runtime gets `tool_calls`
without a single line that knows what a fluid is.

### The half that is not free, named rather than hidden

`tools_to_instruction` renders a client's `tools=[…]` schema as the tag surface the
adapter reads. **That half is not free and no measurement here says it is.** The
adapter was trained on three tag names; a client offering `search_flights` gets a
line saying the tag exists, and nothing in the weights knows what it means. P25
measured what that costs on an unseen subject: **27 of 63**, with 56% of its failures
being names rather than form.

**A claim that `harness.lora` does function-calling would be a claim about this
function, not about the weights.** What the weights do is decide that a step needs a
query and build a keyed call; what the shim does is spell it in someone else's
syntax.

**Arm 3 — end to end against the served kernel with `tools=[…]` — is bought and not
yet run.**
