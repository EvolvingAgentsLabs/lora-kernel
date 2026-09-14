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

---

## Arm 3, as built (2026-09-13)

Two arms over the same thirty cases, the same adapter and the same server. **One
difference**: how the tools are described.

| arm | the tool surface the model reads |
|---|---|
| trained instruction | the protocol prompt the adapter saw in training |
| **OpenAI schema** | the same three tools as `tools=[…]`, rendered by `tools_to_instruction` |

**The shim runs client-side, and that is the honest architecture.** vLLM will not
emit `tool_calls` for an adapter that writes tags and nothing here asks it to: the
client sends tools, the shim renders them into the surface, the model writes tags,
and `to_tool_calls` turns the reply into what an OpenAI client reads.

### A mismatch the schema creates, left in on purpose

The renderer produces `<calc>expression=...</calc>` because that is what a JSON
schema with one property says. **The adapter was trained on `<calc>1.2 * 3</calc>` —
positional, no key.** Repairing that by special-casing `calc` would be the shim
learning a tool's shape, which is the line this whole step exists to keep the
converter on the right side of. **It is left in, and whatever it costs is part of the
measurement.**

### What each outcome means

- **The shim is transparent** if the schema arm matches the trained arm on the
  oracle's tool values. An agent runtime can then speak its own language to this pool.
- **The schema rendering is the expensive half** if it collapses — and the honest
  claim becomes that `harness.lora` decides well and is reached through a translation
  that costs something measurable.
- Either way, **a claim that the adapter "does function-calling" is a claim about
  `tools_to_instruction`**, not about the weights.

---

## Arm 3 outcome (2026-09-13) [ran]

| arm | calls | refused | oracle's tool values | cases producing a call |
|---|--:|--:|--:|--:|
| trained instruction | 178 | 16 (9%) | **59/96 = 0.615** | **30/30** |
| **OpenAI schema** | 176 | **93 (53%)** | **41/96 = 0.427** | **30/30** |

**The shim costs 0.188 on the axis, and multiplies refused calls almost six-fold.**

### The protocol is not switched off — the form is

**Both arms produce a call in all thirty cases.** The worry named before the run —
that describing the tools differently might stop the adapter asking at all — does not
happen. It asks just as often and with the same number of calls (176 against 178). It
asks *wrongly*.

And the wrongness is one thing, not many:

| refusal | trained | **schema** |
|---|--:|--:|
| an expression written as a keyed argument | 1 | **33** |
| unknown unit | 4 | 4 |
| no entry in the handbook | 3 | 3 |
| everything else | 8 | 3 |

**Thirty-three of the schema arm's ninety-three refusals are the `calc` mismatch this
brief left in on purpose.** A one-property JSON schema renders as
`<calc>expression=...</calc>`; the adapter was trained on `<calc>1.2 * 3</calc>`,
positional. Every other refusal category is **identical across the two arms** — 4 and
4, 3 and 3. The schema changed exactly one thing and it broke exactly that thing.

### What this says, and what it does not

**Says**: an OpenAI client can drive this pool today, and the translation costs
something real and *attributable*. It is not a diffuse degradation; it is a shape
mismatch on one tool, visible in the refusal counts, and the rest of the protocol
crosses the bridge intact.

**Does not say** that the shim is fine as written. Special-casing `calc` was refused
before the run because a converter that learns a tool's shape stops being a
serializer — and the number that refusal cost is now known: **33 refusals and about
half of the 0.188 gap.** Whether a schema convention exists that is faithful for both
keyed and positional tools **is a design question this experiment poses rather than
answers.**

**And a caveat on the absolute numbers.** The trained arm reaches 0.615 here against
P21's 0.979, because this is a **single turn**: no harness answers the calls, so the
model writes a whole chain without ever seeing an intermediate value. **Only the A/B
inside this run is comparable**; neither number belongs beside P21's.
