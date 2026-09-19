"""What `accept_rank.py` needs to know about a suite, and nothing else.

WHY A RECORD. The runner was written against the triage inbox with its three tags,
its `IMPORTANT / NOT IMPORTANT` verdict and its human-message bar baked into the
module. P55 A then showed the ordering test unbuyable on that suite and P51 showed
where it is buyable — the desk's `commitment` region — so the suite became a
parameter. Everything a suite decides is listed here; everything else the runner does
(corpus-mode loop, forced scoring, gates, persistence) is the same for both, which is
what makes the two runs comparable.

THE EMAIL SUITE REPRODUCES THE RUNNER'S FIRST BEHAVIOUR BYTE FOR BYTE: same system
prompt, same listing, same block, same tags, same verdict rule, same human bar.
`tests/test_accept_rank.py` still passes unchanged against it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from training.harness.tool_calls import tools_to_instruction


def _positional(schema: list[dict]) -> dict[str, str]:
    """P28's arity convention on the way in: the one parameter of a one-parameter tool."""
    out = {}
    for t in schema:
        fn = t["function"]
        req = fn["parameters"].get("required") or sorted(fn["parameters"]["properties"])
        if len(req) == 1:
            out[fn["name"]] = req[0]
    return out


@dataclass
class Case:
    id: str
    user: str                      # the user turn WITHOUT the tool block
    ctx: dict                      # what the tools answer from (an inbox, a desk)
    truth: object                  # for the record
    verify: Callable[[str | None], bool]
    human: bool = True
    meta: dict = field(default_factory=dict)


@dataclass
class Suite:
    name: str
    system: str
    block: str                     # the tool block, byte for byte what the corpus taught
    tags: tuple[str, ...]
    answer: Callable[[dict, str, str], str]
    positional: dict[str, str]
    parse: Callable[[str], object]         # the final span's text -> an answer or None
    cases: Callable[[int, int], list[Case]]
    bar: Callable[[list[Case]], float]     # the floor a target must clear on its own
    eval_seed: int
    eval_n: int
    # HOW MANY CALLS A CHAIN MAY MAKE. Six is what triage and the desk need; a fluids chain
    # is six to nine, and a loop capped below the corpus's own depth would cut every long
    # case off and score the cap.
    max_calls: int = 6

    @property
    def close(self) -> tuple[str, ...]:
        return tuple(f"</{t}>" for t in self.tags)

    @property
    def tag(self) -> re.Pattern:
        return re.compile(rf"<({'|'.join(self.tags)})>([^<]*)</\1>")

    def user_text(self, case: Case) -> str:
        return f"{case.user}\n\n{self.block}"


# --- triage: the inbox, three tags, IMPORTANT / NOT IMPORTANT ------------------

def _email() -> Suite:
    from training.email.inbox import generate
    from training.email.tools import SCHEMA, answer
    from training.harness.agent_sim import SYSTEM
    from training.harness.generate_email_full import listing
    from training.harness.generate_email_protocol import INSTRUCTION

    def parse(text: str):
        t = text.upper()
        return False if "NOT IMPORTANT" in t else True if "IMPORTANT" in t else None

    def cases(n: int, seed: int) -> list[Case]:
        inbox = generate(n, seed)
        return [Case(id=m["id"], user=listing(m), ctx=inbox, truth=m["_truth"],
                     verify=(lambda said, t=m["_truth"]: said == t),
                     human=not m["_facts"]["automated"])
                for m in inbox["messages"]]

    def bar(cs: list[Case]) -> float:
        ht = [c.truth for c in cs if c.human]
        return max(sum(ht), len(ht) - sum(ht)) / len(ht) if ht else 0.0

    return Suite(name="email", system=SYSTEM, block=INSTRUCTION,
                 tags=("thread_history", "sender_stats", "message"), answer=answer,
                 positional=_positional(SCHEMA), parse=parse, cases=cases, bar=bar,
                 eval_seed=717171, eval_n=475)


# --- the desk: four tags, a free-text answer verified by substring ---------------

def _all_regions():
    from training.email.desk import REGIONS
    return REGIONS


def _desk(region: str = "commitment") -> Suite:
    from training.email.desk import correct, generate
    from training.email.desk_tools import SCHEMA, answer
    from training.harness.desk_sim import SYSTEM

    block = tools_to_instruction(SCHEMA, arity=True, enums=False)

    def cases(n: int, seed: int) -> list[Case]:
        # THE FIRST 240 OF `generate(960, 424242)` ARE P51'S CASES EXACTLY — the draw is
        # a deterministic prefix — so the target's 1.000 on `commitment` was measured on
        # a subset of what is scored here.
        return [Case(id=c["case_id"], user=c["prompt"], ctx=c["desk"], truth=c["answer"],
                     verify=(lambda said, cc=c: correct(cc, said)), human=True,
                     meta={"region": c["region"], "depth": c["depth"]})
                for c in generate(n, seed, regions=(region,) if region == "commitment_deep"
                                  else None or _all_regions())["cases"]
                if c["region"] == region]

    # A DATE HAS NO MAJORITY CLASS. The floor a target must clear on its own is 0 here
    # and the gate reduces to the paired test against the best expert — which is the
    # part of it that ever decided anything.
    return Suite(name=f"desk:{region}", system=SYSTEM, block=block,
                 tags=("inbox", "thread_history", "sender_stats", "message"), answer=answer,
                 positional=_positional(SCHEMA),
                 parse=lambda text: text.strip() or None,
                 # THE DEEP BAND IS ITS OWN GRID: generate(n, seed, regions=(deep,)) spreads
                 # n over four depths, so 240 cases is 60 per depth — the shallow band's
                 # size, and the power `bar.resolvable` priced at 0.92 for +0.10.
                 cases=cases, bar=lambda cs: 0.0, eval_seed=424242,
                 eval_n=240 if region == "commitment_deep" else 960)


# --- fluids: the region measured to fail — served, for once, the way its corpus taught ---

def _fluids() -> Suite:
    """The multitool fluids suite in CORPUS MODE.

    WHY IT EXISTS (milestone 7, arm 0b). `fluids-full` scored 11 of 90 **[ran]** P41 and
    became "the expert that reasons fails". Read where it happens, 74 of its 79 failures
    hold a number that came from nowhere and leave a tool result unused
    (`training/physics/result_use.py`) — and that run reached the expert through
    `tool_calls` / `role: "tool"`, while its corpus taught the result inline,
    `<calc>…</calc>= 4.2305`. Here everything is what `generate_fluids_full` wrote at the
    tag `v0.1-foundations`: the system prompt, the served turn built by *calling*
    `render_tools` over the same schema, the `:.6g` results, the `{"answer": x}` last line.
    """
    import json as _json

    from training.harness.openai_proxy import render_tools
    from training.physics import multitool
    from training.physics.headroom import correct
    from training.physics.tools import SCHEMA, ToolError as PhysicsToolError, answer as phys_answer
    from training.protocol import SYSTEM

    probe = "PROBE"
    served = render_tools([{"role": "user", "content": probe}], SCHEMA)[-1]["content"]
    assert served.startswith(probe + "\n\n"), "render_tools no longer appends the block after a blank line"
    block = served[len(probe) + 2:]

    def answer(handbook, tool: str, body: str) -> str:
        from training.email.tools import ToolError          # the loop catches this one
        try:
            return f"{phys_answer(tool, body, handbook):.6g}"
        except PhysicsToolError as e:
            raise ToolError(str(e)) from e

    def parse(text: str):
        m = re.search(r'\{\s*"answer"\s*:\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*\}', text or "")
        return float(m.group(1)) if m else None

    def cases(n: int, seed: int) -> list[Case]:
        # THE HANDBOOK IN THE SHAPE `lookup` READS. `generate` writes it JSON-shaped — a list
        # of [[fluid, T], row] — and handed over as it comes every lookup raises.
        return [Case(id=c["case_id"], user=c["prompt"],
                     ctx={tuple(k): v for k, v in c["handbook"]}, truth=c["answer"],
                     verify=(lambda said, w=c["answer"]: correct(said, w, 0.02)), human=True,
                     meta={"family": c["family"], "depth": len(c["chain"])})
                for c in multitool.generate(n, seed)]

    return Suite(name="fluids", system=SYSTEM, block=block, tags=("calc", "lookup", "convert"),
                 answer=answer, positional={}, parse=parse, cases=cases, bar=lambda cs: 0.0,
                 eval_seed=616161, eval_n=90, max_calls=12)


def load(name: str) -> Suite:
    if name == "fluids":
        return _fluids()
    if name == "email":
        return _email()
    if name.startswith("desk"):
        return _desk(name.split(":", 1)[1] if ":" in name else "commitment")
    raise ValueError(f"no suite named {name!r}")
