"""What a suite has to satisfy before a number measured on it means anything.

WHY THIS EXISTS. The report of 2026-09-16 (`docs/REPORT.md` at the tag `v0.1-foundations`; its findings are `docs/RECORD.md` §3) lined up every negative result of the last ten
days and found the same thing underneath almost all of them: **the suite was wrong,
not the architecture**. Seven distinct ways, each paid for:

    S3   the prompt already named the region the router was meant to infer
    P13  one tool, so asking for it was copying an expression already written
    P42  the base was already at the ceiling — 0.815 against the adapter's 0.825
    P45  the suite had no difficulty axis at all; its floor was six steps
    P46  the input could not support ranking; 69-82% of a gap was the ceiling
    P1   twelve keywords separated the regions 1.000 of the time
    P49  one region of three was saturated for both arms

Each was found **after** a run, by hand, by someone remembering to look. The
report's own recommendation was to stop doing that:

> *Make the headroom check a gate in the runner, not a habit. A step that cannot
> state its ceiling should not be launchable.*

This is that gate. **A suite either passes it or its numbers are not evidence.**

WHAT IT CANNOT DO, STATED FIRST. Four of the seven checks need a model — a suite's
ceiling is a property of the suite *and the model*, and no amount of reading the
generator reveals it. Those return `needs_model` rather than a verdict, and the
runner that has a model fills them in. Pretending otherwise would be the same class
of mistake this module exists to catch.

AND THE DEEPEST ONE IS NOT HERE. The report's last finding was that **a generated
suite cannot contain a difficulty its author did not think of**. No gate over a
generator can see that, because the gate has the same author. The answer to it is
not a check — it is letting the *base model* choose where the difficulty is, which
is what `profile` is for.
"""

from __future__ import annotations

import collections
import difflib
import re
from dataclasses import dataclass, field


@dataclass
class Finding:
    gate: str
    passed: bool | None          # None = needs a model
    detail: str
    value: float | None = None
    #: Why this suite is allowed to fail this gate. A WAIVER IS NOT A PASS and it is
    #: not silence: it prints, it names the purpose it was granted for, and it can
    #: only be set deliberately. The alternative is a gate that gets ignored by
    #: habit, and a gate ignored by habit has stopped being a gate.
    waived_for: str | None = None


@dataclass
class Report:
    name: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        """False if any gate that COULD be decided was failed and not waived."""
        return all(f.passed is not False or f.waived_for
                   for f in self.findings)

    @property
    def waived(self) -> list[str]:
        return [f.gate for f in self.findings if f.waived_for]

    @property
    def undecided(self) -> list[str]:
        return [f.gate for f in self.findings if f.passed is None]

    def table(self) -> str:
        rows = [f"{self.name}"]
        for f in self.findings:
            mark = {True: "pass", False: "FAIL", None: "needs a model"}[f.passed]
            if f.waived_for:
                mark = "WAIVED"
            v = "" if f.value is None else f"  {f.value:.3f}"
            rows.append(f"  {mark:14} {f.gate:26}{v}  {f.detail}")
            if f.waived_for:
                rows.append(f"  {'':14} {'':26}  waived for: {f.waived_for}")
        return "\n".join(rows)


# --------------------------------------------------------------------------
# The three gates a generator can answer on its own.
# --------------------------------------------------------------------------

def region_not_in_the_prompt(cases: list[dict], region_of, prompt_of,
                             rule=None) -> Finding:
    """S3 and P1. Can the region be read off the prompt instead of inferred?

    S3's routing arm tied exactly with a rule reading `clinic:` out of the text, so
    the mechanism was real and the suite could not price it. P1 then measured a
    coarse route at **1.000** with twelve keywords. A suite whose prompt names the
    region cannot test a router; it can only test whether we can read.
    """
    if rule is None:
        rule = _lexical_rule(cases, region_of, prompt_of)
    hit = sum(rule(prompt_of(c)) == region_of(c) for c in cases)
    acc = hit / max(len(cases), 1)
    regions = {region_of(c) for c in cases}
    chance = 1 / max(len(regions), 1)
    # HALFWAY FROM CHANCE TO PERFECT, NOT A MULTIPLE OF CHANCE. The first version
    # failed a suite at `2 * chance`, which for TWO regions is 1.000 — a threshold
    # that can never fire. Email triage recovered its region 0.940 of the time
    # against 0.500 chance and passed **[ran]** 2026-09-16. A gate with a blind spot
    # at the commonest case is worse than no gate.
    limit = chance + (1 - chance) * 0.5
    ok = acc < limit
    return Finding("region_not_in_the_prompt", ok,
                   f"a keyword rule recovers the region {acc:.3f} of the time "
                   f"against {chance:.3f} chance over {len(regions)} regions "
                   f"(limit {limit:.3f})",
                   acc)


def has_a_difficulty_axis(cases: list[dict], depth_of) -> Finding:
    """P45. Does the suite contain more than one difficulty?

    Its oracle solutions were 6, 7 or 9 steps with **no case below six**, and each
    family was pinned at exactly one depth — so depth and family were the same
    variable and *too weak* could not be told from *too hard*.
    """
    depths = collections.Counter(depth_of(c) for c in cases)
    spread = len(depths)
    ok = spread >= 3
    return Finding("has_a_difficulty_axis", ok,
                   f"{spread} distinct depths {dict(sorted(depths.items()))}",
                   float(spread))


def depth_is_not_the_region(cases: list[dict], region_of, depth_of) -> Finding:
    """P45's other half. If every region sits at one depth they are one variable.

    This is the check that would have caught the fluids suite before it ran: four
    families, each pinned at a single oracle depth, so no arm could separate the
    physics from the length of the chain.
    """
    by_region = collections.defaultdict(set)
    for c in cases:
        by_region[region_of(c)].add(depth_of(c))
    pinned = [r for r, d in by_region.items() if len(d) == 1]
    ok = not pinned
    return Finding("depth_is_not_the_region", ok,
                   ("every region spans several depths" if ok else
                    f"{len(pinned)} of {len(by_region)} regions sit at one depth: "
                    f"{sorted(pinned)[:4]}"),
                   len(pinned) / max(len(by_region), 1))


def the_answer_is_not_a_copy(cases: list[dict], prompt_of, answer_of) -> Finding:
    """P13's question for a task with no tool calls: is the answer already there?

    P13 measured a learned protocol losing 9/30 to twenty lines of `re`, because the
    suite had one tool and asking for it meant **copying an expression already
    written**. The gate above asks that of a tool surface. A completion task has no
    tools, and the same failure has a different face: if the text to be produced is a
    verbatim run of the text already shown, the model is transcribing rather than
    solving — and a transcription suite cannot rank experts.

    Measured as the **longest common run** between the prompt and the answer, as a
    fraction of the answer. It is the generous reading: one long shared run is the
    strongest evidence of copying, and short incidental matches are ignored.
    """
    worst = 0.0
    for c in cases:
        a = (answer_of(c) or "").strip()
        if not a:
            continue
        sm = difflib.SequenceMatcher(None, prompt_of(c), a, autojunk=False)
        m = sm.find_longest_match(0, len(prompt_of(c)), 0, len(a))
        worst = max(worst, m.size / len(a))
    ok = worst < 0.60
    return Finding("the_answer_is_not_a_copy", ok,
                   f"the most copy-like case shares {worst:.3f} of its answer as one "
                   f"run with its prompt", worst)


def asking_is_a_decision(cases: list[dict], tools_of) -> Finding:
    """P13. With one tool, asking for it is copying an expression already written.

    A learned protocol scored 9/30 where twenty lines of `re` scored 23/30, and the
    reason was the suite: one tool, and the call was a copy. A protocol has to be
    tested where the model must CHOOSE which tool and build keyed arguments.
    """
    counts = collections.Counter(len(set(tools_of(c))) for c in cases)
    distinct = {t for c in cases for t in tools_of(c)}
    multi = sum(n for k, n in counts.items() if k >= 2)
    share = multi / max(len(cases), 1)
    ok = len(distinct) >= 3 and share >= 0.5
    return Finding("asking_is_a_decision", ok,
                   f"{len(distinct)} tools in the suite; {share:.3f} of cases need "
                   f"two or more", share)


# --------------------------------------------------------------------------
# The four that need a model, declared rather than guessed.
# --------------------------------------------------------------------------

MODEL_GATES = {
    "base_not_at_the_ceiling":
        "P42: the base scored 0.815 where the adapter scored 0.825. Run the base "
        "first; a suite it already passes cannot show a treatment anything.",
    "base_not_on_the_floor":
        "P45's mirror: if every case is above the treatment's floor every arm "
        "fails and the failure reads as 'the approach does not work'.",
    "no_region_is_saturated":
        "P49: `team` scored 1.000 against the base's 0.967 while the other two had "
        "room. A saturated region dilutes every average it enters.",
    "the_input_can_support_ranking":
        "P46: group the cases by what a predictor can see; if one group holds them "
        "all, the best possible confidence is a constant and orders nothing.",
}


def model_gates() -> list[Finding]:
    return [Finding(k, None, v) for k, v in MODEL_GATES.items()]


# --------------------------------------------------------------------------

def _lexical_rule(cases, region_of, prompt_of, per_region: int = 8):
    """The strongest keyword rule a reader of the generator could write.

    GENEROUS ON PURPOSE. A weak baseline would let a leaky suite through, and the
    conclusion this gate supports — *the region is readable, so the suite cannot
    price a router* — is the one a generous baseline makes harder to dodge.
    """
    words = collections.defaultdict(collections.Counter)
    everywhere = collections.Counter()
    for c in cases:
        toks = set(re.findall(r"[a-z][a-z-]{2,}", prompt_of(c).lower()))
        words[region_of(c)].update(toks)
        everywhere.update(toks)
    keys = {}
    for region, counter in words.items():
        # tokens this region uses and the others do not
        own = [(n / max(everywhere[t], 1), t) for t, n in counter.items()]
        keys[region] = [t for _, t in sorted(own, reverse=True)[:per_region]]

    def rule(text: str) -> str:
        t = text.lower()
        n, best = max((sum(t.count(k) for k in ks), r) for r, ks in keys.items())
        return best if n else "?"

    return rule


def inspect(name: str, cases: list[dict], *, region_of, prompt_of, depth_of,
            tools_of=None, answer_of=None,
            waive: dict[str, str] | None = None) -> Report:
    """Every gate a generator can answer, plus the four that wait for a model.

    `waive` maps a gate name to **the purpose it is waived for**, and the reason is
    required rather than optional. A suite cannot both price a learned router and
    test acceptance-as-ranking: the router needs the region hidden, ranking does
    not care. S3 is what happens when that is left ambiguous — its routing arm tied
    exactly with a rule reading the region out of the prompt. Choosing one and
    saying so is the difference between a waiver and an excuse.
    """
    waive = waive or {}
    for g in waive:
        if g not in {"region_not_in_the_prompt", "has_a_difficulty_axis",
                     "depth_is_not_the_region", "asking_is_a_decision",
                     "the_answer_is_not_a_copy"}:
            raise ValueError(f"{g!r} is not a gate a generator can decide")
    findings = [
        region_not_in_the_prompt(cases, region_of, prompt_of),
        has_a_difficulty_axis(cases, depth_of),
        depth_is_not_the_region(cases, region_of, depth_of),
        # EXACTLY ONE OF THESE APPLIES, chosen by the task's shape rather than by
        # preference. A tool-calling suite is asked whether choosing a tool is a
        # decision; a completion suite is asked whether the answer is already in the
        # prompt. Offering both and waiving one would be a gate ignored by habit.
        (asking_is_a_decision(cases, tools_of) if tools_of is not None
         else the_answer_is_not_a_copy(cases, prompt_of, answer_of)),
        *model_gates(),
    ]
    for f in findings:
        if f.gate in waive and f.passed is False:
            f.waived_for = waive[f.gate]
    return Report(name, findings)
