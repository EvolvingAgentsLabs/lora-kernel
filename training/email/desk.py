"""One inbox, several questions about it, each mechanically checkable.

WHY A NEW SUITE. `results/P50-suite-audit-20260916/` ran the seven gates against
every suite this project had measured on, and **all four failed**. The universal
failure was the worst one: **every region of every suite sat at exactly one depth**,
so *which domain* and *how long the chain is* were the same variable everywhere and
no arm could ever separate them.

WHAT THIS SUITE IS FOR, AND IT DECIDES THE SHAPE. The claim under test is that
**acceptance orders experts the way verified quality does** — the original question,
finally buildable now that a local same-family target exists **[ran]** P48. Testing
it needs **both** numbers on the same cases, so the task must have a **verifier**.
That rules out drafting, which is why this is a desk assistant answering checkable
questions rather than writing replies.

FOUR REGIONS, EVERY ONE GENERATED AT EVERY DEPTH. That is the whole point of the
construction: depth is varied by **how much is handed over**, independently of which
question is asked, so the grid is real rather than a diagonal.

    importance    is this message important?              -> yes / no
    owed          which message am I overdue to answer?   -> a message id
    commitment    what did I promise, and by when?        -> a date
    counterpart   who do I correspond with most here?     -> a name

THE REGION IS VISIBLE IN THE QUESTION, AND THAT IS DECLARED. `region_not_in_the_prompt`
will fail, and it should: a suite cannot both price a learned router and test
acceptance-as-ranking, and S3 is what happens when that is left ambiguous — its
routing arm tied exactly with a rule reading the region out of the prompt. **Ranking
was chosen, so region visibility is a property of this suite and not a defect of it.**

NOTHING DECISIVE IN THE LISTING. Every fact an answer depends on lives behind a tool;
`tests/test_desk.py` asserts it rather than trusting it, because P15 measured a suite
whose values could be recalled being answered 27/30 without calling anything.
"""

from __future__ import annotations

import random
import re

REGIONS = ("importance", "owed", "commitment", "counterpart")

FIRST = ["Ana", "Bruno", "Clara", "Diego", "Elena", "Facundo", "Gabriela", "Hugo",
         "Irene", "Joaquin", "Karina", "Lucas", "Marina", "Nicolas", "Paula"]
LAST = ["Alvarez", "Benitez", "Costa", "Duarte", "Esposito", "Ferreyra", "Gimenez",
        "Herrera", "Ibarra", "Juarez", "Lombardi", "Medina", "Navarro", "Ortiz"]
COMPANIES = ["nordwind", "kelvinlab", "arrayworks", "tallgrass", "pine-and-co"]
MONTHS = ["January", "March", "April", "June", "September", "November"]
SUBJECTS = ["the numbers", "next steps", "your note", "following up", "this week",
            "the draft", "quick one", "the handoff", "status", "a question"]
PREVIEW = "(the sender is waiting on a reply)"

#: How many tool calls the oracle needs. The SAME region appears at every depth,
#: which is the construction the audit said every previous suite lacked.
DEPTHS = (1, 2, 3, 4)


def _person(rng):
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    return name, f"{name.lower().replace(' ', '.')}@{rng.choice(COMPANIES)}.com"


def _desk(rng, n_threads: int, me: str) -> dict:
    """The inbox the questions are asked about. Facts live here, not in a prompt."""
    threads, senders, msgs = {}, {}, []
    for i in range(n_threads):
        name, addr = _person(rng)
        tid, mid = f"thr-{i:03d}", f"msg-{i:03d}"
        i_wrote = rng.random() < 0.5
        direct = rng.random() < 0.6
        asks = rng.random() < 0.55
        frequent = rng.random() < 0.4
        day, month = rng.randrange(1, 28), rng.choice(MONTHS)
        promised = rng.random() < 0.5
        body = []
        if i_wrote:
            body.append({"from": me, "to": [addr],
                         "preview": "(my earlier message in this thread)"})
        body.append({"from": addr, "to": [me] if direct else ["team@ownmail.com"],
                     "cc": [] if direct else [me],
                     "preview": ("Could you confirm this?" if asks
                                 else "Sharing for your records.")})
        if promised:
            body.append({"from": me, "to": [addr],
                         "preview": f"I will have it to you by {month} {day}."})
        threads[tid] = body
        senders[addr] = rng.randrange(6, 40) if frequent else rng.randrange(0, 2)
        msgs.append({
            "id": mid, "thread_id": tid, "from_name": name, "from": addr,
            "subject": rng.choice(SUBJECTS), "preview": PREVIEW,
            "_facts": {"i_wrote_in_thread": i_wrote, "addressed_directly": direct,
                       "asks_something": asks, "frequent_sender": frequent,
                       "automated": False, "promised": promised,
                       "due": f"{month} {day}" if promised else None},
        })
    return {"me": me, "messages": msgs, "threads": threads, "sent_counts": senders}


def _important(f: dict) -> bool:
    return sum(bool(f[k]) for k in ("i_wrote_in_thread", "addressed_directly",
                                    "asks_something", "frequent_sender")) >= 2


# --------------------------------------------------------------------------
# DEPTH IS HOW MUCH IS HANDED OVER, NOT WHICH QUESTION IS ASKED. Each builder
# receives the depth and gives away (4 - depth) of the facts in the prompt, so the
# same region spans the whole axis and the grid is not a diagonal.
# --------------------------------------------------------------------------

def _given(msg: dict, hide: int, region: str, desk: dict | None = None) -> str:
    """The INPUTS TO THIS REGION'S ANSWER that the prompt hands over.

    PER REGION, AND THE FIRST VERSION WAS NOT. It gave the four importance signals
    whatever the question was, so outside `importance` the "depth" reduced no work at
    all — the date still needed the same lookup at depth 1 as at depth 4. Depth would
    have been a label rather than a difficulty, and the grid would have been real in
    the metadata and fake in the cases. Caught before a session was spent on it.

    Never the answer itself: what is given are the facts the answer is computed FROM.
    """
    f = msg["_facts"]
    yn = lambda b: "yes" if b else "no"                                # noqa: E731
    if region == "importance":
        lines = [f"You wrote in this thread: {yn(f['i_wrote_in_thread'])}",
                 f"Addressed to you directly: {yn(f['addressed_directly'])}",
                 f"It asks something of you: {yn(f['asks_something'])}",
                 f"You correspond with this sender often: {yn(f['frequent_sender'])}"]
    elif region == "owed":
        lines = [f"It asks something of you: {yn(f['asks_something'])}",
                 f"Addressed to you directly: {yn(f['addressed_directly'])}",
                 f"You wrote in this thread: {yn(f['i_wrote_in_thread'])}",
                 f"The thread has {len(desk['threads'][msg['thread_id']])} messages"]
    elif region == "commitment":
        lines = [f"You made a promise in this thread: {yn(f['promised'])}",
                 f"The promise is yours, not the sender's: yes",
                 f"It is in the last message you wrote: yes",
                 f"The thread has {len(desk['threads'][msg['thread_id']])} messages"]
    elif region == "counterpart":
        # Facts about HOW to compute the answer, never about who it is. The first
        # version asserted "this sender is the most frequent one", which is the
        # answer wearing a hint.
        lines = [f"Frequency is counted over sent messages, not received: yes",
                 f"The inbox holds {len(desk['messages'])} threads",
                 f"Automated senders are excluded from the count: yes",
                 f"Ties do not occur in this inbox: yes"]
    else:
        raise ValueError(region)
    keep = lines[: max(0, len(lines) - hide)]
    return ("\nAlready established:\n" + "\n".join(f"  {x}" for x in keep)
            if keep else "")


def build(rng, region: str, depth: int, desk: dict) -> dict | None:
    me = desk["me"]
    if region == "importance":
        msg = rng.choice(desk["messages"])
        return {"region": region, "depth": depth, "answer": "yes" if _important(msg["_facts"]) else "no",
                "kind": "yes_no", "focus": msg["id"],
                "question": "Is this message important?",
                "given": _given(msg, depth, region, desk), "msg": msg}
    if region == "owed":
        # The one the user wrote in, that asks something, and has no later reply.
        owed = [m for m in desk["messages"]
                if m["_facts"]["asks_something"] and m["_facts"]["addressed_directly"]]
        if not owed:
            return None
        pick = rng.choice(owed)
        # THE FOCUS IS NOT THE ANSWER'S MESSAGE. Showing `Message msg-010` in a
        # prompt whose answer is `msg-010` is the answer wearing a listing — the
        # same leak `counterpart` had, found by the same test.
        others = [m for m in desk["messages"] if m["id"] != pick["id"]]
        if not others:
            return None
        focus = rng.choice(others)
        return {"region": region, "depth": depth, "answer": pick["id"],
                "kind": "id", "focus": focus["id"],
                "question": "Across this inbox, which message are you most overdue "
                            "to answer? Give its id.",
                "given": _given(pick, depth, region, desk), "msg": focus}
    if region == "commitment":
        due = [m for m in desk["messages"] if m["_facts"]["promised"]]
        if not due:
            return None
        pick = rng.choice(due)
        return {"region": region, "depth": depth, "answer": pick["_facts"]["due"],
                "kind": "date", "focus": pick["id"],
                "question": "What date did you commit to in this thread?",
                "given": _given(pick, depth, region, desk), "msg": pick}
    if region == "counterpart":
        best = max(desk["messages"], key=lambda m: desk["sent_counts"][m["from"]])
        # THE FOCUS IS NOT THE ANSWER'S MESSAGE, AND THE FIRST VERSION MADE IT SO.
        # Showing the winner's own listing put `From: Hugo Duarte` in the prompt for
        # a question whose answer was `Hugo Duarte` — the region would have scored
        # near 1.000 for both arms and saturated, which is P49's failure exactly.
        # Caught by `test_the_answer_is_never_given_away_in_the_prompt`.
        others = [m for m in desk["messages"] if m["from"] != best["from"]]
        if not others:
            return None
        focus = rng.choice(others)
        return {"region": region, "depth": depth, "answer": best["from_name"],
                "kind": "name", "focus": focus["id"],
                "question": "Across this whole inbox, who do you correspond with "
                            "most? Answer with their name.",
                "given": _given(focus, depth, region, desk), "msg": focus}
    raise ValueError(region)


def listing(case: dict) -> str:
    m = case["msg"]
    return (f"Message {m['id']} in thread {m['thread_id']}\n"
            f"From: {m['from_name']} <{m['from']}>\n"
            f"Subject: {m['subject']}\n"
            f"Preview: {m['preview']}\n"
            f"{case['given']}\n\n{case['question']}")


def generate(n: int, seed: int, me: str = "me@ownmail.com",
             regions: tuple[str, ...] = REGIONS,
             depths: tuple[int, ...] = DEPTHS) -> dict:
    """`n` cases spread over the **full region x depth grid**, not a diagonal."""
    rng = random.Random(seed)
    grid = [(r, d) for r in sorted(regions) for d in sorted(depths)]
    desk = _desk(rng, 24, me)
    cases = []
    i = 0
    while len(cases) < n:
        region, depth = grid[i % len(grid)]
        i += 1
        if i % 40 == 0:
            desk = _desk(rng, 24, me)       # a fresh inbox, so nothing memorises
        c = build(rng, region, depth, desk)
        if c is None:
            continue
        c |= {"case_id": f"dk-{len(cases):04d}", "desk": desk}
        c["prompt"] = listing(c)
        cases.append(c)
    return {"cases": cases, "me": me}


def tools_needed(case: dict) -> list[str]:
    """Which tools the oracle has to call, given what the prompt already gave away.

    `owed` and `counterpart` ask about the WHOLE inbox while the listing shows one
    message, so they start with `inbox` — without it a model cannot learn that
    `msg-007` exists and both regions would be unanswerable for every arm. See
    `desk_tools.py`.
    """
    need = {
        "importance": ["thread_history", "sender_stats", "message"],
        "owed": ["inbox", "message", "thread_history", "sender_stats"],
        "commitment": ["thread_history", "message", "sender_stats"],
        "counterpart": ["inbox", "sender_stats", "thread_history", "message"],
    }[case["region"]]
    return need[: max(1, case["depth"])]


MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def dates_in(text: str) -> set[tuple[int, int]]:
    """Every (month, day) a text names, in any shape a model writes.

    A DATE IS A DATE IN ANY SHAPE. The first verifier was a literal substring, and
    P55b measured what that costs: the 32B answered `2023-01-05` for a truth of
    `January 5` on 5 of its 13 "wrong" cases — right date, other shape — and the
    gate read them as the target being weaker **[ran]** 2026-09-17. A check that
    fails while the capability works measures phrasing; this repository deletes such
    checks rather than loosening them. `September 6`, `Sep 6`, `6 September`,
    `2023-09-06` and `September 6th` are the same answer.
    """
    out = set()
    for m in re.finditer(r"\b(?:20\d\d)-(\d{1,2})-(\d{1,2})\b", text):
        out.add((int(m.group(1)), int(m.group(2))))
    for m in re.finditer(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", text):
        mo = _month(m.group(1))
        if mo:
            out.add((mo, int(m.group(2))))
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]{3,9})\b", text):
        mo = _month(m.group(2))
        if mo:
            out.add((mo, int(m.group(1))))
    return out


def _month(word: str) -> int | None:
    w = word.lower()
    for i, name in enumerate(MONTHS, 1):
        if name.startswith(w[:3]) and (len(w) <= 3 or name.startswith(w)):
            return i
    return None


def correct(case: dict, said: str | None) -> bool:
    """Mechanical, and the same function the corpus and the scorer both use."""
    if not said:
        return False
    if case.get("kind") == "date" or _looks_like_date(case["answer"]):
        want = dates_in(case["answer"])
        return bool(want) and bool(want & dates_in(said))
    return case["answer"].lower() in said.lower()


def _looks_like_date(answer: str) -> bool:
    return bool(dates_in(answer))
