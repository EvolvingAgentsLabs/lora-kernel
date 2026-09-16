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

KINDS = ("text", "typed")


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


def text(corpus: str, trained_on: dict, note: str = "") -> dict:
    return {"corpus": corpus, "band": trained_on,
            "output_contract": {"kind": "text"}, "note": note}


def typed(corpus: str, trained_on: dict, values: list[str],
          value_tokens: list[int], note: str = "") -> dict:
    return {"corpus": corpus, "band": trained_on, "note": note,
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


def validate_pool(pool: dict) -> dict:
    return {p: validate(p, r) for p, r in pool.items()}
