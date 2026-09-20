r"""W5d — the answer policy: who writes the final line, decided from the request alone.

W5, W5b and W5c **[ran]** say one thing three ways. The adapter NAVIGATES a procedure it never
trained on (42 : 0 against the untrained base made to walk; 0 retrieval misses) and carries it; it
does not READ a value stated under a condition in a note it never saw (0/11, then 4/15 after a corpus
that showed the shape over eight notes) where the untrained base reads 15/15. Letting the base write
EVERY final line is not a serving design: it gives back 19 control cases (W5b).

So the policy splits by KIND OF TASK, as a rule a role pack can carry (docs/FRAMEWORK.md §4, §6):

    the adapter WALKS, always
    carry   report the last step carried out — or say it is not in the library   → the ADAPTER writes
    rate    a rate computed from an order                                         → the ADAPTER writes
    value   a quantity read off a note, plain or under a condition               → the BARE BASE writes,
            from the pages the adapter's walk opened, served the way `base-reads` is served

WHY `rate` STAYS WITH THE ADAPTER — decided from the trained band only, before any new case was drawn.
A rate is not read, it is computed, and the adapter computes it through the `<calc>` verb: on the
CONTROL sets (the trained distribution; the held-out procedure has no rate step at all) the adapter is
15/15 (W5) and 12/12 (W5c), the base handed the same notes 7/15 and 5/12, and composition — the base
writing the line — 7/15 (W5b). No held-out number was used for this choice; there is none to use.

DECIDABLE WITHOUT THE GRADER'S LABELS. An evaluation row's `family` does not exist at serving time.
`kind()` reads the STATEMENT and nothing else: the form of answer the request itself asks for.

WHAT ITS AGREEMENT IS WORTH, said before it is quoted. These statements are written by a generator
whose last sentence names the answer form, so `kind()` recovers it exactly — agreement 1.0 measures
that the rule is wired to the corpus's wording, NOT that a live request can be classified. *A model of
a generated corpus learns the generator* applies to a regex too. A deployment states the answer form in
the role pack's task schema, or pays for a classifier and measures it on real asks; this file does
neither and says so.

FROZEN. The table and the patterns below were committed before the W5d evaluation sets were written;
the brief cites the commit. Changing either afterwards is a redesign and is counted.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

WRITER = {"carry": "adapter", "rate": "adapter", "value": "base"}

# The answer form the request asks for, in its own closing words. Order matters only for clarity: the
# three patterns are disjoint on every statement the generators write (asserted by `agreement`).
_RATE = re.compile(r"\bwhat (?:rate )?is set, in\b|\banswer with a whole number and its unit\b", re.I)
_VALUE = re.compile(r"\banswer with the quantity and its unit\b", re.I)
_CARRY = re.compile(r"\breport the last step you carried out\b", re.I)

# family (the generator's label, never seen at serving time) → the kind it should be read as
KIND_OF_FAMILY = {"carry": "carry", "none": "carry", "rate": "rate", "quantity": "value", "conditional": "value"}


def kind(statement: str) -> str:
    """carry | rate | value — from the statement alone. An ask that names no form is `carry`: the
    adapter answers, which is what happens today with no policy at all."""
    hits = [k for k, pat in (("rate", _RATE), ("value", _VALUE), ("carry", _CARRY)) if pat.search(statement)]
    if len(hits) > 1:
        raise ValueError(f"the statement asks for two answer forms {hits}: {statement[-120:]!r}")
    return hits[0] if hits else "carry"


def writer(statement: str) -> str:
    return WRITER[kind(statement)]


def agreement(paths: list[Path]) -> dict:
    """Zero GPU: `kind(statement)` against the generator's `family`, on rows nobody evaluates."""
    out = {}
    for p in paths:
        rows = [json.loads(l) for l in Path(p).read_text().splitlines()]
        wrong = [r["case_id"] for r in rows if kind(r["statement"]) != KIND_OF_FAMILY[r["family"]]]
        named = sum(bool(_RATE.search(r["statement"]) or _VALUE.search(r["statement"]) or _CARRY.search(r["statement"]))
                    for r in rows)
        kinds = {}
        for r in rows:
            kinds[kind(r["statement"])] = kinds.get(kind(r["statement"]), 0) + 1
        out[str(p)] = {"rows": len(rows), "agree": len(rows) - len(wrong), "agreement": round(1 - len(wrong) / len(rows), 4),
                       "disagree": wrong[:10], "statements_that_name_a_form": named, "kinds": kinds}
    return out


if __name__ == "__main__":
    import sys
    paths = [Path(a) for a in sys.argv[1:]] or [Path("training/nursing/data_walks_v2/train.jsonl"),
                                                Path("training/nursing/data_walks/train.jsonl")]
    print(json.dumps(agreement(paths), indent=1))
