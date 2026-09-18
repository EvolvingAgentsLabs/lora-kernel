"""What a pool member declares about itself, and what a caller may rely on.

WHY A RECORD AND NOT A PATH. `POOL` mapped an adapter directory to a corpus file,
which is everything the trainer needs and nothing a **caller** needs. A router
choosing between members, or a runtime deciding whether to serve one a request,
has to know two things that were nowhere on disk:

1. **What comes out.** Every adapter here emits free text; a typed one would emit
   one of a fixed set of values with a probability attached. P44 measured why that
   distinction is worth a field rather than a convention: the confidence already on
   the wire does not order the errors — AURC 0.612 against an oracle floor of 0.213,
   a gap of **0.400** **[ran]**.

2. **WHAT BAND IT WAS TRAINED ON.** This is the field P45 forced into existence, and
   it is the one that would have prevented a silent wrong answer. `fluids-full` was
   trained only on 6-to-9-step chains. Served a two-step problem it does not
   simplify — it **over-solves on 18 of 18 cases**, converting metres to metres,
   inventing an area, and answering a question about force that nobody asked
   **[ran]** P45. On three-step problems the bare base beats it, 0.167 to 0.000.

   Nothing in the served interface distinguishes that from a correct answer. An
   adapter that does not declare its band lets a caller hand it work it was never
   shown, and get fluent nonsense back.

THE CONTRACT IS CHECKED, NOT TRUSTED. `validate` refuses a record that omits a
band, names a kind it does not understand, or declares typed values without the
token ids that make a restricted softmax possible — and those ids are verified
against the base at corpus-generation time, never asserted here.

Nothing in this module trains, serves or scores. It is the vocabulary those three
agree on.
"""

from __future__ import annotations

import re

KINDS = ("text", "typed")

# A tag name is what `tool_calls.CALL` will accept back out of a reply. Declaring a
# surface the serializer could never parse would be declaring a capability nobody
# can exercise.
TAG = re.compile(r"^[A-Za-z_][\w-]*$")


class ContractError(ValueError):
    pass


def band(lo: int, hi: int) -> dict:
    """The difficulty band a member was trained on, in oracle solution steps.

    Steps, rather than a word like `beginner`, because steps are what the corpus
    generator already knows and what `ladder.STEPS` already records. A label would
    have to be agreed; a step count is measured.
    """
    # ZERO IS A REAL FLOOR, NOT AN EMPTY ONE. `domain-mt` is the physics corpus with
    # the protocol removed and the reasoning kept: 600 of 600 examples call nothing,
    # by design. Refusing `min_steps = 0` would have made the one adapter that never
    # uses a tool undeclarable **[ran]** 2026-09-15.
    if lo < 0 or hi < lo:
        raise ContractError(f"band ({lo}, {hi}) is not a range")
    return {"min_steps": lo, "max_steps": hi}


def surface(tags) -> list[str]:
    """The tag names a member was trained to write — its tool vocabulary.

    THE FIELD P43 FORCED INTO EXISTENCE, and it is the band's exact counterpart.
    A band says *how deep* a problem may be; a surface says *which tools exist* for
    the member being asked. Without it a caller can hand an adapter trained on three
    tags an agent runtime's whole toolbox, and P43 measured what happens: the
    OpenClaw turn made **no tool calls at all**, because the tags it was offered were
    not tags this expert has ever seen **[ran]** `results/P43-openclaw-e2e-20260915/`.

    P25 priced the same failure from the other side: on a subject whose tag names it
    had never seen, the adapter reached 27 of 63 — it knows *that* a step needs a
    lookup and gets the name wrong **[ran]**.

    AN EMPTY SURFACE IS A DECLARATION, NOT AN OMISSION. `domain-mt` calls nothing in
    600 of 600 examples; `[]` is the true statement about it, and it is what lets a
    caller know not to offer it tools rather than guess from silence.

    **THE ORDER IS PART OF THE DECLARATION AND IS NOT SORTED.** The first version of
    this function sorted, and rendering the pruned surface back produced a block that
    matched the corpus in every character except the order of its three lines — while
    `email-full` saw `thread_history, sender_stats, message` in that order in 598 of
    598 training prompts **[ran]** 2026-09-16. Alphabetising it would have shipped a
    prompt the adapter was never trained on and called it a repair.
    """
    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out


def text(corpus: str, trained_on: dict, note: str = "",
         tags: list[str] | None = None, args: dict | None = None,
         system: str | None = None) -> dict:
    """`system` is the prompt the corpus taught, when the member has one. THE PROMPT IS
    PART OF WHAT WAS RELEASED (`releases/<name>@v1.json` carries its hash) and a member
    served under another runtime's prompt is a different measurement: P63 [ran]
    2026-09-18, under OpenClaw's 37 KB system prompt, `email-full` answered every
    turn from the listing with 0 tool calls, as the bare base does."""
    rec = {"corpus": corpus, "band": trained_on, "surface": surface(tags or []),
           "surface_args": dict(args or {}),
           "output_contract": {"kind": "text"}, "note": note}
    if system:
        rec["system"] = system
    return rec


def typed(corpus: str, trained_on: dict, values: list[str],
          value_tokens: list[int], note: str = "",
          tags: list[str] | None = None) -> dict:
    return {"corpus": corpus, "band": trained_on, "note": note,
            "surface": surface(tags or []),
            "output_contract": {"kind": "typed", "type": "enum",
                                "values": values, "value_tokens": value_tokens}}


def validate(path: str, record: dict) -> dict:
    """Refuse a member whose declaration a caller could not act on."""
    if not isinstance(record, dict):
        raise ContractError(f"{path}: expected a record, got {type(record).__name__}")
    for key in ("corpus", "band", "output_contract"):
        if key not in record:
            raise ContractError(f"{path}: no {key!r}")

    b = record["band"]
    if not isinstance(b, dict) or "min_steps" not in b or "max_steps" not in b:
        raise ContractError(f"{path}: band must carry min_steps and max_steps")
    if b["min_steps"] < 0 or b["max_steps"] < b["min_steps"]:
        raise ContractError(f"{path}: band {b} is not a range")

    # A SURFACE IS OPTIONAL TO DECLARE AND CHECKED ONCE DECLARED. A record written
    # before this field existed is still actionable — a caller reads `None` as "this
    # member does not say", which is different from "this member knows no tools" and
    # has to stay different.
    sf = record.get("surface")
    if sf is not None:
        if not isinstance(sf, list) or any(not isinstance(t, str) for t in sf):
            raise ContractError(f"{path}: surface must be a list of tag names")
        if len(set(sf)) != len(sf):
            raise ContractError(f"{path}: a tag is declared twice in the surface")
        bad = [t for t in sf if not TAG.match(t)]
        if bad:
            raise ContractError(
                f"{path}: {bad} cannot be parsed back out of a reply by "
                "tool_calls.CALL — declaring them would declare a capability "
                "nobody can exercise")

    # THE ARGUMENT KEYS A TAG IS WRITTEN WITH, read off the corpus like the band. They
    # exist because a runtime's own tool can carry the same bare name as a member's
    # tag: OpenClaw offers a native `message` (`action`, `channel`, `target`, …)
    # beside `lora-inbox__message` (`id`) **[ran]** P59, and a prune keyed on the
    # name alone hands the member's `<message>` to the wrong tool. The keys say which.
    sa = record.get("surface_args") or {}
    if not isinstance(sa, dict):
        raise ContractError(f"{path}: surface_args must map tag -> list of keys")
    for tag, keys in sa.items():
        if sf is not None and tag not in sf:
            raise ContractError(f"{path}: surface_args names {tag!r}, not in the surface")
        if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys):
            raise ContractError(f"{path}: surface_args[{tag!r}] must be a list of keys")

    sy = record.get("system")
    if sy is not None and (not isinstance(sy, str) or not sy.strip()):
        raise ContractError(f"{path}: system must be a non-empty prompt when declared")

    oc = record["output_contract"]
    kind = oc.get("kind")
    if kind not in KINDS:
        raise ContractError(f"{path}: output kind {kind!r} is not one of {KINDS}")
    if kind == "typed":
        vals, toks = oc.get("values"), oc.get("value_tokens")
        if not vals:
            raise ContractError(f"{path}: a typed member declares no values")
        # WITHOUT THE IDS THERE IS NO RESTRICTED SOFTMAX. A typed contract whose
        # values are not single tokens on the base that serves it is a text
        # contract wearing a label, and the ids are the only thing that says so.
        if not toks or len(toks) != len(vals):
            raise ContractError(
                f"{path}: {len(vals)} values but {len(toks or [])} value_tokens; "
                "each value must be one verified token on the serving base")
        if len(set(toks)) != len(toks):
            raise ContractError(f"{path}: two values share a token id — "
                                "they cannot be told apart in one forward pass")
    return record


def accepts(record: dict, steps: int) -> bool:
    """Is a problem of this depth inside the band this member was trained on?

    The question P45 made answerable. A caller that asks it before routing gets a
    refusal instead of a fluent, padded, wrong answer.
    """
    b = record["band"]
    return b["min_steps"] <= steps <= b["max_steps"]


def offers(record: dict, tag: str) -> bool:
    """Does this member have a tag for that tool?

    `None` — the member does not declare a surface — answers yes, because a record
    written before the field existed makes no claim either way and refusing it would
    be reading silence as a denial.
    """
    sf = record.get("surface")
    return True if sf is None else tag in sf


def validate_pool(pool: dict) -> dict:
    return {p: validate(p, r) for p, r in pool.items()}
