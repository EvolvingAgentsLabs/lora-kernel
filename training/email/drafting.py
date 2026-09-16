"""Reply drafting over one inbox, in three temáticas that share a person's day.

WHY THIS SUITE EXISTS. The pool's two members are fluid mechanics and inbox triage,
which never co-occur — and the proof is a number first reported as good news: twelve
keywords pick the right one **1.000** of the time **[ran]**. A discrimination problem
solved by twelve keywords is not a test of expert selection. These three are
deliberately **close**: all three are reply drafting, all three land in one inbox on
the same morning, and the tools are identical. **Only the policy differs.**

THERE IS NO MECHANICAL VERIFIER FOR A DRAFT, AND THAT IS THE POINT. No rule says a
reply is good, which is where S7's tournament has always stalled. The metric is
speculative **acceptance** against a larger target, which needs no judge.

BUT ACCEPTANCE ALONE CANNOT SEE AN EXPERT THAT MIMICS STYLE AND SAYS NOTHING. So every
case carries `must_carry`: the facts a correct reply has to contain — the date asked
for, the reference number, the amount. Checking for them is mechanical, it is a
**floor rather than a quality score**, and it is the guard that keeps *both wrote
nothing* from reading as agreement.

AND THE DECISIVE FACTS STAY BEHIND THE TOOLS. P15 measured a suite whose values could
be recalled being answered 27/30 without calling anything. Here the reference number,
the amount and the deadline live in the thread and the sender's history — never in the
listing — so `tests/test_drafting.py` asserts the listing alone cannot produce a
compliant draft, rather than trusting that it cannot.
"""

from __future__ import annotations

import random

TOPICS = ("client", "team", "vendor")

FIRST = ["Ana", "Bruno", "Clara", "Diego", "Elena", "Facundo", "Gabriela", "Hugo",
         "Irene", "Joaquin", "Karina", "Lucas", "Marina", "Nicolas", "Paula"]
LAST = ["Alvarez", "Benitez", "Costa", "Duarte", "Esposito", "Ferreyra", "Gimenez",
        "Herrera", "Ibarra", "Juarez", "Lombardi", "Medina", "Navarro", "Ortiz"]
COMPANIES = ["nordwind", "kelvinlab", "arrayworks", "tallgrass", "pine-and-co"]

# SUBJECTS THAT DO NOT NAME THE TEMATICA. A subject line reading `Invoice 4471` would
# hand a keyword rule the answer, and the whole design is about the regime where the
# prompt does NOT carry it. These are the deliberately bland lines a real thread has.
SUBJECTS = ["the numbers", "next steps", "your note", "following up", "this week",
            "the draft", "quick one", "re: our call", "the handoff", "status"]

MONTHS = ["January", "March", "April", "June", "September", "November"]


def _person(rng):
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    return name, f"{name.lower().replace(' ', '.')}@{rng.choice(COMPANIES)}.com"


def _client(rng):
    ref = f"Q-{rng.randrange(1000, 9999)}"
    day = rng.randrange(1, 28)
    month = rng.choice(MONTHS)
    amount = f"{rng.randrange(4, 90)},{rng.randrange(100, 999)}"
    facts = {"reference": ref, "deadline": f"{month} {day}", "amount": amount}
    # EVERY FACT `must_carry` ASKS FOR IS SOMEWHERE IN THIS THREAD, and nowhere in
    # the listing. The first draft put the deadline and the amount only in `facts`,
    # so no arm could ever have produced a compliant reply and every one of them
    # would have scored zero on two of three — a suite that makes the model look
    # broken because the suite is. Caught before it ran; `tests/test_drafting.py`
    # now asserts the property rather than trusting it.
    history = [
        {"role": "them",
         "text": f"We reviewed quote {ref}. Before we sign we need the delivery "
                 f"date confirmed and the figure held."},
        {"role": "me",
         "text": f"Approved internally at {amount}. Waiting on logistics for a date."},
        {"role": "them",
         "text": f"Logistics said {month} {day}. Can you confirm that back to us?"},
    ]
    must = [ref, f"{month} {day}", amount]
    return history[-1]["text"], facts, history, must


def _team(rng):
    ticket = f"ENG-{rng.randrange(100, 999)}"
    day = rng.randrange(1, 28)
    month = rng.choice(MONTHS)
    owner = rng.choice(FIRST)
    facts = {"reference": ticket, "deadline": f"{month} {day}", "owner": owner}
    history = [
        {"role": "them",
         "text": f"{ticket} is blocked on the migration. Who picks it up?"},
        {"role": "me",
         "text": f"{owner} has capacity from next sprint; {ticket} was cut from "
                 f"last week's batch."},
        {"role": "them",
         "text": f"Fine. The migration window closes {month} {day} — does it land "
                 f"before that?"},
    ]
    must = [ticket, f"{month} {day}", owner]
    return history[-1]["text"], facts, history, must


def _vendor(rng):
    inv = f"INV-{rng.randrange(10000, 99999)}"
    day = rng.randrange(1, 28)
    month = rng.choice(MONTHS)
    amount = f"{rng.randrange(1, 40)},{rng.randrange(100, 999)}"
    facts = {"reference": inv, "deadline": f"{month} {day}", "amount": amount}
    history = [
        {"role": "them",
         "text": f"Invoice {inv} is outstanding. Please confirm a payment date."},
        {"role": "me",
         "text": f"{inv} is with finance for {amount}."},
        {"role": "them",
         "text": f"Our terms close {month} {day}. Confirm that and return the "
                 f"signed copy."},
    ]
    must = [inv, f"{month} {day}", amount]
    return history[-1]["text"], facts, history, must


BUILDERS = {"client": _client, "team": _team, "vendor": _vendor}

INSTRUCTION = (
    "Draft a reply to this message. Use the tools to read the thread and what is "
    "known about the sender before you write. The reply must answer what was asked "
    "and name every concrete detail it depends on."
)


def generate(n: int, seed: int, me: str = "me@ownmail.com",
             topics: tuple[str, ...] = TOPICS) -> dict:
    """`n` threads spread evenly over the temáticas, with the facts behind tools."""
    rng = random.Random(seed)
    cases, threads, senders = [], {}, {}
    names = sorted(topics)
    for i in range(n):
        topic = names[i % len(names)]
        sender_name, sender = _person(rng)
        body, facts, history, must = BUILDERS[topic](rng)
        cid, tid = f"drf-{i:04d}", f"thr-{i:04d}"
        threads[tid] = [
            {"from": sender if h["role"] == "them" else me,
             "to": [me] if h["role"] == "them" else [sender],
             "preview": h["text"]} for h in history
        ]
        senders[sender] = {"threads": rng.randrange(2, 30), "topic": topic}
        cases.append({
            "case_id": cid, "thread_id": tid, "topic": topic,
            # THE LISTING IS THIN ON PURPOSE. The subject does not name the
            # temática and the preview does not carry the reference, the amount or
            # the deadline — those are what the tools are for, and putting them here
            # would repeat P15's fault with a new face.
            "from_name": sender_name, "from": sender,
            "subject": rng.choice(SUBJECTS),
            "preview": "(the sender is waiting on a reply)",
            "prompt": None,           # filled by `render`
            "_facts": facts, "must_carry": must,
        })
        cases[-1]["prompt"] = render(cases[-1])
    return {"me": me, "cases": cases, "threads": threads, "senders": senders}


def render(case: dict) -> str:
    return (f"Message {case['case_id']} in thread {case['thread_id']}\n"
            f"From: {case['from_name']} <{case['from']}>\n"
            f"Subject: {case['subject']}\n"
            f"Preview: {case['preview']}\n\n"
            f"{INSTRUCTION}")


def carries(draft: str, must: list[str]) -> dict:
    """How much of what the reply depends on actually appears in it.

    A FLOOR, NOT A SCORE. It does not say the draft is good; it says the draft is not
    fluent nothing. That is the failure speculative acceptance cannot see, because two
    models can agree at length on a reply that commits to no date and names no
    reference.
    """
    present = [m for m in must if m.lower() in (draft or "").lower()]
    return {"found": len(present), "needed": len(must),
            "complete": len(present) == len(must),
            "missing": [m for m in must if m not in present]}
