"""One prompt contract, shared by both corpora and by the evaluation.

WHY THIS FILE EXISTS. P8 composed a kernel adapter with a domain adapter and got
0/30, and I read that as weight-space interference. It was not measurable as
that: the kernel corpus was 600/600 `<calc>` with no LaTeX, the domain corpus was
0/598 `<calc>` with 433 LaTeX, the domain corpus's system prompt told the model to
show no working over 598 targets that all show working, and **every arm ran under
that domain prompt** [ran] `results/P8-harness-lora-20260909/`. The corruption
inside the tags was the superposition of two taught notations, not a fact about
composition.

So the contract moves here, and both corpora import it. After this, the two
adapters differ in exactly one thing: whether the arithmetic is delegated.

THE INSTRUCTION SAYS NOTHING ABOUT `<calc>`, DELIBERATELY. If the prompt asks for
tags, then the prompt is the protocol and the kernel adapter is decoration —
whatever the composition scores would be a fact about prompting. `ARCHITECTURE.md`
§4 claims the protocol lives in weights, so the prompt must not carry it, and the
kernel has to reach for the tool because it was trained to and for no other
reason.
"""

from __future__ import annotations

SYSTEM = (
    "You are a careful engineer. Work in SI units and be exact."
)

# Neutral: a numbered chain with intermediate values and a final JSON object.
# Nothing here mentions a tool, a tag, or who does the arithmetic.
INSTRUCTION = (
    "Solve the problem. Work in SI units. Show your working as a short numbered "
    "chain of steps, each with its intermediate value. Then, on the final line, "
    'give the answer as one JSON object: {"answer": <number>}, where <number> is '
    "the numeric value in %s."
)


def user_prompt(statement: str, unit: str | None = None) -> str:
    """The one user instruction. `unit` is None for the kernel's unitless tasks.

    The two corpora must not differ in wording, so the unitless form is this
    string with its unit clause removed rather than a second string that can
    drift away from it.
    """
    text = INSTRUCTION % unit if unit else INSTRUCTION.replace(" in %s", "")
    return f"{statement}\n\n{text}"
