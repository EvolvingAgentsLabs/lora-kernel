"""A day's inbox, and a definition of "important" that cannot be read off a preview.

WHY THIS DOMAIN. The architecture's claim only pays where there is a **region**: a
narrow task repeated daily. Triaging one person's morning mail is that, and it has a
property fluid mechanics did not — **the right answer is mechanically checkable**, so
a verifier exists without a judge, which is what S7's tournament still lacks.

THE DEFINITION, AND IT IS A DEFINITION RATHER THAN A GUESS. A message is important
when at least two of these hold:

    it continues a thread I wrote in       — someone answered me
    it is addressed to me directly         — To:, not Cc:
    it asks something of me                — a question, or an ask with a date
    the sender is a frequent counterpart   — we have real history

and never, whatever else is true, when it is automated — a list, a no-reply, a
notification.

THE LESSON FROM P15 IS BUILT IN. There, a suite whose values could be memorised was
answered without the tools at all — 27/30 — and the experiment measured nothing until
a per-case handbook made recall impossible. So here **the two decisive facts are not
in the preview**: whether I wrote in the thread lives in the thread's history, and
whether the sender is frequent lives in a counter. A model that only reads the inbox
listing cannot do better than guessing, and `tests/test_email.py` asserts exactly
that rather than trusting it.
"""

from __future__ import annotations

import random

FIRST = ["Ana", "Bruno", "Clara", "Diego", "Elena", "Facundo", "Gabriela", "Hugo",
         "Irene", "Joaquin", "Karina", "Lucas", "Marina", "Nicolas", "Paula"]
LAST = ["Alvarez", "Benitez", "Costa", "Duarte", "Esposito", "Ferreyra", "Gimenez",
        "Herrera", "Ibarra", "Juarez", "Lombardi", "Medina", "Navarro", "Ortiz"]
COMPANIES = ["nordwind", "kelvinlab", "arrayworks", "tallgrass", "pine-and-co"]

ASKS = ["Can you confirm the numbers before Thursday?",
        "Could you review this and tell me what you think?",
        "Do you have the signed copy? I need it for Friday.",
        "Would you be able to join the call on Tuesday?",
        "What should I tell them about the deadline?"]
STATEMENTS = ["Sharing this for your records, no action needed.",
              "FYI, we shipped it yesterday.",
              "Notes from the meeting are attached.",
              "Adding you for visibility.",
              "Here is the summary I promised."]
# Neutral openings. They say nothing about whether the message asks for anything.
PREVIEWS = ["Hi — quick note about this.", "Hello, following up here.",
            "Hi, one thing on this thread.", "Hey — see below.",
            "Good morning, on the item we discussed."]
PREVIEW_AUTOMATED = "This is an automated message."

AUTOMATED = [("noreply@{c}.com", "Your weekly usage report"),
             ("notifications@{c}.com", "3 new comments on your board"),
             ("digest@{c}.com", "This week in {c}"),
             ("billing@{c}.com", "Invoice 4821 is available")]


def _person(rng) -> tuple[str, str]:
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    handle = name.lower().replace(" ", ".")
    return name, f"{handle}@{rng.choice(COMPANIES)}.com"


def important(facts: dict) -> bool:
    """The definition, in one place, used by the generator and by the scorer."""
    if facts["automated"]:
        return False
    signals = (facts["i_wrote_in_thread"], facts["addressed_directly"],
               facts["asks_something"], facts["frequent_sender"])
    return sum(bool(s) for s in signals) >= 2


def generate(n: int, seed: int, me: str = "me@ownmail.com") -> dict:
    """One morning's inbox: the listing, the threads behind it, and the truth."""
    rng = random.Random(seed)
    messages, threads, sent_counts = [], {}, {}

    for i in range(n):
        mid = f"msg-{i:03d}"
        tid = f"thr-{i:03d}"
        automated = rng.random() < 0.25
        if automated:
            addr_t, subj_t = rng.choice(AUTOMATED)
            company = rng.choice(COMPANIES)
            sender_name = company
            sender = addr_t.format(c=company)
            subject = subj_t.format(c=company)
            body = "This is an automated message."
            facts = {"automated": True, "i_wrote_in_thread": False,
                     "addressed_directly": False, "asks_something": False,
                     "frequent_sender": False}
            history = [{"from": sender, "to": [me], "preview": body}]
        else:
            sender_name, sender = _person(rng)
            i_wrote = rng.random() < 0.45
            direct = rng.random() < 0.55
            asks = rng.random() < 0.5
            frequent = rng.random() < 0.4
            body = rng.choice(ASKS if asks else STATEMENTS)
            # `Re:` IS NOT A TELL, AND THE FIRST DRAFT MADE IT ONE. It was written
            # exactly when the user had replied, so a rule reading the subject line
            # recovered a decisive fact for free and `test_the_listing_alone…`
            # reached 0.795 against a 0.520 bar — P15's fault, caught by its own
            # test before a GPU saw it [ran] 2026-09-14. A thread carries `Re:`
            # whenever anyone has replied, which is most of them.
            subject = ("Re: " if rng.random() < 0.5 else "") + rng.choice(
                ["the Q3 numbers", "contract draft", "next week", "the migration",
                 "your note", "budget review", "the handoff"])
            facts = {"automated": False, "i_wrote_in_thread": i_wrote,
                     "addressed_directly": direct, "asks_something": asks,
                     "frequent_sender": frequent}
            history = []
            if i_wrote:
                history.append({"from": me, "to": [sender],
                                "preview": "(my earlier message in this thread)"})
            history.append({"from": sender,
                            "to": [me] if direct else ["team@ownmail.com"],
                            "cc": [] if direct else [me], "preview": body})
            sent_counts[sender] = rng.randrange(6, 40) if frequent else rng.randrange(0, 2)

        threads[tid] = history
        messages.append({
            # THE LISTING IS DELIBERATELY THIN. Whether I wrote in the thread and
            # whether the sender is frequent are NOT here — they are what the tools
            # are for, and putting them here would repeat P15's fault.
            "id": mid, "thread_id": tid, "from_name": sender_name,
            "from": sender, "subject": subject,
            # AND THE PREVIEW DOES NOT CARRY THE ASK EITHER. Showing the body put a
            # question mark in the listing exactly when the message asked for
            # something — the second leak the same test found. The ask lives behind
            # `message`, which is what that tool is for.
            "preview": PREVIEW_AUTOMATED if automated else rng.choice(PREVIEWS),
            "_truth": important(facts), "_facts": facts,
        })

    return {"me": me, "messages": messages, "threads": threads,
            "sent_counts": sent_counts}
